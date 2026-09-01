import http.server, socketserver, json, urllib.parse, os, sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services import PlataformaService

PORT = 3000
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "banco_membros.db")
service = PlataformaService(db_path)
service.seed_dados_iniciais()

# Garantir usuario demo no banco
service.cadastrar_usuario("Heverton Peres", "admin@aidd.com", "123456")
service.matricular(1, 1)
service.matricular(1, 2)
service.alternar_progresso_aula(1, 1)

class PlatformHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/api/cursos":
            uid_param = params.get("usuario_id", [""])[0]
            uid = int(uid_param) if uid_param.isdigit() else None
            cursos = service.listar_cursos(uid)
            self._send_json(cursos)
        elif path == "/api/aulas":
            cid = int(params.get("curso_id", [0])[0])
            uid_param = params.get("usuario_id", [""])[0]
            uid = int(uid_param) if uid_param.isdigit() else None
            aulas = service.obter_aulas(cid, uid)
            self._send_json(aulas)
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        elif path == "/" or path == "":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        data = json.loads(body) if body else {}

        if parsed.path == "/api/cadastro":
            res = service.cadastrar_usuario(data.get("nome", ""), data.get("email", ""), data.get("senha", ""))
            self._send_json(res)
        elif parsed.path == "/api/login":
            res = service.autenticar(data.get("email", ""), data.get("senha", ""))
            self._send_json(res)
        elif parsed.path == "/api/matricular":
            res = service.matricular(int(data.get("usuario_id", 0)), int(data.get("curso_id", 0)))
            self._send_json(res)
        elif parsed.path == "/api/progresso":
            res = service.alternar_progresso_aula(int(data.get("usuario_id", 0)), int(data.get("aula_id", 0)))
            self._send_json(res)
        else:
            self.send_error(404, "Endpoint nao encontrado")

    def _send_json(self, data, status=200):
        res = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(res)))
        self.end_headers()
        self.wfile.write(res)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

def start_server():
    server = ThreadedHTTPServer(("", PORT), PlatformHandler)
    print(f"[OK] Servidor Multithreaded rodando em: http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    start_server()
