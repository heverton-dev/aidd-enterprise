import json

class RouteRegistry:
    def __init__(self):
        self.routes = {"GET": {}, "POST": {}}
        self.docs = {}

    def get(self, path: str, summary: str = "", tags: list = None):
        def decorator(fn):
            self.routes["GET"][path] = fn
            return fn
        return decorator

    def post(self, path: str, summary: str = "", tags: list = None):
        def decorator(fn):
            self.routes["POST"][path] = fn
            return fn
        return decorator

    def generate_openapi_json(self, title: str, version: str):
        return {"openapi": "3.1.0", "info": {"title": title, "version": version}}

    def get_swagger_html(self, title: str):
        return """<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Reference Studio — AIDD Enterprise Suite v4.0</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #020617;
            --bg-sidebar: #050b18;
            --bg-middle: #040814;
            --bg-studio: #030712;
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #3b82f6;
            --primary-light: #60a5fa;
            --method-get: #10b981;
            --method-post: #3b82f6;
            --method-delete: #ef4444;
            --code-bg: #030712;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body {
            background: var(--bg-body);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        header {
            height: 56px;
            background: rgba(3, 7, 18, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            flex-shrink: 0;
            z-index: 50;
        }
        .brand-group { display: flex; align-items: center; gap: 0.8rem; text-decoration: none; }
        .brand-title { font-weight: 800; font-size: 0.95rem; color: #fff; display: flex; align-items: center; gap: 0.6rem; }
        .badge-ver { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: var(--primary-light); font-size: 0.72rem; font-weight: 800; padding: 0.2rem 0.5rem; border-radius: 9999px; }

        .btn {
            padding: 0.45rem 0.9rem;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.04);
            color: #fff;
            text-decoration: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            transition: all 0.2s;
        }
        .btn:hover { background: rgba(255, 255, 255, 0.08); border-color: var(--border-hover); }
        .btn-primary { background: var(--primary); border-color: var(--primary); }

        .studio-layout {
            display: grid;
            grid-template-columns: 290px 1fr 480px;
            flex: 1;
            height: calc(100vh - 56px);
            overflow: hidden;
        }

        aside.sidebar {
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            overflow-y: auto;
            padding: 1.2rem 0.8rem;
            display: flex;
            flex-direction: column;
            gap: 1.2rem;
        }
        .search-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            padding: 0.55rem 0.8rem;
            border-radius: 8px;
            color: var(--text-muted);
            font-size: 0.82rem;
        }
        .search-box input {
            background: none;
            border: none;
            outline: none;
            color: #fff;
            font-size: 0.84rem;
            width: 100%;
        }
        .nav-cat-title {
            font-size: 0.72rem;
            font-weight: 800;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            padding: 0.8rem 0.6rem 0.3rem 0.6rem;
        }
        .endpoint-link {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.55rem 0.7rem;
            border-radius: 8px;
            color: #cbd5e1;
            font-size: 0.84rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
            text-decoration: none;
        }
        .endpoint-link:hover, .endpoint-link.active {
            background: rgba(59, 130, 246, 0.12);
            color: #fff;
        }
        .method-pill {
            font-size: 0.65rem;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            min-width: 44px;
            text-align: center;
        }
        .pill-get { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .pill-post { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .pill-delete { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

        main.doc-column {
            background: var(--bg-middle);
            overflow-y: auto;
            padding: 3rem 3.5rem;
            border-right: 1px solid var(--border);
        }
        .doc-tag-badge {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--primary-light);
            letter-spacing: 0.05em;
            margin-bottom: 0.6rem;
        }
        .doc-endpoint-title { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 1rem; color: #fff; }
        .path-badge-box {
            display: inline-flex;
            align-items: center;
            gap: 0.8rem;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            padding: 0.6rem 1rem;
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 1.8rem;
        }
        .doc-desc { font-size: 0.98rem; line-height: 1.7; color: #cbd5e1; margin-bottom: 2rem; }

        h3.section-header {
            font-size: 1.1rem;
            font-weight: 800;
            color: #fff;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--border);
        }

        .params-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        .params-table th, .params-table td { padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.86rem; }
        .params-table th { font-size: 0.72rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; }
        .param-name { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #fff; }
        .param-type { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #94a3b8; }
        .badge-req { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); font-size: 0.68rem; font-weight: 800; padding: 0.1rem 0.35rem; border-radius: 4px; margin-left: 0.4rem; }

        aside.studio-column {
            background: var(--bg-studio);
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        .studio-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .studio-title { font-size: 0.88rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }

        .lang-tabs {
            display: flex;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.2rem;
            gap: 0.2rem;
        }
        .lang-tab {
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-muted);
            cursor: pointer;
            border: none;
            background: none;
            transition: all 0.15s;
        }
        .lang-tab.active { background: rgba(59, 130, 246, 0.2); color: var(--primary-light); }

        .code-box {
            background: #020617;
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
        }
        .code-header {
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--border);
            padding: 0.6rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-muted);
        }
        pre.code-content {
            padding: 1.2rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            line-height: 1.6;
            color: #e2e8f0;
            overflow-x: auto;
        }

        textarea.body-editor {
            width: 100%;
            height: 180px;
            background: #020617;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.82rem;
            color: #60a5fa;
            outline: none;
            resize: vertical;
            line-height: 1.5;
        }
        textarea.body-editor:focus { border-color: var(--primary); }

        .btn-run {
            background: var(--primary);
            border: 1px solid var(--primary);
            color: #fff;
            font-weight: 800;
            font-size: 0.9rem;
            padding: 0.8rem;
            border-radius: 10px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }
        .btn-run:hover { background: #2563eb; transform: translateY(-1px); }

        .response-box {
            background: #020617;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            min-height: 140px;
            max-height: 240px;
            overflow-y: auto;
            color: #34d399;
        }
    </style>
</head>
<body>

    <header>
        <div class="brand-group">
            <div class="brand-title">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                <span>AIDD Enterprise Suite v4.0</span>
                <span class="badge-ver">API Reference Studio</span>
            </div>
        </div>
        <div style="display: flex; gap: 0.8rem;">
            <a href="/" class="btn">Aplicação Web</a>
            <a href="/docs/guia" class="btn" style="border-color: rgba(59,130,246,0.5); color: #93c5fd;">Guia do Projeto</a>
        </div>
    </header>

    <div class="studio-layout">
        <aside class="sidebar">
            <div class="search-box">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input type="text" placeholder="Filtrar endpoints..." oninput="filtrarSidebar(this.value)">
            </div>
            <div id="sidebar-endpoints-tree"></div>
        </aside>

        <main class="doc-column" id="doc-main-area">
            <div class="doc-tag-badge" id="doc-tag">CRM Vendas</div>
            <h1 class="doc-endpoint-title" id="doc-title">Listar Pipeline Kanban</h1>
            
            <div class="path-badge-box">
                <span class="method-pill pill-get" id="doc-method-pill">GET</span>
                <span id="doc-path">/api/crm/pipeline</span>
            </div>

            <p class="doc-desc" id="doc-desc">Descrição detalhada do endpoint.</p>

            <h3 class="section-header">Autenticação</h3>
            <p style="font-size: 0.86rem; color: var(--text-muted);" id="doc-auth">Bearer token ou Sessão</p>

            <h3 class="section-header">Parâmetros de Requisição</h3>
            <table class="params-table">
                <thead>
                    <tr>
                        <th>CAMPO</th>
                        <th>TIPO</th>
                        <th>DESCRIÇÃO</th>
                    </tr>
                </thead>
                <tbody id="params-table-body">
                    <tr><td colspan="3" style="color: var(--text-muted);">Nenhum parâmetro obrigatório no corpo.</td></tr>
                </tbody>
            </table>

            <h3 class="section-header">Respostas Esperadas</h3>
            <div style="display: flex; gap: 0.5rem; margin-bottom: 1rem;">
                <span style="background: rgba(16,185,129,0.15); color: #34d399; font-size: 0.75rem; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 6px; font-family: 'JetBrains Mono', monospace;">200 OK — Sucesso</span>
            </div>
        </main>

        <aside class="studio-column">
            <div class="studio-header">
                <div class="studio-title">Interactive Playground</div>
                <div class="lang-tabs">
                    <button class="lang-tab active" onclick="trocarLinguagem('curl')">cURL</button>
                    <button class="lang-tab" onclick="trocarLinguagem('js')">JavaScript</button>
                    <button class="lang-tab" onclick="trocarLinguagem('python')">Python</button>
                </div>
            </div>

            <div class="code-box">
                <div class="code-header">
                    <span id="snippet-lang-title">cURL Request</span>
                    <button class="btn" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="copiarSnippet()">Copiar</button>
                </div>
                <pre class="code-content" id="snippet-code-box">curl -X GET http://localhost:3000/api/crm/pipeline</pre>
            </div>

            <div id="body-editor-container" style="display: none;">
                <div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem;">Corpo da Requisição (JSON)</div>
                <textarea class="body-editor" id="live-body-editor"></textarea>
            </div>

            <button class="btn-run" onclick="executarChamadaAoVivo()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Executar Chamada (Send Request)
            </button>

            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                    <div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Resposta do Servidor</div>
                    <span id="response-status-badge" style="font-size: 0.72rem; font-weight: 800; font-family: 'JetBrains Mono', monospace;"></span>
                </div>
                <div class="response-box" id="live-response-box">// Clique em "Executar Chamada" para testar ao vivo</div>
            </div>
        </aside>
    </div>

    <script>
        const endpointsData = [{"id": "crm_pipeline", "tag": "CRM Vendas & Funil", "method": "GET", "path": "/api/crm/pipeline", "title": "Listar Pipeline Kanban", "desc": "Retorna todos os estágios do Kanban de vendas agrupados por status (Novos, Qualificados, Proposta, Negociação, Fechado/Ganho) com valores consolidados.", "auth": "Bearer token ou Sessão Ativa", "params": [], "body": null, "sample_response": {"novo": {"nome": "Novos Leads", "itens": [{"id": 1, "nome": "Dr. Carlos", "score": 95, "valor_estimado": 28500.0}], "total_valor": 28500.0}, "qualificado": {"nome": "Qualificados", "itens": [], "total_valor": 0}, "ganho": {"nome": "Fechado / Ganho", "itens": [{"id": 2, "nome": "Dra. Helena", "score": 98, "valor_estimado": 75000.0}], "total_valor": 75000.0}}}, {"id": "crm_salvar_lead", "tag": "CRM Vendas & Funil", "method": "POST", "path": "/api/crm/leads/salvar", "title": "Cadastrar ou Atualizar Lead", "desc": "Cria um novo lead ou atualiza os dados cadastrais, score de qualificação (0-100) e valor estimado. Caso o status seja 'ganho', dispara o EventBus Cross-Domain para o ERP.", "auth": "Bearer token / API Key", "params": [{"name": "id", "type": "integer", "req": false, "desc": "ID do lead (opcional para criação, obrigatório para edição)"}, {"name": "nome", "type": "string", "req": true, "desc": "Nome completo do decisor ou contato"}, {"name": "email", "type": "string", "req": true, "desc": "E-mail corporativo válido"}, {"name": "telefone", "type": "string", "req": true, "desc": "Telefone / WhatsApp com DDD"}, {"name": "empresa", "type": "string", "req": false, "desc": "Razão social ou nome fantasia"}, {"name": "score", "type": "integer", "req": false, "desc": "Pontuação de maturidade comercial (0 a 100)"}, {"name": "status", "type": "string", "req": false, "desc": "Estágio: 'novo', 'qualificado', 'proposta', 'negociacao', 'ganho'"}, {"name": "valor_estimado", "type": "number", "req": false, "desc": "Valor previsto do contrato em BRL"}], "body": {"nome": "Roberto Alcantara", "email": "roberto@alcantara.com.br", "telefone": "5511999887766", "empresa": "Alcantara Corp", "score": 92, "status": "qualificado", "valor_estimado": 45000.0}, "sample_response": {"sucesso": true, "id": 5}}, {"id": "crm_mover_lead", "tag": "CRM Vendas & Funil", "method": "POST", "path": "/api/crm/pipeline/mover", "title": "Mover Estágio do Lead (Kanban)", "desc": "Altera o estágio do lead no Kanban. Dispara o evento 'lead_ganho' automaticamente se o novo estágio for 'ganho', provisionando a receita no ERP.", "auth": "Bearer token", "params": [{"name": "lead_id", "type": "integer", "req": true, "desc": "Identificador único do Lead"}, {"name": "novo_status", "type": "string", "req": true, "desc": "Novo status: 'novo', 'qualificado', 'proposta', 'negociacao', 'ganho'"}], "body": {"lead_id": 1, "novo_status": "ganho"}, "sample_response": {"sucesso": true, "lead_id": 1, "status": "ganho"}}, {"id": "crm_excluir_lead", "tag": "CRM Vendas & Funil", "method": "POST", "path": "/api/crm/leads/excluir", "title": "Excluir Lead", "desc": "Remove definitivamente um lead do CRM.", "auth": "Bearer token", "params": [{"name": "id", "type": "integer", "req": true, "desc": "ID do lead a ser excluído"}], "body": {"id": 1}, "sample_response": {"sucesso": true}}, {"id": "erp_contas", "tag": "ERP Financeiro & DRE", "method": "GET", "path": "/api/erp/contas", "title": "Listar Lançamentos Financeiros", "desc": "Retorna o razão de contas a pagar e receber ordenados por vencimento.", "auth": "Bearer token", "params": [], "body": null, "sample_response": [{"id": 1, "descricao": "Contrato Fechado: BioMed", "tipo": "receita", "categoria": "Contratos CRM", "valor": 75000.0, "status": "pago", "data_vencimento": "2026-09-15"}, {"id": 2, "descricao": "Infraestrutura Hetzner", "tipo": "despesa", "categoria": "Servidores", "valor": 1250.0, "status": "pago", "data_vencimento": "2026-09-05"}]}, {"id": "erp_fluxo", "tag": "ERP Financeiro & DRE", "method": "GET", "path": "/api/erp/fluxo-caixa", "title": "DRE & Resumo Fluxo de Caixa", "desc": "Calcula em tempo real o saldo realizado (receitas pagas - despesas pagas) e o saldo projetado.", "auth": "Bearer token", "params": [], "body": null, "sample_response": {"receitas_recebidas": 75000.0, "despesas_pagas": 1250.0, "saldo_realizado": 73750.0, "saldo_projetado": 88850.0}}, {"id": "erp_salvar_conta", "tag": "ERP Financeiro & DRE", "method": "POST", "path": "/api/erp/contas/salvar", "title": "Novo Lançamento Financeiro", "desc": "Registra uma nova conta a pagar ou a receber.", "auth": "Bearer token", "params": [{"name": "descricao", "type": "string", "req": true, "desc": "Identificação do lançamento"}, {"name": "tipo", "type": "string", "req": true, "desc": "'receita' ou 'despesa'"}, {"name": "categoria", "type": "string", "req": true, "desc": "Categoria contábil"}, {"name": "valor", "type": "number", "req": true, "desc": "Valor monetário em BRL"}, {"name": "data_vencimento", "type": "string (YYYY-MM-DD)", "req": true, "desc": "Data de vencimento"}], "body": {"descricao": "Licenciamento Cloud Suite", "tipo": "receita", "categoria": "Software", "valor": 18500.0, "data_vencimento": "2026-09-25", "entidade_nome": "Cliente VIP"}, "sample_response": {"sucesso": true}}, {"id": "erp_alternar_status", "tag": "ERP Financeiro & DRE", "method": "POST", "path": "/api/erp/contas/alternar-status", "title": "1-Clique Status (Pago / Pendente)", "desc": "Alterna atomicamente o estado de liquidação da conta e recalcula o fluxo de caixa.", "auth": "Bearer token", "params": [{"name": "id", "type": "integer", "req": true, "desc": "ID do lançamento"}], "body": {"id": 1}, "sample_response": {"sucesso": true, "status": "pago"}}, {"id": "helpdesk_tickets", "tag": "Central de Helpdesk & SLA", "method": "GET", "path": "/api/helpdesk/tickets", "title": "Fila de Chamados & SLA", "desc": "Lista todos os tickets ordenados por criticidade P1 > P2 > P3.", "auth": "Bearer token", "params": [], "body": null, "sample_response": [{"id": 1, "protocolo": "TICK-A92B1C", "assunto": "Configuração Webhook", "prioridade": "P1", "status": "aberto", "sla_limite_horas": 2}]}, {"id": "helpdesk_salvar_ticket", "tag": "Central de Helpdesk & SLA", "method": "POST", "path": "/api/helpdesk/tickets/salvar", "title": "Abrir Novo Chamado", "desc": "Cria um chamado de suporte com protocolo único UUID e define o SLA de acordo com a criticidade.", "auth": "Bearer token", "params": [{"name": "assunto", "type": "string", "req": true, "desc": "Título resumo do problema"}, {"name": "descricao", "type": "string", "req": true, "desc": "Detalhes técnicos da solicitação"}, {"name": "cliente_nome", "type": "string", "req": true, "desc": "Nome do solicitante"}, {"name": "prioridade", "type": "string", "req": true, "desc": "'P1' (2h), 'P2' (4h) ou 'P3' (24h)"}], "body": {"assunto": "Erro de Timeout na API", "descricao": "Requisição POST /api/leads/salvar retornando 504 no webhook.", "cliente_nome": "Rafael Souza", "prioridade": "P1"}, "sample_response": {"sucesso": true, "protocolo": "TICK-E49A1F"}}, {"id": "membros_cursos", "tag": "Área de Membros & Cursos", "method": "GET", "path": "/api/membros/cursos", "title": "Listar Cursos VIP", "desc": "Retorna o catálogo de cursos, contagem de aulas e grade curricular.", "auth": "Livre", "params": [], "body": null, "sample_response": [{"id": 1, "titulo": "Formação Engenharia Agêntica", "categoria": "Arquitetura", "total_aulas": 24}]}, {"id": "catalogo_produtos", "tag": "Catálogo Digital & Pedidos", "method": "GET", "path": "/api/catalogo/produtos", "title": "Listar Produtos do Catálogo", "desc": "Retorna os produtos disponíveis para venda direta.", "auth": "Livre", "params": [], "body": null, "sample_response": [{"id": 1, "nome": "Licença AIDD Enterprise v4.0", "preco": 4990.0, "estoque": 100}]}, {"id": "catalogo_pedido", "tag": "Catálogo Digital & Pedidos", "method": "POST", "path": "/api/catalogo/pedidos/salvar", "title": "Finalizar Pedido de Compra", "desc": "Registra o pedido e dispara o lançamento automático da receita no ERP.", "auth": "Livre", "params": [{"name": "cliente_nome", "type": "string", "req": true, "desc": "Nome do comprador"}, {"name": "cliente_telefone", "type": "string", "req": true, "desc": "WhatsApp do comprador"}, {"name": "total", "type": "number", "req": true, "desc": "Valor total do pedido"}, {"name": "itens", "type": "array", "req": true, "desc": "Lista de itens comprados"}], "body": {"cliente_nome": "Mariana Castro", "cliente_telefone": "5511988884433", "total": 4990.0, "itens": [{"nome": "Licença AIDD Enterprise v4.0", "preco": 4990.0}]}, "sample_response": {"sucesso": true, "pedido_id": 12}}];
        let currentEndpoint = endpointsData[0];
        let currentLang = 'curl';

        function montarSidebar(lista) {
            const tree = document.getElementById('sidebar-endpoints-tree');
            let html = '';
            let currentTag = '';

            lista.forEach((ep, idx) => {
                if (ep.tag !== currentTag) {
                    currentTag = ep.tag;
                    html += '<div class="nav-cat-title">' + currentTag + '</div>';
                }
                const pillClass = ep.method === 'GET' ? 'pill-get' : (ep.method === 'POST' ? 'pill-post' : 'pill-delete');
                const activeClass = ep.id === currentEndpoint.id ? 'active' : '';
                html += '<div class="endpoint-link ' + activeClass + '" onclick="selecionarEndpoint('' + ep.id + '')">' +
                        '<span class="method-pill ' + pillClass + '">' + ep.method + '</span>' +
                        '<span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' + ep.title + '</span>' +
                        '</div>';
            });
            tree.innerHTML = html;
        }

        function selecionarEndpoint(id) {
            currentEndpoint = endpointsData.find(e => e.id === id);
            document.querySelectorAll('.endpoint-link').forEach(el => {
                el.classList.toggle('active', el.innerText.includes(currentEndpoint.title));
            });

            document.getElementById('doc-tag').innerText = currentEndpoint.tag;
            document.getElementById('doc-title').innerText = currentEndpoint.title;
            document.getElementById('doc-path').innerText = currentEndpoint.path;
            document.getElementById('doc-desc').innerText = currentEndpoint.desc;
            document.getElementById('doc-auth').innerText = currentEndpoint.auth;

            const pill = document.getElementById('doc-method-pill');
            pill.innerText = currentEndpoint.method;
            pill.className = 'method-pill ' + (currentEndpoint.method === 'GET' ? 'pill-get' : (currentEndpoint.method === 'POST' ? 'pill-post' : 'pill-delete'));

            const tbody = document.getElementById('params-table-body');
            if (currentEndpoint.params && currentEndpoint.params.length > 0) {
                tbody.innerHTML = currentEndpoint.params.map(p => {
                    const reqBadge = p.req ? '<span class="badge-req">OBRIGATÓRIO</span>' : '';
                    return '<tr>' +
                           '<td><span class="param-name">' + p.name + '</span> ' + reqBadge + '</td>' +
                           '<td><span class="param-type">' + p.type + '</span></td>' +
                           '<td>' + p.desc + '</td>' +
                           '</tr>';
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="3" style="color: var(--text-muted);">Nenhum parâmetro necessário.</td></tr>';
            }

            const bodyEditorContainer = document.getElementById('body-editor-container');
            const bodyEditor = document.getElementById('live-body-editor');
            if (currentEndpoint.method === 'POST' && currentEndpoint.body) {
                bodyEditorContainer.style.display = 'block';
                bodyEditor.value = JSON.stringify(currentEndpoint.body, null, 2);
            } else {
                bodyEditorContainer.style.display = 'none';
            }

            atualizarSnippetCodigo();
            document.getElementById('live-response-box').innerText = JSON.stringify(currentEndpoint.sample_response, null, 2);
            document.getElementById('response-status-badge').innerText = 'EXEMPLO 200 OK';
            document.getElementById('response-status-badge').style.color = '#34d399';
        }

        function trocarLinguagem(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-tab').forEach(b => {
                b.classList.toggle('active', b.innerText.toLowerCase().includes(lang));
            });
            atualizarSnippetCodigo();
        }

        function atualizarSnippetCodigo() {
            const box = document.getElementById('snippet-code-box');
            const ep = currentEndpoint;
            const bodyStr = ep.body ? JSON.stringify(ep.body, null, 2) : '';

            if (currentLang === 'curl') {
                if (ep.method === 'GET') {
                    box.innerText = 'curl -X GET "http://localhost:3000' + ep.path + '" \
  -H "Authorization: Bearer seu_token"';
                } else {
                    box.innerText = 'curl -X POST "http://localhost:3000' + ep.path + '" \
  -H "Content-Type: application/json" \
  -d '' + bodyStr + ''';
                }
            } else if (currentLang === 'js') {
                if (ep.method === 'GET') {
                    box.innerText = 'fetch("http://localhost:3000' + ep.path + '")
  .then(res => res.json())
  .then(data => console.log(data));';
                } else {
                    box.innerText = 'fetch("http://localhost:3000' + ep.path + '", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(' + bodyStr + ')
})
  .then(res => res.json())
  .then(data => console.log(data));';
                }
            } else if (currentLang === 'python') {
                if (ep.method === 'GET') {
                    box.innerText = 'import requests

response = requests.get("http://localhost:3000' + ep.path + '")
print(response.json())';
                } else {
                    box.innerText = 'import requests

payload = ' + bodyStr + '
response = requests.post("http://localhost:3000' + ep.path + '", json=payload)
print(response.json())';
                }
            }
        }

        async function executarChamadaAoVivo() {
            const box = document.getElementById('live-response-box');
            const badge = document.getElementById('response-status-badge');
            box.innerText = 'Enviando requisição...';

            try {
                const t0 = performance.now();
                let res;
                if (currentEndpoint.method === 'GET') {
                    res = await fetch(currentEndpoint.path);
                } else {
                    const bodyText = document.getElementById('live-body-editor').value;
                    res = await fetch(currentEndpoint.path, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: bodyText
                    });
                }
                const elapsed = Math.round(performance.now() - t0);
                const data = await res.json();
                badge.innerText = 'HTTP ' + res.status + ' OK (' + elapsed + 'ms)';
                badge.style.color = res.ok ? '#34d399' : '#f87171';
                box.innerText = JSON.stringify(data, null, 2);
            } catch (err) {
                badge.innerText = 'ERRO NA CONEXÃO';
                badge.style.color = '#f87171';
                box.innerText = err.message;
            }
        }

        function filtrarSidebar(query) {
            const q = query.toLowerCase();
            const filtrados = endpointsData.filter(e => e.title.toLowerCase().includes(q) || e.path.toLowerCase().includes(q) || e.tag.toLowerCase().includes(q));
            montarSidebar(filtrados);
        }

        function copiarSnippet() {
            const code = document.getElementById('snippet-code-box').innerText;
            navigator.clipboard.writeText(code);
            alert('Código copiado para a área de transferência!');
        }

        window.onload = () => {
            montarSidebar(endpointsData);
            selecionarEndpoint('crm_pipeline');
        };
    </script>
</body>
</html>"""
