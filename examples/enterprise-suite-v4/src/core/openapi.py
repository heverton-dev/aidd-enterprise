import json

class RouteRegistry:
    def __init__(self):
        self.routes = {"GET": {}, "POST": {}}
        self.docs = {}

    def get(self, path: str, summary: str = "", tags: list = None, description: str = "", parameters: list = None, responses: dict = None):
        def decorator(fn):
            self.routes["GET"][path] = fn
            self.docs[path] = {
                "method": "get",
                "summary": summary,
                "description": description or summary,
                "tags": tags or ["Geral"],
                "parameters": parameters or [],
                "responses": responses or {"200": {"description": "Sucesso", "content": {"application/json": {}}}}
            }
            return fn
        return decorator

    def post(self, path: str, summary: str = "", tags: list = None, description: str = "", request_body: dict = None, responses: dict = None):
        def decorator(fn):
            self.routes["POST"][path] = fn
            self.docs[path] = {
                "method": "post",
                "summary": summary,
                "description": description or summary,
                "tags": tags or ["Geral"],
                "request_body": request_body,
                "responses": responses or {"200": {"description": "Operação realizada com sucesso", "content": {"application/json": {}}}}
            }
            return fn
        return decorator

    def generate_openapi_json(self, title: str, version: str):
        paths_obj = {}
        for path, info in self.docs.items():
            m = info["method"]
            if path not in paths_obj:
                paths_obj[path] = {}
            
            op = {
                "summary": info["summary"],
                "description": info["description"],
                "tags": info["tags"],
                "responses": info["responses"]
            }
            if info.get("parameters"):
                op["parameters"] = info["parameters"]
            if info.get("request_body"):
                op["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": info["request_body"]
                        }
                    }
                }
            paths_obj[path][m] = op

        return {
            "openapi": "3.1.0",
            "info": {
                "title": title,
                "version": version,
                "description": "API Reference corporativa da Suíte AIDD Enterprise v4.0 com suporte a Cross-Domain EventBus e Webhooks."
            },
            "servers": [
                {"url": "http://localhost:3000", "description": "Servidor Local de Produção"}
            ],
            "paths": paths_obj
        }

    def get_swagger_html(self, title: str):
        # Renderizador Moderno Scalar API Reference (Padrão Evolution Foundation / Mintlify)
        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #06090f;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        /* Custom Theme Override para padrão Dark Moderno */
        .scalar-api-reference {{
            --scalar-font: 'Plus Jakarta Sans', sans-serif !important;
            --scalar-font-code: 'JetBrains Mono', monospace !important;
            --scalar-background-1: #06090f !important;
            --scalar-background-2: #0b101b !important;
            --scalar-background-3: #111827 !important;
            --scalar-color-1: #f9fafb !important;
            --scalar-color-2: #94a3b8 !important;
            --scalar-color-3: #64748b !important;
            --scalar-color-accent: #3b82f6 !important;
            --scalar-color-green: #10b981 !important;
            --scalar-color-orange: #f59e0b !important;
            --scalar-color-red: #ef4444 !important;
            --scalar-border-color: rgba(255, 255, 255, 0.08) !important;
        }}
    </style>
</head>
<body>
    <script
        id="api-reference"
        data-url="/openapi.json"
        data-configuration='{{"theme":"solarized","darkMode":true,"layout":"modern","showSidebar":true,"searchHotKey":"k"}}'
        src="https://cdn.jsdelivr.net/npm/@scalar/api-reference@latest">
    </script>
</body>
</html>"""
