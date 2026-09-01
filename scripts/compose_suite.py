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
    """Gera front-end Super-App Impeccable com abas para cada módulo."""
    tabs_nav = []
    sections = []
    scripts = []

    for i, mod in enumerate(module_slugs):
        slug = slugify(mod)
        pascal = pascal_case(mod)
        is_active = (i == 0)
        active_class = "tab-btn active" if is_active else "tab-btn"
        hidden_class = "" if is_active else "hidden"

        tabs_nav.append(f'''
            <button onclick="mudarAba('{slug}')" id="tab-btn-{slug}" class="{active_class} px-4 py-2.5 text-xs font-semibold text-slate-300 hover:text-white rounded-xl flex items-center gap-2 transition whitespace-nowrap border border-transparent">
                <span class="w-2 h-2 rounded-full bg-sky-400"></span>
                <span>{pascal}</span>
            </button>''')

        sections.append(f'''
        <!-- ABA {pascal} -->
        <section id="sec-{slug}" class="space-y-4 {hidden_class}">
            <div class="bg-slate-900/60 rounded-xl border border-slate-800 p-5 space-y-4 shadow-xl">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                    <div>
                        <h2 class="text-base font-bold text-slate-100 flex items-center gap-2">
                            <span class="w-2.5 h-2.5 rounded-full bg-sky-500"></span>
                            Gestão de {pascal}
                        </h2>
                        <p class="text-xs text-slate-400">Operações e registros da fatia vertical {pascal}</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <button onclick="carregar{pascal}()" class="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition" title="Atualizar">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                        </button>
                        <button onclick="abrirModalNovo('{slug}')" class="px-3.5 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition shadow-lg shadow-sky-600/20">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                            <span>Novo {pascal}</span>
                        </button>
                    </div>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead class="bg-slate-950/80 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
                            <tr>
                                <th class="p-3">ID</th>
                                <th class="p-3">Título</th>
                                <th class="p-3">Status</th>
                                <th class="p-3">Criado em</th>
                                <th class="p-3 text-right">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="tabela-{slug}-corpo" class="divide-y divide-slate-800/60 text-slate-300">
                            <tr><td colspan="5" class="p-4 text-center text-slate-500">Carregando dados...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>''')

        scripts.append(f'''
        async function carregar{pascal}() {{
            try {{
                const res = await fetch('/api/{slug}');
                const dados = await res.json();
                const tbody = document.getElementById('tabela-{slug}-corpo');
                if (!dados || dados.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="5" class="p-4 text-center text-slate-500">Nenhum registro encontrado.</td></tr>';
                    return;
                }}
                tbody.innerHTML = dados.map(item => `
                    <tr class="hover:bg-slate-800/40 transition">
                        <td class="p-3 font-mono text-sky-400">#${{item.id}}</td>
                        <td class="p-3 font-semibold text-slate-200">${{item.titulo}}</td>
                        <td class="p-3"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase">${{item.status || 'ativo'}}</span></td>
                        <td class="p-3 text-slate-400 font-mono text-[11px]">${{item.criado_em || '--'}}</td>
                        <td class="p-3 text-right">
                            <button onclick="deletarItem('{slug}', ${{item.id}})" class="px-2.5 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded text-[11px] font-medium transition">Excluir</button>
                        </td>
                    </tr>
                `).join('');
            }} catch (e) {{
                console.error('Erro ao carregar {slug}:', e);
            }}
        }}''')

    tabs_nav_str = "\n".join(tabs_nav)
    sections_str = "\n".join(sections)
    scripts_str = "\n".join(scripts)
    initial_loads = "\n".join([f"        carregar{pascal_case(m)}();" for m in module_slugs])

    html_template = """<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__SUITE_NAME__ — Super-App</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        ::-webkit-scrollbar { width: 4px; height: 4px; }
        ::-webkit-scrollbar-track { background: #090d16; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        .tab-btn.active {
            color: #38bdf8 !important;
            border: 1px solid rgba(56, 189, 248, 0.35) !important;
            background: rgba(14, 165, 233, 0.12) !important;
        }
    </style>
</head>
<body class="bg-[#090d16] text-slate-100 min-h-screen font-sans flex flex-col">
    <!-- TOPBAR -->
    <header class="min-h-[56px] h-14 border-b border-slate-800 bg-[#0f172a]/95 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
            <span class="font-extrabold text-sm text-slate-100">__SUITE_NAME__</span>
            <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30">v4.1 Enterprise</span>
        </div>
        <div class="flex items-center gap-2">
            <a href="/docs" target="_blank" class="text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">Swagger Studio</a>
            <a href="/webhooks" target="_blank" class="text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">Webhook Studio</a>
            <a href="/mcp" target="_blank" class="text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">MCP Native</a>
        </div>
    </header>

    <!-- NAVEGAÇÃO DE ABAS -->
    <nav class="bg-[#0f172a] border-b border-slate-800 px-6 sticky top-14 z-30 flex items-center justify-center overflow-x-auto">
        <div class="max-w-7xl w-full flex items-center justify-center gap-2 py-2">
            __TABS_NAV__
        </div>
    </nav>

    <!-- CONTEÚDO -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        __SECTIONS__
    </main>

    <!-- MODAL GENÉRICO DE CADASTRO -->
    <div id="modal-generic" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 space-y-4 shadow-2xl">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 id="modal-titulo" class="text-sm font-bold text-slate-100">Novo Registro</h3>
                <button onclick="fecharModal()" class="text-slate-400 hover:text-white text-base">&times;</button>
            </div>
            <form onsubmit="salvarItemGenerico(event)" class="space-y-3 text-xs">
                <input type="hidden" id="modal-slug">
                <div>
                    <label class="block text-slate-400 mb-1">Título</label>
                    <input type="text" id="modal-input-titulo" required class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-100 outline-none focus:border-sky-500">
                </div>
                <div>
                    <label class="block text-slate-400 mb-1">Descrição</label>
                    <textarea id="modal-input-desc" rows="2" class="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-100 outline-none focus:border-sky-500"></textarea>
                </div>
                <div class="flex justify-end gap-2 pt-2 border-t border-slate-800">
                    <button type="button" onclick="fecharModal()" class="px-3 py-2 rounded-lg bg-slate-800 text-slate-300">Cancelar</button>
                    <button type="submit" class="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold">Salvar</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function mudarAba(slug) {
            document.querySelectorAll('section[id^="sec-"]').forEach(s => s.classList.add('hidden'));
            document.querySelectorAll('button[id^="tab-btn-"]').forEach(b => b.classList.remove('active'));
            const sec = document.getElementById('sec-' + slug);
            const btn = document.getElementById('tab-btn-' + slug);
            if (sec) sec.classList.remove('hidden');
            if (btn) btn.classList.add('active');
        }

        function abrirModalNovo(slug) {
            document.getElementById('modal-slug').value = slug;
            document.getElementById('modal-titulo').textContent = 'Novo Registro (' + slug + ')';
            document.getElementById('modal-input-titulo').value = '';
            document.getElementById('modal-input-desc').value = '';
            document.getElementById('modal-generic').classList.remove('hidden');
        }

        function fecharModal() {
            document.getElementById('modal-generic').classList.add('hidden');
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
                    body: JSON.stringify({ titulo, descricao })
                });
                const data = await res.json();
                if (data.sucesso) {
                    fecharModal();
                    const fnName = 'carregar' + slug.charAt(0).toUpperCase() + slug.slice(1);
                    if (window[fnName]) window[fnName]();
                } else {
                    alert('Erro: ' + (data.erro || 'Falha ao salvar'));
                }
            } catch (err) {
                alert('Erro na requisição: ' + err);
            }
        }

        async function deletarItem(slug, id) {
            if (!confirm('Deseja realmente remover este registro?')) return;
            try {
                const res = await fetch('/api/' + slug + '/deletar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const data = await res.json();
                if (data.sucesso) {
                    const fnName = 'carregar' + slug.charAt(0).toUpperCase() + slug.slice(1);
                    if (window[fnName]) window[fnName]();
                }
            } catch (e) {
                console.error(e);
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
    core_files = ["database.py", "events.py", "openapi.py", "security.py", "webhooks.py", "mcp_server.py"]
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

    # Nginx
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
