import http.server, socketserver, json, urllib.parse, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import Database
from core.events import EventBus
from core.openapi import RouteRegistry
from core.webhooks import WebhookDispatcher
from core.models import init_all_schemas
import uuid

PORT = 3000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
db = Database(f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'suite.db')}")
events = EventBus()
webhook_dispatcher = WebhookDispatcher(db)

with db.get_connection() as conn:
    init_all_schemas(conn)
    # Seed inicial se necessário
    if conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 0:
        conn.executescript("""
            INSERT INTO leads (nome, email, telefone, empresa, score, status, valor_estimado) VALUES
            ('Carlos Eduardo Mendes', 'carlos@techcorp.com.br', '5511988887777', 'TechCorp Brasil', 95, 'qualificado', 18500.0),
            ('Dra. Helena Castro', 'helena@biomed.med.br', '5541999991111', 'BioMed Lab', 98, 'ganho', 75000.0);

            INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome) VALUES
            ('Contrato Fechado: BioMed Lab', 'receita', 'Contratos CRM', 75000.0, '2026-09-15', 'pago', 'BioMed Lab'),
            ('Infraestrutura Cloud Hetzner', 'despesa', 'Servidores', 1250.0, '2026-09-05', 'pago', 'Hetzner Online');

            INSERT INTO tickets (protocolo, assunto, descricao, cliente_nome, cliente_email, prioridade, status, sla_limite_horas) VALUES
            ('TICK-A92B1C', 'Configuração de Webhook n8n', 'Suporte à integração da esteira de vendas.', 'Rafael Souza', 'rafael@empresa.com', 'P1', 'aberto', 2);

            INSERT INTO cursos (titulo, descricao, categoria, thumbnail) VALUES
            ('Engenharia de Software com IA', 'Domine arquitetura modular e agentes autônomos.', 'Arquitetura', 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&auto=format&fit=crop&q=60');

            INSERT INTO produtos (nome, preco, categoria, descricao) VALUES
            ('Licença AIDD Enterprise v4.0', 4990.00, 'Software', 'Acesso completo à suíte integrada com 5 domínios.');
        """)
        conn.commit()

# =========================================================================
# CROSS-DOMAIN ORCHESTRATION (Regras de Negócio Cruzadas entre Domínios)
# =========================================================================
# 1. Quando Lead é Ganho no CRM -> Gera Receita no ERP automaticamente!
def on_lead_ganho(dados):
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
            VALUES (?, 'receita', 'Vendas CRM', ?, date('now', '+15 days'), 'pendente', ?)
        """, (f"Contrato Ganho: {dados.get('nome')}", float(dados.get('valor', 0)), dados.get('empresa', 'Cliente CRM')))
        conn.commit()
    webhook_dispatcher.disparar("cross_domain.crm_to_erp", dados)

events.on("lead_ganho", on_lead_ganho)
events.on("lead_criado", lambda d: webhook_dispatcher.disparar("crm.lead_criado", d))
events.on("conta_criada", lambda d: webhook_dispatcher.disparar("erp.conta_criada", d))
events.on("ticket_aberto", lambda d: webhook_dispatcher.disparar("helpdesk.ticket_aberto", d))

registry = RouteRegistry()

# ----------------- ROTAS CRM -----------------
@registry.get("/api/crm/pipeline", summary="Kanban de Vendas CRM", tags=["CRM"])
def get_pipeline(params):
    with db.get_connection() as conn:
        leads = [dict(r) for r in conn.execute("SELECT * FROM leads ORDER BY score DESC").fetchall()]
        estagios = {
            "novo": {"nome": "Novos Leads", "itens": [], "total_valor": 0},
            "qualificado": {"nome": "Qualificados", "itens": [], "total_valor": 0},
            "proposta": {"nome": "Proposta Enviada", "itens": [], "total_valor": 0},
            "negociacao": {"nome": "Em Negociação", "itens": [], "total_valor": 0},
            "ganho": {"nome": "Fechado / Ganho", "itens": [], "total_valor": 0}
        }
        for l in leads:
            st = l.get("status", "novo")
            if st in estagios:
                estagios[st]["itens"].append(l)
                estagios[st]["total_valor"] += l.get("valor_estimado", 0)
        return estagios

@registry.post("/api/crm/leads/salvar", summary="Salvar ou Editar Lead", tags=["CRM"])
def post_salvar_lead(data):
    lid = data.get("id")
    with db.get_connection() as conn:
        if lid:
            conn.execute("UPDATE leads SET nome=?, email=?, telefone=?, empresa=?, score=?, status=?, valor_estimado=? WHERE id=?",
                         (data["nome"], data["email"], data["telefone"], data.get("empresa",""), int(data.get("score",50)), data.get("status","novo"), float(data.get("valor_estimado",0)), int(lid)))
            nid = int(lid)
        else:
            cur = conn.execute("INSERT INTO leads (nome, email, telefone, empresa, score, status, valor_estimado) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (data["nome"], data["email"], data["telefone"], data.get("empresa",""), int(data.get("score",50)), data.get("status","novo"), float(data.get("valor_estimado",0))))
            nid = cur.lastrowid
        conn.commit()
        if data.get("status") == "ganho":
            events.emit("lead_ganho", {"id": nid, "nome": data["nome"], "valor": data.get("valor_estimado",0), "empresa": data.get("empresa","")})
    return {"sucesso": True, "id": nid}

@registry.post("/api/crm/pipeline/mover", summary="Move Lead e dispara Cross-Domain", tags=["CRM"])
def post_mover_lead(data):
    lid = int(data.get("lead_id", 0))
    st = data.get("novo_status", "qualificado")
    with db.get_connection() as conn:
        conn.execute("UPDATE leads SET status = ? WHERE id = ?", (st, lid))
        conn.commit()
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lid,)).fetchone()
        if row and st == "ganho":
            lead_dict = dict(row)
            events.emit("lead_ganho", {"id": lid, "nome": lead_dict["nome"], "valor": lead_dict["valor_estimado"], "empresa": lead_dict["empresa"]})
    return {"sucesso": True, "lead_id": lid, "status": st}

# ----------------- ROTAS ERP -----------------
@registry.get("/api/erp/contas", summary="Lançamentos Financeiros ERP", tags=["ERP Financeiro"])
def get_contas(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM lancamentos ORDER BY data_vencimento ASC").fetchall()]

@registry.get("/api/erp/fluxo-caixa", summary="DRE & Resumo Fluxo de Caixa", tags=["ERP Financeiro"])
def get_fluxo(params):
    with db.get_connection() as conn:
        rec_paga = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE tipo='receita' AND status='pago'").fetchone()[0]
        desp_paga = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE tipo='despesa' AND status='pago'").fetchone()[0]
        rec_total = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE tipo='receita'").fetchone()[0]
        desp_total = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE tipo='despesa'").fetchone()[0]
        return {
            "receitas_recebidas": rec_paga,
            "despesas_pagas": desp_paga,
            "saldo_realizado": rec_paga - desp_paga,
            "saldo_projetado": rec_total - desp_total
        }

@registry.post("/api/erp/contas/salvar", summary="Salvar Lançamento ERP", tags=["ERP Financeiro"])
def post_salvar_conta(data):
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
            VALUES (?, ?, ?, ?, ?, 'pendente', ?)
        """, (data["descricao"], data["tipo"], data["categoria"], float(data["valor"]), data["data_vencimento"], data.get("entidade_nome","Geral")))
        conn.commit()
    return {"sucesso": True}

@registry.post("/api/erp/contas/alternar-status", summary="Alternar Pago / Pendente", tags=["ERP Financeiro"])
def post_alternar_conta(data):
    cid = int(data.get("id", 0))
    with db.get_connection() as conn:
        st = conn.execute("SELECT status FROM lancamentos WHERE id = ?", (cid,)).fetchone()[0]
        novo_st = "pago" if st == "pendente" else "pendente"
        conn.execute("UPDATE lancamentos SET status = ? WHERE id = ?", (novo_st, cid))
        conn.commit()
    return {"sucesso": True, "status": novo_st}

# ----------------- ROTAS HELPDESK -----------------
@registry.get("/api/helpdesk/tickets", summary="Fila de Chamados com SLA", tags=["Helpdesk"])
def get_tickets(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY CASE prioridade WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, id DESC").fetchall()]

@registry.post("/api/helpdesk/tickets/salvar", summary="Novo Chamado Helpdesk", tags=["Helpdesk"])
def post_salvar_ticket(data):
    proto = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    prio = data.get("prioridade", "P3")
    sla = 2 if prio == "P1" else (4 if prio == "P2" else 24)
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO tickets (protocolo, assunto, descricao, cliente_nome, cliente_email, prioridade, status, sla_limite_horas)
            VALUES (?, ?, ?, ?, ?, ?, 'aberto', ?)
        """, (proto, data["assunto"], data["descricao"], data["cliente_nome"], data["cliente_email"], prio, sla))
        conn.commit()
    events.emit("ticket_aberto", {"protocolo": proto, "prioridade": prio})
    return {"sucesso": True, "protocolo": proto}

@registry.post("/api/helpdesk/tickets/avancar-status", summary="Avançar status chamado", tags=["Helpdesk"])
def post_avancar_ticket(data):
    tid = int(data.get("id", 0))
    with db.get_connection() as conn:
        st = conn.execute("SELECT status FROM tickets WHERE id = ?", (tid,)).fetchone()[0]
        novo_st = "em_andamento" if st == "aberto" else ("resolvido" if st == "em_andamento" else "aberto")
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (novo_st, tid))
        conn.commit()
    return {"sucesso": True, "status": novo_st}

# ----------------- ROTAS MEMBROS & CATÁLOGO -----------------
@registry.get("/api/membros/cursos", summary="Lista Cursos Disponíveis", tags=["Membros & Cursos"])
def get_cursos(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cursos").fetchall()]

@registry.get("/api/catalogo/produtos", summary="Lista Produtos Catálogo", tags=["Catálogo & E-commerce"])
def get_produtos(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM produtos").fetchall()]

class AppHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        p = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(p.query)
        if p.path == "/docs/guia":
            with open(os.path.join(STATIC_DIR, "docs.html"), "r", encoding="utf-8") as df:
                self._send_html(df.read())
        elif p.path == "/docs":
            self._send_html(registry.get_swagger_html("AIDD v4.0 Enterprise Suite — OpenAPI Swagger"))
        elif p.path == "/openapi.json":
            self._send_json(registry.generate_openapi_json("AIDD Enterprise Suite v4.0", "4.0.0"))
        elif p.path in registry.routes["GET"]:
            self._send_json(registry.routes["GET"][p.path](params))
        elif p.path == "/favicon.ico":
            self.send_response(204); self.end_headers()
        elif p.path == "/" or p.path == "":
            self.path = "/index.html"; super().do_GET()
        else: super().do_GET()

    def do_POST(self):
        p = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        if p.path in registry.routes["POST"]:
            self._send_json(registry.routes["POST"][p.path](data))
        else: self.send_error(404)

    def _send_json(self, data):
        res = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(res)))
        self.end_headers(); self.wfile.write(res)

    def _send_html(self, html):
        res = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(res)))
        self.end_headers(); self.wfile.write(res)

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True

if __name__ == "__main__":
    server = ThreadedServer(("", PORT), AppHandler)
    print(f"[OK] AIDD v4.0 Enterprise Suite rodando em: http://localhost:{PORT}")
    print(f"[OK] Documentação OnOrca em: http://localhost:{PORT}/docs/guia")
    print(f"[OK] Swagger API Docs em: http://localhost:{PORT}/docs")
    server.serve_forever()
