import http.server, socketserver, json, urllib.parse, os, sys, uuid

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import Database
from core.events import EventBus
from core.openapi import RouteRegistry
from core.webhooks import WebhookDispatcher
from core.models import init_all_schemas

PORT = 3000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
db = Database(f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'suite.db')}")
events = EventBus()
webhook_dispatcher = WebhookDispatcher(db)

with db.get_connection() as conn:
    init_all_schemas(conn)

# =========================================================================
# CROSS-DOMAIN ORCHESTRATION RULES (EventBus Central)
# =========================================================================
def on_lead_ganho(dados):
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
            VALUES (?, 'receita', 'Vendas CRM', ?, date('now', '+15 days'), 'pendente', ?)
        """, (f"Contrato Ganho: {dados.get('nome')}", float(dados.get('valor', 0)), dados.get('empresa', 'Cliente CRM')))
        conn.commit()
    webhook_dispatcher.disparar("cross_domain.crm_to_erp", dados)

def on_pedido_catalogo(dados):
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
            VALUES (?, 'receita', 'E-commerce Catálogo', ?, date('now'), 'pago', ?)
        """, (f"Pedido Catálogo: {dados.get('cliente_nome')}", float(dados.get('total', 0)), dados.get('cliente_nome', 'Cliente')))
        conn.commit()
    webhook_dispatcher.disparar("cross_domain.catalogo_to_erp", dados)

events.on("lead_ganho", on_lead_ganho)
events.on("pedido_criado", on_pedido_catalogo)

registry = RouteRegistry()

# ----------------- CRM REST FULL-CRUD -----------------
@registry.get("/api/crm/pipeline", summary="Kanban de Vendas CRM", tags=["CRM Vendas"])
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

@registry.post("/api/crm/leads/salvar", summary="Criar ou Atualizar Lead", tags=["CRM Vendas"])
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

@registry.post("/api/crm/leads/excluir", summary="Excluir Lead", tags=["CRM Vendas"])
def post_excluir_lead(data):
    lid = int(data.get("id", 0))
    with db.get_connection() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lid,))
        conn.commit()
    return {"sucesso": True}

@registry.post("/api/crm/pipeline/mover", summary="Move Estágio do Lead", tags=["CRM Vendas"])
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

# ----------------- ERP REST FULL-CRUD -----------------
@registry.get("/api/erp/contas", summary="Lista Lançamentos ERP", tags=["ERP Financeiro"])
def get_contas(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM lancamentos ORDER BY data_vencimento ASC").fetchall()]

@registry.get("/api/erp/fluxo-caixa", summary="DRE & Resumo de Fluxo de Caixa", tags=["ERP Financeiro"])
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

@registry.post("/api/erp/contas/salvar", summary="Salvar ou Editar Lançamento", tags=["ERP Financeiro"])
def post_salvar_conta(data):
    cid = data.get("id")
    with db.get_connection() as conn:
        if cid:
            conn.execute("UPDATE lancamentos SET descricao=?, tipo=?, categoria=?, valor=?, data_vencimento=?, entidade_nome=? WHERE id=?",
                         (data["descricao"], data["tipo"], data["categoria"], float(data["valor"]), data["data_vencimento"], data.get("entidade_nome","Geral"), int(cid)))
        else:
            conn.execute("""
                INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
                VALUES (?, ?, ?, ?, ?, 'pendente', ?)
            """, (data["descricao"], data["tipo"], data["categoria"], float(data["valor"]), data["data_vencimento"], data.get("entidade_nome","Geral")))
        conn.commit()
    return {"sucesso": True}

@registry.post("/api/erp/contas/excluir", summary="Excluir Lançamento", tags=["ERP Financeiro"])
def post_excluir_conta(data):
    cid = int(data.get("id", 0))
    with db.get_connection() as conn:
        conn.execute("DELETE FROM lancamentos WHERE id = ?", (cid,))
        conn.commit()
    return {"sucesso": True}

@registry.post("/api/erp/contas/alternar-status", summary="1-Clique Status Pago/Pendente", tags=["ERP Financeiro"])
def post_alternar_conta(data):
    cid = int(data.get("id", 0))
    with db.get_connection() as conn:
        st = conn.execute("SELECT status FROM lancamentos WHERE id = ?", (cid,)).fetchone()[0]
        novo_st = "pago" if st == "pendente" else "pendente"
        conn.execute("UPDATE lancamentos SET status = ? WHERE id = ?", (novo_st, cid))
        conn.commit()
    return {"sucesso": True, "status": novo_st}

# ----------------- HELPDESK REST FULL-CRUD -----------------
@registry.get("/api/helpdesk/tickets", summary="Lista Fila de Chamados", tags=["Central Helpdesk"])
def get_tickets(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY CASE prioridade WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, id DESC").fetchall()]

@registry.post("/api/helpdesk/tickets/salvar", summary="Criar ou Editar Chamado", tags=["Central Helpdesk"])
def post_salvar_ticket(data):
    tid = data.get("id")
    with db.get_connection() as conn:
        prio = data.get("prioridade", "P3")
        sla = 2 if prio == "P1" else (4 if prio == "P2" else 24)
        if tid:
            conn.execute("UPDATE tickets SET assunto=?, descricao=?, cliente_nome=?, cliente_email=?, prioridade=?, sla_limite_horas=? WHERE id=?",
                         (data["assunto"], data["descricao"], data["cliente_nome"], data["cliente_email"], prio, sla, int(tid)))
            proto = conn.execute("SELECT protocolo FROM tickets WHERE id = ?", (int(tid),)).fetchone()[0]
        else:
            proto = f"TICK-{uuid.uuid4().hex[:6].upper()}"
            conn.execute("""
                INSERT INTO tickets (protocolo, assunto, descricao, cliente_nome, cliente_email, prioridade, status, sla_limite_horas)
                VALUES (?, ?, ?, ?, ?, ?, 'aberto', ?)
            """, (proto, data["assunto"], data["descricao"], data["cliente_nome"], data["cliente_email"], prio, sla))
        conn.commit()
    return {"sucesso": True, "protocolo": proto}

@registry.post("/api/helpdesk/tickets/excluir", summary="Excluir Chamado", tags=["Central Helpdesk"])
def post_excluir_ticket(data):
    tid = int(data.get("id", 0))
    with db.get_connection() as conn:
        conn.execute("DELETE FROM tickets WHERE id = ?", (tid,))
        conn.commit()
    return {"sucesso": True}

@registry.post("/api/helpdesk/tickets/avancar-status", summary="1-Clique Status Chamado", tags=["Central Helpdesk"])
def post_avancar_ticket(data):
    tid = int(data.get("id", 0))
    with db.get_connection() as conn:
        st = conn.execute("SELECT status FROM tickets WHERE id = ?", (tid,)).fetchone()[0]
        novo_st = "em_andamento" if st == "aberto" else ("resolvido" if st == "em_andamento" else "aberto")
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (novo_st, tid))
        conn.commit()
    return {"sucesso": True, "status": novo_st}

# ----------------- MEMBROS & CATÁLOGO REST FULL-CRUD -----------------
@registry.get("/api/membros/cursos", summary="Lista Cursos VIP", tags=["Membros & Cursos"])
def get_cursos(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM cursos").fetchall()]

@registry.post("/api/membros/assinar", summary="Checkout Assinatura", tags=["Membros & Cursos"])
def post_assinar(data):
    with db.get_connection() as conn:
        conn.execute("""
            INSERT INTO assinaturas (usuario_nome, usuario_email, plano, metodo, valor, status)
            VALUES (?, ?, ?, ?, ?, 'ativa')
        """, (data["nome"], data["email"], data.get("plano", "Pro"), data.get("metodo", "Pix"), float(data.get("valor", 97.0))))
        conn.commit()
    return {"sucesso": True}

@registry.get("/api/catalogo/produtos", summary="Lista Produtos Catálogo", tags=["Catálogo & E-commerce"])
def get_produtos(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM produtos").fetchall()]

@registry.post("/api/catalogo/pedidos/salvar", summary="Finalizar Pedido Catálogo", tags=["Catálogo & E-commerce"])
def post_salvar_pedido(data):
    with db.get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO pedidos (cliente_nome, cliente_telefone, total, itens_json, status)
            VALUES (?, ?, ?, ?, 'pago')
        """, (data["cliente_nome"], data["cliente_telefone"], float(data["total"]), json.dumps(data.get("itens", []))))
        conn.commit()
        pid = cur.lastrowid
        events.emit("pedido_criado", {"id": pid, "cliente_nome": data["cliente_nome"], "total": data["total"]})
    return {"sucesso": True, "pedido_id": pid}

# ----------------- SERVIDOR HTTP -----------------
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
            self._send_html(registry.get_swagger_html("AIDD Enterprise Suite v4.0 — OpenAPI Swagger"))
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
    print(f"[OK] AIDD Enterprise Suite v4.0 rodando em: http://localhost:{PORT}")
    print(f"[OK] Documentação da Suíte em: http://localhost:{PORT}/docs/guia")
    print(f"[OK] Swagger API Docs em: http://localhost:{PORT}/docs")
    server.serve_forever()
