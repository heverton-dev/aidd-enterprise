import json

class RouteRegistry:
    def __init__(self):
        self.routes = {"GET": {}, "POST": {}, "PUT": {}, "DELETE": {}}
        self.endpoints = []

    def get(self, path: str, summary: str = "", tags: list = None, description: str = "", query_params: list = None, responses: dict = None):
        def decorator(fn):
            self.routes["GET"][path] = fn
            self.endpoints.append({
                "id": f"get_{path.replace('/', '_').strip('_')}",
                "method": "GET",
                "path": path,
                "summary": summary or path,
                "tag": tags[0] if tags else "Geral",
                "description": description or summary or f"Recupera dados de {path}",
                "auth": "Bearer Token / Sessão Ativa",
                "query_params": query_params or [],
                "request_body": None,
                "responses": responses or {
                    "200": {
                        "description": "Operação realizada com sucesso",
                        "content": {"application/json": {"example": {"status": "success", "data": []}}}
                    },
                    "400": {"description": "Requisição inválida ou parâmetros ausentes", "content": {"application/json": {"example": {"error": "Bad Request", "message": "Parâmetro obrigatório ausente"}}}},
                    "401": {"description": "Não autorizado ou token expirado", "content": {"application/json": {"example": {"error": "Unauthorized", "message": "Token inválido"}}}},
                    "500": {"description": "Erro interno no servidor", "content": {"application/json": {"example": {"error": "Internal Server Error"}}}}
                }
            })
            return fn
        return decorator

    def post(self, path: str, summary: str = "", tags: list = None, description: str = "", body_schema: list = None, body_example: dict = None, responses: dict = None):
        def decorator(fn):
            self.routes["POST"][path] = fn
            self.endpoints.append({
                "id": f"post_{path.replace('/', '_').strip('_')}",
                "method": "POST",
                "path": path,
                "summary": summary or path,
                "tag": tags[0] if tags else "Geral",
                "description": description or summary or f"Executa mutação em {path}",
                "auth": "Bearer Token / API Key",
                "query_params": [],
                "body_schema": body_schema or [],
                "body_example": body_example or {},
                "responses": responses or {
                    "200": {
                        "description": "Registro criado ou processado com sucesso",
                        "content": {"application/json": {"example": {"sucesso": True, "id": 1}}}
                    },
                    "400": {"description": "Payload JSON inválido ou falha de validação", "content": {"application/json": {"example": {"error": "Validation Error", "fields": ["campo_obrigatorio"]}}}},
                    "401": {"description": "Não autorizado", "content": {"application/json": {"example": {"error": "Unauthorized"}}}},
                    "500": {"description": "Erro interno no servidor", "content": {"application/json": {"example": {"error": "Internal Server Error"}}}}
                }
            })
            return fn
        return decorator

    def generate_openapi_json(self, title: str, version: str):
        paths_obj = {}
        for ep in self.endpoints:
            p = ep["path"]
            m = ep["method"].lower()
            if p not in paths_obj:
                paths_obj[p] = {}
            op = {
                "summary": ep["summary"],
                "description": ep["description"],
                "tags": [ep["tag"]],
                "responses": {
                    code: {"description": r["description"], "content": r.get("content", {})}
                    for code, r in ep["responses"].items()
                }
            }
            if ep.get("body_example"):
                op["requestBody"] = {
                    "required": True,
                    "content": {"application/json": {"schema": {"type": "object", "example": ep["body_example"]}}}
                }
            paths_obj[p][m] = op

        return {
            "openapi": "3.1.0",
            "info": {"title": title, "version": version, "description": "API Reference Dinâmica de Alta Fidelidade"},
            "paths": paths_obj
        }

    def get_swagger_html(self, title: str):
        endpoints_json = json.dumps(self.endpoints, ensure_ascii=False)

        html_template = """<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>__TITLE__</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #030712;
            --bg-sidebar: #050b18;
            --bg-middle: #040814;
            --bg-studio: #020617;
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.16);
            --primary: #3b82f6;
            --primary-light: #60a5fa;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --method-get: #10b981;
            --method-post: #3b82f6;
            --method-delete: #ef4444;
            --code-bg: #010409;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background: var(--bg-body); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        /* TOPBAR */
        header {
            height: 56px;
            background: rgba(3, 7, 18, 0.95);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 1.8rem;
            flex-shrink: 0;
            z-index: 50;
        }
        .brand-title { font-weight: 800; font-size: 0.95rem; color: #fff; display: flex; align-items: center; gap: 0.6rem; }
        .badge-ver { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: var(--primary-light); font-size: 0.72rem; font-weight: 800; padding: 0.2rem 0.5rem; border-radius: 9999px; }

        .btn { padding: 0.45rem 0.85rem; border-radius: 8px; font-size: 0.82rem; font-weight: 600; border: 1px solid var(--border); background: rgba(255, 255, 255, 0.04); color: #fff; text-decoration: none; cursor: pointer; display: inline-flex; align-items: center; gap: 0.4rem; transition: all 0.15s; }
        .btn:hover { background: rgba(255, 255, 255, 0.08); border-color: var(--border-hover); }
        .btn-primary { background: var(--primary); border-color: var(--primary); }

        /* STUDIO 3-COLUMNS LAYOUT */
        .studio-layout {
            display: grid;
            grid-template-columns: 310px 1fr 500px;
            flex: 1;
            height: calc(100vh - 56px);
            overflow: hidden;
        }
        @media (max-width: 1300px) { .studio-layout { grid-template-columns: 280px 1fr 440px; } }

        /* 1. SIDEBAR (ESQUERDA) */
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
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            padding: 0.55rem 0.8rem;
            border-radius: 8px;
            color: var(--text-muted);
            font-size: 0.82rem;
        }
        .search-box input { background: none; border: none; outline: none; color: #fff; font-size: 0.84rem; width: 100%; }
        .nav-cat-title { font-size: 0.72rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; padding: 0.8rem 0.6rem 0.3rem 0.6rem; }
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
        }
        .endpoint-link:hover, .endpoint-link.active { background: rgba(59, 130, 246, 0.12); color: #fff; }
        .method-pill { font-size: 0.65rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; padding: 0.15rem 0.4rem; border-radius: 4px; min-width: 44px; text-align: center; }
        .pill-get { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .pill-post { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
        .pill-delete { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

        /* 2. DOCUMENTAÇÃO TÉCNICA (MEIO) */
        main.doc-column {
            background: var(--bg-middle);
            overflow-y: auto;
            padding: 3rem 3.5rem;
            border-right: 1px solid var(--border);
        }
        .doc-tag-badge { font-size: 0.75rem; font-weight: 700; text-transform: uppercase; color: var(--primary-light); letter-spacing: 0.05em; margin-bottom: 0.6rem; }
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

        h3.section-header { font-size: 1.1rem; font-weight: 800; color: #fff; margin: 2rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }

        .params-table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; }
        .params-table th, .params-table td { padding: 0.85rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.86rem; }
        .params-table th { font-size: 0.72rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; }
        .param-name { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: #fff; }
        .param-type { font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #94a3b8; }
        .badge-req { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); font-size: 0.68rem; font-weight: 800; padding: 0.1rem 0.35rem; border-radius: 4px; margin-left: 0.4rem; }

        .response-tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .resp-status-btn { padding: 0.3rem 0.7rem; border-radius: 6px; font-size: 0.75rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; border: 1px solid var(--border); background: rgba(255,255,255,0.02); color: var(--text-muted); cursor: pointer; }
        .resp-status-btn.active-200 { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
        .resp-status-btn.active-400 { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }
        .resp-status-btn.active-500 { background: rgba(239, 68, 68, 0.15); color: #f87171; border-color: rgba(239, 68, 68, 0.3); }

        /* 3. PLAYGROUND STUDIO (DIREITA) */
        aside.studio-column {
            background: var(--bg-studio);
            overflow-y: auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }
        .studio-header { display: flex; justify-content: space-between; align-items: center; }
        .studio-title { font-size: 0.88rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }

        .lang-tabs { display: flex; background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border); border-radius: 8px; padding: 0.2rem; gap: 0.2rem; }
        .lang-tab { padding: 0.35rem 0.75rem; border-radius: 6px; font-size: 0.75rem; font-weight: 700; color: var(--text-muted); cursor: pointer; border: none; background: none; transition: all 0.15s; }
        .lang-tab.active { background: rgba(59, 130, 246, 0.2); color: var(--primary-light); }

        .code-box { background: var(--code-bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .code-header { background: rgba(255, 255, 255, 0.02); border-bottom: 1px solid var(--border); padding: 0.6rem 1rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); }
        pre.code-content { padding: 1.2rem; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; line-height: 1.6; color: #e2e8f0; overflow-x: auto; }

        textarea.body-editor {
            width: 100%;
            height: 180px;
            background: var(--code-bg);
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
            background: var(--code-bg);
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
        <div class="brand-title">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            <span>__TITLE__</span>
            <span class="badge-ver">OpenAPI 3.1.0</span>
        </div>
        <div style="display: flex; gap: 0.8rem;">
            <a href="/" class="btn">Aplicação Web</a>
            <a href="/mcp" class="btn" style="border-color: rgba(16,185,129,0.4); color: #34d399;">Portal MCP</a>
            <a href="/docs/guia" class="btn" style="border-color: rgba(59,130,246,0.5); color: #93c5fd;">Guia Oficial</a>
            <a href="/openapi.json" target="_blank" class="btn">Exportar JSON</a>
        </div>
    </header>

    <div class="studio-layout">
        <!-- 1. SIDEBAR -->
        <aside class="sidebar">
            <div class="search-box">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input type="text" placeholder="Filtrar endpoints..." oninput="filtrarSidebar(this.value)">
            </div>
            <div id="sidebar-endpoints-tree"></div>
        </aside>

        <!-- 2. DOCUMENTAÇÃO DO ENDPOINT -->
        <main class="doc-column" id="doc-main-area">
            <div class="doc-tag-badge" id="doc-tag">Tag</div>
            <h1 class="doc-endpoint-title" id="doc-title">Carregando...</h1>
            
            <div class="path-badge-box">
                <span class="method-pill pill-get" id="doc-method-pill">GET</span>
                <span id="doc-path">/api/...</span>
            </div>

            <p class="doc-desc" id="doc-desc">Descrição do endpoint.</p>

            <h3 class="section-header">Autenticação</h3>
            <p style="font-size: 0.86rem; color: var(--text-muted);" id="doc-auth">Bearer token ou Sessão</p>

            <h3 class="section-header" id="params-header-title">Parâmetros de Requisição</h3>
            <table class="params-table">
                <thead>
                    <tr><th>CAMPO</th><th>TIPO</th><th>DESCRIÇÃO</th></tr>
                </thead>
                <tbody id="params-table-body"></tbody>
            </table>

            <h3 class="section-header">Respostas da API</h3>
            <div class="response-tabs" id="response-code-tabs"></div>
            <pre class="code-box" style="padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #34d399;" id="response-schema-viewer"></pre>
        </main>

        <!-- 3. PLAYGROUND STUDIO -->
        <aside class="studio-column">
            <div class="studio-header">
                <div class="studio-title">Interactive Playground</div>
                <div class="lang-tabs">
                    <button class="lang-tab active" onclick="trocarLinguagem('curl')">cURL</button>
                    <button class="lang-tab" onclick="trocarLinguagem('js')">JavaScript</button>
                    <button class="lang-tab" onclick="trocarLinguagem('python')">Python</button>
                </div>
            </div>

            <!-- CODE SNIPPET -->
            <div class="code-box">
                <div class="code-header">
                    <span id="snippet-lang-title">cURL Request</span>
                    <button class="btn" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="copiarSnippet()">Copiar</button>
                </div>
                <pre class="code-content" id="snippet-code-box">curl ...</pre>
            </div>

            <!-- REQUEST BODY EDITOR (SE POST) -->
            <div id="body-editor-container" style="display: none;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
                    <span style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Body Payload (JSON)</span>
                    <button class="btn" style="padding: 0.15rem 0.4rem; font-size: 0.7rem;" onclick="resetBodyDefault()">Restaurar Padrão</button>
                </div>
                <textarea class="body-editor" id="live-body-editor"></textarea>
            </div>

            <button class="btn-run" onclick="executarChamadaAoVivo()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                Executar Chamada (Send Request)
            </button>

            <!-- RESPOSTA EM TEMPO REAL -->
            <div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                    <div style="font-size: 0.78rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase;">Resposta do Servidor</div>
                    <span id="response-status-badge" style="font-size: 0.72rem; font-weight: 800; font-family: 'JetBrains Mono', monospace;"></span>
                </div>
                <div class="response-box" id="live-response-box">// Clique em "Executar Chamada" para disparar a requisição</div>
            </div>
        </aside>
    </div>

    <script>
        const endpointsData = __ENDPOINTS_JSON__;
        let currentEndpoint = endpointsData[0] || null;
        let currentLang = 'curl';
        let currentRespCode = '200';

        function montarSidebar(lista) {
            const tree = document.getElementById('sidebar-endpoints-tree');
            let html = '';
            let currentTag = '';

            lista.forEach((ep) => {
                if (ep.tag !== currentTag) {
                    currentTag = ep.tag;
                    html += '<div class="nav-cat-title">' + currentTag + '</div>';
                }
                const pillClass = ep.method === 'GET' ? 'pill-get' : 'pill-post';
                const activeClass = (currentEndpoint && ep.id === currentEndpoint.id) ? 'active' : '';
                html += '<div class="endpoint-link ' + activeClass + '" onclick="selecionarEndpoint(\'' + ep.id + '\')">' +
                        '<span class="method-pill ' + pillClass + '">' + ep.method + '</span>' +
                        '<span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' + ep.summary + '</span>' +
                        '</div>';
            });
            tree.innerHTML = html;
        }

        function selecionarEndpoint(id) {
            currentEndpoint = endpointsData.find(e => e.id === id) || endpointsData[0];
            if (!currentEndpoint) return;

            document.querySelectorAll('.endpoint-link').forEach(el => {
                el.classList.toggle('active', el.innerText.includes(currentEndpoint.summary));
            });

            document.getElementById('doc-tag').innerText = currentEndpoint.tag;
            document.getElementById('doc-title').innerText = currentEndpoint.summary;
            document.getElementById('doc-path').innerText = currentEndpoint.path;
            document.getElementById('doc-desc').innerText = currentEndpoint.description;
            document.getElementById('doc-auth').innerText = currentEndpoint.auth;

            const pill = document.getElementById('doc-method-pill');
            pill.innerText = currentEndpoint.method;
            pill.className = 'method-pill ' + (currentEndpoint.method === 'GET' ? 'pill-get' : 'pill-post');

            // Tabela de Parâmetros
            const tbody = document.getElementById('params-table-body');
            const params = (currentEndpoint.method === 'GET' ? currentEndpoint.query_params : currentEndpoint.body_schema) || [];
            
            if (params.length > 0) {
                tbody.innerHTML = params.map(p => {
                    const reqBadge = p.req ? '<span class="badge-req">OBRIGATÓRIO</span>' : '';
                    return '<tr><td><span class="param-name">' + p.name + '</span> ' + reqBadge + '</td><td><span class="param-type">' + p.type + '</span></td><td>' + p.desc + '</td></tr>';
                }).join('');
            } else {
                tbody.innerHTML = '<tr><td colspan="3" style="color: var(--text-muted);">Nenhum parâmetro necessário no corpo.</td></tr>';
            }

            // Tabs de Respostas
            const respTabs = document.getElementById('response-code-tabs');
            const respCodes = Object.keys(currentEndpoint.responses || {});
            respTabs.innerHTML = respCodes.map(code => {
                const activeCls = code === '200' ? 'active-200' : (code.startsWith('4') ? 'active-400' : 'active-500');
                return '<button class="resp-status-btn ' + (code === '200' ? activeCls : '') + '" onclick="selecionarResposta(\'' + code + '\')">' + code + ' ' + (currentEndpoint.responses[code].description || '') + '</button>';
            }).join('');

            selecionarResposta('200');

            // Body Editor
            const bodyEditorContainer = document.getElementById('body-editor-container');
            const bodyEditor = document.getElementById('live-body-editor');
            if (currentEndpoint.method === 'POST' && currentEndpoint.body_example) {
                bodyEditorContainer.style.display = 'block';
                bodyEditor.value = JSON.stringify(currentEndpoint.body_example, null, 2);
            } else {
                bodyEditorContainer.style.display = 'none';
            }

            atualizarSnippetCodigo();
            document.getElementById('live-response-box').innerText = '// Clique em "Executar Chamada" para disparar a requisição ao vivo';
            document.getElementById('response-status-badge').innerText = '';
        }

        function selecionarResposta(code) {
            currentRespCode = code;
            document.querySelectorAll('.resp-status-btn').forEach(btn => {
                const isThis = btn.innerText.startsWith(code);
                btn.className = 'resp-status-btn ' + (isThis ? (code === '200' ? 'active-200' : (code.startsWith('4') ? 'active-400' : 'active-500')) : '');
            });

            const respObj = currentEndpoint.responses[code];
            const viewer = document.getElementById('response-schema-viewer');
            if (respObj && respObj.content && respObj.content['application/json']) {
                viewer.innerText = JSON.stringify(respObj.content['application/json'].example || respObj, null, 2);
            } else {
                viewer.innerText = JSON.stringify(respObj, null, 2);
            }
        }

        function trocarLinguagem(lang) {
            currentLang = lang;
            document.querySelectorAll('.lang-tab').forEach(b => {
                b.classList.toggle('active', b.innerText.toLowerCase().includes(lang));
            });
            atualizarSnippetCodigo();
        }

        function resetBodyDefault() {
            if (currentEndpoint && currentEndpoint.body_example) {
                document.getElementById('live-body-editor').value = JSON.stringify(currentEndpoint.body_example, null, 2);
            }
        }

        function atualizarSnippetCodigo() {
            if (!currentEndpoint) return;
            const box = document.getElementById('snippet-code-box');
            const ep = currentEndpoint;
            const bodyStr = ep.body_example ? JSON.stringify(ep.body_example, null, 2) : '';

            if (currentLang === 'curl') {
                if (ep.method === 'GET') {
                    box.innerText = 'curl -X GET "http://localhost:3000' + ep.path + '" \
  -H "Authorization: Bearer seu_token_aqui"';
                } else {
                    box.innerText = 'curl -X POST "http://localhost:3000' + ep.path + '" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer seu_token_aqui" \
  -d '' + bodyStr + ''';
                }
            } else if (currentLang === 'js') {
                if (ep.method === 'GET') {
                    box.innerText = 'const response = await fetch("http://localhost:3000' + ep.path + '", {
  headers: { "Authorization": "Bearer seu_token_aqui" }
});
const data = await response.json();
console.log(data);';
                } else {
                    box.innerText = 'const response = await fetch("http://localhost:3000' + ep.path + '", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": "Bearer seu_token_aqui"
  },
  body: JSON.stringify(' + bodyStr + ')
});
const data = await response.json();
console.log(data);';
                }
            } else if (currentLang === 'python') {
                if (ep.method === 'GET') {
                    box.innerText = 'import requests

headers = {"Authorization": "Bearer seu_token_aqui"}
response = requests.get("http://localhost:3000' + ep.path + '", headers=headers)
print(response.json())';
                } else {
                    box.innerText = 'import requests

payload = ' + bodyStr + '
headers = {"Authorization": "Bearer seu_token_aqui"}
response = requests.post("http://localhost:3000' + ep.path + '", json=payload, headers=headers)
print(response.json())';
                }
            }
        }

        async function executarChamadaAoVivo() {
            if (!currentEndpoint) return;
            const box = document.getElementById('live-response-box');
            const badge = document.getElementById('response-status-badge');
            box.innerText = 'Enviando requisição para http://localhost:3000' + currentEndpoint.path + '...';

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
            const filtrados = endpointsData.filter(e => e.summary.toLowerCase().includes(q) || e.path.toLowerCase().includes(q) || e.tag.toLowerCase().includes(q));
            montarSidebar(filtrados);
        }

        function copiarSnippet() {
            const code = document.getElementById('snippet-code-box').innerText;
            navigator.clipboard.writeText(code);
            alert('Snippet copiado com sucesso!');
        }

        window.onload = () => {
            montarSidebar(endpointsData);
            if (endpointsData.length > 0) selecionarEndpoint(endpointsData[0].id);
        };
    </script>
</body>
</html>"""
        return html_template.replace("__TITLE__", title).replace("__ENDPOINTS_JSON__", endpoints_json)
