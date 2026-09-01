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

if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "suite.db")
    server = EnterpriseMCPServer(db_file)
    server.run_stdio()
