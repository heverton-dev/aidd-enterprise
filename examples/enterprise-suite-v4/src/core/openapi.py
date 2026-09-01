import json

class RouteRegistry:
    def __init__(self):
        self.routes = {"GET": {}, "POST": {}}
        self.docs = {}

    def get(self, path: str, summary: str = "", tags: list = None):
        def decorator(fn):
            self.routes["GET"][path] = fn
            self.docs[path] = {"method": "get", "summary": summary, "tags": tags or ["Geral"]}
            return fn
        return decorator

    def post(self, path: str, summary: str = "", tags: list = None):
        def decorator(fn):
            self.routes["POST"][path] = fn
            self.docs[path] = {"method": "post", "summary": summary, "tags": tags or ["Geral"]}
            return fn
        return decorator

    def generate_openapi_json(self, title: str, version: str):
        paths_obj = {}
        for path, info in self.docs.items():
            m = info["method"]
            if path not in paths_obj:
                paths_obj[path] = {}
            paths_obj[path][m] = {
                "summary": info["summary"],
                "tags": info["tags"],
                "responses": {"200": {"description": "Sucesso", "content": {"application/json": {}}}}
            }
        return {
            "openapi": "3.0.0",
            "info": {"title": title, "version": version},
            "paths": paths_obj
        }

    def get_swagger_html(self, title: str):
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
</head>
<body style="margin: 0; background: #0b0f19;">
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({{ url: '/openapi.json', dom_id: '#swagger-ui', deepLinking: true }});
    </script>
</body>
</html>"""
