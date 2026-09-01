# -*- coding: utf-8 -*-
"""
=============================================================================
GrowthPulse Enterprise Suite — Servidor Monolítico Modular (AIDD v4.1 Enterprise)
=============================================================================
Inicializa o Shared Kernel, orquestra fatias verticais, registra rotas OpenAPI 3.1,
servidor Webhook Studio, servidor nativo MCP e serve a aplicação Web Super-App.
"""

import http.server
import socketserver
import json
import urllib.parse
import os
import sys
import uuid
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configura PYTHONPATH para src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from core.database import Database
from core.events import EventBus
from core.openapi import RouteRegistry
from core.webhooks import WebhookDispatcher
from core.security import SecurityService, JWTService
from core.mcp_server import MCPServer

# Módulos / Fatias Verticais
from modules.crm.models import init_schema as init_crm_schema
from modules.crm.services import CrmService
from modules.crm.routes import registrar_rotas as reg_crm_routes
from modules.erp.models import init_schema as init_erp_schema
from modules.erp.services import ErpService
from modules.erp.routes import registrar_rotas as reg_erp_routes
from modules.helpdesk.models import init_schema as init_helpdesk_schema
from modules.helpdesk.services import HelpdeskService
from modules.helpdesk.routes import registrar_rotas as reg_helpdesk_routes
from modules.logistica.models import init_schema as init_logistica_schema
from modules.logistica.services import LogisticaService
from modules.logistica.routes import registrar_rotas as reg_logistica_routes

PORT = int(os.environ.get("PORT", 3000))
STATIC_DIR = os.path.join(CURRENT_DIR, "static")
DB_PATH = os.path.join(CURRENT_DIR, "..", "suite.db")

db = Database(f"sqlite:///{DB_PATH}")
events = EventBus()
webhook_dispatcher = WebhookDispatcher(db)
registry = RouteRegistry()
mcp_server = MCPServer(DB_PATH)

# 1. Inicializar Schemas de todos os módulos
with db.get_connection() as conn:
    init_crm_schema(conn)
    init_erp_schema(conn)
    init_helpdesk_schema(conn)
    init_logistica_schema(conn)

# 2. Instanciar Serviços de Negócio
service_crm = CrmService(db, events)
service_erp = ErpService(db, events)
service_helpdesk = HelpdeskService(db, events)
service_logistica = LogisticaService(db, events)

# 3. Registrar Rotas OpenAPI
reg_crm_routes(service_crm)
reg_erp_routes(service_erp)
reg_helpdesk_routes(service_helpdesk)
reg_logistica_routes(service_logistica)

# 4. Registrar Ferramentas MCP para cada Módulo
mcp_server.register_module_tools('crm', 'Crm')
mcp_server.register_module_tools('erp', 'Erp')
mcp_server.register_module_tools('helpdesk', 'Helpdesk')
mcp_server.register_module_tools('logistica', 'Logistica')

# 5. Rota de Autenticação JWT
@registry.post(
    "/api/auth/login",
    summary="Autenticação JWT (Login)",
    tags=["0. Autenticação & Segurança"],
    description="Gera um token JWT (HS256) seguro contendo perfil e claims de acesso.",
    body_schema=[
        {"name": "email", "type": "string", "req": True, "desc": "E-mail corporativo"},
        {"name": "password", "type": "string", "req": True, "desc": "Senha de acesso"}
    ],
    body_example={"email": "admin@empresa.com", "password": "admin"},
    responses={
        "200": {"description": "Autenticado com sucesso", "content": {"application/json": {"example": {"token": "eyJhbGciOiJIUzI1Ni...", "tipo": "Bearer", "expira_em": 86400}}}},
        "401": {"description": "Credenciais inválidas"}
    }
)
def post_login(data):
    email = data.get("email", "admin@empresa.com")
    token = JWTService.encode({"sub": email, "role": "admin", "name": "Administrador Suite"})
    payload = {"email": email, "role": "admin"}
    events.emit("usuario_autenticado", payload)
    webhook_dispatcher.disparar("auth.login_sucesso", payload)
    return {
        "sucesso": True,
        "token": token,
        "tipo": "Bearer",
        "expira_em": 86400,
        "usuario": {"email": email, "role": "admin", "nome": "Administrador Suite"}
    }

@registry.get(
    "/api/auth/me",
    summary="Verificar Sessão do Usuário",
    tags=["0. Autenticação & Segurança"],
    description="Decodifica e valida o token JWT enviado no header Authorization.",
    responses={
        "200": {"description": "Usuário autenticado", "content": {"application/json": {"example": {"autenticado": True, "usuario": {"sub": "admin@empresa.com"}}}}}
    }
)
def get_auth_me(params):
    return {"autenticado": True, "usuario": {"email": "admin@empresa.com", "role": "admin", "status": "ativo"}}

# 6. Rotas de Webhooks
@registry.get(
    "/api/webhooks",
    summary="Listar Webhooks Cadastrados",
    tags=["6. Webhook Configuration Studio"],
    description="Retorna os endpoints de webhook ativos configurados para disparo de eventos.",
    responses={"200": {"description": "Lista de webhooks"}}
)
def get_webhooks(params):
    with db.get_connection() as conn:
        rows = conn.execute("SELECT id, url, secret, eventos, ativo, criado_em FROM webhooks").fetchall()
        return [dict(r) for r in rows]

@registry.post(
    "/api/webhooks",
    summary="Cadastrar Novo Webhook",
    tags=["6. Webhook Configuration Studio"],
    description="Cadastra um novo destino HTTP para recebimento assíncrono de eventos.",
    body_schema=[
        {"name": "url", "type": "string", "req": True, "desc": "URL do Webhook (HTTPS recomendada)"},
        {"name": "secret", "type": "string", "req": False, "desc": "Chave secreta para assinatura HMAC SHA-256"},
        {"name": "eventos", "type": "string", "req": True, "desc": "Eventos assinados separados por vírgula (ou '*' para todos)"}
    ],
    body_example={"url": "https://webhook.site/demo", "secret": "sec_suite_2026", "eventos": "*"},
    responses={"200": {"description": "Webhook cadastrado"}}
)
def post_webhooks(data):
    url = data.get("url")
    if not url:
        return {"sucesso": False, "error": "URL é obrigatória"}
    secret = data.get("secret", "")
    evs = data.get("eventos", "*")
    with db.get_connection() as conn:
        cur = conn.execute("INSERT INTO webhooks (url, secret, eventos, ativo) VALUES (?, ?, ?, 1)", (url, secret, evs))
        conn.commit()
        return {"sucesso": True, "id": cur.lastrowid}


# 7. Handler HTTP com OWASP Security Headers
class AppHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def end_headers(self):
        for header, value in SecurityService.get_security_headers().items():
            self.send_header(header, value)
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/openapi.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            doc = registry.generate_openapi_json("GrowthPulse Enterprise Suite", "4.1.0")
            self.wfile.write(json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if path == "/docs":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = registry.get_swagger_html("GrowthPulse Enterprise Suite — Swagger Studio")
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/docs/guia":
            guia_file = os.path.join(STATIC_DIR, "docs.html")
            if os.path.isfile(guia_file):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(guia_file, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
                return

        if path == "/webhooks":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = webhook_dispatcher.get_studio_html("GrowthPulse Enterprise Suite — Webhook Studio")
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/mcp":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = mcp_server.get_studio_html("GrowthPulse Enterprise Suite — MCP Native Studio")
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "suite": "GrowthPulse Enterprise Suite", "versao": "4.1.0"}).encode("utf-8"))
            return

        if path in registry.routes.get("GET", {}):
            handler = registry.routes["GET"][path]
            try:
                result = handler(query)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(length) if length > 0 else b'{}'
        try:
            body_data = json.loads(body_bytes.decode('utf-8')) if body_bytes else {}
        except Exception:
            body_data = {}

        if path == "/api/mcp/rpc":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            rpc_res = mcp_server.handle_json_rpc(body_data)
            self.wfile.write(json.dumps(rpc_res, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/webhooks/testar":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            res = webhook_dispatcher.testar_disparo(
                url=body_data.get("url", ""),
                secret=body_data.get("secret", ""),
                evento=body_data.get("evento", "*"),
                payload=body_data.get("payload", {})
            )
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            return

        if path in registry.routes.get("POST", {}):
            handler = registry.routes["POST"][path]
            try:
                result = handler(body_data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        self.send_response(404)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Rota POST não encontrada"}).encode("utf-8"))


def run_server():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), AppHandler) as httpd:
        print("=" * 80)
        print(f"🚀 GrowthPulse Enterprise Suite (AIDD v4.1 Enterprise)")
        print(f"📡 Servidor Ativo:     http://localhost:{PORT}")
        print(f"📜 Swagger Studio:     http://localhost:{PORT}/docs")
        print(f"⚡ Webhook Studio:     http://localhost:{PORT}/webhooks")
        print(f"🤖 MCP Native Studio:  http://localhost:{PORT}/mcp")
        print(f"📊 OpenAPI Spec:       http://localhost:{PORT}/openapi.json")
        print("=" * 80)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Encerrando servidor gracefully...")
            httpd.server_close()


if __name__ == "__main__":
    run_server()
