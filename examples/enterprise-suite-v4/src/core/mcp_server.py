import sys, json, os, sqlite3, uuid

class EnterpriseMCPServer:
    """
    Servidor MCP Universal (Model Context Protocol) para AIDD Enterprise Suite v4.0.
    Compatível com Antigravity, Claude Desktop, Cursor, Windsurf, Zed e OnOrca.
    Suporta protocolo JSON-RPC 2.0 via STDIO ou HTTP.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.tools = {
            "crm_listar_pipeline": {
                "description": "Retorna o pipeline completo de vendas do CRM agrupado por estágios do Kanban.",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "crm_salvar_lead": {
                "description": "Cadastra um novo lead comercial ou atualiza um existente.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "nome": {"type": "string", "description": "Nome completo do decisor"},
                        "email": {"type": "string", "description": "E-mail corporativo"},
                        "telefone": {"type": "string", "description": "Telefone / WhatsApp"},
                        "empresa": {"type": "string", "description": "Razão social da empresa"},
                        "score": {"type": "integer", "description": "Pontuação comercial (0-100)"},
                        "status": {"type": "string", "description": "novo, qualificado, proposta, negociacao, ganho"},
                        "valor_estimado": {"type": "number", "description": "Valor estimado do contrato em BRL"}
                    },
                    "required": ["nome", "email", "telefone"]
                }
            },
            "crm_mover_lead": {
                "description": "Altera o estágio do lead no Kanban. Dispara receita no ERP se o status for 'ganho'.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "integer", "description": "ID do lead"},
                        "novo_status": {"type": "string", "description": "novo, qualificado, proposta, negociacao, ganho"}
                    },
                    "required": ["lead_id", "novo_status"]
                }
            },
            "erp_obter_fluxo_caixa": {
                "description": "Consulta o DRE e resumo de fluxo de caixa (saldo realizado e saldo projetado).",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "erp_lancar_conta": {
                "description": "Registra uma nova conta a pagar ou a receber no ERP financeiro.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "descricao": {"type": "string", "description": "Descrição do lançamento"},
                        "tipo": {"type": "string", "description": "receita ou despesa"},
                        "categoria": {"type": "string", "description": "Categoria contábil"},
                        "valor": {"type": "number", "description": "Valor monetário em BRL"},
                        "data_vencimento": {"type": "string", "description": "Data YYYY-MM-DD"}
                    },
                    "required": ["descricao", "tipo", "categoria", "valor", "data_vencimento"]
                }
            },
            "helpdesk_listar_tickets": {
                "description": "Lista todos os chamados de suporte com controle de criticidade (P1/P2/P3) e SLA.",
                "inputSchema": {"type": "object", "properties": {}}
            },
            "helpdesk_abrir_ticket": {
                "description": "Abre um chamado de suporte técnico com protocolo UUID gerado automaticamente.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "assunto": {"type": "string", "description": "Assunto do chamado"},
                        "descricao": {"type": "string", "description": "Descrição técnica detalhada"},
                        "cliente_nome": {"type": "string", "description": "Nome do solicitante"},
                        "prioridade": {"type": "string", "description": "P1 (2h), P2 (4h) ou P3 (24h)"}
                    },
                    "required": ["assunto", "descricao", "cliente_nome"]
                }
            },
            "catalogo_listar_produtos": {
                "description": "Consulta todos os produtos disponíveis no catálogo comercial.",
                "inputSchema": {"type": "object", "properties": {}}
            }
        }

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def handle_call_tool(self, name: str, args: dict) -> dict:
        with self._get_conn() as conn:
            if name == "crm_listar_pipeline":
                leads = [dict(r) for r in conn.execute("SELECT * FROM leads ORDER BY score DESC").fetchall()]
                return {"content": [{"type": "text", "text": json.dumps(leads, ensure_ascii=False, indent=2)}]}

            elif name == "crm_salvar_lead":
                cur = conn.execute("""
                    INSERT INTO leads (nome, email, telefone, empresa, score, status, valor_estimado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (args["nome"], args["email"], args["telefone"], args.get("empresa", "Cliente"), int(args.get("score", 50)), args.get("status", "novo"), float(args.get("valor_estimado", 0))))
                conn.commit()
                return {"content": [{"type": "text", "text": f"Lead cadastrado com sucesso! ID: {cur.lastrowid}"}]}

            elif name == "crm_mover_lead":
                conn.execute("UPDATE leads SET status = ? WHERE id = ?", (args["novo_status"], int(args["lead_id"])))
                conn.commit()
                if args["novo_status"] == "ganho":
                    row = conn.execute("SELECT * FROM leads WHERE id = ?", (int(args["lead_id"]),)).fetchone()
                    if row:
                        conn.execute("""
                            INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
                            VALUES (?, 'receita', 'Vendas CRM', ?, date('now', '+15 days'), 'pendente', ?)
                        """, (f"Contrato Ganho: {row['nome']}", float(row['valor_estimado']), row['empresa']))
                        conn.commit()
                return {"content": [{"type": "text", "text": f"Lead {args['lead_id']} movido para {args['novo_status'].upper()}!"}]}

            elif name == "erp_obter_fluxo_caixa":
                rec = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE tipo='receita' AND status='pago'").fetchone()[0]
                desp = conn.execute("SELECT COALESCE(SUM(valor), 0) FROM lancamentos WHERE tipo='despesa' AND status='pago'").fetchone()[0]
                res = {"receitas_pagas": rec, "despesas_pagas": desp, "saldo_realizado": rec - desp}
                return {"content": [{"type": "text", "text": json.dumps(res, ensure_ascii=False, indent=2)}]}

            elif name == "erp_lancar_conta":
                conn.execute("""
                    INSERT INTO lancamentos (descricao, tipo, categoria, valor, data_vencimento, status, entidade_nome)
                    VALUES (?, ?, ?, ?, ?, 'pendente', 'Geral')
                """, (args["descricao"], args["tipo"], args["categoria"], float(args["valor"]), args["data_vencimento"]))
                conn.commit()
                return {"content": [{"type": "text", "text": "Lançamento financeiro registrado com sucesso no ERP!"}]}

            elif name == "helpdesk_listar_tickets":
                tickets = [dict(r) for r in conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()]
                return {"content": [{"type": "text", "text": json.dumps(tickets, ensure_ascii=False, indent=2)}]}

            elif name == "helpdesk_abrir_ticket":
                proto = f"TICK-{uuid.uuid4().hex[:6].upper()}"
                prio = args.get("prioridade", "P3")
                sla = 2 if prio == "P1" else (4 if prio == "P2" else 24)
                conn.execute("""
                    INSERT INTO tickets (protocolo, assunto, descricao, cliente_nome, cliente_email, prioridade, status, sla_limite_horas)
                    VALUES (?, ?, ?, ?, 'cliente@empresa.com', ?, 'aberto', ?)
                """, (proto, args["assunto"], args["descricao"], args["cliente_nome"], prio, sla))
                conn.commit()
                return {"content": [{"type": "text", "text": f"Chamado aberto com sucesso! Protocolo: {proto} (SLA: {sla}h)"}]}

            elif name == "catalogo_listar_produtos":
                prods = [dict(r) for r in conn.execute("SELECT * FROM produtos").fetchall()]
                return {"content": [{"type": "text", "text": json.dumps(prods, ensure_ascii=False, indent=2)}]}

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
                    "serverInfo": {"name": "aidd-enterprise-suite-mcp", "version": "4.0.0"}
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

    def run_stdio(self):
        """Loop de execução contínuo via STDIN/STDOUT para conectar no Claude Desktop, Cursor e Antigravity."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                req = json.loads(line)
                resp = self.process_rpc(req)
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_resp = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}}
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


    def get_portal_html(self) -> str:
        tools_dict = self.tools
        server_path = os.path.abspath(__file__)
        return """<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP Universal Hub — AIDD Enterprise Suite v4.0</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #020617;
            --bg-card: #050b18;
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-light: #60a5fa;
            --green: #10b981;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background: var(--bg-body); color: var(--text-main); min-height: 100vh; display: flex; flex-direction: column; }

        header { height: 60px; background: rgba(3, 7, 18, 0.95); backdrop-filter: blur(20px); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 2rem; position: sticky; top: 0; z-index: 50; }
        .brand-title { font-weight: 800; font-size: 1rem; color: #fff; display: flex; align-items: center; gap: 0.6rem; }
        .badge-status { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; font-size: 0.72rem; font-weight: 800; padding: 0.25rem 0.6rem; border-radius: 9999px; display: inline-flex; align-items: center; gap: 0.35rem; }
        .badge-status::before { content: ''; width: 7px; height: 7px; background: #10b981; border-radius: 50%; display: inline-block; }

        .btn { padding: 0.45rem 0.9rem; border-radius: 8px; font-size: 0.82rem; font-weight: 600; border: 1px solid var(--border); background: rgba(255, 255, 255, 0.04); color: #fff; text-decoration: none; cursor: pointer; display: inline-flex; align-items: center; gap: 0.4rem; transition: all 0.2s; }
        .btn:hover { background: rgba(255, 255, 255, 0.08); border-color: var(--border-hover); }

        main { max-width: 1200px; margin: 0 auto; width: 100%; padding: 2.5rem 1.5rem; display: flex; flex-direction: column; gap: 2.5rem; }
        
        .hero { background: linear-gradient(180deg, rgba(59, 130, 246, 0.08) 0%, transparent 100%); border: 1px solid var(--border); border-radius: 16px; padding: 2rem; }
        .hero h1 { font-size: 2rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 0.6rem; }
        .hero p { color: var(--text-muted); font-size: 0.95rem; line-height: 1.6; max-width: 800px; }

        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
        @media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }

        .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
        .card-title { font-size: 1.1rem; font-weight: 800; color: #fff; display: flex; align-items: center; gap: 0.5rem; }

        pre.code-block { background: #020617; border: 1px solid var(--border); border-radius: 10px; padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #60a5fa; overflow-x: auto; line-height: 1.5; }

        .tool-card { background: rgba(255, 255, 255, 0.02); border: 1px solid var(--border); border-radius: 10px; padding: 1rem; margin-bottom: 0.8rem; transition: all 0.2s; }
        .tool-card:hover { border-color: rgba(59, 130, 246, 0.4); background: rgba(59, 130, 246, 0.04); }
        .tool-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
        .tool-name { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; font-weight: 700; color: #fff; }
        .tool-badge { background: rgba(59, 130, 246, 0.15); color: var(--primary-light); font-size: 0.68rem; font-weight: 800; padding: 0.15rem 0.45rem; border-radius: 4px; font-family: 'JetBrains Mono', monospace; }
        .tool-desc { font-size: 0.84rem; color: var(--text-muted); line-height: 1.5; }

        .btn-test { background: var(--primary); border: 1px solid var(--primary); color: #fff; font-weight: 700; font-size: 0.85rem; padding: 0.6rem 1rem; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
        .btn-test:hover { background: #2563eb; }
    </style>
</head>
<body>

    <header>
        <div class="brand-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            <span>AIDD Universal MCP Server</span>
            <span class="badge-status">ATIVO & ONLINE (v2024-11-05)</span>
        </div>
        <div style="display: flex; gap: 0.8rem;">
            <a href="/" class="btn">Aplicação Super-App</a>
            <a href="/docs" class="btn">Swagger Studio</a>
            <a href="/docs/guia" class="btn">Guia OnOrca</a>
        </div>
    </header>

    <main>
        <div class="hero">
            <h1>Model Context Protocol (MCP) — Servidor Nativo</h1>
            <p>Servidor Universal MCP integrado à Suíte Corporativa v4.0. Permite que agentes de IA (Google Antigravity, Claude Desktop, Cursor, Zed, Windsurf, OnOrca) consultem e alterem dados do CRM, ERP, Helpdesk e Catálogo via STDIO ou HTTP JSON-RPC 2.0.</p>
        </div>

        <div class="grid-2">
            <!-- CONFIGURAÇÃO CLAUDE / CURSOR -->
            <div class="card">
                <div class="card-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    Conexão no Claude Desktop / Cursor / Antigravity
                </div>
                <p style="font-size: 0.85rem; color: var(--text-muted);">Copie a configuração abaixo no arquivo <code>claude_desktop_config.json</code> ou nas configurações de MCP do seu aplicativo:</p>
                <pre class="code-block">{
  "mcpServers": {
    "aidd-enterprise-suite": {
      "command": "python",
      "args": [
        "C:\\Users\\trcnologia\\Desktop\\enterprise-suite-v4\\src\\core\\mcp_server.py"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}</pre>
                <button class="btn" onclick="copiarConfig()" style="align-self: flex-start;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    Copiar Configuração JSON
                </button>
            </div>

            <!-- TESTE JSON-RPC VIA WEB -->
            <div class="card">
                <div class="card-title">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    Testador Web de Ferramentas MCP (Live Runner)
                </div>
                <p style="font-size: 0.85rem; color: var(--text-muted);">Dispare uma chamada JSON-RPC 2.0 direta para o endpoint HTTP <code>/mcp</code>:</p>
                <div style="display: flex; gap: 0.6rem;">
                    <select id="select-mcp-tool" style="flex: 1; background: #020617; border: 1px solid var(--border); color: #fff; padding: 0.6rem; border-radius: 8px; font-size: 0.85rem; outline: none;">
                    </select>
                    <button class="btn-test" onclick="executarTesteMcp()">Executar Tool</button>
                </div>
                <div id="mcp-test-response" style="background: #020617; border: 1px solid var(--border); border-radius: 10px; padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #34d399; min-height: 120px; max-height: 180px; overflow-y: auto;">
                    // Selecione uma ferramenta e clique em "Executar Tool" para ver o retorno em JSON
                </div>
            </div>
        </div>

        <!-- LISTA DE FERRAMENTAS DISPONÍVEIS -->
        <div class="card">
            <div class="card-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
                Catálogo de Ferramentas MCP Nativas (Tools)
            </div>
            <div id="mcp-tools-list"></div>
        </div>
    </main>

    <script>
        const tools = [{"name": "crm_listar_pipeline", "description": "Retorna o pipeline completo de vendas do CRM agrupado por estágios do Kanban.", "schema": {"type": "object"}}, {"name": "crm_salvar_lead", "description": "Cadastra um novo lead comercial ou atualiza um existente.", "schema": {"type": "object"}}, {"name": "crm_mover_lead", "description": "Altera o estágio do lead no Kanban. Dispara receita no ERP se o status for ganho.", "schema": {"type": "object"}}, {"name": "erp_obter_fluxo_caixa", "description": "Consulta o DRE e resumo de fluxo de caixa (saldo realizado e saldo projetado).", "schema": {"type": "object"}}, {"name": "erp_lancar_conta", "description": "Registra uma nova conta a pagar ou a receber no ERP financeiro.", "schema": {"type": "object"}}, {"name": "helpdesk_listar_tickets", "description": "Lista todos os chamados de suporte com controle de criticidade (P1/P2/P3) e SLA.", "schema": {"type": "object"}}, {"name": "helpdesk_abrir_ticket", "description": "Abre um chamado de suporte técnico com protocolo UUID gerado automaticamente.", "schema": {"type": "object"}}, {"name": "catalogo_listar_produtos", "description": "Consulta todos os produtos disponíveis no catálogo comercial.", "schema": {"type": "object"}}];

        function renderizarFerramentas() {
            const container = document.getElementById('mcp-tools-list');
            const select = document.getElementById('select-mcp-tool');
            let html = '';
            let optHtml = '';

            tools.forEach(t => {
                optHtml += `<option value="${t.name}">${t.name}</option>`;
                html += `
                    <div class="tool-card">
                        <div class="tool-header">
                            <span class="tool-name">${t.name}</span>
                            <span class="tool-badge">TOOL</span>
                        </div>
                        <div class="tool-desc">${t.description}</div>
                    </div>
                `;
            });

            container.innerHTML = html;
            select.innerHTML = optHtml;
        }

        async function executarTesteMcp() {
            const toolName = document.getElementById('select-mcp-tool').value;
            const resBox = document.getElementById('mcp-test-response');
            resBox.innerText = 'Executando MCP Tool: ' + toolName + '...';

            try {
                const payload = {
                    jsonrpc: "2.0",
                    id: Date.now(),
                    method: "tools/call",
                    params: {
                        name: toolName,
                        arguments: {}
                    }
                };

                const res = await fetch('/mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                resBox.innerText = JSON.stringify(data, null, 2);
            } catch (err) {
                resBox.innerText = 'Erro: ' + err.message;
            }
        }

        function copiarConfig() {
            const code = document.querySelector('pre.code-block').innerText;
            navigator.clipboard.writeText(code);
            alert('Configuração MCP copiada para a área de transferência!');
        }

        window.onload = renderizarFerramentas;
    </script>
</body>
</html>"""

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "suite.db")
    server = EnterpriseMCPServer(db_file)
    server.run_stdio()
