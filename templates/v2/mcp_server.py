# -*- coding: utf-8 -*-
"""
=============================================================================
AIDD v4.1 Enterprise — Shared Kernel MCP Server (mcp_server.py)
=============================================================================
Servidor nativo Model Context Protocol (MCP) compatível com JSON-RPC 2.0.
Permite integração direta com Claude Desktop, Cursor, Antigravity e agentes autônomos.
Suporta registro dinâmico de ferramentas para módulos e fatias verticais.
"""

import json
import sqlite3
import sys
import os
import re
from typing import Dict, List, Any, Optional, Callable


def _sanitize_ident(ident: str) -> str:
    """Valida e sanitiza identificadores de tabelas e colunas."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '', str(ident).strip())
    if not clean:
        raise ValueError(f"Identificador inválido: {ident}")
    return clean


class MCPServer:
    """Servidor Universal Model Context Protocol (MCP) para Monólitos Modulares."""

    TOOLS = [
        {
            "name": "sistema_saude_status",
            "description": "Retorna o status operacional, versão do framework e módulos ativos no ecossistema.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "detalhado": {"type": "boolean", "description": "Se verdadeiro, inclui métricas de tabelas e contagem de registros"}
                }
            }
        },
        {
            "name": "sistema_executar_consulta",
            "description": "Executa uma consulta SQL segura de leitura (SELECT) no banco de dados SQLite WAL da suíte.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tabela": {"type": "string", "description": "Nome da tabela a ser consultada"},
                    "limite": {"type": "integer", "description": "Número máximo de registros a retornar (default 50)"}
                },
                "required": ["tabela"]
            }
        }
    ]

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "suite.db")
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.tools: List[Dict[str, Any]] = [t.copy() for t in self.TOOLS]

        self._handlers["sistema_saude_status"] = self._handle_saude_status
        self._handlers["sistema_executar_consulta"] = self._handle_executar_consulta

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Optional[Callable] = None):
        """Registra uma nova ferramenta no servidor MCP."""
        tool_def = {
            "name": name,
            "description": description,
            "inputSchema": input_schema if input_schema and input_schema.get("type") == "object" else {"type": "object", "properties": {}}
        }
        self.tools = [t for t in self.tools if t["name"] != name]
        self.tools.append(tool_def)
        if handler:
            self._handlers[name] = handler

    def register_module_tools(self, module_slug: str, module_name: str):
        """Registra automaticamente ferramentas CRUD para um módulo/fatia vertical."""
        slug = _sanitize_ident(module_slug.lower().strip())
        pascal = module_name

        self.register_tool(
            name=f"{slug}_listar",
            description=f"Lista todos os registros cadastrados no módulo {pascal}.",
            input_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "Filtrar por status (ex: ativo, inativo, concluido)"},
                    "apenas_ativos": {"type": "boolean", "description": "Se verdadeiro, filtra apenas itens ativos"}
                }
            },
            handler=lambda args, s=slug: self._generic_listar(s, args)
        )

        self.register_tool(
            name=f"{slug}_obter_por_id",
            description=f"Recupera os detalhes completos de um registro do módulo {pascal} pelo ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID do registro a consultar"}
                },
                "required": ["id"]
            },
            handler=lambda args, s=slug: self._generic_obter(s, args)
        )

        self.register_tool(
            name=f"{slug}_criar",
            description=f"Cria um novo registro no módulo {pascal} e emite evento no EventBus.",
            input_schema={
                "type": "object",
                "properties": {
                    "titulo": {"type": "string", "description": "Título identificador do item"},
                    "descricao": {"type": "string", "description": "Descrição detalhada"},
                    "status": {"type": "string", "description": "Status inicial (default 'ativo')"},
                    "dados": {"type": "object", "description": "Dados customizados em formato JSON"}
                },
                "required": ["titulo"]
            },
            handler=lambda args, s=slug: self._generic_criar(s, args)
        )

        self.register_tool(
            name=f"{slug}_atualizar",
            description=f"Atualiza as informações de um registro existente no módulo {pascal}.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID do registro a atualizar"},
                    "titulo": {"type": "string", "description": "Novo título"},
                    "descricao": {"type": "string", "description": "Nova descrição"},
                    "status": {"type": "string", "description": "Novo status"}
                },
                "required": ["id"]
            },
            handler=lambda args, s=slug: self._generic_atualizar(s, args)
        )

        self.register_tool(
            name=f"{slug}_deletar",
            description=f"Exclui permanentemente um registro do módulo {pascal}.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID do registro a remover"}
                },
                "required": ["id"]
            },
            handler=lambda args, s=slug: self._generic_deletar(s, args)
        )

    def _handle_saude_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        detalhado = args.get("detalhado", False)
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tabelas_raw = cur.fetchall()
            tabelas = [r[0] for r in tabelas_raw]
            info_tabelas = {}
            if detalhado:
                for t in tabelas:
                    clean_t = _sanitize_ident(t)
                    count_sql = "SELECT COUNT(*) FROM " + clean_t
                    cur.execute(count_sql)
                    res = cur.fetchone()
                    info_tabelas[t] = res[0] if res else 0

            return {
                "sucesso": True,
                "status": "online",
                "versao": "4.1.0 Enterprise",
                "total_ferramentas_mcp": len(self.tools),
                "tabelas_ativas": tabelas,
                "detalhes": info_tabelas if detalhado else None
            }

    def _handle_executar_consulta(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tabela = _sanitize_ident(args.get("tabela", ""))
        limite = int(args.get("limite", 50))
        if not tabela:
            return {"sucesso": False, "erro": "Nome da tabela é obrigatório"}

        with self._get_conn() as conn:
            cur = conn.cursor()
            query_sql = "SELECT * FROM " + tabela + " LIMIT ?"
            cur.execute(query_sql, (limite,))
            rows = cur.fetchall()
            return {
                "sucesso": True,
                "total": len(rows),
                "registros": [dict(r) for r in rows]
            }

    def _generic_listar(self, slug: str, args: Dict[str, Any]) -> Dict[str, Any]:
        table = "mod_" + _sanitize_ident(slug)
        status = args.get("status")
        apenas_ativos = args.get("apenas_ativos", True)
        with self._get_conn() as conn:
            cur = conn.cursor()
            conditions = ["1=1"]
            params = []
            if apenas_ativos:
                conditions.append("ativo = 1")
            if status:
                conditions.append("status = ?")
                params.append(status)

            where_clause = " AND ".join(conditions)
            sql = "SELECT * FROM " + table + " WHERE " + where_clause + " ORDER BY id DESC"
            try:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return {"sucesso": True, "modulo": slug, "total": len(rows), "itens": [dict(r) for r in rows]}
            except Exception as e:
                return {"sucesso": False, "modulo": slug, "erro": str(e)}

    def _generic_obter(self, slug: str, args: Dict[str, Any]) -> Dict[str, Any]:
        table = "mod_" + _sanitize_ident(slug)
        item_id = int(args.get("id", 0))
        with self._get_conn() as conn:
            cur = conn.cursor()
            sql = "SELECT * FROM " + table + " WHERE id = ?"
            try:
                cur.execute(sql, (item_id,))
                row = cur.fetchone()
                if row:
                    return {"sucesso": True, "modulo": slug, "item": dict(row)}
                return {"sucesso": False, "modulo": slug, "erro": "Registro não encontrado"}
            except Exception as e:
                return {"sucesso": False, "modulo": slug, "erro": str(e)}

    def _generic_criar(self, slug: str, args: Dict[str, Any]) -> Dict[str, Any]:
        table = "mod_" + _sanitize_ident(slug)
        titulo = args.get("titulo", "").strip()
        descricao = args.get("descricao", "")
        status = args.get("status", "ativo")
        dados = json.dumps(args.get("dados", {}), ensure_ascii=False)
        with self._get_conn() as conn:
            cur = conn.cursor()
            sql = "INSERT INTO " + table + " (titulo, descricao, dados_json, status, ativo) VALUES (?, ?, ?, ?, 1)"
            try:
                cur.execute(sql, (titulo, descricao, dados, status))
                conn.commit()
                return {"sucesso": True, "modulo": slug, "id": cur.lastrowid, "titulo": titulo}
            except Exception as e:
                return {"sucesso": False, "modulo": slug, "erro": str(e)}

    def _generic_atualizar(self, slug: str, args: Dict[str, Any]) -> Dict[str, Any]:
        table = "mod_" + _sanitize_ident(slug)
        item_id = int(args.get("id", 0))
        with self._get_conn() as conn:
            cur = conn.cursor()
            sel_sql = "SELECT * FROM " + table + " WHERE id = ?"
            try:
                cur.execute(sel_sql, (item_id,))
                row = cur.fetchone()
                if not row:
                    return {"sucesso": False, "erro": "Registro não encontrado"}
                novo_titulo = args.get("titulo", row["titulo"])
                nova_desc = args.get("descricao", row["descricao"])
                novo_status = args.get("status", row["status"])
                up_sql = "UPDATE " + table + " SET titulo = ?, descricao = ?, status = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?"
                cur.execute(up_sql, (novo_titulo, nova_desc, novo_status, item_id))
                conn.commit()
                return {"sucesso": True, "modulo": slug, "id": item_id, "status": novo_status}
            except Exception as e:
                return {"sucesso": False, "modulo": slug, "erro": str(e)}

    def _generic_deletar(self, slug: str, args: Dict[str, Any]) -> Dict[str, Any]:
        table = "mod_" + _sanitize_ident(slug)
        item_id = int(args.get("id", 0))
        with self._get_conn() as conn:
            cur = conn.cursor()
            sql = "DELETE FROM " + table + " WHERE id = ?"
            try:
                cur.execute(sql, (item_id,))
                conn.commit()
                return {"sucesso": True, "modulo": slug, "id": item_id}
            except Exception as e:
                return {"sucesso": False, "modulo": slug, "erro": str(e)}

    def get_tools_manifest(self) -> List[Dict[str, Any]]:
        """Retorna o manifesto de ferramentas no formato padrão MCP."""
        return self.tools

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executa uma ferramenta registrada."""
        if name in self._handlers:
            try:
                return self._handlers[name](args)
            except Exception as e:
                return {"sucesso": False, "erro": f"Erro na execução da ferramenta '{name}': {str(e)}"}

        return {"sucesso": False, "erro": f"Ferramenta '{name}' não encontrada no servidor MCP"}

    def handle_json_rpc(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa requisições JSON-RPC 2.0 (tools/list e tools/call)."""
        req_id = request_data.get("id", 1)
        method = request_data.get("method")
        params = request_data.get("params", {})

        if method in ("tools/list", "toolsList"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.get_tools_manifest()}
            }
        elif method in ("tools/call", "toolsCall"):
            name = params.get("name")
            args = params.get("arguments", {})
            try:
                res = self.execute_tool(name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)}
                }
        elif method in ("initialize", "ping"):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "aidd-enterprise-mcp", "version": "4.1.0"},
                    "capabilities": {"tools": {}}
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Método '{method}' não suportado"}
            }

    # Alias para compatibilidade com gates
    handle_request = handle_json_rpc

    def get_studio_html(self, title: str = "AIDD Enterprise — MCP Server Studio") -> str:
        """Gera a interface Web Impeccable para o Studio de Ferramentas MCP (/mcp)."""
        tools = self.get_tools_manifest()
        claude_config = {
            "mcpServers": {
                "aidd-suite": {
                    "command": "python",
                    "args": ["-m", "src.core.mcp_server"],
                    "env": {"PYTHONPATH": "."}
                }
            }
        }
        claude_config_json = json.dumps(claude_config, indent=2)

        cards_html = []
        for t in tools:
            schema_json = json.dumps(t["inputSchema"], indent=2, ensure_ascii=False)
            cards_html.append(f'''
                <div class="tool-card bg-slate-900/60 border border-slate-800 p-5 rounded-xl flex flex-col justify-between" data-name="{t["name"].lower()}">
                    <div>
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-mono text-sm font-bold text-purple-400">{t["name"]}</span>
                        </div>
                        <p class="text-xs text-slate-300 mb-3">{t["description"]}</p>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">Input Schema</div>
                        <pre class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-x-auto max-h-36">{schema_json}</pre>
                    </div>
                </div>
            ''')
        cards_str = "\n".join(cards_html)

        return f"""<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
        ::-webkit-scrollbar-track {{ background: #020617; }}
        ::-webkit-scrollbar-thumb {{ background: #1e293b; border-radius: 2px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #334155; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-[#020617] text-slate-100 min-h-screen font-sans antialiased flex flex-col">
    <!-- TOPBAR -->
    <header class="min-h-[56px] h-14 border-b border-slate-800 bg-[#0f172a]/95 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
            <span class="font-extrabold text-sm text-slate-100">{title}</span>
            <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30">JSON-RPC 2.0</span>
            <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        </div>
        <div class="flex items-center gap-2">
            <a href="/" class="text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">App</a>
            <a href="/docs" class="text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">Swagger</a>
            <a href="/webhooks" class="text-xs text-slate-300 hover:text-white bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700">Webhooks</a>
        </div>
    </header>

    <main class="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        <!-- STATS -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div class="text-xs text-slate-400 font-bold uppercase tracking-wider">Ferramentas MCP</div>
                <div class="text-2xl font-black text-purple-400 mt-1">{len(tools)} Tools</div>
            </div>
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div class="text-xs text-slate-400 font-bold uppercase tracking-wider">Protocolo</div>
                <div class="text-2xl font-black text-sky-400 mt-1">JSON-RPC 2.0</div>
            </div>
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div class="text-xs text-slate-400 font-bold uppercase tracking-wider">Transportes</div>
                <div class="text-2xl font-black text-emerald-400 mt-1">STDIO & HTTP</div>
            </div>
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div class="text-xs text-slate-400 font-bold uppercase tracking-wider">Conexão LLM</div>
                <div class="text-2xl font-black text-amber-400 mt-1">Claude / Cursor</div>
            </div>
        </div>

        <!-- CONFIG CLAUDE -->
        <div class="bg-slate-900/60 p-5 rounded-xl border border-slate-800">
            <div class="flex items-center justify-between mb-3">
                <span class="text-xs font-bold uppercase tracking-wider text-slate-300">Configuração Claude Desktop & Cursor (claude_desktop_config.json)</span>
                <button onclick="copiarConfig()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1 rounded border border-slate-700 transition">Copiar JSON</button>
            </div>
            <pre class="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs text-slate-300 font-mono overflow-x-auto" id="config-json">{claude_config_json}</pre>
        </div>

        <!-- LISTA DE TOOLS -->
        <div class="space-y-4">
            <div class="flex items-center justify-between">
                <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400">Catálogo de Ferramentas Disponíveis</h2>
                <input type="text" id="filter-tools" placeholder="Filtrar ferramentas..." oninput="filtrar(this.value)" class="bg-slate-950 border border-slate-800 text-xs rounded-lg px-3 py-1.5 w-64 outline-none focus:border-purple-500">
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4" id="grid-tools">
                {cards_str}
            </div>
        </div>
    </main>

    <script>
        function copiarConfig() {{
            const txt = document.getElementById('config-json').textContent;
            navigator.clipboard.writeText(txt).then(() => alert('Configuração copiada!'));
        }}
        function filtrar(q) {{
            const val = q.toLowerCase();
            document.querySelectorAll('.tool-card').forEach(c => {{
                c.style.display = c.getAttribute('data-name').includes(val) ? 'flex' : 'none';
            }});
        }}
    </script>
</body>
</html>"""


# Aliases para compatibilidade reversa
EnterpriseMCPServer = MCPServer
LogisticaMCPServer = MCPServer
MedHealthMCPServer = MCPServer


def run_stdio_server(db_path: str):
    """Executa o servidor MCP via Standard I/O (STDIO) para Claude Desktop."""
    server = MCPServer(db_path)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            resp = server.handle_json_rpc(req)
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {str(e)}"}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "suite.db")
    run_stdio_server(db_file)
