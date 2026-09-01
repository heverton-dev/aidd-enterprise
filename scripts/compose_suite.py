#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIDD v4.1 — Enterprise Suite Composition Engine
Compõe múltiplos domínios em um Monólito Modular com:
- EventBus Cross-Domain
- Webhook Dispatcher com HMAC SHA-256
- Swagger Studio OpenAPI 3.1 Unificado
- Servidor Nativo MCP (Model Context Protocol)
- Front-end Super-App Impeccable
- Suíte de Quality Gates Rígidos
"""

import os, sys, shutil, json
from add_module import criar_modulo

def compose_suite(target_dir: str, suite_name: str, modules: list):
    print(f"[*] Iniciando composição da Suite Enterprise v4.1: {suite_name}")
    print(f"[*] Módulos selecionados: {', '.join(modules)}")
    
    # 1. Estrutura base de diretórios
    os.makedirs(os.path.join(target_dir, "src", "core"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src", "shared", "ui"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src", "static"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src", "modules"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "tests", "unit"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "scripts", "gates"), exist_ok=True)

    open(os.path.join(target_dir, "src", "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(target_dir, "src", "core", "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(target_dir, "src", "modules", "__init__.py"), "w", encoding="utf-8").close()
    open(os.path.join(target_dir, "tests", "__init__.py"), "w", encoding="utf-8").close()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_v2 = os.path.join(base_dir, "templates", "v2")
    templates_gates = os.path.join(base_dir, "templates", "gates")

    # 2. Copiar Shared Kernel
    if os.path.exists(templates_v2):
        for f in ["database.py", "events.py", "webhooks.py", "security.py", "openapi.py", "mcp_server.py"]:
            src_f = os.path.join(templates_v2, f)
            dst_f = os.path.join(target_dir, "src", "core", f)
            if os.path.exists(src_f):
                shutil.copyfile(src_f, dst_f)
                print(f"  [+] Core Kernel: {f}")

        # Copiar UI estática base
        for sf in ["index.html", "docs.html"]:
            src_sf = os.path.join(templates_v2, sf)
            dst_sf = os.path.join(target_dir, "src", "static", sf)
            if os.path.exists(src_sf):
                shutil.copyfile(src_sf, dst_sf)
                print(f"  [+] Static Portal: {sf}")

    # 3. Gerar cada fatia vertical via add_module
    for mod in modules:
        criar_modulo(mod, f"Módulo de {mod}", target_dir)

    # 4. Copiar Gates Rígidos
    if os.path.exists(templates_gates):
        for g in os.listdir(templates_gates):
            if g.endswith(".py"):
                shutil.copyfile(os.path.join(templates_gates, g), os.path.join(target_dir, "scripts", "gates", g))
                print(f"  [+] Quality Gate: {g}")

    # Copiar scripts aidd.py e add_module.py
    scripts_src = os.path.join(base_dir, "scripts")
    for s in ["aidd.py", "add_module.py"]:
        src_s = os.path.join(scripts_src, s)
        dst_s = os.path.join(target_dir, "scripts", s)
        if os.path.exists(src_s):
            shutil.copyfile(src_s, dst_s)

    # 5. Gerar requirements.txt
    req_content = """pytest>=7.0.0
requests>=2.28.0
locust>=2.15.0
"""
    with open(os.path.join(target_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(req_content)
    print("  [+] requirements.txt gerado com sucesso.")

    # 6. Gerar PLANO-EXECUCAO-ESTRUTURADO.json
    plano_data = {
        "projeto": {
            "nome": suite_name,
            "descricao": f"Suite Enterprise Modular {suite_name}",
            "arquitetura": "AIDD v4.1 Cross-Domain Monolith",
            "zero_api_key_mode": True,
            "status": "INICIALIZADO",
            "modulos_ativos": modules
        },
        "fases": [
            {
                "id": "fase-01-scaffolding",
                "nome": "Composição e Inicialização do Kernel",
                "status": "CONCLUIDO",
                "mesa_orca": "mesa-arquitetura"
            },
            {
                "id": "fase-02-fatias-verticais",
                "nome": "Implementação das Fatias Verticais e Full CRUD",
                "status": "EM_ANDAMENTO",
                "mesa_orca": "mesa-dev"
            },
            {
                "id": "fase-03-auditoria-gates",
                "nome": "Auditoria de Gates Rígidos e Testes Unitários",
                "status": "PENDENTE",
                "mesa_orca": "mesa-qa"
            }
        ]
    }
    with open(os.path.join(target_dir, "PLANO-EXECUCAO-ESTRUTURADO.json"), "w", encoding="utf-8") as f:
        json.dump(plano_data, f, indent=2, ensure_ascii=False)
    print("  [+] PLANO-EXECUCAO-ESTRUTURADO.json gerado.")

    # 7. Gerar server.py modular dinâmico
    server_code = '''import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.database import Database
from core.events import EventBus
from core.webhooks import WebhookDispatcher
from core.mcp_server import MCPServer
from core.openapi import RouteRegistry

# Inicialização do Core
db = Database()
event_bus = EventBus()
webhook_dispatcher = WebhookDispatcher(db)
mcp = MCPServer(db)
registry = RouteRegistry()

# Inicialização Dinâmica dos Módulos
'''
    for mod in modules:
        server_code += f'''from modules.{mod}.models import init_schema as init_{mod}_schema
from modules.{mod}.services import {mod.capitalize()}Service
from modules.{mod}.routes import registrar_rotas as reg_{mod}_rotas

with db.get_connection() as conn:
    init_{mod}_schema(conn)

{mod}_service = {mod.capitalize()}Service(db, event_bus)
reg_{mod}_rotas({mod}_service)
'''

    server_code += '''
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

def load_static(filename):
    path = os.path.join(STATIC_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

class ModularSuiteHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Webhook-Signature")

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html_str, status=200):
        body = html_str.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in ["/", "/index.html"]:
            return self._html(load_static("index.html"))
        if path in ["/docs", "/docs/"]:
            return self._html(registry.get_swagger_html())
        if path == "/openapi.json":
            return self._json(registry.get_openapi_spec())
        if path == "/health":
            return self._json({"status": "healthy", "suite": "''' + suite_name + '''", "version": "4.1.0"})

        # Roteamento dinâmico via RouteRegistry
        handler = registry.routes["GET"].get(path)
        if handler:
            try:
                res = handler(params)
                return self._json(res)
            except Exception as e:
                return self._json({"erro": str(e)}, 500)

        self._json({"erro": "Rota não encontrada", "path": path}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        if path == "/mcp":
            res = mcp.handle_request(json.dumps(body))
            return self._json(res)

        handler = registry.routes["POST"].get(path)
        if handler:
            try:
                res = handler(body)
                return self._json(res, 201)
            except Exception as e:
                return self._json({"erro": str(e)}, 500)

        self._json({"erro": "Rota não encontrada", "path": path}, 404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        handler = registry.routes["PUT"].get(path)
        if handler:
            try:
                res = handler(body)
                return self._json(res)
            except Exception as e:
                return self._json({"erro": str(e)}, 500)

        self._json({"erro": "Rota não encontrada", "path": path}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}

        handler = registry.routes["DELETE"].get(path)
        if handler:
            try:
                res = handler(body)
                return self._json(res)
            except Exception as e:
                return self._json({"erro": str(e)}, 500)

        self._json({"erro": "Rota não encontrada", "path": path}, 404)

def run(port=3000):
    server = HTTPServer(("0.0.0.0", port), ModularSuiteHandler)
    print(f"🚀 [AIDD v4.1] Suite '{suite_name}' operacional em http://localhost:{port}")
    print(f"📚 Swagger Studio OpenAPI: http://localhost:{port}/docs")
    print(f"🤖 Servidor MCP: http://localhost:{port}/mcp")
    server.serve_forever()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run(port)
'''
    with open(os.path.join(target_dir, "src", "server.py"), "w", encoding="utf-8") as f:
        f.write(server_code)
    print("  [+] src/server.py modular gerado com sucesso!")

    print(f"\n[OK] Suite Enterprise '{suite_name}' 100% composta com sucesso em: {target_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python compose_suite.py <target_dir> <suite_name> [modulo1] [modulo2] ...")
        sys.exit(1)

    target = sys.argv[1]
    name = sys.argv[2]
    mods = sys.argv[3:] if len(sys.argv) > 3 else ["crm", "erp", "helpdesk", "logistica"]
    compose_suite(target, name, mods)
