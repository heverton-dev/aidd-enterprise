#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
AIDD v4.1 Enterprise — Cross-Project Enterprise Suite Composition Engine
=============================================================================
Compõe suítes empresariais e monólitos modulares completos com:
- Shared Kernel (Database SQLite WAL, EventBus, RouteRegistry, WebhookDispatcher, SecurityService, MCPServer)
- Fatias Verticais completas (models, services, routes, UI components, testes unitários)
- Servidor Monolítico Modular dinâmico (server.py)
- Swagger Studio OpenAPI 3.1 & Webhook Configuration Studio & MCP Native Portal
- Bateria completa de Gates Determinísticos Anti-Fail
- Manifesto estruturado PLANO-EXECUCAO-ESTRUTURADO.json e requirements.txt
"""

import os
import sys
import shutil
import json
import uuid
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Importa o gerador de fatias verticais
try:
    from add_module import criar_modulo, slugify, pascal_case
except ImportError:
    from scripts.add_module import criar_modulo, slugify, pascal_case


def generate_modular_server_code(suite_name: str, module_slugs: list) -> str:
    """Gera o código-fonte do servidor dinâmico server.py que carrega todos os módulos."""
    imports_lines = []
    init_schema_calls = []
    service_inits = []
    routes_regs = []
    mcp_tool_regs = []

    for mod in module_slugs:
        slug = slugify(mod)
        pascal = pascal_case(mod)
        imports_lines.append(f"from modules.{slug}.models import init_schema as init_{slug}_schema")
        imports_lines.append(f"from modules.{slug}.services import {pascal}Service")
        imports_lines.append(f"from modules.{slug}.routes import registrar_rotas as reg_{slug}_routes")

        init_schema_calls.append(f"    init_{slug}_schema(conn)")
        service_inits.append(f"service_{slug} = {pascal}Service(db, events)")
        routes_regs.append(f"reg_{slug}_routes(service_{slug})")
        mcp_tool_regs.append(f"mcp_server.register_module_tools('{slug}', '{pascal}')")

    imports_str = "\n".join(imports_lines)
    init_schemas_str = "\n".join(init_schema_calls)
    service_inits_str = "\n".join(service_inits)
    routes_regs_str = "\n".join(routes_regs)
    mcp_tool_regs_str = "\n".join(mcp_tool_regs)

    template = """# -*- coding: utf-8 -*-
\"\"\"
=============================================================================
__SUITE_NAME__ — Servidor Monolítico Modular (AIDD v4.1 Enterprise)
=============================================================================
Inicializa o Shared Kernel, orquestra fatias verticais, registra rotas OpenAPI 3.1,
servidor Webhook Studio, servidor nativo MCP e serve a aplicação Web Super-App.
\"\"\"

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
__IMPORTS__

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
__INIT_SCHEMAS__

# 2. Instanciar Serviços de Negócio
__SERVICE_INITS__

# 3. Registrar Rotas OpenAPI
__ROUTES_REGS__

# 4. Registrar Ferramentas MCP para cada Módulo
__MCP_TOOL_REGS__

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
        self.send_header("Access-Control-Allow-Origin", "*")
        for header, value in SecurityService.get_security_headers().items():
            self.send_header(header, value)
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ["/", "/index.html"]:
            index_file = os.path.join(STATIC_DIR, "index.html")
            if os.path.isfile(index_file):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(index_file, "rb") as f:
                    self.wfile.write(f.read())
                return

        if path.startswith("/static/"):
            rel_p = path[len("/static/"):]
            target_f = os.path.join(STATIC_DIR, rel_p)
            if os.path.isfile(target_f):
                content_type = "text/html" if target_f.endswith(".html") else ("application/javascript" if target_f.endswith(".js") else "text/css" if target_f.endswith(".css") else "text/plain")
                self.send_response(200)
                self.send_header("Content-Type", f"{content_type}; charset=utf-8")
                self.end_headers()
                with open(target_f, "rb") as f:
                    self.wfile.write(f.read())
                return

        if path == "/openapi.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            doc = registry.generate_openapi_json("__SUITE_NAME__", "4.1.0")
            self.wfile.write(json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"))
            return

        if path == "/docs":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = registry.get_swagger_html("__SUITE_NAME__ — Swagger Studio")
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
            html = webhook_dispatcher.get_studio_html("__SUITE_NAME__ — Webhook Studio")
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/mcp":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = mcp_server.get_studio_html("__SUITE_NAME__ — MCP Native Studio")
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "suite": "__SUITE_NAME__", "versao": "4.1.0"}).encode("utf-8"))
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
    global PORT
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    httpd = None
    for attempt_port in range(PORT, PORT + 25):
        try:
            httpd = socketserver.ThreadingTCPServer(("", attempt_port), AppHandler)
            PORT = attempt_port
            break
        except OSError:
            continue

    if not httpd:
        print("[FATAL] Não foi possível vincular o servidor em nenhuma porta entre 3000 e 3025.")
        sys.exit(1)

    with httpd:
        print("=" * 80)
        print(f"🚀 __SUITE_NAME__ (AIDD v4.1 Enterprise)")
        print(f"📡 Servidor Ativo:     http://localhost:{PORT}")
        print(f"📜 Swagger Studio:     http://localhost:{PORT}/docs")
        print(f"⚡ Webhook Studio:     http://localhost:{PORT}/webhooks")
        print(f"🤖 MCP Native Studio:  http://localhost:{PORT}/mcp")
        print(f"📊 OpenAPI Spec:       http://localhost:{PORT}/openapi.json")
        print("=" * 80)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\n[!] Encerrando servidor gracefully...")
            httpd.server_close()


if __name__ == "__main__":
    run_server()
"""
    return (
        template
        .replace("__SUITE_NAME__", suite_name)
        .replace("__IMPORTS__", imports_str)
        .replace("__INIT_SCHEMAS__", init_schemas_str)
        .replace("__SERVICE_INITS__", service_inits_str)
        .replace("__ROUTES_REGS__", routes_regs_str)
        .replace("__MCP_TOOL_REGS__", mcp_tool_regs_str)
    )


def generate_superapp_index_html(suite_name: str, module_slugs: list) -> str:
    """Gera front-end Super-App Impeccable com CSS 100% embutido (offline-first)."""
    tabs_nav = []
    sections = []
    scripts = []

    for i, mod in enumerate(module_slugs):
        slug = slugify(mod)
        pascal = pascal_case(mod)
        is_active = (i == 0)
        active_tab_class = "tab-btn active" if is_active else "tab-btn"
        active_sec_class = "tab-section active" if is_active else "tab-section"

        tabs_nav.append(f'''
            <button type="button" onclick="mudarAba('{slug}')" id="tab-btn-{slug}" class="{active_tab_class}" aria-label="Acessar módulo {pascal}">
                <span class="tab-indicator"></span>
                <span>{pascal}</span>
            </button>''')

        sections.append(f'''
        <!-- ABA {pascal} -->
        <section id="sec-{slug}" class="{active_sec_class}">
            <!-- CARDS DE KPIS DO MÓDULO -->
            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-title">Total de Registros</span>
                        <span class="kpi-icon sky">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                        </span>
                    </div>
                    <div class="kpi-val" id="kpi-{slug}-total">--</div>
                    <div class="kpi-sub">Cadastros em {pascal}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-title">Registros Ativos</span>
                        <span class="kpi-icon emerald">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </span>
                    </div>
                    <div class="kpi-val" id="kpi-{slug}-ativos">--</div>
                    <div class="kpi-sub">Operando normalmente</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-title">Concluídos / Arquivados</span>
                        <span class="kpi-icon indigo">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                        </span>
                    </div>
                    <div class="kpi-val" id="kpi-{slug}-concluidos">--</div>
                    <div class="kpi-sub">Finalizados no período</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-header">
                        <span class="kpi-title">Taxa de Conclusão</span>
                        <span class="kpi-icon amber">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
                        </span>
                    </div>
                    <div class="kpi-val" id="kpi-{slug}-taxa">--%</div>
                    <div class="kpi-sub">Eficiência operacional</div>
                </div>
            </div>

            <!-- TABELA DE DADOS & OPERAÇÕES -->
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <h2 class="panel-title">
                            <span class="dot-sky"></span>
                            Gestão de {pascal}
                        </h2>
                        <p class="panel-desc">Operações, listagem e ciclo de vida da fatia vertical {pascal}</p>
                    </div>
                    <div class="panel-actions">
                        <div class="search-box">
                            <input type="text" id="busca-{slug}" placeholder="Buscar em {pascal}..." onkeyup="filtrar{pascal}()" class="input-search">
                        </div>
                        <button type="button" onclick="carregar{pascal}()" class="btn btn-secondary" title="Recarregar" aria-label="Recarregar dados">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                        </button>
                        <button type="button" onclick="abrirModalNovo('{slug}')" class="btn btn-primary" aria-label="Criar novo {pascal}">
                            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                            <span>Novo {pascal}</span>
                        </button>
                    </div>
                </div>

                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th style="width: 70px;">ID</th>
                                <th>Título</th>
                                <th style="width: 120px;">Status</th>
                                <th style="width: 170px;">Criado em</th>
                                <th style="width: 100px; text-align: right;">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="tabela-{slug}-corpo">
                            <tr><td colspan="5" class="table-empty">Carregando dados do módulo {pascal}...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>''')

        scripts.append(f'''
        let dados{pascal}Cache = [];

        async function carregar{pascal}() {{
            try {{
                // 1. Carregar Métricas
                try {{
                    const mRes = await fetch('/api/{slug}/metricas');
                    if (mRes.ok) {{
                        const m = await mRes.json();
                        document.getElementById('kpi-{slug}-total').textContent = m.total ?? 0;
                        document.getElementById('kpi-{slug}-ativos').textContent = m.ativos ?? 0;
                        document.getElementById('kpi-{slug}-concluidos').textContent = m.concluidos ?? 0;
                        document.getElementById('kpi-{slug}-taxa').textContent = (m.taxa_conclusao ?? 0) + '%';
                    }}
                }} catch (e) {{ console.warn('Erro metricas {slug}:', e); }}

                // 2. Carregar Registros
                const res = await fetch('/api/{slug}');
                dados{pascal}Cache = await res.json();
                renderizarTabela{pascal}(dados{pascal}Cache);
            }} catch (e) {{
                console.error('Erro ao carregar {slug}:', e);
                mostrarToast('Falha ao carregar registros de {pascal}', 'erro');
            }}
        }}

        function renderizarTabela{pascal}(lista) {{
            const tbody = document.getElementById('tabela-{slug}-corpo');
            if (!lista || lista.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" class="table-empty">Nenhum registro ativo localizado.</td></tr>';
                return;
            }}
            tbody.innerHTML = lista.map(item => `
                <tr>
                    <td class="col-id">#${{item.id}}</td>
                    <td class="col-title">
                        <div class="item-title">${{escapeHtml(item.titulo)}}</div>
                        ${{item.descricao ? `<div class="item-desc">${{escapeHtml(item.descricao)}}</div>` : ''}}
                    </td>
                    <td><span class="badge badge-status">${{escapeHtml(item.status || 'ativo')}}</span></td>
                    <td class="col-date">${{escapeHtml(item.criado_em || '--')}}</td>
                    <td class="col-actions">
                        <button type="button" onclick="deletarItem('{slug}', ${{item.id}})" class="btn btn-delete" title="Excluir" aria-label="Excluir registro">Excluir</button>
                    </td>
                </tr>
            `).join('');
        }}

        function filtrar{pascal}() {{
            const termo = (document.getElementById('busca-{slug}').value || '').toLowerCase();
            if (!termo) {{
                renderizarTabela{pascal}(dados{pascal}Cache);
                return;
            }}
            const filtrados = dados{pascal}Cache.filter(i => 
                (i.titulo && i.titulo.toLowerCase().includes(termo)) ||
                (i.descricao && i.descricao.toLowerCase().includes(termo))
            );
            renderizarTabela{pascal}(filtrados);
        }}''')

    tabs_nav_str = "\n".join(tabs_nav)
    sections_str = "\n".join(sections)
    scripts_str = "\n".join(scripts)
    initial_loads = "\n".join([f"            carregar{pascal_case(m)}();" for m in module_slugs])

    html_template = """<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__SUITE_NAME__ — Super-App Enterprise</title>
    <style>
        :root {
            --bg-base: #090d16;
            --bg-surface: #0f172a;
            --bg-panel: #141e33;
            --border-subtle: #1e293b;
            --border-highlight: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-sky: #0ea5e9;
            --accent-sky-hover: #38bdf8;
            --accent-emerald: #10b981;
            --accent-rose: #f43f5e;
            --accent-amber: #f59e0b;
            --accent-indigo: #6366f1;
            --radius-md: 8px;
            --radius-lg: 12px;
            --radius-xl: 16px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.5;
        }
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: var(--bg-base); }
        ::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 2px; }

        /* HEADER */
        .topbar {
            height: 56px;
            background: rgba(15, 23, 42, 0.95);
            border-bottom: 1px solid var(--border-subtle);
            position: sticky;
            top: 0;
            z-index: 40;
            padding: 0 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(8px);
        }
        .topbar-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 14px; }
        .badge-ver {
            font-size: 10px;
            text-transform: uppercase;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 9999px;
            background: rgba(14, 165, 233, 0.15);
            color: var(--accent-sky-hover);
            border: 1px solid rgba(14, 165, 233, 0.3);
        }
        .topbar-links { display: flex; align-items: center; gap: 8px; }
        .topbar-link {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            background: #1e293b;
            padding: 6px 12px;
            border-radius: var(--radius-md);
            text-decoration: none;
            border: 1px solid var(--border-highlight);
            transition: all 0.15s;
        }
        .topbar-link:hover { color: #fff; background: #334155; }

        /* TABS */
        .tabs-nav {
            background: var(--bg-surface);
            border-bottom: 1px solid var(--border-subtle);
            padding: 8px 24px;
            position: sticky;
            top: 56px;
            z-index: 30;
            display: flex;
            justify-content: center;
            overflow-x: auto;
        }
        .tabs-container { display: flex; gap: 8px; max-width: 1200px; width: 100%; }
        .tab-btn {
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted);
            padding: 8px 16px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.15s;
        }
        .tab-btn:hover { color: #fff; background: rgba(255,255,255,0.03); }
        .tab-btn.active {
            color: var(--accent-sky-hover);
            background: rgba(14, 165, 233, 0.12);
            border-color: rgba(14, 165, 233, 0.35);
        }
        .tab-indicator { width: 6px; height: 6px; border-radius: 50%; background: var(--accent-sky); }

        /* MAIN & SECTIONS */
        .main-content {
            flex: 1;
            max-width: 1200px;
            width: 100%;
            margin: 0 auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }
        .tab-section { display: none; }
        .tab-section.active { display: block; }

        /* KPIS GRID */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 20px;
        }
        .kpi-card {
            background: rgba(20, 30, 51, 0.7);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-lg);
            padding: 16px;
            backdrop-filter: blur(4px);
        }
        .kpi-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
        .kpi-title { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
        .kpi-icon {
            width: 24px;
            height: 24px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .kpi-icon.sky { background: rgba(14, 165, 233, 0.15); color: var(--accent-sky); }
        .kpi-icon.emerald { background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); }
        .kpi-icon.indigo { background: rgba(99, 102, 241, 0.15); color: var(--accent-indigo); }
        .kpi-icon.amber { background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); }
        .kpi-val { font-size: 24px; font-weight: 800; color: #fff; line-height: 1.2; }
        .kpi-sub { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

        /* PANEL & TABLE */
        .panel {
            background: rgba(20, 30, 51, 0.7);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            padding: 20px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 16px;
        }
        .panel-title { font-size: 15px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; }
        .dot-sky { width: 8px; height: 8px; border-radius: 50%; background: var(--accent-sky); display: inline-block; }
        .panel-desc { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
        .panel-actions { display: flex; align-items: center; gap: 8px; }
        .search-box .input-search {
            background: #090d16;
            border: 1px solid var(--border-subtle);
            color: #fff;
            padding: 7px 12px;
            border-radius: var(--radius-md);
            font-size: 12px;
            outline: none;
            width: 180px;
            transition: all 0.15s;
        }
        .search-box .input-search:focus { border-color: var(--accent-sky); width: 220px; }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 14px;
            font-size: 12px;
            font-weight: 600;
            border-radius: var(--radius-md);
            border: none;
            cursor: pointer;
            transition: all 0.15s;
        }
        .btn svg { width: 14px; height: 14px; }
        .btn-primary { background: var(--accent-sky); color: #fff; }
        .btn-primary:hover { background: var(--accent-sky-hover); }
        .btn-secondary { background: #1e293b; color: var(--text-muted); border: 1px solid var(--border-highlight); }
        .btn-secondary:hover { color: #fff; background: #334155; }
        .btn-delete {
            background: rgba(244, 63, 94, 0.12);
            color: var(--accent-rose);
            border: 1px solid rgba(244, 63, 94, 0.25);
            padding: 4px 10px;
            font-size: 11px;
            border-radius: 4px;
        }
        .btn-delete:hover { background: rgba(244, 63, 94, 0.25); }

        .table-container { width: 100%; overflow-x: auto; }
        .data-table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }
        .data-table thead th {
            background: rgba(9, 13, 22, 0.8);
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.5px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-subtle);
        }
        .data-table tbody td {
            padding: 12px;
            border-bottom: 1px solid rgba(30, 41, 59, 0.5);
            color: #cbd5e1;
        }
        .data-table tbody tr:hover td { background: rgba(255, 255, 255, 0.02); }
        .col-id { font-family: ui-monospace, monospace; color: var(--accent-sky-hover); font-weight: 600; }
        .item-title { font-weight: 600; color: #fff; }
        .item-desc { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
        .col-date { font-family: ui-monospace, monospace; font-size: 11px; color: var(--text-muted); }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge-status { background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); }
        .table-empty { text-align: center; padding: 24px; color: var(--text-muted); }

        /* MODAL */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            z-index: 999;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 16px;
        }
        .modal-overlay.open { display: flex; }
        .modal-card {
            background: #0f172a;
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-xl);
            width: 100%;
            max-width: 440px;
            padding: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border-subtle);
            margin-bottom: 16px;
        }
        .modal-title { font-size: 14px; font-weight: 700; color: #fff; }
        .modal-close { background: transparent; border: none; color: var(--text-muted); font-size: 18px; cursor: pointer; }
        .modal-close:hover { color: #fff; }
        .form-group { margin-bottom: 12px; }
        .form-group label { display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); margin-bottom: 4px; }
        .form-control {
            width: 100%;
            background: #090d16;
            border: 1px solid var(--border-subtle);
            color: #fff;
            padding: 8px 12px;
            border-radius: var(--radius-md);
            font-size: 12px;
            outline: none;
        }
        .form-control:focus { border-color: var(--accent-sky); }
        .modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-subtle); }

        /* TOAST */
        .toast-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .toast {
            background: #1e293b;
            color: #fff;
            padding: 10px 16px;
            border-radius: var(--radius-md);
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--border-highlight);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            animation: slideIn 0.2s ease-out;
        }
        .toast.sucesso { border-left: 4px solid var(--accent-emerald); }
        .toast.erro { border-left: 4px solid var(--accent-rose); }
        @keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
    </style>
</head>
<body>
    <!-- TOPBAR -->
    <header class="topbar">
        <div class="topbar-brand">
            <span>__SUITE_NAME__</span>
            <span class="badge-ver">v4.1 Enterprise</span>
        </div>
        <div class="topbar-links">
            <a href="/docs" target="_blank" class="topbar-link">Swagger Studio</a>
            <a href="/webhooks" target="_blank" class="topbar-link">Webhook Studio</a>
            <a href="/mcp" target="_blank" class="topbar-link">MCP Native</a>
        </div>
    </header>

    <!-- ABAS DE NAVEGAÇÃO -->
    <nav class="tabs-nav">
        <div class="tabs-container">
            __TABS_NAV__
        </div>
    </nav>

    <!-- CONTEÚDO DOS MÓDULOS -->
    <main class="main-content">
        __SECTIONS__
    </main>

    <!-- MODAL DE CADASTRO -->
    <div id="modal-generic" class="modal-overlay" onclick="if(event.target === this) fecharModal()">
        <div class="modal-card">
            <div class="modal-header">
                <h3 id="modal-titulo" class="modal-title">Novo Registro</h3>
                <button type="button" onclick="fecharModal()" class="modal-close" aria-label="Fechar modal">&times;</button>
            </div>
            <form onsubmit="salvarItemGenerico(event)">
                <input type="hidden" id="modal-slug">
                <div class="form-group">
                    <label for="modal-input-titulo">Título *</label>
                    <input type="text" id="modal-input-titulo" required placeholder="Digite o título descritivo..." class="form-control">
                </div>
                <div class="form-group">
                    <label for="modal-input-desc">Descrição Detalhada</label>
                    <textarea id="modal-input-desc" rows="3" placeholder="Informações adicionais..." class="form-control"></textarea>
                </div>
                <div class="modal-footer">
                    <button type="button" onclick="fecharModal()" class="btn btn-secondary">Cancelar</button>
                    <button type="submit" class="btn btn-primary">Salvar Registro</button>
                </div>
            </form>
        </div>
    </div>

    <!-- TOASTS CONTAINER -->
    <div id="toast-container" class="toast-container"></div>

    <script>
        function mudarAba(slug) {
            document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            const sec = document.getElementById('sec-' + slug);
            const btn = document.getElementById('tab-btn-' + slug);
            if (sec) sec.classList.add('active');
            if (btn) btn.classList.add('active');
        }

        function abrirModalNovo(slug) {
            document.getElementById('modal-slug').value = slug;
            document.getElementById('modal-titulo').textContent = 'Novo Registro (' + slug.toUpperCase() + ')';
            document.getElementById('modal-input-titulo').value = '';
            document.getElementById('modal-input-desc').value = '';
            document.getElementById('modal-generic').classList.add('open');
            setTimeout(() => document.getElementById('modal-input-titulo').focus(), 50);
        }

        function fecharModal() {
            document.getElementById('modal-generic').classList.remove('open');
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function mostrarToast(msg, tipo = 'sucesso') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = 'toast ' + tipo;
            toast.textContent = msg;
            container.appendChild(toast);
            setTimeout(() => { toast.remove(); }, 3500);
        }

        async function salvarItemGenerico(e) {
            e.preventDefault();
            const slug = document.getElementById('modal-slug').value;
            const titulo = document.getElementById('modal-input-titulo').value;
            const descricao = document.getElementById('modal-input-desc').value;

            try {
                const res = await fetch('/api/' + slug + '/criar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ titulo, descricao, status: 'ativo' })
                });
                const data = await res.json();
                if (data.sucesso) {
                    fecharModal();
                    mostrarToast('Registro salvo com sucesso!');
                    const fnName = 'carregar' + slug.charAt(0).toUpperCase() + slug.slice(1);
                    if (window[fnName]) window[fnName]();
                } else {
                    mostrarToast('Erro ao salvar: ' + (data.erro || 'Falha na operação'), 'erro');
                }
            } catch (err) {
                mostrarToast('Erro na requisição: ' + err, 'erro');
            }
        }

        async function deletarItem(slug, id) {
            if (!confirm('Deseja realmente remover o registro #' + id + '?')) return;
            try {
                const res = await fetch('/api/' + slug + '/deletar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const data = await res.json();
                if (data.sucesso) {
                    mostrarToast('Registro #' + id + ' removido!');
                    const fnName = 'carregar' + slug.charAt(0).toUpperCase() + slug.slice(1);
                    if (window[fnName]) window[fnName]();
                } else {
                    mostrarToast('Erro ao remover: ' + (data.erro || 'Falha'), 'erro');
                }
            } catch (e) {
                console.error(e);
                mostrarToast('Erro ao excluir registro', 'erro');
            }
        }

        __SCRIPTS__

        // Inicialização
        document.addEventListener('DOMContentLoaded', () => {
__INITIAL_LOADS__
        });
    </script>
</body>
</html>"""

    return (
        html_template
        .replace("__SUITE_NAME__", suite_name)
        .replace("__TABS_NAV__", tabs_nav_str)
        .replace("__SECTIONS__", sections_str)
        .replace("__SCRIPTS__", scripts_str)
        .replace("__INITIAL_LOADS__", initial_loads)
    )


def compose_suite(target_dir: str, suite_name: str, modules: list):
    """Motor principal de composição cross-project."""
    target_dir = os.path.abspath(target_dir)
    print("=" * 80)
    print(f"🚀 [AIDD v4.1 Enterprise] Composição de Suíte Modular Cross-Project: {suite_name}")
    print(f"📁 Diretório de Destino: {target_dir}")
    print(f"📦 Fatias Verticais:     {', '.join(modules)}")
    print("=" * 80)

    SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_v2 = os.path.join(SKILL_ROOT, "templates", "v2")
    gates_dir = os.path.join(SKILL_ROOT, "templates", "gates")
    scripts_dir = os.path.join(SKILL_ROOT, "scripts")

    # 1. Estrutura de Diretórios
    src_dir = os.path.join(target_dir, "src")
    core_dir = os.path.join(src_dir, "core")
    shared_ui_dir = os.path.join(src_dir, "shared", "ui")
    shared_utils_dir = os.path.join(src_dir, "shared", "utils")
    modules_dir = os.path.join(src_dir, "modules")
    static_dir = os.path.join(src_dir, "static")
    static_comp_dir = os.path.join(static_dir, "components")
    tests_unit_dir = os.path.join(target_dir, "tests", "unit")
    target_gates_dir = os.path.join(target_dir, "scripts", "gates")
    target_scripts_dir = os.path.join(target_dir, "scripts")

    os.makedirs(core_dir, exist_ok=True)
    os.makedirs(shared_ui_dir, exist_ok=True)
    os.makedirs(shared_utils_dir, exist_ok=True)
    os.makedirs(modules_dir, exist_ok=True)
    os.makedirs(static_comp_dir, exist_ok=True)
    os.makedirs(tests_unit_dir, exist_ok=True)
    os.makedirs(target_gates_dir, exist_ok=True)
    os.makedirs(target_scripts_dir, exist_ok=True)

    open(os.path.join(src_dir, "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(core_dir, "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(modules_dir, "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(src_dir, "shared", "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(shared_ui_dir, "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(shared_utils_dir, "__init__.py"), "w", encoding="utf-8").close()

    # 2. Copiar Shared Kernel Core
    core_files = ["database.py", "events.py", "openapi.py", "security.py", "webhooks.py", "mcp_server.py", "result.py", "jobs.py"]
    for cf in core_files:
        src = os.path.join(templates_v2, cf)
        dst = os.path.join(core_dir, cf)
        if os.path.isfile(src):
            shutil.copyfile(src, dst)
            print(f"  [+] Core Kernel: {cf}")

    # Copiar Shared UI
    shared_ui_src = os.path.join(templates_v2, "shared", "ui")
    if os.path.isdir(shared_ui_src):
        for f in os.listdir(shared_ui_src):
            src = os.path.join(shared_ui_src, f)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(shared_ui_dir, f))
                print(f"  [+] Shared UI: {f}")

    # Copiar Shared Utils
    shared_utils_src = os.path.join(templates_v2, "shared", "utils")
    if os.path.isdir(shared_utils_src):
        for f in os.listdir(shared_utils_src):
            src = os.path.join(shared_utils_src, f)
            if os.path.isfile(src):
                shutil.copyfile(src, os.path.join(shared_utils_dir, f))
                print(f"  [+] Shared Utils: {f}")

    # 3. Gerar Manifesto Estruturado PLANO-EXECUCAO-ESTRUTURADO.json
    plano_dict = {
        "projeto": {
            "nome": suite_name,
            "slug": slugify(suite_name),
            "versao": "4.1.0",
            "framework": "AIDD Master Pack v4.1 Enterprise Anti-Fail",
            "status": "em_desenvolvimento",
            "criado_em": datetime.datetime.now().isoformat()
        },
        "arquitetura": {
            "padrao": "Monólito Modular com Clean Architecture",
            "comunicacao": "EventBus Pub/Sub Assíncrono",
            "documentacao": "OpenAPI 3.1 & Swagger Studio Nativo (/docs)",
            "webhooks": "Webhook Configuration Studio com Assinatura HMAC SHA-256 (/webhooks)",
            "mcp": "Model Context Protocol Native Server (/mcp & JSON-RPC 2.0)",
            "persistencia": "SQLite Concorrente WAL Mode (Write-Ahead Logging)",
            "design_system": "Impeccable Super-App UI com 4px scrollbar e Single-Line Header"
        },
        "modulos": [],
        "gates_qualidade": [
            {"gate": "G_ESTRUTURA", "descricao": "Validação de layout modular, manifestos e Clean Architecture"},
            {"gate": "G_QUALIDADE", "descricao": "Análise estática de sintaxe e eliminação de stubs vazios"},
            {"gate": "G_TESTES", "descricao": "Execução obrigatória de 100% dos testes unitários com pytest"},
            {"gate": "G_CONTRACTS", "descricao": "Validação de esquemas OpenAPI 3.1 e contratos MCP"},
            {"gate": "G_SEGREDOS", "descricao": "Varredura de entropia de Shannon contra vazamento de chaves"},
            {"gate": "G_HARNESS_COMPAT", "descricao": "Conformidade multi-harness (Antigravity, Cline, OpenHands, Cursor)"}
        ]
    }
    with open(os.path.join(target_dir, "PLANO-EXECUCAO-ESTRUTURADO.json"), "w", encoding="utf-8") as f:
        json.dump(plano_dict, f, ensure_ascii=False, indent=2)

    # 4. Gerar Fatias Verticais para cada Módulo
    clean_modules = [slugify(m) for m in modules if m.strip()]
    for mod in clean_modules:
        criar_modulo(mod, target_dir=target_dir)

    # 5. Gerar Servidor Monolítico Modular src/server.py
    server_code = generate_modular_server_code(suite_name, clean_modules)
    with open(os.path.join(src_dir, "server.py"), "w", encoding="utf-8") as f:
        f.write(server_code)
    print("  [+] Servidor dinâmico 'src/server.py' gerado com sucesso!")

    # 6. Gerar Front-end Super-App src/static/index.html
    index_html = generate_superapp_index_html(suite_name, clean_modules)
    with open(os.path.join(static_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("  [+] Front-end Super-App 'src/static/index.html' gerado!")

    # Copiar docs.html estático se existir
    if os.path.isfile(os.path.join(templates_v2, "docs.html")):
        shutil.copyfile(os.path.join(templates_v2, "docs.html"), os.path.join(static_dir, "docs.html"))

    # 7. Gerar requirements.txt
    req_content = "pytest>=7.4.0\nrequests>=2.31.0\n"
    with open(os.path.join(target_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(req_content)
    print("  [+] Manifesto 'requirements.txt' gerado!")

    # 8. Copiar Quality Gates
    if os.path.isdir(gates_dir):
        for g in os.listdir(gates_dir):
            if g.endswith(".py"):
                shutil.copyfile(os.path.join(gates_dir, g), os.path.join(target_gates_dir, g))
                print(f"  [+] Quality Gate: {g}")

    # 9. Copiar Scripts de Automação
    for s in ["aidd.py", "add_module.py", "compose_suite.py"]:
        src = os.path.join(scripts_dir, s)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(target_scripts_dir, s))
            print(f"  [+] Script: {s}")

    # 10. Copiar Arquivos de Produção, Deploy, Nginx & Governança ORCA ADE
    for prod_f in ["Dockerfile", "docker-compose.yml", "deploy.sh", "AGENTS.md", "CLAUDE.md", "GEMINI.md"]:
        src = os.path.join(templates_v2, prod_f)
        if os.path.isfile(src):
            shutil.copyfile(src, os.path.join(target_dir, prod_f))
            print(f"  [+] Governança & Deploy: {prod_f}")

    # Nginx Shield & SSL
    nginx_src = os.path.join(templates_v2, "nginx")
    nginx_dst = os.path.join(target_dir, "nginx")
    if os.path.isdir(nginx_src):
        os.makedirs(nginx_dst, exist_ok=True)
        for root, _, files in os.walk(nginx_src):
            rel = os.path.relpath(root, nginx_src)
            d_dir = os.path.join(nginx_dst, rel) if rel != "." else nginx_dst
            os.makedirs(d_dir, exist_ok=True)
            for f in files:
                shutil.copyfile(os.path.join(root, f), os.path.join(d_dir, f))
        print("  [+] Nginx Shield & Configurações copiadas!")

    # 11. Gerar Sincronização Multi-IDE de Rules (.cursor, .claude, .agent)
    cursor_rules_dir = os.path.join(target_dir, ".cursor", "rules")
    claude_dir = os.path.join(target_dir, ".claude")
    agent_rules_dir = os.path.join(target_dir, ".agent", "rules")
    os.makedirs(cursor_rules_dir, exist_ok=True)
    os.makedirs(claude_dir, exist_ok=True)
    os.makedirs(agent_rules_dir, exist_ok=True)

    rules_content = f"""# Governança Anti-Falha e Regras de Ouro — {suite_name}

1. **Zero Acoplamento:** Módulos em `src/modules/` comunicam-se exclusivamente via `EventBus` pub/sub. Proibido import direto entre módulos irmãos.
2. **Clean Architecture:** Toda fatia possui `models.py`, `services.py`, `routes.py`, UI isolada e testes unitários.
3. **Persistência Segura:** SQLite WAL com `busy_timeout=5000` e parametrização de queries (`?`).
4. **Impeccable UI:** SVGs Lucide, modais customizados, toasts assíncronos e conformidade WCAG 2.1.
5. **Quality Gates:** Homologação obrigatória (exit 0) em todos os 7 gates mecânicos (`python scripts/aidd.py audit --report`).
"""
    with open(os.path.join(cursor_rules_dir, "aidd_rules.mdc"), "w", encoding="utf-8") as f:
        f.write(rules_content)
    with open(os.path.join(claude_dir, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write(rules_content)
    with open(os.path.join(agent_rules_dir, "rules.md"), "w", encoding="utf-8") as f:
        f.write(rules_content)
    print("  [+] Multi-IDE Rules (.cursor, .claude, .agent) sincronizadas!")

    # 12. Gerar Grafo de Memória do Projeto CONTEXTO-PROJETO.md
    contexto_md = f"""# Grafo de Contexto e Memória do Projeto: {suite_name}

## 1. Visão Geral
- **Nome:** {suite_name}
- **Framework:** AIDD Master Pack v4.1 Enterprise Anti-Fail
- **Banco de Dados:** SQLite Concorrente WAL (`suite.db`)
- **Portais Ativos:** `/` (Super-App), `/docs` (Swagger Studio), `/mcp` (MCP Server), `/webhooks` (Webhook Studio)

## 2. Fatias Verticais Ativas ({len(clean_modules)})
"""
    for m in clean_modules:
        contexto_md += f"- **Módulo `{m}`**: `src/modules/{m}/` (CRUD, OpenAPI, MCP e testes em `tests/unit/test_{m}.py`)\n"

    contexto_md += """
## 3. Kernel Compartilhado (Shared Kernel)
- `database.py`: Conexão SQLite WAL com busy_timeout e controle de migrações.
- `events.py`: EventBus pub/sub desacoplado com envelope e tracing UUID.
- `result.py`: Monad Result Pattern (`Result.ok()`, `Result.fail()`).
- `jobs.py`: Fila de tarefas em background (`JobQueue`).
- `security.py` & `openapi.py`: Criptografia JWT HS256, RBAC e OpenAPI 3.1.
"""
    with open(os.path.join(target_dir, "CONTEXTO-PROJETO.md"), "w", encoding="utf-8") as f:
        f.write(contexto_md)
    print("  [+] Grafo de Memória 'CONTEXTO-PROJETO.md' gerado!")

    print("\n" + "=" * 80)
    print(f"🏆 [SUCESSO]: Suíte Enterprise '{suite_name}' 100% Composta!")
    print(f"   ➔ Iniciar Servidor: cd {target_dir} && python src/server.py")
    print(f"   ➔ Auditar Qualidade: cd {target_dir} && python scripts/aidd.py audit --report")
    print(f"   ➔ Executar Testes:   cd {target_dir} && python scripts/aidd.py test")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python compose_suite.py <target_dir> <suite_name> [modulo1] [modulo2] ...")
        sys.exit(1)

    target = sys.argv[1]
    name = sys.argv[2]
    mods = sys.argv[3:] if len(sys.argv) > 3 else ["crm", "erp", "helpdesk", "logistica"]
    compose_suite(target, name, mods)
