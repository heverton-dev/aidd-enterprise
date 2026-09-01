# -*- coding: utf-8 -*-
"""
Suíte de testes unitários para o módulo 'logistica'.
Valida isolamento de schema, persistência SQLite WAL, regras de negócio e disparo de eventos.
"""

import pytest
import os
import sys

# Garante que src esteja no PYTHONPATH
SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from core.database import Database
from core.events import EventBus
from modules.logistica.models import init_schema
from modules.logistica.services import LogisticaService


@pytest.fixture
def test_env(tmp_path):
    """Fixture que isola o banco de dados e o EventBus para cada teste."""
    db_file = str(tmp_path / "test_logistica.db")
    db = Database(f"sqlite:///{db_file}")
    with db.get_connection() as conn:
        init_schema(conn)

    events = EventBus()
    eventos_capturados = []
    events.on("logistica_criado", lambda d: eventos_capturados.append(("criado", d)))
    events.on("logistica_atualizado", lambda d: eventos_capturados.append(("atualizado", d)))
    events.on("logistica_deletado", lambda d: eventos_capturados.append(("deletado", d)))

    service = LogisticaService(db, events)
    return {"service": service, "events": eventos_capturados, "db": db}


def test_fluxo_completo_crud_logistica(test_env):
    service = test_env["service"]
    eventos = test_env["events"]

    # 1. CREATE
    res_cria = service.criar(
        titulo="Item Teste Unitário Logistica",
        descricao="Validação automatizada de integridade",
        status="ativo",
        dados={"valor": 150.0, "prioridade": "alta"}
    )
    assert res_cria["sucesso"] is True
    novo_id = res_cria["id"]
    assert novo_id > 0
    assert len(eventos) == 1
    assert eventos[0][0] == "criado"
    assert eventos[0][1]["id"] == novo_id

    # 2. READ (Obter por ID)
    item = service.obter_por_id(novo_id)
    assert item is not None
    assert item["titulo"] == "Item Teste Unitário Logistica"
    assert item["status"] == "ativo"

    # 3. LIST
    lista = service.listar()
    assert len(lista) == 1
    assert lista[0]["id"] == novo_id

    # 4. UPDATE
    res_up = service.atualizar(
        item_id=novo_id,
        titulo="Item Teste Logistica Atualizado",
        status="concluido"
    )
    assert res_up["sucesso"] is True
    assert len(eventos) == 2
    assert eventos[1][0] == "atualizado"

    item_mod = service.obter_por_id(novo_id)
    assert item_mod["titulo"] == "Item Teste Logistica Atualizado"
    assert item_mod["status"] == "concluido"

    # 5. DELETE
    res_del = service.deletar(novo_id)
    assert res_del["sucesso"] is True
    assert len(eventos) == 3
    assert eventos[2][0] == "deletado"

    assert len(service.listar()) == 0
    assert service.obter_por_id(novo_id) is None


def test_validacao_titulo_obrigatorio_logistica(test_env):
    service = test_env["service"]
    with pytest.raises(ValueError):
        service.criar(titulo="   ")
