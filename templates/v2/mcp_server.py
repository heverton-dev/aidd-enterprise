import json, sqlite3, sys, os, uuid

class MedHealthMCPServer:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_tools_manifest(self):
        return [
            {
                "name": "med_triagem_listar",
                "description": "Lista pacientes na fila de triagem do Pronto-Socorro com filtro opcional por classificação Manchester (vermelho, laranja, amarelo, verde, azul) e status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "classificacao": {"type": "string", "description": "vermelho | laranja | amarelo | verde | azul | todos"},
                        "status": {"type": "string", "description": "aguardando | em_atendimento | internado | alta"}
                    }
                }
            },
            {
                "name": "med_triagem_classificar",
                "description": "Realiza a triagem de urgência Manchester de um paciente calculando SLA e prioridade.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "paciente_nome": {"type": "string", "description": "Nome completo do paciente"},
                        "idade": {"type": "integer", "description": "Idade em anos"},
                        "sinais_vitais": {"type": "string", "description": "Sinais vitais (PA, FC, SpO2, Temp, Dor)"},
                        "queixa_principal": {"type": "string", "description": "Sintomas e queixa clínica principal"},
                        "classificacao": {"type": "string", "description": "vermelho (0m) | laranja (10m) | amarelo (60m) | verde (120m) | azul (240m)"}
                    },
                    "required": ["paciente_nome", "idade", "sinais_vitais", "queixa_principal", "classificacao"]
                }
            },
            {
                "name": "med_triagem_chamar_leito",
                "description": "Aloca um paciente triado em leito ou box de observação e inicia atendimento.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "triagem_id": {"type": "integer", "description": "ID do registro de triagem"},
                        "leito": {"type": "string", "description": "Identificação do leito/box"}
                    },
                    "required": ["triagem_id", "leito"]
                }
            },
            {
                "name": "med_pep_buscar_prontuario",
                "description": "Consulta o prontuário eletrônico completo, diagnósticos CID-10, histórico e prescrições do paciente.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "termo_busca": {"type": "string", "description": "Nome do paciente ou número do prontuário (PEP-XXXX)"}
                    },
                    "required": ["termo_busca"]
                }
            },
            {
                "name": "med_pep_registrar_evolucao",
                "description": "Adiciona nova evolução clínica, conduta ou diagnóstico CID-10 no prontuário do paciente.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prontuario_id": {"type": "integer", "description": "ID do prontuário"},
                        "evolucao": {"type": "string", "description": "Texto da evolução médica e conduta"},
                        "cid10": {"type": "string", "description": "Código e descrição CID-10"}
                    },
                    "required": ["prontuario_id", "evolucao"]
                }
            },
            {
                "name": "med_pep_emitir_prescricao",
                "description": "Emite uma prescrição médica eletrônica para dispensação na farmácia hospitalar.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prontuario_id": {"type": "integer", "description": "ID do prontuário"},
                        "medicamento": {"type": "string", "description": "Nome comercial ou princípio ativo"},
                        "dosagem": {"type": "string", "description": "Posologia e dosagem"},
                        "frequencia": {"type": "string", "description": "Intervalo (ex: 8/8h, Dose Única)"},
                        "via_administracao": {"type": "string", "description": "Oral | Intravenosa | Intramuscular | Inalatória"}
                    },
                    "required": ["prontuario_id", "medicamento", "dosagem", "frequencia", "via_administracao"]
                }
            },
            {
                "name": "med_cirurgico_listar_escala",
                "description": "Lista cirurgias agendadas no Bloco Cirúrgico por data, sala e status pré/intra/pós-op.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "agendada | pre_op | em_andamento | rpa_recuperacao | concluida"}
                    }
                }
            },
            {
                "name": "med_cirurgico_agendar",
                "description": "Agenda novo procedimento cirúrgico, reserva sala e aloca equipe cirúrgica.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "paciente_nome": {"type": "string", "description": "Nome do paciente"},
                        "procedimento": {"type": "string", "description": "Nome do procedimento cirúrgico"},
                        "sala_bloco": {"type": "string", "description": "Sala cirúrgica (ex: Sala 01, Sala 02)"},
                        "cirurgiao_principal": {"type": "string", "description": "Cirurgião responsável"},
                        "anestesista": {"type": "string", "description": "Médico anestesista"},
                        "tipo_anestesia": {"type": "string", "description": "Geral | Raqui | Local | Sedação"},
                        "data_hora_cirurgia": {"type": "string", "description": "Data e hora (YYYY-MM-DD HH:MM)"},
                        "necessita_opme": {"type": "boolean", "description": "Indica se requer órteses/próteses"}
                    },
                    "required": ["paciente_nome", "procedimento", "sala_bloco", "cirurgiao_principal", "anestesista", "tipo_anestesia", "data_hora_cirurgia"]
                }
            },
            {
                "name": "med_cirurgico_atualizar_status",
                "description": "Avança a fase do paciente no Centro Cirúrgico (pre_op, em_andamento, rpa_recuperacao, concluida).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cirurgia_id": {"type": "integer", "description": "ID da cirurgia"},
                        "novo_status": {"type": "string", "description": "pre_op | em_andamento | rpa_recuperacao | concluida | cancelada"}
                    },
                    "required": ["cirurgia_id", "novo_status"]
                }
            },
            {
                "name": "med_farmacia_consultar_estoque",
                "description": "Consulta o estoque da farmácia hospitalar, validade, lotes e medicamentos em nível crítico.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "categoria": {"type": "string", "description": "antibiotico | analgesico | anestesico | controlado | alto_custo"},
                        "apenas_criticos": {"type": "boolean", "description": "Se verdadeiro, filtra apenas itens abaixo do estoque mínimo"}
                    }
                }
            },
            {
                "name": "med_farmacia_dispensar_medicamento",
                "description": "Efetua a baixa e dispensação controlada de medicamento para paciente hospitalizado.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prescricao_id": {"type": "integer", "description": "ID da prescrição atendida"},
                        "codigo_item": {"type": "string", "description": "Código do medicamento em estoque (MED-XXXX)"},
                        "quantidade": {"type": "integer", "description": "Quantidade de unidades dispensadas"},
                        "farmaceutico_crf": {"type": "string", "description": "Registro do farmacêutico responsável (CRF)"}
                    },
                    "required": ["codigo_item", "quantidade", "farmaceutico_crf"]
                }
            },
            {
                "name": "med_farmacia_cadastrar_lote",
                "description": "Registra nova entrada de lote de medicamento na farmácia hospitalar.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "medicamento": {"type": "string", "description": "Nome comercial / dosagem"},
                        "lote": {"type": "string", "description": "Número do lote de fabricação"},
                        "categoria": {"type": "string", "description": "antibiotico | analgesico | anestesico | controlado | alto_custo"},
                        "quantidade": {"type": "integer", "description": "Quantidade total de frascos/ampolas/comprimidos"},
                        "quantidade_minima": {"type": "integer", "description": "Ponto de reposição mínimo"},
                        "validade": {"type": "string", "description": "Data de validade (YYYY-MM-DD)"},
                        "temperatura": {"type": "string", "description": "Faixa de temperatura de conservação"}
                    },
                    "required": ["medicamento", "lote", "categoria", "quantidade", "quantidade_minima", "validade"]
                }
            },
            {
                "name": "med_faturamento_listar_guias",
                "description": "Lista guias de internação e contas médicas TISS/TUSS com filtros por status e convênio.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "gerada | autorizada | faturada | glosada | liquidada"},
                        "convenio": {"type": "string", "description": "Nome da operadora ou SUS/Particular"}
                    }
                }
            },
            {
                "name": "med_faturamento_emitir_guia",
                "description": "Gera nova guia hospitalar TISS com código TUSS e valor estimado.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "paciente_nome": {"type": "string", "description": "Nome do paciente"},
                        "convenio": {"type": "string", "description": "Convênio ou Particular"},
                        "codigo_tuss": {"type": "string", "description": "Código TUSS (8 dígitos)"},
                        "descricao_procedimento": {"type": "string", "description": "Descrição do procedimento faturado"},
                        "valor_total": {"type": "number", "description": "Valor total da conta hospitalar em R$"}
                    },
                    "required": ["paciente_nome", "convenio", "codigo_tuss", "descricao_procedimento", "valor_total"]
                }
            },
            {
                "name": "med_faturamento_liquidar_guia",
                "description": "Liquida e registra o recebimento do pagamento da guia hospitalar.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "guia_id": {"type": "integer", "description": "ID da guia TISS a liquidar"}
                    },
                    "required": ["guia_id"]
                }
            },
            {
                "name": "med_kpi_dashboard_geral",
                "description": "Retorna o panorama gerencial consolidado do hospital: ocupação, fila Manchester, cirurgias ativas e faturamento total.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def execute_tool(self, name: str, args: dict):
        with self._get_conn() as conn:
            cursor = conn.cursor()

            if name == "med_triagem_listar":
                cls = args.get("classificacao", "todos")
                st = args.get("status")
                query = "SELECT * FROM triagens WHERE 1=1"
                params = []
                if cls and cls != "todos":
                    query += " AND classificacao = ?"
                    params.append(cls)
                if st:
                    query += " AND status = ?"
                    params.append(st)
                query += " ORDER BY tempo_espera_max_min ASC, criado_em ASC"
                rows = cursor.execute(query, params).fetchall()
                return {"sucesso": True, "total": len(rows), "pacientes": [dict(r) for r in rows]}

            elif name == "med_triagem_classificar":
                slas = {"vermelho": 0, "laranja": 10, "amarelo": 60, "verde": 120, "azul": 240}
                cls = args.get("classificacao", "verde").lower()
                sla = slas.get(cls, 120)
                proto = f"TRI-{uuid.uuid4().hex[:4].upper()}"
                cursor.execute("""
                    INSERT INTO triagens (protocolo, paciente_nome, idade, sinais_vitais, queixa_principal, classificacao, tempo_espera_max_min, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'aguardando')
                """, (proto, args["paciente_nome"], args["idade"], args["sinais_vitais"], args["queixa_principal"], cls, sla))
                conn.commit()
                return {"sucesso": True, "protocolo": proto, "classificacao": cls, "tempo_espera_max_min": sla, "mensagem": "Paciente triado com sucesso"}

            elif name == "med_triagem_chamar_leito":
                tid = args["triagem_id"]
                leito = args["leito"]
                cursor.execute("UPDATE triagens SET leito_alocado = ?, status = 'em_atendimento' WHERE id = ?", (leito, tid))
                conn.commit()
                return {"sucesso": True, "triagem_id": tid, "leito": leito, "status": "em_atendimento"}

            elif name == "med_pep_buscar_prontuario":
                term = f"%{args['termo_busca']}%"
                pronts = cursor.execute("SELECT * FROM prontuarios WHERE paciente_nome LIKE ? OR numero_prontuario LIKE ?", (term, term)).fetchall()
                res = []
                for p in pronts:
                    p_dict = dict(p)
                    prescs = cursor.execute("SELECT * FROM prescricoes WHERE prontuario_id = ?", (p["id"],)).fetchall()
                    p_dict["prescricoes"] = [dict(pr) for pr in prescs]
                    res.append(p_dict)
                return {"sucesso": True, "total": len(res), "prontuarios": res}

            elif name == "med_pep_registrar_evolucao":
                pid = args["prontuario_id"]
                evol = args["evolucao"]
                cid = args.get("cid10")
                if cid:
                    cursor.execute("UPDATE prontuarios SET evolucao_clinica = ?, diagnostico_cid10 = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?", (evol, cid, pid))
                else:
                    cursor.execute("UPDATE prontuarios SET evolucao_clinica = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?", (evol, pid))
                conn.commit()
                return {"sucesso": True, "prontuario_id": pid, "mensagem": "Evolução clínica registrada com sucesso"}

            elif name == "med_pep_emitir_prescricao":
                pid = args["prontuario_id"]
                p_row = cursor.execute("SELECT paciente_nome FROM prontuarios WHERE id = ?", (pid,)).fetchone()
                p_nome = p_row["paciente_nome"] if p_row else "Paciente"
                cursor.execute("""
                    INSERT INTO prescricoes (prontuario_id, paciente_nome, medicamento, dosagem, frequencia, via_administracao, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'pendente')
                """, (pid, p_nome, args["medicamento"], args["dosagem"], args["frequencia"], args["via_administracao"]))
                conn.commit()
                presc_id = cursor.lastrowid
                return {"sucesso": True, "prescricao_id": presc_id, "paciente": p_nome, "status": "pendente"}

            elif name == "med_cirurgico_listar_escala":
                st = args.get("status")
                query = "SELECT * FROM cirurgias WHERE 1=1"
                params = []
                if st:
                    query += " AND status = ?"
                    params.append(st)
                query += " ORDER BY data_hora_cirurgia ASC"
                rows = cursor.execute(query, params).fetchall()
                return {"sucesso": True, "total": len(rows), "cirurgias": [dict(r) for r in rows]}

            elif name == "med_cirurgico_agendar":
                cod = f"CC-{uuid.uuid4().hex[:4].upper()}"
                opme = 1 if args.get("necessita_opme") else 0
                cursor.execute("""
                    INSERT INTO cirurgias (codigo_agendamento, paciente_nome, procedimento, sala_bloco, cirurgiao_principal, anestesista, tipo_anestesia, data_hora_cirurgia, status, necessita_opme)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'agendada', ?)
                """, (cod, args["paciente_nome"], args["procedimento"], args["sala_bloco"], args["cirurgiao_principal"], args["anestesista"], args["tipo_anestesia"], args["data_hora_cirurgia"], opme))
                conn.commit()
                return {"sucesso": True, "codigo_agendamento": cod, "mensagem": "Cirurgia agendada com sucesso"}

            elif name == "med_cirurgico_atualizar_status":
                cid = args["cirurgia_id"]
                st = args["novo_status"]
                cursor.execute("UPDATE cirurgias SET status = ? WHERE id = ?", (st, cid))
                conn.commit()
                return {"sucesso": True, "cirurgia_id": cid, "status": st}

            elif name == "med_farmacia_consultar_estoque":
                cat = args.get("categoria")
                criticos = args.get("apenas_criticos", False)
                query = "SELECT * FROM farmacia_estoque WHERE 1=1"
                params = []
                if cat:
                    query += " AND categoria = ?"
                    params.append(cat)
                if criticos:
                    query += " AND quantidade_disponivel <= quantidade_minima"
                rows = cursor.execute(query, params).fetchall()
                return {"sucesso": True, "total": len(rows), "estoque": [dict(r) for r in rows]}

            elif name == "med_farmacia_dispensar_medicamento":
                item_cod = args["codigo_item"]
                qtd = args["quantidade"]
                crf = args["farmaceutico_crf"]
                presc_id = args.get("prescricao_id")

                item = cursor.execute("SELECT * FROM farmacia_estoque WHERE codigo_item = ?", (item_cod,)).fetchone()
                if not item:
                    return {"sucesso": False, "error": f"Item {item_cod} não encontrado no estoque"}
                if item["quantidade_disponivel"] < qtd:
                    return {"sucesso": False, "error": f"Saldo insuficiente em estoque ({item['quantidade_disponivel']} disponiveis)"}

                novo_saldo = item["quantidade_disponivel"] - qtd
                novo_st = "critico" if novo_saldo <= item["quantidade_minima"] else "normal"
                if novo_saldo == 0:
                    novo_st = "zerado"

                cursor.execute("UPDATE farmacia_estoque SET quantidade_disponivel = ?, status_estoque = ? WHERE id = ?", (novo_saldo, novo_st, item["id"]))

                paciente = "Ambulatorial / Geral"
                if presc_id:
                    cursor.execute("UPDATE prescricoes SET status = 'dispensada' WHERE id = ?", (presc_id,))
                    p_info = cursor.execute("SELECT paciente_nome FROM prescricoes WHERE id = ?", (presc_id,)).fetchone()
                    if p_info:
                        paciente = p_info["paciente_nome"]

                cursor.execute("""
                    INSERT INTO dispensacoes (prescricao_id, medicamento, quantidade, farmaceutico_crf, paciente_nome)
                    VALUES (?, ?, ?, ?, ?)
                """, (presc_id, item["medicamento"], qtd, crf, paciente))
                conn.commit()
                return {"sucesso": True, "medicamento": item["medicamento"], "quantidade_dispensada": qtd, "saldo_restante": novo_saldo, "paciente": paciente}

            elif name == "med_farmacia_cadastrar_lote":
                cod = f"MED-{uuid.uuid4().hex[:4].upper()}"
                st = "critico" if args["quantidade"] <= args["quantidade_minima"] else "normal"
                cursor.execute("""
                    INSERT INTO farmacia_estoque (codigo_item, medicamento, lote, categoria, quantidade_disponivel, quantidade_minima, temperatura_armazenamento, validade, status_estoque)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (cod, args["medicamento"], args["lote"], args["categoria"], args["quantidade"], args["quantidade_minima"], args.get("temperatura", "Ambiente"), args["validade"], st))
                conn.commit()
                return {"sucesso": True, "codigo_item": cod, "medicamento": args["medicamento"], "status_estoque": st}

            elif name == "med_faturamento_listar_guias":
                st = args.get("status")
                conv = args.get("convenio")
                query = "SELECT * FROM faturamento_guias WHERE 1=1"
                params = []
                if st:
                    query += " AND status_guia = ?"
                    params.append(st)
                if conv:
                    query += " AND convenio LIKE ?"
                    params.append(f"%{conv}%")
                query += " ORDER BY id DESC"
                rows = cursor.execute(query, params).fetchall()
                return {"sucesso": True, "total": len(rows), "guias": [dict(r) for r in rows]}

            elif name == "med_faturamento_emitir_guia":
                num = f"TISS-{uuid.uuid4().hex[:4].upper()}"
                cursor.execute("""
                    INSERT INTO faturamento_guias (numero_guia, paciente_nome, convenio, codigo_tuss, descricao_procedimento, valor_total, status_guia)
                    VALUES (?, ?, ?, ?, ?, ?, 'gerada')
                """, (num, args["paciente_nome"], args["convenio"], args["codigo_tuss"], args["descricao_procedimento"], float(args["valor_total"])))
                conn.commit()
                return {"sucesso": True, "numero_guia": num, "valor_total": args["valor_total"], "status": "gerada"}

            elif name == "med_faturamento_liquidar_guia":
                gid = args["guia_id"]
                cursor.execute("UPDATE faturamento_guias SET status_guia = 'liquidada', data_liquidacao = datetime('now') WHERE id = ?", (gid,))
                conn.commit()
                return {"sucesso": True, "guia_id": gid, "status": "liquidada"}

            elif name == "med_kpi_dashboard_geral":
                total_triagens = cursor.execute("SELECT COUNT(*) FROM triagens WHERE status = 'aguardando'").fetchone()[0]
                criticos_triagem = cursor.execute("SELECT COUNT(*) FROM triagens WHERE classificacao IN ('vermelho', 'laranja') AND status = 'aguardando'").fetchone()[0]
                cirurgias_hoje = cursor.execute("SELECT COUNT(*) FROM cirurgias WHERE status IN ('pre_op', 'em_andamento', 'agendada')").fetchone()[0]
                estoque_critico = cursor.execute("SELECT COUNT(*) FROM farmacia_estoque WHERE quantidade_disponivel <= quantidade_minima").fetchone()[0]
                faturamento_aberto = cursor.execute("SELECT COALESCE(SUM(valor_total), 0) FROM faturamento_guias WHERE status_guia != 'liquidada'").fetchone()[0]
                faturamento_liquidado = cursor.execute("SELECT COALESCE(SUM(valor_total), 0) FROM faturamento_guias WHERE status_guia = 'liquidada'").fetchone()[0]

                return {
                    "sucesso": True,
                    "kpis": {
                        "pacientes_aguardando_triagem": total_triagens,
                        "emergencias_vermelho_laranja": criticos_triagem,
                        "cirurgias_programadas_hoje": cirurgias_hoje,
                        "medicamentos_estoque_critico": estoque_critico,
                        "faturamento_aberto_brl": round(faturamento_aberto, 2),
                        "faturamento_liquidado_brl": round(faturamento_liquidado, 2)
                    }
                }

            return {"sucesso": False, "error": f"Ferramenta {name} não reconhecida"}

    def handle_json_rpc(self, request_data: dict) -> dict:
        req_id = request_data.get("id", 1)
        method = request_data.get("method")
        params = request_data.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.get_tools_manifest()}
            }
        elif method == "tools/call":
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
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Método {method} não suportado"}
            }

    def get_studio_html(self, title: str = "MedHealth Suite v4.0 — MCP Native Server Studio") -> str:
        tools = self.get_tools_manifest()
        tools_json = json.dumps(tools, ensure_ascii=False)
        claude_config = {
            "mcpServers": {
                "med-health-suite": {
                    "command": "python",
                    "args": ["-m", "src.core.mcp_server"],
                    "env": {"PYTHONPATH": "."}
                }
            }
        }
        claude_config_json = json.dumps(claude_config, indent=2)

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
        :root {{
            --bg-base: #020617;
            --bg-surface: #0f172a;
            --bg-elevated: #1e293b;
            --border: #1e293b;
            --border-focus: #38bdf8;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #0284c7;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; }}
        
        /* SCROLLBAR REGRA DE OURO: 4PX */
        ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
        ::-webkit-scrollbar-track {{ background: #020617; }}
        ::-webkit-scrollbar-thumb {{ background: #1e293b; border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: #334155; }}

        .code-box {{ font-family: 'JetBrains Mono', monospace; }}
    </style>
</head>
<body class="bg-[#020617] text-slate-100 min-h-screen font-sans antialiased flex flex-col selection:bg-purple-500/30 selection:text-purple-200">

    <!-- HEADER SYSTEM DESIGN -->
    <header class="h-16 border-b border-slate-800 bg-[#0f172a]/90 backdrop-blur sticky top-0 z-40 px-6 flex items-center justify-between">
        <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400 font-black shadow-lg shadow-purple-500/10">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
            </div>
            <div>
                <div class="flex items-center gap-2">
                    <span class="font-extrabold tracking-tight text-sm text-slate-100">MedHealth MCP Server</span>
                    <span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">JSON-RPC 2.0</span>
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                </div>
                <p class="text-[11px] text-slate-400">16 Tools Hospitalares para Claude Desktop, Cursor e Agentes Autônomos</p>
            </div>
        </div>

        <!-- BUSCA RÁPIDA / Ctrl + K -->
        <div class="relative flex items-center mx-4 flex-1 max-w-md hidden md:flex">
            <svg class="w-4 h-4 text-slate-400 absolute left-3 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            <input type="text" id="mcp-search-input" placeholder="Filtrar ferramentas MCP (Ctrl + K)..." 
                   oninput="filtrarMCPTools(this.value)"
                   class="w-full bg-slate-950/80 border border-slate-700/80 text-xs rounded-lg pl-9 pr-14 py-1.5 focus:outline-none focus:border-purple-500 text-slate-100 placeholder-slate-500 shadow-inner">
            <kbd class="absolute right-2 text-[10px] bg-slate-800 border border-slate-700 text-slate-400 px-1.5 py-0.5 rounded font-mono shadow-sm pointer-events-none">Ctrl K</kbd>
        </div>

        <!-- LINKS DE NAVEGAÇÃO -->
        <div class="flex items-center gap-2">
            <a href="/" class="text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition">
                <span>Super-App</span>
            </a>
            <a href="/docs" class="text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition">
                <span>Swagger Studio</span>
            </a>
            <a href="/webhooks" class="text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition">
                <span>Webhooks</span>
            </a>
            <a href="/docs/guia" class="text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700 flex items-center gap-1.5 transition">
                <span>Guia Técnico</span>
            </a>
        </div>
    </header>

    <main class="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">

        <!-- KPI SUMMARY BAR -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div class="bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <div class="text-xs text-slate-400 font-bold uppercase tracking-wider">Ferramentas Nativas</div>
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
                <div class="text-xs text-slate-400 font-bold uppercase tracking-wider">Conectores LLM</div>
                <div class="text-2xl font-black text-amber-400 mt-1">Claude / Cursor</div>
            </div>
        </div>

        <!-- CONFIG CLAUDE DESKTOP SNIPPET -->
        <div class="bg-slate-900/60 p-5 rounded-xl border border-slate-800">
            <div class="flex items-center justify-between mb-3">
                <div class="flex items-center gap-2">
                    <span class="text-xs font-bold uppercase tracking-wider text-slate-300">Configuração para Claude Desktop & Cursor</span>
                    <span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">claude_desktop_config.json</span>
                </div>
                <button onclick="copiarConfigClaude()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-1 rounded border border-slate-700 flex items-center gap-1.5 transition">
                    <svg class="w-3.5 h-3.5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                    <span id="btn-copy-label">Copiar Config</span>
                </button>
            </div>
            <pre class="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs text-slate-300 font-mono overflow-x-auto selection:bg-purple-500/40" id="claude-config-text">{claude_config_json}</pre>
        </div>

        <!-- GRID DE FERRAMENTAS MCP -->
        <div>
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400">Catálogo de Ferramentas Disponíveis</h2>
                <span class="text-xs text-slate-500" id="tools-counter">Exibindo {len(tools)} ferramentas</span>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4" id="tools-grid">
                {"".join([f'''
                <div class="tool-card bg-slate-900/60 border border-slate-800 p-5 rounded-xl hover:border-purple-500/40 transition flex flex-col justify-between" data-name="{t["name"].lower()}" data-desc="{t["description"].lower()}">
                    <div>
                        <div class="flex items-center justify-between mb-2">
                            <span class="font-mono text-sm font-bold text-purple-400 flex items-center gap-2">
                                <svg class="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                                {t["name"]}
                            </span>
                            <button onclick="copiarTexto('{t["name"]}', 'Nome copiado')" class="text-[10px] text-slate-400 hover:text-slate-200 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700 transition">Copiar Nome</button>
                        </div>
                        <p class="text-xs text-slate-300 mb-3 leading-relaxed">{t["description"]}</p>
                    </div>
                    <div>
                        <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1">Input Schema (JSON)</div>
                        <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-x-auto max-h-48">
                            <pre>{json.dumps(t["inputSchema"], indent=2, ensure_ascii=False)}</pre>
                        </div>
                    </div>
                </div>
                ''' for t in tools])}
            </div>
        </div>
    </main>

    <!-- TOAST -->
    <div id="toast" class="fixed bottom-6 right-6 bg-emerald-600 text-white text-xs font-semibold px-4 py-2.5 rounded-lg shadow-xl hidden items-center gap-2 z-50">
        <span id="toast-msg">Copiado</span>
    </div>

        // SPOTLIGHT COMMAND PALETTE PARA MCP STUDIO (ZERO EMOJIS)
        let spotlightSelectedIndex = 0;
        let spotlightFilteredCommands = [];

        function getMcpIconSvg(type) {{
            const icons = {{
                app: '<svg width="16" height="16" fill="none" stroke="#38bdf8" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>',
                docs: '<svg width="16" height="16" fill="none" stroke="#38bdf8" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>',
                webhooks: '<svg width="16" height="16" fill="none" stroke="#f59e0b" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>',
                mcp: '<svg width="16" height="16" fill="none" stroke="#a855f7" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>',
                guia: '<svg width="16" height="16" fill="none" stroke="#10b981" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>',
                copy: '<svg width="16" height="16" fill="none" stroke="#a855f7" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"/></svg>',
                tool: '<svg width="16" height="16" fill="none" stroke="#a855f7" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>'
            }};
            return icons[type] || '<svg width="16" height="16" fill="none" stroke="#94a3b8" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>';
        }}

        function getSpotlightCommands() {{
            const baseCommands = [
                {{ id: 'nav-app', cat: 'Navegação', title: 'Super-App Clínico (Home)', desc: 'Dashboard e painéis hospitalares', iconType: 'app', action: () => {{ window.location.href = '/'; }} }},
                {{ id: 'nav-docs', cat: 'Navegação', title: 'Swagger Studio (OpenAPI)', desc: 'Documentação interativa REST e live playground', iconType: 'docs', action: () => {{ window.location.href = '/docs'; }} }},
                {{ id: 'nav-wh', cat: 'Navegação', title: 'Webhook Studio', desc: 'Simulador de eventos e logs de webhook', iconType: 'webhooks', action: () => {{ window.location.href = '/webhooks'; }} }},
                {{ id: 'nav-mcp', cat: 'Navegação', title: 'MCP Native Server Portal', desc: '16 Ferramentas JSON-RPC para Claude Desktop e LLMs', iconType: 'mcp', action: () => {{ window.location.href = '/mcp'; }} }},
                {{ id: 'nav-guia', cat: 'Navegação', title: 'Manual Enciclopédico & Design System', desc: '11 Capítulos de arquitetura, segurança e UI', iconType: 'guia', action: () => {{ window.location.href = '/docs/guia'; }} }},
                {{ id: 'act-copy-cfg', cat: 'Ações MCP', title: 'Copiar claude_desktop_config.json', desc: 'Configuração pronta para o Claude Desktop e Cursor', iconType: 'copy', action: () => {{ copiarConfigClaude(); }} }}
            ];

            const toolsCommands = {tools_json}.map(t => ({{
                id: 'tool-' + t.name,
                cat: 'Ferramentas MCP (16)',
                title: t.name,
                desc: t.description,
                iconType: 'tool',
                action: () => {{
                    const inp = document.getElementById('mcp-search-input');
                    if (inp) {{ inp.value = t.name; filtrarMCPTools(t.name); }}
                }}
            }}));

            return [...baseCommands, ...toolsCommands];
        }}

        function abrirSpotlight() {{
            let modal = document.getElementById('spotlight-modal');
            if (!modal) {{
                criarSpotlightDOM();
                modal = document.getElementById('spotlight-modal');
            }}
            modal.style.display = 'flex';
            const inp = document.getElementById('spotlight-input');
            inp.value = '';
            filtrarSpotlight('');
            setTimeout(() => inp.focus(), 50);
        }}

        function fecharSpotlight() {{
            const modal = document.getElementById('spotlight-modal');
            if (modal) modal.style.display = 'none';
        }}

        function criarSpotlightDOM() {{
            const div = document.createElement('div');
            div.id = 'spotlight-modal';
            div.style.cssText = 'position:fixed;inset:0;background:rgba(2,6,23,0.85);backdrop-filter:blur(8px);z-index:9999;display:none;align-items:flex-start;justify-content:center;padding-top:5rem;';
            div.onclick = (e) => {{ if (e.target === div) fecharSpotlight(); }};
            div.innerHTML = `
                <div style="background:#0f172a;border:1px solid rgba(255,255,255,0.15);border-radius:16px;width:100%;max-width:640px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.7);overflow:hidden;display:flex;flex-direction:column;max-height:80vh;" onclick="event.stopPropagation()">
                    <div style="padding:1rem;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;gap:0.75rem;background:rgba(255,255,255,0.02);">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        <input type="text" id="spotlight-input" placeholder="Buscar ferramentas MCP, ações ou navegação (Ctrl + K)..." 
                               oninput="filtrarSpotlight(this.value)" onkeydown="navegarSpotlightTeclado(event)"
                               style="width:100%;background:transparent;border:none;color:#fff;font-size:0.9rem;font-weight:600;outline:none;">
                        <kbd style="font-size:0.7rem;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);padding:0.2rem 0.5rem;border-radius:4px;color:#94a3b8;cursor:pointer;" onclick="fecharSpotlight()">ESC</kbd>
                    </div>
                    <div id="spotlight-results" style="overflow-y:auto;padding:0.5rem;max-height:55vh;display:flex;flex-direction:column;gap:0.25rem;"></div>
                    <div style="padding:0.6rem 1rem;background:#020617;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;font-size:0.72rem;color:#94a3b8;">
                        <div><kbd style="background:rgba(255,255,255,0.1);padding:0.1rem 0.3rem;border-radius:3px;">↑</kbd> <kbd style="background:rgba(255,255,255,0.1);padding:0.1rem 0.3rem;border-radius:3px;">↓</kbd> Navegar • <kbd style="background:rgba(255,255,255,0.1);padding:0.1rem 0.3rem;border-radius:3px;">↵</kbd> Executar • <kbd style="background:rgba(255,255,255,0.1);padding:0.1rem 0.3rem;border-radius:3px;">ESC</kbd> Fechar</div>
                        <span style="color:#a855f7;font-weight:bold;font-family:monospace;">Spotlight Command Palette</span>
                    </div>
                </div>`;
            document.body.appendChild(div);
        }}

        function filtrarSpotlight(q) {{
            const query = (q || '').toLowerCase().trim();
            const allCommands = getSpotlightCommands();
            spotlightFilteredCommands = allCommands.filter(cmd => 
                !query || 
                cmd.title.toLowerCase().includes(query) || 
                cmd.desc.toLowerCase().includes(query) || 
                cmd.cat.toLowerCase().includes(query)
            );
            spotlightSelectedIndex = 0;
            renderizarSpotlightResultados();
        }}

        function renderizarSpotlightResultados() {{
            const container = document.getElementById('spotlight-results');
            if (!container) return;
            if (spotlightFilteredCommands.length === 0) {{
                container.innerHTML = `<div style="padding:2rem;text-align:center;color:#64748b;font-size:0.85rem;">Nenhuma ferramenta ou comando encontrado</div>`;
                return;
            }}
            let html = '';
            let currentCat = '';
            spotlightFilteredCommands.forEach((cmd, idx) => {{
                if (cmd.cat !== currentCat) {{
                    currentCat = cmd.cat;
                    html += `<div style="font-size:0.68rem;font-weight:800;text-transform:uppercase;color:#64748b;padding:0.5rem 0.75rem 0.2rem 0.75rem;letter-spacing:0.05em;">${{currentCat}}</div>`;
                }}
                const isSelected = idx === spotlightSelectedIndex;
                const iconSvg = getMcpIconSvg(cmd.iconType);
                html += `
                <div onclick="executarSpotlightComando(${{idx}})" 
                     style="display:flex;align-items:center;justify-content:space-between;padding:0.6rem 0.8rem;border-radius:8px;cursor:pointer;background:${{isSelected ? 'rgba(168,85,247,0.15)' : 'transparent'}};border:1px solid ${{isSelected ? 'rgba(168,85,247,0.3)' : 'transparent'}};transition:all 0.15s;">
                    <div style="display:flex;align-items:center;gap:0.6rem;min-width:0;">
                        <div style="width:28px;height:28px;border-radius:6px;background:rgba(255,255,255,0.05);display:flex;align-items:center;justify-content:center;flex-shrink:0;">${{iconSvg}}</div>
                        <div style="min-width:0;">
                            <div style="font-weight:700;font-size:0.82rem;color:#fff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:${{cmd.cat.startsWith('Ferramentas') ? 'monospace' : 'inherit'}};">${{cmd.title}}</div>
                            <div style="font-size:0.72rem;color:#94a3b8;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${{cmd.desc}}</div>
                        </div>
                    </div>
                    <span style="font-size:0.68rem;color:#94a3b8;background:rgba(255,255,255,0.05);padding:0.15rem 0.4rem;border-radius:4px;flex-shrink:0;">${{cmd.cat}}</span>
                </div>`;
            }});
            container.innerHTML = html;
        }}

        function executarSpotlightComando(idx) {{
            const cmd = spotlightFilteredCommands[idx];
            if (cmd && cmd.action) {{
                fecharSpotlight();
                cmd.action();
            }}
        }}

        function navegarSpotlightTeclado(e) {{
            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                if (spotlightSelectedIndex < spotlightFilteredCommands.length - 1) {{
                    spotlightSelectedIndex++;
                    renderizarSpotlightResultados();
                }}
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                if (spotlightSelectedIndex > 0) {{
                    spotlightSelectedIndex--;
                    renderizarSpotlightResultados();
                }}
            }} else if (e.key === 'Enter') {{
                e.preventDefault();
                executarSpotlightComando(spotlightSelectedIndex);
            }} else if (e.key === 'Escape') {{
                e.preventDefault();
                fecharSpotlight();
            }}
        }}

        document.addEventListener('keydown', (e) => {{
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {{
                e.preventDefault();
                abrirSpotlight();
            }} else if (e.key === 'Escape') {{
                fecharSpotlight();
            }}
        }});

        function filtrarMCPTools(q) {{
            const query = (q || '').toLowerCase().trim();
            const cards = document.querySelectorAll('.tool-card');
            let visiveis = 0;
            cards.forEach(card => {{
                const name = card.getAttribute('data-name') || '';
                const desc = card.getAttribute('data-desc') || '';
                const match = !query || name.includes(query) || desc.includes(query);
                card.style.display = match ? 'flex' : 'none';
                if (match) visiveis++;
            }});
            document.getElementById('tools-counter').textContent = `Exibindo ${{visiveis}} de ${{cards.length}} ferramentas`;
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            document.getElementById('toast-msg').textContent = msg;
            t.classList.remove('hidden');
            t.classList.add('flex');
            setTimeout(() => {{
                t.classList.add('hidden');
                t.classList.remove('flex');
            }}, 3000);
        }}

        function copiarTexto(texto, msg) {{
            navigator.clipboard.writeText(texto).then(() => {{
                showToast(msg || 'Copiado para a área de transferência');
            }});
        }}

        function copiarConfigClaude() {{
            const code = document.getElementById('claude-config-text').textContent;
            copiarTexto(code, 'Configuração copiada para o Claude Desktop!');
        }}
    </script>
</body>
</html>"""

def run_stdio_server(db_path: str):
    server = MedHealthMCPServer(db_path)
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
