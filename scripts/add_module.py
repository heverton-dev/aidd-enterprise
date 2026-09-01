import os, sys, re, json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[\s_-]+', '_', text)

def criar_modulo(nome_modulo: str, descricao: str = "", base_target: str = "."):
    slug = slugify(nome_modulo)
    module_dir = os.path.join(base_target, "src", "modules", slug)
    
    if os.path.exists(module_dir):
        print(f"[WARN] O módulo '{slug}' já existe em: {module_dir}")
        return
        
    print(f"[AIDD v4.1] Gerando fatia vertical desacoplada: '{slug}'...")
    os.makedirs(module_dir, exist_ok=True)
    open(os.path.join(module_dir, "__init__.py"), "w", encoding="utf-8").close()
    
    # 1. models.py
    models_code = f'''import sqlite3

def init_schema(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mod_{slug} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT DEFAULT '',
            status TEXT DEFAULT 'ativo',
            dados_json TEXT DEFAULT '{{}}',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_{slug}_ativo ON mod_{slug}(ativo);
        CREATE INDEX IF NOT EXISTS idx_{slug}_status ON mod_{slug}(status);
    """)
    conn.commit()
'''
    with open(os.path.join(module_dir, "models.py"), "w", encoding="utf-8") as f:
        f.write(models_code)
        
    # 2. services.py (Full CRUD Diligente)
    services_code = f'''import json
from core.database import Database
from core.events import EventBus

class {slug.capitalize()}Service:
    def __init__(self, db: Database, events: EventBus = None):
        self.db = db
        self.events = events

    def listar(self, apenas_ativos: bool = True):
        with self.db.get_connection() as conn:
            query = "SELECT * FROM mod_{slug}"
            if apenas_ativos:
                query += " WHERE ativo = 1"
            query += " ORDER BY id DESC"
            rows = conn.execute(query).fetchall()
            return [dict(r) for r in rows]

    def obter(self, item_id: int):
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM mod_{slug} WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None

    def criar(self, titulo: str, descricao: str = "", dados: dict = None):
        dados_dict = dados if dados is not None else {{}}
        with self.db.get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO mod_{slug} (titulo, descricao, dados_json) VALUES (?, ?, ?)",
                (titulo.strip(), descricao.strip(), json.dumps(dados_dict))
            )
            conn.commit()
            novo_id = cur.lastrowid
            payload = {{"id": novo_id, "titulo": titulo, "modulo": "{slug}"}}
            if self.events:
                self.events.emit("{slug}_criado", payload)
            return {{"sucesso": True, "id": novo_id, "titulo": titulo}}

    def atualizar(self, item_id: int, titulo: str = None, descricao: str = None, status: str = None, dados: dict = None):
        campos = []
        valores = []
        if titulo is not None:
            campos.append("titulo = ?")
            valores.append(titulo.strip())
        if descricao is not None:
            campos.append("descricao = ?")
            valores.append(descricao.strip())
        if status is not None:
            campos.append("status = ?")
            valores.append(status.strip())
        if dados is not None:
            campos.append("dados_json = ?")
            valores.append(json.dumps(dados))
        if not campos:
            return {{"sucesso": False, "erro": "Nenhum campo para atualizar"}}
        
        campos.append("atualizado_em = CURRENT_TIMESTAMP")
        valores.append(item_id)
        
        with self.db.get_connection() as conn:
            conn.execute(f"UPDATE mod_{slug} SET {{', '.join(campos)}} WHERE id = ?", tuple(valores))
            conn.commit()
            if self.events:
                self.events.emit("{slug}_atualizado", {{"id": item_id, "modulo": "{slug}"}})
            return {{"sucesso": True, "id": item_id}}

    def deletar(self, item_id: int):
        with self.db.get_connection() as conn:
            conn.execute("UPDATE mod_{slug} SET ativo = 0 WHERE id = ?", (item_id,))
            conn.commit()
            if self.events:
                self.events.emit("{slug}_deletado", {{"id": item_id, "modulo": "{slug}"}})
            return {{"sucesso": True, "id": item_id}}
'''
    with open(os.path.join(module_dir, "services.py"), "w", encoding="utf-8") as f:
        f.write(services_code)

    # 3. routes.py (OpenAPI RouteRegistry)
    routes_code = f'''from core.openapi import RouteRegistry

registry = RouteRegistry()

def registrar_rotas(service):
    @registry.get("/api/{slug}", summary="Lista itens do módulo {slug}", tag="{slug.capitalize()}")
    def listar(params):
        return service.listar()

    @registry.get("/api/{slug}/obter", summary="Obtém detalhes de um item", tag="{slug.capitalize()}")
    def obter(params):
        item_id = int(params.get("id", [0])[0] if isinstance(params.get("id"), list) else params.get("id", 0))
        res = service.obter(item_id)
        return res if res else {{"erro": "Item não encontrado"}}

    @registry.post("/api/{slug}", summary="Cria novo item no módulo {slug}", tag="{slug.capitalize()}")
    def criar(data):
        return service.criar(data.get("titulo", ""), data.get("descricao", ""), data.get("dados", {{}}))

    @registry.put("/api/{slug}", summary="Atualiza item do módulo {slug}", tag="{slug.capitalize()}")
    def atualizar(data):
        return service.atualizar(int(data.get("id", 0)), data.get("titulo"), data.get("descricao"), data.get("status"), data.get("dados"))

    @registry.delete("/api/{slug}", summary="Remove item do módulo {slug}", tag="{slug.capitalize()}")
    def deletar(data):
        return service.deletar(int(data.get("id", 0)))
'''
    with open(os.path.join(module_dir, "routes.py"), "w", encoding="utf-8") as f:
        f.write(routes_code)

    # 4. Componente Visual Impeccable
    comp_dir = os.path.join(base_target, "src", "static", "components")
    os.makedirs(comp_dir, exist_ok=True)
    comp_html = f'''<div class="card module-card" id="module-{slug}">
    <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h3 style="font-size: 1.2rem; font-weight: 700; color: #f8fafc;">{slug.capitalize()}</h3>
        <span class="badge badge-green">Fatia Vertical Ativa</span>
    </div>
    <div class="card-body" id="{slug}-items-container">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Carregando dados do módulo {slug}...</p>
    </div>
    <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
        <input type="text" id="input-{slug}-novo" placeholder="Novo {slug}..." style="flex: 1; padding: 0.6rem 1rem; border-radius: 8px; border: 1px solid var(--border); background: #060911; color: #fff;">
        <button class="btn btn-green" onclick="adicionarItem('{slug}')">Adicionar</button>
    </div>
</div>
'''
    with open(os.path.join(comp_dir, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(comp_html)

    # 5. Testes Unitários com pytest
    test_dir = os.path.join(base_target, "tests", "unit")
    os.makedirs(test_dir, exist_ok=True)
    test_code = f'''import pytest, sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
from core.database import Database
from core.events import EventBus
from modules.{slug}.services import {slug.capitalize()}Service
from modules.{slug}.models import init_schema

def test_modulo_{slug}_crud_completo(tmp_path):
    db_file = str(tmp_path / "test_{slug}.db")
    db = Database(db_file)
    with db.get_connection() as conn:
        init_schema(conn)
        
    events = EventBus()
    eventos_recebidos = []
    events.on("{slug}_criado", lambda d: eventos_recebidos.append(d))
    events.on("{slug}_atualizado", lambda d: eventos_recebidos.append(d))
    events.on("{slug}_deletado", lambda d: eventos_recebidos.append(d))

    service = {slug.capitalize()}Service(db, events)
    
    # 1. CREATE
    res_criar = service.criar("Item Teste {slug.capitalize()}", "Descricao detalhada", {{"valor": 150}})
    assert res_criar["sucesso"] is True
    novo_id = res_criar["id"]
    assert len(eventos_recebidos) == 1
    
    # 2. READ (Listar & Obter)
    itens = service.listar()
    assert len(itens) == 1
    assert itens[0]["titulo"] == "Item Teste {slug.capitalize()}"
    
    item = service.obter(novo_id)
    assert item is not None
    assert item["id"] == novo_id
    assert item["descricao"] == "Descricao detalhada"
    
    # 3. UPDATE
    res_up = service.atualizar(novo_id, titulo="Item Atualizado", status="concluido")
    assert res_up["sucesso"] is True
    item_up = service.obter(novo_id)
    assert item_up["titulo"] == "Item Atualizado"
    assert item_up["status"] == "concluido"
    assert len(eventos_recebidos) == 2
    
    # 4. DELETE
    del_res = service.deletar(novo_id)
    assert del_res["sucesso"] is True
    assert len(service.listar()) == 0
    assert len(eventos_recebidos) == 3
'''
    with open(os.path.join(test_dir, f"test_{slug}.py"), "w", encoding="utf-8") as f:
        f.write(test_code)

    print(f"[OK] Módulo '{slug}' gerado com 100% de conformidade (Models, Services, Routes, UI e Pytest)!")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python scripts/add_module.py <nome_do_modulo> [descricao] [base_target]")
        sys.exit(1)
    target_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    desc = sys.argv[2] if len(sys.argv) > 2 else ""
    criar_modulo(sys.argv[1], desc, target_dir)
