import urllib.request, json, threading, hmac, hashlib, time, uuid, os

class WebhookDispatcher:
    EVENT_CATALOG = [
        {
            "event": "*",
            "modulo": "Global",
            "descricao": "Assina todos os eventos gerados por todos os módulos da suite.",
            "exemplo": {"event": "qualquer_evento", "data": {}}
        },
        {
            "event": "cross_domain.entrega_to_financeiro",
            "modulo": "Cross-Domain",
            "descricao": "Disparado quando uma entrega é finalizada e liquida a receita no financeiro.",
            "exemplo": {"codigo_rastreio": "BR-LOG-9821", "valor_frete": 8500.0, "status": "entregue"}
        },
        {
            "event": "frotas.veiculo_cadastrado",
            "modulo": "Frotas",
            "descricao": "Disparado ao adicionar um novo caminhão ou utilitário à frota.",
            "exemplo": {"placa": "BRA2E19", "modelo": "Volvo FH 540", "motorista": "Marcos Vinicius", "capacidade_kg": 32000}
        },
        {
            "event": "frotas.status_alterado",
            "modulo": "Frotas",
            "descricao": "Disparado quando o status operacional do veículo é modificado.",
            "exemplo": {"id": 1, "placa": "BRA2E19", "novo_status": "em_rota"}
        },
        {
            "event": "frotas.manutencao_alerta",
            "modulo": "Frotas",
            "descricao": "Disparado quando um veículo entra em manutenção e aciona o suporte SLA.",
            "exemplo": {"placa": "BRA2E19", "protocolo": "INC-A1B2", "prioridade": "P1"}
        },
        {
            "event": "entregas.remessa_criada",
            "modulo": "Entregas",
            "descricao": "Disparado ao registrar uma nova ordem de remessa ou transporte.",
            "exemplo": {"codigo_rastreio": "BR-LOG-4310", "destinatario": "SolarTech", "valor_frete": 14200.0}
        },
        {
            "event": "entregas.status_alterado",
            "modulo": "Entregas",
            "descricao": "Disparado quando a entrega muda de status (pendente -> em_transito -> entregue).",
            "exemplo": {"id": 1, "codigo_rastreio": "BR-LOG-9821", "novo_status": "entregue"}
        },
        {
            "event": "wms.item_adicionado",
            "modulo": "WMS",
            "descricao": "Disparado ao cadastrar um novo SKU no armazém logístico.",
            "exemplo": {"sku": "SKU-LOG-101", "descricao": "Bobinas de Aco", "quantidade": 450, "posicao": "RUA-A-04"}
        },
        {
            "event": "wms.posicao_alterada",
            "modulo": "WMS",
            "descricao": "Disparado na movimentação física de mercadoria no armazém.",
            "exemplo": {"id": 1, "sku": "SKU-LOG-101", "nova_posicao": "RUA-C-09"}
        },
        {
            "event": "financeiro.lancamento_criado",
            "modulo": "Financeiro",
            "descricao": "Disparado na criação de uma conta a pagar ou receber.",
            "exemplo": {"tipo": "receita", "descricao": "Faturamento Frete", "valor": 8500.0, "status": "pago"}
        },
        {
            "event": "suporte.incidente_aberto",
            "modulo": "SLA & Suporte",
            "descricao": "Disparado na abertura de um chamado crítico ou operacional.",
            "exemplo": {"protocolo": "INC-88A1", "titulo": "Falha Mecânica", "prioridade": "P1", "sla_horas": 2}
        },
        {
            "event": "suporte.incidente_resolvido",
            "modulo": "SLA & Suporte",
            "descricao": "Disparado ao solucionar um incidente de suporte.",
            "exemplo": {"id": 1, "status": "resolvido"}
        },
        {
            "event": "auth.login_sucesso",
            "modulo": "Segurança",
            "descricao": "Disparado após autenticação JWT bem-sucedida de um operador.",
            "exemplo": {"email": "admin@empresa.com", "role": "admin"}
        }
    ]

    def __init__(self, db):
        self.db = db

    def calcular_assinatura(self, secret: str, payload_bytes: bytes) -> str:
        if not secret:
            return ""
        sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    def disparar(self, evento: str, payload: dict):
        def _exec():
            try:
                with self.db.get_connection() as conn:
                    rows = conn.execute("SELECT id, nome, url, eventos, secret, retry_count FROM webhooks WHERE ativo = 1").fetchall()
                    if not rows:
                        return
                    webhooks = [dict(r) for r in rows]

                body_dict = {
                    "event": evento,
                    "timestamp": int(time.time()),
                    "delivery_id": str(uuid.uuid4()),
                    "data": payload
                }
                body_bytes = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")

                for wh in webhooks:
                    eventos_sub = []
                    try:
                        eventos_sub = json.loads(wh["eventos"]) if wh["eventos"] else ["*"]
                    except:
                        eventos_sub = [wh["eventos"]]

                    # Match event topic or wildcard
                    if "*" not in eventos_sub and evento not in eventos_sub:
                        continue

                    self._enviar_com_retry(wh, evento, body_bytes, body_dict)
            except Exception as e:
                print(f"[Webhook Dispatcher Error] {e}")

        threading.Thread(target=_exec, daemon=True).start()

    def _enviar_com_retry(self, wh: dict, evento: str, body_bytes: bytes, body_dict: dict):
        max_retries = wh.get("retry_count", 3) or 1
        url = wh["url"]
        secret = wh.get("secret", "")
        signature = self.calcular_assinatura(secret, body_bytes)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AIDD-Enterprise-Webhook-Studio/4.0",
            "X-Webhook-Event": evento,
            "X-Webhook-Delivery": body_dict.get("delivery_id", str(uuid.uuid4())),
            "X-Webhook-Timestamp": str(body_dict.get("timestamp", int(time.time())))
        }
        if signature:
            headers["X-Webhook-Signature"] = signature
            headers["X-Hub-Signature-256"] = signature

        for tentativa in range(1, max_retries + 1):
            t0 = time.time()
            status_code = None
            resp_body = ""
            status = "falha"
            try:
                req = urllib.request.Request(url, data=body_bytes, headers=headers)
                with urllib.request.urlopen(req, timeout=6) as response:
                    status_code = response.status
                    resp_body = response.read().decode("utf-8", errors="replace")[:1000]
                    status = "sucesso" if (200 <= status_code < 300) else "falha"
            except urllib.error.HTTPError as he:
                status_code = he.code
                resp_body = he.read().decode("utf-8", errors="replace")[:1000]
                status = "falha"
            except urllib.error.URLError as ue:
                resp_body = str(ue.reason)
                status = "timeout" if "timed out" in str(ue.reason).lower() else "falha"
            except Exception as ex:
                resp_body = str(ex)
                status = "falha"

            duracao_ms = round((time.time() - t0) * 1000, 2)

            # Grava no log de auditoria de webhooks
            try:
                with self.db.get_connection() as conn:
                    conn.execute("""
                        INSERT INTO webhook_logs (webhook_id, evento, url, payload_json, status_code, response_body, duracao_ms, status, tentativas)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (wh["id"], evento, url, json.dumps(body_dict, ensure_ascii=False), status_code, resp_body, duracao_ms, status, tentativa))
                    conn.commit()
            except Exception as db_err:
                print(f"[Webhook Log DB Error] {db_err}")

            if status == "sucesso":
                break
            time.sleep(1)

    def testar_disparo(self, url: str, secret: str, evento: str, payload: dict) -> dict:
        """Executa um disparo síncrono de teste e retorna métricas detalhadas."""
        body_dict = {
            "event": evento,
            "timestamp": int(time.time()),
            "delivery_id": str(uuid.uuid4()),
            "data": payload
        }
        body_bytes = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
        signature = self.calcular_assinatura(secret, body_bytes)

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AIDD-Enterprise-Webhook-Studio/4.0",
            "X-Webhook-Event": evento,
            "X-Webhook-Delivery": body_dict["delivery_id"],
            "X-Webhook-Timestamp": str(body_dict["timestamp"])
        }
        if signature:
            headers["X-Webhook-Signature"] = signature
            headers["X-Hub-Signature-256"] = signature

        t0 = time.time()
        status_code = None
        resp_body = ""
        status = "falha"

        try:
            req = urllib.request.Request(url, data=body_bytes, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as response:
                status_code = response.status
                resp_body = response.read().decode("utf-8", errors="replace")
                status = "sucesso" if (200 <= status_code < 300) else "falha"
        except urllib.error.HTTPError as he:
            status_code = he.code
            resp_body = he.read().decode("utf-8", errors="replace")
            status = "falha"
        except urllib.error.URLError as ue:
            resp_body = f"Erro de Conexão: {ue.reason}"
            status = "timeout" if "timed out" in str(ue.reason).lower() else "falha"
        except Exception as ex:
            resp_body = f"Erro inesperado: {str(ex)}"
            status = "falha"

        duracao_ms = round((time.time() - t0) * 1000, 2)

        # Grava log do teste
        try:
            with self.db.get_connection() as conn:
                conn.execute("""
                    INSERT INTO webhook_logs (webhook_id, evento, url, payload_json, status_code, response_body, duracao_ms, status, tentativas)
                    VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, 1)
                """, (evento, url, json.dumps(body_dict, ensure_ascii=False), status_code, resp_body[:1000], duracao_ms, status))
                conn.commit()
        except Exception:
            pass

        return {
            "sucesso": (status == "sucesso"),
            "status_code": status_code,
            "duracao_ms": duracao_ms,
            "status": status,
            "headers_enviados": headers,
            "payload_enviado": body_dict,
            "resposta_recebida": resp_body[:2000]
        }

    def listar_webhooks(self):
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM webhooks ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def listar_logs(self, limit: int = 50, status_filtro: str = None):
        with self.db.get_connection() as conn:
            if status_filtro and status_filtro != "todos":
                rows = conn.execute("SELECT * FROM webhook_logs WHERE status = ? ORDER BY id DESC LIMIT ?", (status_filtro, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM webhook_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_studio_html(self, title: str = "AIDD v4 — Webhook Configuration Studio") -> str:
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #060913;
            --bg-surface: #0c1222;
            --bg-elevated: #131d36;
            --bg-hover: #1b284a;
            --border: #1e293b;
            --border-light: rgba(255, 255, 255, 0.08);
            --border-focus: #3b82f6;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --text-subtle: #64748b;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --violet: #8b5cf6;
            --violet-hover: #7c3aed;
            --green: #10b981;
            --green-bg: rgba(16, 185, 129, 0.12);
            --red: #ef4444;
            --red-bg: rgba(239, 68, 68, 0.12);
            --amber: #f59e0b;
            --amber-bg: rgba(245, 158, 11, 0.12);
            --radius-sm: 6px;
            --radius-md: 10px;
            --radius-lg: 14px;
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-base);
            color: var(--text-main);
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }}

        ::-webkit-scrollbar {{
            width: 4px;
            height: 4px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-base);
        }}
        ::-webkit-scrollbar-thumb {{
            background: var(--border);
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--text-subtle);
        }}

        header {{
            background: rgba(12, 18, 34, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 0.85rem 2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 50;
            white-space: nowrap;
            overflow-x: auto;
            scrollbar-width: none;
        }}
        header::-webkit-scrollbar {{ display: none; }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            font-size: 1.05rem;
            letter-spacing: -0.01em;
            text-decoration: none;
            color: var(--text-main);
        }}

        .brand svg {{
            color: var(--violet);
        }}

        .badge-ver {{
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(59, 130, 246, 0.2));
            color: #c4b5fd;
            border: 1px solid rgba(139, 92, 246, 0.4);
            font-size: 0.68rem;
            font-weight: 700;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}

        .nav-tabs {{
            display: flex;
            gap: 0.4rem;
            background: rgba(0, 0, 0, 0.3);
            padding: 0.3rem;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }}

        .nav-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 0.45rem 0.9rem;
            font-size: 0.82rem;
            font-weight: 600;
            border-radius: var(--radius-sm);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.45rem;
            transition: all 0.15s ease;
        }}

        .nav-btn:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.04);
        }}

        .nav-btn.active {{
            color: #ffffff;
            background: var(--violet);
            box-shadow: 0 2px 8px rgba(139, 92, 246, 0.35);
        }}

        .header-actions {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.82rem;
            font-weight: 600;
            padding: 0.48rem 0.95rem;
            border-radius: var(--radius-sm);
            cursor: pointer;
            text-decoration: none;
            transition: all 0.15s ease;
            border: 1px solid var(--border);
            background: var(--bg-surface);
            color: var(--text-main);
        }}

        .btn:hover {{
            background: var(--bg-elevated);
            border-color: var(--border-focus);
        }}

        .btn-primary {{
            background: var(--violet);
            border-color: var(--violet);
            color: #ffffff;
        }}
        .btn-primary:hover {{
            background: var(--violet-hover);
            border-color: var(--violet-hover);
        }}

        .btn-success {{
            background: var(--green);
            border-color: var(--green);
            color: #ffffff;
        }}
        .btn-sm {{
            padding: 0.3rem 0.6rem;
            font-size: 0.75rem;
        }}

        main {{
            flex: 1;
            padding: 2rem;
            max-width: 1440px;
            width: 100%;
            margin: 0 auto;
        }}

        /* METRICS HERO */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            position: relative;
            overflow: hidden;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--violet), var(--primary));
        }}

        .stat-title {{
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-subtle);
            font-weight: 700;
        }}

        .stat-val {{
            font-size: 1.6rem;
            font-weight: 800;
            color: #ffffff;
            font-family: 'JetBrains Mono', monospace;
        }}

        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
            animation: fadeIn 0.2s ease-in-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* CARDS & TABLES */
        .panel {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            overflow: hidden;
            box-shadow: var(--shadow-md);
            margin-bottom: 2rem;
        }}

        .panel-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.015);
        }}

        .panel-title {{
            font-size: 1.05rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }}

        .panel-desc {{
            font-size: 0.82rem;
            color: var(--text-muted);
            margin-top: 0.2rem;
        }}

        .table-responsive {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.85rem;
        }}

        th {{
            background: rgba(0, 0, 0, 0.2);
            color: var(--text-subtle);
            font-weight: 700;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.85rem 1.25rem;
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border);
            color: var(--text-main);
            vertical-align: middle;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.2rem 0.55rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }}

        .badge-success {{ background: var(--green-bg); color: var(--green); border: 1px solid rgba(16,185,129,0.3); }}
        .badge-danger {{ background: var(--red-bg); color: var(--red); border: 1px solid rgba(239,68,68,0.3); }}
        .badge-warning {{ background: var(--amber-bg); color: var(--amber); border: 1px solid rgba(245,158,11,0.3); }}
        .badge-event {{ background: rgba(139, 92, 246, 0.15); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.3); font-family: 'JetBrains Mono', monospace; }}

        .code-pill {{
            font-family: 'JetBrains Mono', monospace;
            background: rgba(0, 0, 0, 0.4);
            padding: 0.2rem 0.5rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            font-size: 0.8rem;
            color: #93c5fd;
        }}

        /* FORM ELEMENTS */
        .form-group {{
            margin-bottom: 1.25rem;
        }}
        .form-label {{
            display: block;
            font-size: 0.82rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.45rem;
        }}
        .form-control {{
            width: 100%;
            background: var(--bg-base);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 0.65rem 0.9rem;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            font-family: inherit;
            transition: border-color 0.15s ease;
        }}
        .form-control:focus {{
            outline: none;
            border-color: var(--violet);
            box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2);
        }}
        textarea.form-control {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            resize: vertical;
        }}

        /* MODAL */
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(4px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 100;
            padding: 1.5rem;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal-card {{
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            width: 100%;
            max-width: 600px;
            box-shadow: var(--shadow-lg);
            overflow: hidden;
            animation: modalPop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        @keyframes modalPop {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .modal-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .modal-body {{
            padding: 1.5rem;
            max-height: 75vh;
            overflow-y: auto;
        }}
        .modal-footer {{
            padding: 1rem 1.5rem;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: flex-end;
            gap: 0.75rem;
            background: rgba(0, 0, 0, 0.15);
        }}

        /* 2-COLUMN PLAYGROUND */
        .playground-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}
        @media (max-width: 992px) {{
            .playground-grid {{ grid-template-columns: 1fr; }}
        }}

        .console-box {{
            background: #020617;
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: #cbd5e1;
            overflow-x: auto;
            max-height: 480px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}

        /* TOAST */
        #toast {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--bg-elevated);
            color: #ffffff;
            border: 1px solid var(--violet);
            padding: 0.85rem 1.25rem;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-lg);
            display: none;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.85rem;
            z-index: 200;
            animation: slideUp 0.25s ease;
        }}
        @keyframes slideUp {{
            from {{ transform: translateY(20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
    </style>
</head>
<body>

    <header>
        <a href="/webhooks" class="brand">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c0-2.21 1.79-4 4-4h1"/><path d="M6 13V7a4 4 0 0 1 7.9-1"/><path d="M12 7h6a4 4 0 0 1 0 8h-1"/><circle cx="6" cy="17" r="1"/><circle cx="18" cy="15" r="1"/><circle cx="10" cy="4" r="1"/></svg>
            <span>Webhook Configuration Studio</span>
            <span class="badge-ver">v4.0 Enterprise</span>
        </a>

        <div class="nav-tabs">
            <button class="nav-btn active" onclick="switchTab('endpoints')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                Endpoints ({len(self.listar_webhooks())})
            </button>
            <button class="nav-btn" onclick="switchTab('playground')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Simulador & Testes
            </button>
            <button class="nav-btn" onclick="switchTab('logs')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                Auditoria & Logs
            </button>
            <button class="nav-btn" onclick="switchTab('catalog')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                Catálogo de Eventos & HMAC
            </button>
        </div>

        <div class="header-actions">
            <a href="/" class="btn">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
                Super-App
            </a>
            <a href="/mcp" class="btn" style="border-color: rgba(16,185,129,0.4); color: #34d399;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                Portal MCP
            </a>
            <a href="/docs" class="btn btn-primary">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Swagger Studio
            </a>
        </div>
    </header>

    <main>
        <!-- KPI METRICS -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-title">Endpoints Configurados</span>
                <span class="stat-val" id="stat-endpoints">0</span>
            </div>
            <div class="stat-card">
                <span class="stat-title">Disparos Realizados</span>
                <span class="stat-val" id="stat-total-logs" style="color: var(--violet);">0</span>
            </div>
            <div class="stat-card">
                <span class="stat-title">Taxa de Sucesso (2xx)</span>
                <span class="stat-val" id="stat-success-rate" style="color: var(--green);">100%</span>
            </div>
            <div class="stat-card">
                <span class="stat-title">Assinatura de Segurança</span>
                <span class="stat-val" style="color: #60a5fa; font-size: 1.2rem; margin-top: 0.3rem;">HMAC SHA-256</span>
            </div>
        </div>

        <!-- 1. ABA ENDPOINTS -->
        <div id="tab-endpoints" class="tab-content active">
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
                            Destinos & Webhook Endpoints
                        </div>
                        <div class="panel-desc">Gerencie os servidores externos que recebem notificações de eventos da Suite em tempo real com retry e assinatura criptográfica.</div>
                    </div>
                    <button class="btn btn-primary" onclick="abrirModalCriar()">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                        Novo Endpoint
                    </button>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Nome & Destino (URL)</th>
                                <th>Eventos Assinados</th>
                                <th>Secret HMAC</th>
                                <th>Retries</th>
                                <th>Status</th>
                                <th style="text-align: right;">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="lista-endpoints">
                            <tr><td colspan="6" style="text-align: center; color: var(--text-subtle);">Carregando endpoints...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 2. ABA SIMULADOR & TESTES -->
        <div id="tab-playground" class="tab-content">
            <div class="playground-grid">
                <div class="panel" style="margin-bottom: 0;">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                                Emissor de Disparos de Teste
                            </div>
                            <div class="panel-desc">Envie um evento simulado para validar seu webhook endpoint e checar latência e resposta.</div>
                        </div>
                    </div>
                    <div style="padding: 1.5rem;">
                        <div class="form-group">
                            <label class="form-label">Carregar de Endpoint Cadastrado</label>
                            <select id="play-select-wh" class="form-control" onchange="preencherPlayground(this.value)">
                                <option value="">-- Selecione ou digite manualmente --</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">URL de Destino (POST)</label>
                            <input type="url" id="play-url" class="form-control" placeholder="https://webhook.site/..." required>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Secret Token (para X-Webhook-Signature HMAC)</label>
                            <input type="text" id="play-secret" class="form-control" placeholder="sec_hub_v4_...">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Tópico do Evento</label>
                            <select id="play-evento" class="form-control" onchange="trocarTemplateEvento(this.value)">
                                <option value="cross_domain.entrega_to_financeiro">cross_domain.entrega_to_financeiro</option>
                                <option value="frotas.veiculo_cadastrado">frotas.veiculo_cadastrado</option>
                                <option value="frotas.manutencao_alerta">frotas.manutencao_alerta</option>
                                <option value="entregas.remessa_criada">entregas.remessa_criada</option>
                                <option value="entregas.status_alterado">entregas.status_alterado</option>
                                <option value="wms.item_adicionado">wms.item_adicionado</option>
                                <option value="financeiro.lancamento_criado">financeiro.lancamento_criado</option>
                                <option value="suporte.incidente_aberto">suporte.incidente_aberto</option>
                                <option value="auth.login_sucesso">auth.login_sucesso</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Payload JSON (data)</label>
                            <textarea id="play-payload" class="form-control" rows="6"></textarea>
                        </div>
                        <button class="btn btn-primary" style="width: 100%; justify-content: center; padding: 0.75rem;" onclick="executarTesteDisparo()">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                            Disparar Webhook Agora
                        </button>
                    </div>
                </div>

                <div class="panel" style="margin-bottom: 0;">
                    <div class="panel-header">
                        <div>
                            <div class="panel-title">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                                Resposta & Headers da Entrega
                            </div>
                            <div class="panel-desc">Monitoramento síncrono de headers calculados, assinatura HMAC e corpo HTTP.</div>
                        </div>
                        <span id="play-badge-status" class="badge badge-warning">Aguardando Disparo</span>
                    </div>
                    <div style="padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem;">
                        <div>
                            <label class="form-label">Headers HTTP Enviados</label>
                            <div id="play-headers" class="console-box" style="height: 110px;">// Execute um disparo para visualizar headers</div>
                        </div>
                        <div>
                            <label class="form-label">Corpo de Resposta do Receptor</label>
                            <div id="play-response" class="console-box" style="height: 180px;">// O payload de resposta do endpoint aparecerá aqui</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 3. ABA AUDITORIA & LOGS -->
        <div id="tab-logs" class="tab-content">
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                            Histórico de Disparos & Auditoria de Webhooks
                        </div>
                        <div class="panel-desc">Auditoria ponta a ponta com status code, tempo de execução (ms) e histórico de tentativas.</div>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <select id="filtro-status-logs" class="form-control" style="width: auto; padding: 0.35rem 0.75rem;" onchange="carregarLogs()">
                            <option value="todos">Todos os Status</option>
                            <option value="sucesso">Somente Sucesso</option>
                            <option value="falha">Somente Falhas</option>
                            <option value="timeout">Somente Timeouts</option>
                        </select>
                        <button class="btn btn-sm" onclick="carregarLogs()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                            Atualizar
                        </button>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Data/Hora</th>
                                <th>Evento</th>
                                <th>Destino (URL)</th>
                                <th>Status HTTP</th>
                                <th>Latência</th>
                                <th>Tentativas</th>
                                <th style="text-align: right;">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="lista-logs">
                            <tr><td colspan="7" style="text-align: center; color: var(--text-subtle);">Carregando logs de auditoria...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- 4. ABA CATÁLOGO & HMAC GUIDE -->
        <div id="tab-catalog" class="tab-content">
            <div class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--violet)" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                            Catálogo Oficial de Eventos do Sistema
                        </div>
                        <div class="panel-desc">Lista canônica dos tópicos de eventos emitidos pelas fatias verticais e pelo EventBus cross-domain.</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Tópico do Evento</th>
                                <th>Módulo de Origem</th>
                                <th>Descrição da Ação</th>
                                <th>Exemplo de Payload</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''<tr>
                                <td><span class="badge badge-event">{ev["event"]}</span></td>
                                <td><span class="code-pill">{ev["modulo"]}</span></td>
                                <td>{ev["descricao"]}</td>
                                <td><span class="code-pill">{json.dumps(ev["exemplo"], ensure_ascii=False)}</span></td>
                            </tr>''' for ev in self.EVENT_CATALOG])}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div>
                        <div class="panel-title">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#60a5fa" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                            Guia de Verificação de Assinatura HMAC SHA-256
                        </div>
                        <div class="panel-desc">Como seu servidor receptor deve validar o cabeçalho <code>X-Webhook-Signature</code> para garantir autenticidade.</div>
                    </div>
                </div>
                <div style="padding: 1.5rem; display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                    <div>
                        <label class="form-label" style="color: #93c5fd;">Validação em Node.js (Express / Fastify)</label>
                        <div class="console-box">const crypto = require('crypto');

function verifyWebhook(req, res, next) {{
  const signature = req.headers['x-webhook-signature']; // sha256=...
  const secret = process.env.WEBHOOK_SECRET;
  
  const hmac = crypto.createHmac('sha256', secret);
  const digest = 'sha256=' + hmac.update(req.rawBody).digest('hex');
  
  if (crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(digest))) {{
    return next();
  }}
  return res.status(401).send('Invalid Signature');
}}</div>
                    </div>
                    <div>
                        <label class="form-label" style="color: #93c5fd;">Validação em Python (FastAPI / Flask / Django)</label>
                        <div class="console-box">import hmac, hashlib

def verify_webhook(raw_body: bytes, signature_header: str, secret: str) -> bool:
    expected_sig = "sha256=" + hmac.new(
        secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature_header, expected_sig)</div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- MODAL CRIAR/EDITAR ENDPOINT -->
    <div id="modal-endpoint" class="modal-overlay">
        <div class="modal-card">
            <div class="modal-header">
                <div class="panel-title" id="modal-titulo">Novo Webhook Endpoint</div>
                <button class="btn btn-sm" onclick="fecharModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="wh-id">
                <div class="form-group">
                    <label class="form-label">Nome do Endpoint / Aplicação Receptora</label>
                    <input type="text" id="wh-nome" class="form-control" placeholder="ex: ERP SAP Liquidações / Slack Bot" required>
                </div>
                <div class="form-group">
                    <label class="form-label">URL de Destino (HTTPS recomendada)</label>
                    <input type="url" id="wh-url" class="form-control" placeholder="https://seu-servidor.com/webhook" required>
                </div>
                <div class="form-group">
                    <label class="form-label">Secret Token (Assinatura HMAC SHA-256)</label>
                    <div style="display: flex; gap: 0.5rem;">
                        <input type="text" id="wh-secret" class="form-control" placeholder="sec_hub_v4_...">
                        <button type="button" class="btn" onclick="gerarSecretRandom()">Gerar</button>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Tópicos de Eventos Assinados</label>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; font-size: 0.8rem; background: rgba(0,0,0,0.2); padding: 0.75rem; border-radius: var(--radius-sm);">
                        <label><input type="checkbox" name="wh-ev" value="*" checked> <b>Todos (*)</b></label>
                        <label><input type="checkbox" name="wh-ev" value="cross_domain.entrega_to_financeiro"> cross_domain.entrega_to_financeiro</label>
                        <label><input type="checkbox" name="wh-ev" value="frotas.veiculo_cadastrado"> frotas.veiculo_cadastrado</label>
                        <label><input type="checkbox" name="wh-ev" value="frotas.manutencao_alerta"> frotas.manutencao_alerta</label>
                        <label><input type="checkbox" name="wh-ev" value="entregas.remessa_criada"> entregas.remessa_criada</label>
                        <label><input type="checkbox" name="wh-ev" value="entregas.status_alterado"> entregas.status_alterado</label>
                        <label><input type="checkbox" name="wh-ev" value="wms.item_adicionado"> wms.item_adicionado</label>
                        <label><input type="checkbox" name="wh-ev" value="financeiro.lancamento_criado"> financeiro.lancamento_criado</label>
                        <label><input type="checkbox" name="wh-ev" value="suporte.incidente_aberto"> suporte.incidente_aberto</label>
                        <label><input type="checkbox" name="wh-ev" value="auth.login_sucesso"> auth.login_sucesso</label>
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Tentativas de Retry em caso de falha</label>
                    <select id="wh-retry" class="form-control">
                        <option value="1">1 tentativa (Sem retry)</option>
                        <option value="3" selected>3 tentativas (Recomendado)</option>
                        <option value="5">5 tentativas</option>
                    </select>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="fecharModal()">Cancelar</button>
                <button class="btn btn-primary" onclick="salvarEndpoint()">Salvar Endpoint</button>
            </div>
        </div>
    </div>

    <!-- MODAL DETALHES DE LOG -->
    <div id="modal-log-detalhe" class="modal-overlay">
        <div class="modal-card" style="max-width: 700px;">
            <div class="modal-header">
                <div class="panel-title">Auditoria do Disparo</div>
                <button class="btn btn-sm" onclick="document.getElementById('modal-log-detalhe').classList.remove('active')">&times;</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label class="form-label">Payload Enviado</label>
                    <div id="log-det-payload" class="console-box" style="height: 140px;"></div>
                </div>
                <div class="form-group">
                    <label class="form-label">Resposta do Servidor Receptor</label>
                    <div id="log-det-resp" class="console-box" style="height: 140px;"></div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn" onclick="document.getElementById('modal-log-detalhe').classList.remove('active')">Fechar</button>
            </div>
        </div>
    </div>

    <!-- TOAST -->
    <div id="toast">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <span id="toast-msg">Sucesso</span>
    </div>

    <script>
        let endpointsData = [];
        let logsData = [];

        const EVENT_TEMPLATES = {{
            "cross_domain.entrega_to_financeiro": {{"codigo_rastreio": "BR-LOG-9821", "valor_frete": 8500.0, "status": "entregue", "cliente": "BioMed Farmaceutica"}},
            "frotas.veiculo_cadastrado": {{"placa": "BRA2E19", "modelo": "Volvo FH 540", "motorista": "Marcos Vinicius", "capacidade_kg": 32000}},
            "frotas.manutencao_alerta": {{"placa": "BRA2E19", "protocolo": "INC-A1B2", "prioridade": "P1", "descricao": "Pressao de Oleo Baixa"}},
            "entregas.remessa_criada": {{"codigo_rastreio": "BR-LOG-4310", "destinatario": "SolarTech Energia", "cidade_destino": "Curitiba/PR", "valor_frete": 14200.0}},
            "entregas.status_alterado": {{"id": 1, "codigo_rastreio": "BR-LOG-9821", "novo_status": "entregue"}},
            "wms.item_adicionado": {{"sku": "SKU-LOG-101", "descricao": "Bobinas de Aco Inox", "quantidade": 450, "posicao_palete": "RUA-A-04"}},
            "financeiro.lancamento_criado": {{"tipo": "receita", "descricao": "Faturamento Frete BR-LOG-9821", "valor": 8500.0, "status": "pago"}},
            "suporte.incidente_aberto": {{"protocolo": "INC-88A1", "titulo": "Manutencao Preventiva", "prioridade": "P1", "sla_horas": 2}},
            "auth.login_sucesso": {{"email": "admin@empresa.com", "role": "admin", "timestamp": Date.now()}}
        }};

        function switchTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            
            const targetTab = document.getElementById('tab-' + tabId);
            if (targetTab) targetTab.classList.add('active');
            
            event.currentTarget.classList.add('active');

            if (tabId === 'endpoints') carregarEndpoints();
            if (tabId === 'logs') carregarLogs();
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            document.getElementById('toast-msg').textContent = msg;
            t.style.display = 'flex';
            setTimeout(() => {{ t.style.display = 'none'; }}, 3000);
        }}

        function gerarSecretRandom() {{
            const rand = 'sec_hub_v4_' + Math.random().toString(36).substring(2, 12) + Math.random().toString(36).substring(2, 8);
            document.getElementById('wh-secret').value = rand;
        }}

        async function carregarEndpoints() {{
            try {{
                const res = await fetch('/api/webhooks');
                endpointsData = await res.json();
                
                document.getElementById('stat-endpoints').textContent = endpointsData.length;
                const selectWh = document.getElementById('play-select-wh');
                selectWh.innerHTML = '<option value="">-- Selecione ou digite manualmente --</option>';

                const tbody = document.getElementById('lista-endpoints');
                if (endpointsData.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--text-subtle);">Nenhum webhook endpoint configurado ainda.</td></tr>';
                    return;
                }}

                let html = '';
                endpointsData.forEach(wh => {{
                    let eventosList = [];
                    try {{ eventosList = JSON.parse(wh.eventos); }} catch(e) {{ eventosList = [wh.eventos]; }}
                    
                    const eventosBadges = eventosList.map(e => `<span class="badge badge-event">${{e}}</span>`).join(' ');
                    const statusBadge = wh.ativo == 1 
                        ? '<span class="badge badge-success">Ativo</span>' 
                        : '<span class="badge badge-danger">Inativo</span>';

                    selectWh.innerHTML += `<option value="${{wh.id}}">${{wh.nome}} (${{wh.url}})</option>`;

                    html += `<tr>
                        <td>
                            <div style="font-weight: 700;">${{wh.nome}}</div>
                            <div style="font-size: 0.78rem; color: var(--text-subtle); font-family: monospace;">${{wh.url}}</div>
                        </td>
                        <td>${{eventosBadges}}</td>
                        <td>
                            <span class="code-pill">••••••••</span>
                        </td>
                        <td><span class="badge badge-event">${{wh.retry_count || 3}}x</span></td>
                        <td>${{statusBadge}}</td>
                        <td style="text-align: right;">
                            <button class="btn btn-sm" onclick="testarEndpointDireto(${{wh.id}})">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                                Testar Ping
                            </button>
                            <button class="btn btn-sm" onclick="alternarStatus(${{wh.id}})">
                                ${{wh.ativo == 1 ? 'Pausar' : 'Ativar'}}
                            </button>
                            <button class="btn btn-sm" style="color: var(--red); border-color: rgba(239,68,68,0.4);" onclick="excluirEndpoint(${{wh.id}})">
                                Excluir
                            </button>
                        </td>
                    </tr>`;
                }});
                tbody.innerHTML = html;
            }} catch (err) {{
                console.error(err);
            }}
        }}

        function abrirModalCriar() {{
            document.getElementById('modal-titulo').textContent = 'Novo Webhook Endpoint';
            document.getElementById('wh-id').value = '';
            document.getElementById('wh-nome').value = '';
            document.getElementById('wh-url').value = '';
            gerarSecretRandom();
            document.getElementById('modal-endpoint').classList.add('active');
        }}

        function fecharModal() {{
            document.getElementById('modal-endpoint').classList.remove('active');
        }}

        async function salvarEndpoint() {{
            const id = document.getElementById('wh-id').value;
            const nome = document.getElementById('wh-nome').value.trim();
            const url = document.getElementById('wh-url').value.trim();
            const secret = document.getElementById('wh-secret').value.trim();
            const retry_count = parseInt(document.getElementById('wh-retry').value) || 3;

            if (!nome || !url) {{
                alert('Preencha Nome e URL.');
                return;
            }}

            const checkboxes = document.querySelectorAll('input[name="wh-ev"]:checked');
            const eventos = Array.from(checkboxes).map(cb => cb.value);

            const payload = {{
                nome,
                url,
                secret,
                eventos: JSON.stringify(eventos.length > 0 ? eventos : ["*"]),
                retry_count,
                ativo: 1
            }};

            const epUrl = id ? '/api/webhooks/atualizar' : '/api/webhooks';
            if (id) payload.id = parseInt(id);

            const res = await fetch(epUrl, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload)
            }});

            const data = await res.json();
            if (data.sucesso) {{
                fecharModal();
                showToast('Webhook salvo com sucesso!');
                carregarEndpoints();
            }} else {{
                alert('Erro ao salvar webhook: ' + (data.error || 'Falha'));
            }}
        }}

        async function alternarStatus(id) {{
            const res = await fetch('/api/webhooks/toggle', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ id }})
            }});
            const data = await res.json();
            if (data.sucesso) {{
                showToast('Status atualizado!');
                carregarEndpoints();
            }}
        }}

        async function excluirEndpoint(id) {{
            if (!confirm('Deseja realmente remover este webhook endpoint?')) return;
            const res = await fetch('/api/webhooks/excluir', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ id }})
            }});
            const data = await res.json();
            if (data.sucesso) {{
                showToast('Webhook excluído.');
                carregarEndpoints();
            }}
        }}

        function preencherPlayground(whId) {{
            if (!whId) return;
            const wh = endpointsData.find(w => w.id == whId);
            if (!wh) return;
            document.getElementById('play-url').value = wh.url;
            document.getElementById('play-secret').value = wh.secret;
        }}

        function trocarTemplateEvento(ev) {{
            const tmpl = EVENT_TEMPLATES[ev] || {{ "mensagem": "Disparo de Teste" }};
            document.getElementById('play-payload').value = JSON.stringify(tmpl, null, 2);
        }}

        async function executarTesteDisparo() {{
            const url = document.getElementById('play-url').value.trim();
            const secret = document.getElementById('play-secret').value.trim();
            const evento = document.getElementById('play-evento').value;
            let payload = {{}};

            try {{
                payload = JSON.parse(document.getElementById('play-payload').value);
            }} catch(e) {{
                alert('JSON inválido no corpo do payload.');
                return;
            }}

            const badgeStatus = document.getElementById('play-badge-status');
            badgeStatus.className = 'badge badge-warning';
            badgeStatus.textContent = 'Enviando...';

            try {{
                const res = await fetch('/api/webhooks/testar', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ url, secret, evento, payload }})
                }});
                const data = await res.json();

                if (data.sucesso) {{
                    badgeStatus.className = 'badge badge-success';
                    badgeStatus.textContent = `200 OK (${{data.duracao_ms}}ms)`;
                    showToast('Disparo entregue com sucesso!');
                }} else {{
                    badgeStatus.className = 'badge badge-danger';
                    badgeStatus.textContent = `Falha: ${{data.status_code || 'Erro'}} (${{data.duracao_ms}}ms)`;
                }}

                document.getElementById('play-headers').textContent = JSON.stringify(data.headers_enviados, null, 2);
                document.getElementById('play-response').textContent = data.resposta_recebida || '(Nenhum corpo de resposta)';
            }} catch (err) {{
                badgeStatus.className = 'badge badge-danger';
                badgeStatus.textContent = 'Erro de Rede';
                document.getElementById('play-response').textContent = String(err);
            }}
        }}

        async function testarEndpointDireto(whId) {{
            const wh = endpointsData.find(w => w.id == whId);
            if (!wh) return;
            switchTab('playground');
            document.getElementById('play-select-wh').value = whId;
            preencherPlayground(whId);
            trocarTemplateEvento(document.getElementById('play-evento').value);
            setTimeout(executarTesteDisparo, 200);
        }}

        async function carregarLogs() {{
            const statusFiltro = document.getElementById('filtro-status-logs').value;
            try {{
                const res = await fetch(`/api/webhooks/logs?status=${{statusFiltro}}`);
                logsData = await res.json();

                document.getElementById('stat-total-logs').textContent = logsData.length;
                if (logsData.length > 0) {{
                    const sucs = logsData.filter(l => l.status === 'sucesso').length;
                    const rate = Math.round((sucs / logsData.length) * 100);
                    document.getElementById('stat-success-rate').textContent = rate + '%';
                }}

                const tbody = document.getElementById('lista-logs');
                if (logsData.length === 0) {{
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-subtle);">Nenhum log gravado ainda.</td></tr>';
                    return;
                }}

                let html = '';
                logsData.forEach(log => {{
                    const badge = log.status === 'sucesso' 
                        ? `<span class="badge badge-success">${{log.status_code || 200}} OK</span>`
                        : `<span class="badge badge-danger">${{log.status_code || log.status}}</span>`;

                    html += `<tr>
                        <td style="font-size: 0.78rem; color: var(--text-muted);">${{log.criado_em}}</td>
                        <td><span class="badge badge-event">${{log.evento}}</span></td>
                        <td style="font-family: monospace; font-size: 0.78rem;">${{log.url}}</td>
                        <td>${{badge}}</td>
                        <td><span class="code-pill">${{log.duracao_ms}}ms</span></td>
                        <td>${{log.tentativas || 1}}x</td>
                        <td style="text-align: right;">
                            <button class="btn btn-sm" onclick="verDetalhesLog(${{log.id}})">Ver Payload</button>
                            <button class="btn btn-sm" onclick="reenviarLog(${{log.id}})">Reenviar</button>
                        </td>
                    </tr>`;
                }});
                tbody.innerHTML = html;
            }} catch(err) {{
                console.error(err);
            }}
        }}

        function verDetalhesLog(logId) {{
            const l = logsData.find(x => x.id == logId);
            if (!l) return;
            document.getElementById('log-det-payload').textContent = l.payload_json || '(Vazio)';
            document.getElementById('log-det-resp').textContent = l.response_body || '(Sem corpo retornado)';
            document.getElementById('modal-log-detalhe').classList.add('active');
        }}

        async function reenviarLog(logId) {{
            const res = await fetch('/api/webhooks/logs/reenviar', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ log_id: logId }})
            }});
            const data = await res.json();
            if (data.sucesso) {{
                showToast('Webhook reenviado!');
                carregarLogs();
            }} else {{
                alert('Erro ao reenviar: ' + (data.error || 'Falha'));
            }}
        }}

        // Inicialização
        document.addEventListener('DOMContentLoaded', () => {{
            trocarTemplateEvento('cross_domain.entrega_to_financeiro');
            carregarEndpoints();
            carregarLogs();
        }});
    </script>
</body>
</html>
"""
