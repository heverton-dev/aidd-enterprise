import http.server, socketserver, json, urllib.parse, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import Database
from core.events import EventBus
from core.openapi import RouteRegistry
from core.webhooks import WebhookDispatcher
from core.models import init_all_schemas
from core.mcp_server import LogisticaMCPServer

PORT = 3000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
db = Database(f"sqlite:///{os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'suite.db')}")
events = EventBus()
webhook_dispatcher = WebhookDispatcher(db)
mcp_engine = LogisticaMCPServer(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "suite.db"))

with db.get_connection() as conn:
    init_all_schemas(conn)

# =========================================================================
# REGRAS CROSS-DOMAIN (EventBus)
# =========================================================================
def on_entrega_finalizada(dados):
    with db.get_connection() as conn:
        conn.execute("INSERT INTO fretes_financeiro (tipo, descricao, valor, status, data_vencimento) VALUES ('receita', ?, ?, 'pago', date('now'))",
                     (f"Frete Liquidado: {dados.get('codigo_rastreio')}", float(dados.get('valor_frete', 0))))
        conn.commit()
    webhook_dispatcher.disparar("cross_domain.entrega_to_financeiro", dados)

events.on("entrega_finalizada", on_entrega_finalizada)

registry = RouteRegistry()

# 1. FROTAS
@registry.get("/api/frotas/veiculos", summary="Listar Veículos da Frota", tags=["1. Gestão de Frotas"])
def get_veiculos(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM veiculos").fetchall()]

@registry.post(
    "/api/frotas/veiculos/salvar",
    summary="Cadastrar Veículo",
    tags=["1. Gestão de Frotas"],
    params=[
        {"name": "placa", "type": "string", "req": True, "desc": "Placa do veículo"},
        {"name": "modelo", "type": "string", "req": True, "desc": "Modelo do caminhão"},
        {"name": "motorista", "type": "string", "req": True, "desc": "Motorista responsável"},
        {"name": "capacidade_kg", "type": "number", "req": True, "desc": "Capacidade em KG"}
    ],
    body={"placa": "XYZ9B88", "modelo": "Mercedes-Benz Actros", "motorista": "Fernando Dias", "capacidade_kg": 30000.0}
)
def post_salvar_veiculo(data):
    with db.get_connection() as conn:
        conn.execute("INSERT INTO veiculos (placa, modelo, motorista, capacidade_kg, status) VALUES (?, ?, ?, ?, 'disponivel')",
                     (data["placa"].upper(), data["modelo"], data["motorista"], float(data["capacidade_kg"])))
        conn.commit()
    return {"sucesso": True}

@registry.post("/api/frotas/veiculos/alternar", summary="Alternar Status Veículo", tags=["1. Gestão de Frotas"], params=[{"name": "id", "type": "integer", "req": True, "desc": "ID do veículo"}], body={"id": 1})
def post_alternar_veiculo(data):
    vid = int(data.get("id", 0))
    with db.get_connection() as conn:
        st = conn.execute("SELECT status FROM veiculos WHERE id = ?", (vid,)).fetchone()[0]
        novo_st = "em_rota" if st == "disponivel" else ("manutencao" if st == "em_rota" else "disponivel")
        conn.execute("UPDATE veiculos SET status = ? WHERE id = ?", (novo_st, vid))
        conn.commit()
    return {"sucesso": True, "status": novo_st}

# 2. ENTREGAS & RASTREAMENTO
@registry.get("/api/entregas/listar", summary="Listar Remessas & Rastreio", tags=["2. Entregas & Rastreio"])
def get_entregas(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM entregas ORDER BY id DESC").fetchall()]

@registry.post(
    "/api/entregas/salvar",
    summary="Criar Remessa de Entrega",
    tags=["2. Entregas & Rastreio"],
    params=[
        {"name": "destinatario", "type": "string", "req": True, "desc": "Destinatário"},
        {"name": "cidade_destino", "type": "string", "req": True, "desc": "Cidade/UF"},
        {"name": "valor_frete", "type": "number", "req": True, "desc": "Valor do frete"},
        {"name": "peso_kg", "type": "number", "req": True, "desc": "Peso da carga"}
    ],
    body={"destinatario": "BioTech Farmacêutica", "cidade_destino": "Ribeirão Preto/SP", "valor_frete": 9200.0, "peso_kg": 16000.0}
)
def post_salvar_entrega(data):
    import uuid
    cod = f"BR-LOG-{uuid.uuid4().hex[:4].upper()}"
    with db.get_connection() as conn:
        conn.execute("INSERT INTO entregas (codigo_rastreio, destinatario, cidade_destino, valor_frete, peso_kg, status) VALUES (?, ?, ?, ?, ?, 'pendente')",
                     (cod, data["destinatario"], data["cidade_destino"], float(data["valor_frete"]), float(data["peso_kg"])))
        conn.commit()
    return {"sucesso": True, "codigo_rastreio": cod}

@registry.post("/api/entregas/finalizar", summary="Finalizar Entrega (➔ Lança Frete no Financeiro)", tags=["2. Entregas & Rastreio"], params=[{"name": "id", "type": "integer", "req": True, "desc": "ID da entrega"}], body={"id": 1})
def post_finalizar_entrega(data):
    eid = int(data.get("id", 0))
    with db.get_connection() as conn:
        conn.execute("UPDATE entregas SET status = 'entregue' WHERE id = ?", (eid,))
        conn.commit()
        row = conn.execute("SELECT * FROM entregas WHERE id = ?", (eid,)).fetchone()
        if row:
            events.emit("entrega_finalizada", dict(row))
    return {"sucesso": True, "status": "entregue"}

# 3. WMS ESTOQUE
@registry.get("/api/wms/estoque", summary="Consultar Saldo Armazém WMS", tags=["3. Armazém WMS"])
def get_estoque(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM estoque_wms").fetchall()]

# 4. FINANCEIRO DE FRETES
@registry.get("/api/financeiro/fretes", summary="Razão Financeiro de Fretes", tags=["4. Financeiro de Fretes"])
def get_fretes(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM fretes_financeiro ORDER BY id DESC").fetchall()]

# 5. INCIDENTES & SLA
@registry.get("/api/suporte/incidentes", summary="Fila de Incidentes SLA", tags=["5. Central de Incidentes"])
def get_incidentes(params):
    with db.get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM incidentes_sla").fetchall()]

# ----------------- HTTP SERVER HANDLER -----------------
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
            self._send_html(registry.get_swagger_html("Logística Hub Suite v4.0 — API Reference Studio"))
        elif p.path == "/mcp":
            self._send_html(mcp_engine.get_portal_html())
        elif p.path == "/openapi.json":
            self._send_json(registry.generate_openapi_json("Logística Hub Suite v4.0", "4.0.0"))
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
        if p.path == "/mcp":
            self._send_json(mcp_engine.process_rpc(data))
        elif p.path in registry.routes["POST"]:
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
    print(f"[OK] Logística Hub Suite v4.0 rodando em: http://localhost:{PORT}")
    print(f"[OK] Swagger Studio em: http://localhost:{PORT}/docs")
    print(f"[OK] Guia do Projeto em: http://localhost:{PORT}/docs/guia")
    print(f"[OK] Portal MCP em: http://localhost:{PORT}/mcp")
    server.serve_forever()
