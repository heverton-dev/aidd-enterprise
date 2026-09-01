import json, os, sys

class MCPServer:
    """
    Universal Model Context Protocol (MCP) Server JSON-RPC 2.0
    Expõe ferramentas de inspeção, CRUD dinâmico e saúde para Claude Desktop, Cursor e Antigravity.
    """
    def __init__(self, db, tools_registry=None):
        self.db = db
        self.tools_registry = tools_registry or {}
        self.BASE_TOOLS = [
            {
                "name": "sistema_health",
                "description": "Retorna o status de saúde e conectividade do monólito modular.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "sistema_kpis",
                "description": "Retorna os principais KPIs e contagens de entidades dos módulos ativos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "executar_consulta",
                "description": "Executa uma consulta parametrizada segura de leitura no banco SQLite WAL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "tabela": {"type": "string", "description": "Nome da tabela a consultar"},
                        "limite": {"type": "integer", "description": "Quantidade máxima de registros", "default": 20}
                    },
                    "required": ["tabela"]
                }
            }
        ]

    def register_tool(self, name: str, description: str, input_schema: dict, handler):
        self.tools_registry[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler
        }

    def get_tools(self):
        registered = [{"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]} for t in self.tools_registry.values()]
        return self.BASE_TOOLS + registered

    def handle_request(self, request_body: str):
        try:
            req = json.loads(request_body)
        except Exception:
            return self._jsonrpc_error(None, -32700, "Parse error")

        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id")

        if method == "initialize":
            return self._jsonrpc_result(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "AIDD Universal MCP Server", "version": "4.1.0"}
            })
        if method == "tools/list":
            return self._jsonrpc_result(req_id, {"tools": self.get_tools()})
        if method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            return self._jsonrpc_result(req_id, self._call_tool(tool_name, arguments))
        if method == "ping":
            return self._jsonrpc_result(req_id, {})

        return self._jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    def _call_tool(self, name: str, args: dict):
        if name == "sistema_health":
            return {"content": [{"type": "text", "text": json.dumps({"status": "healthy", "version": "4.1.0"}, indent=2)}]}
        if name == "sistema_kpis":
            with self.db.get_connection() as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'mod_%'").fetchall()
                counts = {}
                for t in tables:
                    tname = t["name"]
                    c = conn.execute(f"SELECT count(*) as total FROM {tname} WHERE ativo = 1").fetchone()
                    counts[tname] = c["total"] if c else 0
                return {"content": [{"type": "text", "text": json.dumps({"kpis": counts}, indent=2)}]}
        if name == "executar_consulta":
            tabela = args.get("tabela", "")
            limite = min(args.get("limite", 20), 100)
            if not tabela.isidentifier():
                return {"content": [{"type": "text", "text": "Nome de tabela inválido"}], "isError": True}
            with self.db.get_connection() as conn:
                rows = conn.execute(f"SELECT * FROM {tabela} LIMIT ?", (limite,)).fetchall()
                return {"content": [{"type": "text", "text": json.dumps([dict(r) for r in rows], default=str, indent=2)}]}

        if name in self.tools_registry:
            handler = self.tools_registry[name]["handler"]
            try:
                res = handler(args)
                return {"content": [{"type": "text", "text": json.dumps(res, default=str, indent=2)}]}
            except Exception as e:
                return {"content": [{"type": "text", "text": f"Erro na execução da tool: {str(e)}"}], "isError": True}

        return {"content": [{"type": "text", "text": f"Ferramenta '{name}' não encontrada"}], "isError": True}

    def _jsonrpc_result(self, req_id, result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def _jsonrpc_error(self, req_id, code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}
