import sys, json, os, sqlite3, uuid

class LogisticaMCPServer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.tools = {
            "frotas_listar_veiculos": {
                "description": "Lista todos os veículos da frota, motoristas, capacidade em KG e status operacional.",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "frotas_cadastrar_veiculo": {
                "description": "Cadastra um novo caminhão ou utilitário na frota com placa e capacidade.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "placa": {"type": "string", "description": "Placa do veículo"},
                        "modelo": {"type": "string", "description": "Modelo do caminhão"},
                        "motorista": {"type": "string", "description": "Nome do motorista responsável"},
                        "capacidade_kg": {"type": "number", "description": "Capacidade de carga em KG"}
                    },
                    "required": ["placa", "modelo", "motorista", "capacidade_kg"]
                }
            },
            "entregas_criar_remessa": {
                "description": "Cria uma nova remessa de entrega com código de rastreamento e valor de frete.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "destinatario": {"type": "string", "description": "Nome do cliente destinatário"},
                        "cidade_destino": {"type": "string", "description": "Cidade e UF"},
                        "valor_frete": {"type": "number", "description": "Valor monetário do frete em BRL"},
                        "peso_kg": {"type": "number", "description": "Peso total da carga"}
                    },
                    "required": ["destinatario", "cidade_destino", "valor_frete", "peso_kg"]
                }
            },
            "entregas_atualizar_status": {
                "description": "Atualiza o status da entrega (coletado, em_transito, entregue). Dispara faturamento no financeiro se 'entregue'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "entrega_id": {"type": "integer", "description": "ID da entrega"},
                        "novo_status": {"type": "string", "description": "coletado, em_transito, entregue"}
                    },
                    "required": ["entrega_id", "novo_status"]
                }
            },
            "wms_consultar_estoque": {
                "description": "Consulta os itens e saldo de estoque no armazém WMS com posições de palete.",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "financeiro_resumo_fretes": {
                "description": "Retorna o saldo de fretes recebidos e custos operacionais de combustível/pedágio.",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "suporte_abrir_incidente": {
                "description": "Abre um chamado de suporte operacional / pane mecânica com protocolo de rastreio e SLA.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string", "description": "Título do incidente"},
                        "veiculo_placa": {"type": "string", "description": "Placa do caminhão envolvido"},
                        "prioridade": {"type": "string", "description": "P1 (2h), P2 (4h) ou P3 (24h)"}
                    },
                    "required": ["titulo", "prioridade"]
                }
            }
        }

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def handle_call_tool(self, name: str, args: dict) -> dict:
        with self._get_conn() as conn:
            if name == "frotas_listar_veiculos":
                veics = [dict(r) for r in conn.execute("SELECT * FROM veiculos").fetchall()]
                return {"content": [{"type": "text", "text": json.dumps(veics, ensure_ascii=False, indent=2)}]}

            elif name == "frotas_cadastrar_veiculo":
                conn.execute("INSERT INTO veiculos (placa, modelo, motorista, capacidade_kg, status) VALUES (?, ?, ?, ?, 'disponivel')",
                             (args["placa"].upper(), args["modelo"], args["motorista"], float(args["capacidade_kg"])))
                conn.commit()
                return {"content": [{"type": "text", "text": f"Veículo {args['placa'].upper()} cadastrado com sucesso!"}]}

            elif name == "entregas_criar_remessa":
                cod = f"BR-LOG-{uuid.uuid4().hex[:4].upper()}"
                conn.execute("INSERT INTO entregas (codigo_rastreio, destinatario, cidade_destino, valor_frete, peso_kg, status) VALUES (?, ?, ?, ?, ?, 'pendente')",
                             (cod, args["destinatario"], args["cidade_destino"], float(args["valor_frete"]), float(args["peso_kg"])))
                conn.commit()
                return {"content": [{"type": "text", "text": f"Remessa criada! Código de Rastreamento: {cod}"}]}

            elif name == "entregas_atualizar_status":
                conn.execute("UPDATE entregas SET status = ? WHERE id = ?", (args["novo_status"], int(args["entrega_id"])))
                conn.commit()
                if args["novo_status"] == "entregue":
                    row = conn.execute("SELECT * FROM entregas WHERE id = ?", (int(args["entrega_id"]),)).fetchone()
                    if row:
                        conn.execute("INSERT INTO fretes_financeiro (tipo, descricao, valor, status, data_vencimento) VALUES ('receita', ?, ?, 'pago', date('now'))",
                                     (f"Faturamento Frete {row['codigo_rastreio']}", float(row['valor_frete'])))
                        conn.commit()
                return {"content": [{"type": "text", "text": f"Entrega #{args['entrega_id']} atualizada para {args['novo_status'].upper()}!"}]}

            elif name == "wms_consultar_estoque":
                itens = [dict(r) for r in conn.execute("SELECT * FROM estoque_wms").fetchall()]
                return {"content": [{"type": "text", "text": json.dumps(itens, ensure_ascii=False, indent=2)}]}

            elif name == "financeiro_resumo_fretes":
                rec = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM fretes_financeiro WHERE tipo='receita' AND status='pago'").fetchone()[0]
                desp = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM fretes_financeiro WHERE tipo='despesa' AND status='pago'").fetchone()[0]
                res = {"fretes_recebidos": rec, "despesas_operacionais": desp, "saldo_liquido": rec - desp}
                return {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]}

            elif name == "suporte_abrir_incidente":
                proto = f"INC-{uuid.uuid4().hex[:6].upper()}"
                prio = args.get("prioridade", "P3")
                sla = 2 if prio == "P1" else (4 if prio == "P2" else 24)
                conn.execute("INSERT INTO incidentes_sla (protocolo, titulo, veiculo_placa, prioridade, status, sla_horas) VALUES (?, ?, ?, ?, 'aberto', ?)",
                             (proto, args["titulo"], args.get("veiculo_placa", "N/A"), prio, sla))
                conn.commit()
                return {"content": [{"type": "text", "text": f"Incidente aberto! Protocolo: {proto} (SLA: {sla}h)"}]}

            else:
                return {"isError": True, "content": [{"type": "text", "text": f"Ferramenta desconhecida: {name}"}]}

    def process_rpc(self, request: dict) -> dict:
        method = request.get("method")
        msg_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "logistica-hub-mcp", "version": "4.0.0"}
                }
            }
        elif method == "tools/list":
            tools_list = [{"name": k, "description": v["description"], "inputSchema": v["inputSchema"]} for k, v in self.tools.items()]
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}
        elif method == "tools/call":
            params = request.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            res = self.handle_call_tool(name, args)
            return {"jsonrpc": "2.0", "id": msg_id, "result": res}
        else:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}

    def get_portal_html(self) -> str:
        tools_list = [{"name": k, "description": v["description"]} for k, v in self.tools.items()]
        tools_json = json.dumps(tools_list, ensure_ascii=False)
        server_path = os.path.abspath(__file__).replace("\\\\", "/")

        return f"""<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Universal Hub — Logística Suite v4.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{ --bg: #020617; --card: #050b18; --border: rgba(255,255,255,0.08); --primary: #3b82f6; --text: #f8fafc; --muted: #94a3b8; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 2rem; }}
        header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2rem; }}
        .badge-status {{ background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; font-size: 0.75rem; font-weight: 800; padding: 0.3rem 0.7rem; border-radius: 9999px; }}
        .btn {{ padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.85rem; font-weight: 600; border: 1px solid var(--border); background: rgba(255,255,255,0.04); color: #fff; text-decoration: none; cursor: pointer; }}
        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }}
        pre {{ background: #020617; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #60a5fa; overflow-x: auto; }}
        .tool-box {{ background: rgba(255,255,255,0.02); border: 1px solid var(--border); border-radius: 8px; padding: 0.8rem 1rem; margin-bottom: 0.6rem; }}
        .tool-title {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 0.88rem; color: #fff; }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1 style="font-size: 1.6rem; font-weight: 800;">Logística Hub — MCP Server Nativo</h1>
            <p style="color: var(--muted); font-size: 0.9rem;">Model Context Protocol ativo para Claude Desktop, Cursor e Antigravity</p>
        </div>
        <div style="display: flex; gap: 0.8rem; align-items: center;">
            <span class="badge-status">🟢 ONLINE (v2024-11-05)</span>
            <a href="/" class="btn">Aplicação</a>
            <a href="/docs" class="btn">Swagger Studio</a>
        </div>
    </header>

    <div class="grid-2">
        <div class="card">
            <h3 style="color: #fff;">Configuração de Conexão MCP</h3>
            <pre>{{
  "mcpServers": {{
    "logistica-hub-suite": {{
      "command": "python",
      "args": ["{server_path}"],
      "env": {{ "PYTHONIOENCODING": "utf-8" }}
    }}
  }}
}}</pre>
            <button class="btn" onclick="navigator.clipboard.writeText(document.querySelector('pre').innerText); alert('Copiado!');">Copiar Configuração JSON</button>
        </div>

        <div class="card">
            <h3 style="color: #fff;">Testador Web de Ferramentas (Live Runner)</h3>
            <div style="display: flex; gap: 0.6rem;">
                <select id="sel-tool" style="flex: 1; background: #020617; border: 1px solid var(--border); color: #fff; padding: 0.6rem; border-radius: 8px;"></select>
                <button class="btn" style="background: var(--primary); border-color: var(--primary);" onclick="testTool()">Executar Tool</button>
            </div>
            <div id="resp" style="background: #020617; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #34d399; min-height: 120px;">// Retorno JSON</div>
        </div>
    </div>

    <div class="card" style="margin-top: 1.5rem;">
        <h3 style="color: #fff;">Catálogo de Ferramentas Registradas</h3>
        <div id="tool-list"></div>
    </div>

    <script>
        const tools = {tools_json};
        const sel = document.getElementById('sel-tool');
        const list = document.getElementById('tool-list');
        let selHtml = '';
        let listHtml = '';

        tools.forEach(t => {{
            selHtml += `<option value="${{t.name}}">${{t.name}}</option>`;
            listHtml += `<div class="tool-box"><div class="tool-title">${{t.name}}</div><div style="font-size: 0.82rem; color: var(--muted);">${{t.description}}</div></div>`;
        }});
        sel.innerHTML = selHtml;
        list.innerHTML = listHtml;

        async function testTool() {{
            const name = sel.value;
            document.getElementById('resp').innerText = 'Executando ' + name + '...';
            try {{
                const r = await fetch('/mcp', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ jsonrpc: '2.0', id: 1, method: 'tools/call', params: {{ name, arguments: {{}} }} }})
                }});
                const data = await r.json();
                document.getElementById('resp').innerText = JSON.stringify(data, null, 2);
            }} catch(e) {{
                document.getElementById('resp').innerText = 'Erro: ' + e.message;
            }}
        }}
    </script>
</body>
</html>"""

    def run_stdio(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line: break
                req = json.loads(line)
                resp = self.process_rpc(req)
                sys.stdout.write(json.dumps(resp) + "\\n")
                sys.stdout.flush()
            except Exception as e:
                err_resp = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}
                sys.stdout.write(json.dumps(err_resp) + "\\n")
                sys.stdout.flush()

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "suite.db")
    server = LogisticaMCPServer(db_file)
    server.run_stdio()
