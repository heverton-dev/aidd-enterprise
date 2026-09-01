# -*- coding: utf-8 -*-
"""
Registro de rotas OpenAPI 3.1 para o módulo 'logistica'.
"""

from typing import Any, Optional, Dict, List
from core.openapi import RouteRegistry

registry = RouteRegistry()


def registrar_rotas(service: Any = None):
    tag_name = "Logistica"

    @registry.get(
        "/api/logistica",
        summary="Listar todos os itens do módulo logistica",
        tags=[tag_name],
        description="Retorna a lista de registros cadastrados no módulo logistica.",
        query_params=[
            {"name": "status", "type": "string", "req": False, "desc": "Filtrar por status"},
            {"name": "apenas_ativos", "type": "boolean", "req": False, "desc": "Filtrar apenas itens ativos (default True)"}
        ],
        responses={
            "200": {"description": "Lista recuperada com sucesso", "content": {"application/json": {"example": [{"id": 1, "titulo": "Exemplo", "status": "ativo"}]}}}
        }
    )
    def listar(params):
        status = params.get("status", [None])[0] if isinstance(params.get("status"), list) else params.get("status")
        return service.listar(status=status) if service else []

    @registry.get(
        "/api/logistica/obter",
        summary="Obter item de logistica por ID",
        tags=[tag_name],
        description="Retorna os detalhes completos de um registro do módulo logistica.",
        query_params=[
            {"name": "id", "type": "integer", "req": True, "desc": "ID do registro"}
        ],
        responses={
            "200": {"description": "Registro encontrado", "content": {"application/json": {"example": {"id": 1, "titulo": "Exemplo"}}}},
            "404": {"description": "Registro não encontrado"}
        }
    )
    def obter(params):
        item_id = int(params.get("id", [0])[0] if isinstance(params.get("id"), list) else params.get("id", 0))
        res = service.obter_por_id(item_id) if service else None
        return res if res else {"sucesso": False, "erro": "Item não encontrado"}

    @registry.post(
        "/api/logistica/criar",
        summary="Criar novo item no módulo logistica",
        tags=[tag_name],
        description="Cadastra um novo registro com emissão de evento no EventBus.",
        body_schema=[
            {"name": "titulo", "type": "string", "req": True, "desc": "Título identificador"},
            {"name": "descricao", "type": "string", "req": False, "desc": "Descrição complementar"},
            {"name": "status", "type": "string", "req": False, "desc": "Status inicial (default 'ativo')"},
            {"name": "dados", "type": "object", "req": False, "desc": "Objeto JSON customizado"}
        ],
        body_example={"titulo": "Novo Registro Logistica", "descricao": "Descrição detalhada", "status": "ativo", "dados": {"prioridade": "alta"}},
        responses={
            "200": {"description": "Item criado com sucesso", "content": {"application/json": {"example": {"sucesso": True, "id": 1}}}}
        }
    )
    def criar(data):
        if not service:
            return {"sucesso": False, "erro": "Serviço indisponível"}
        try:
            return service.criar(
                titulo=data.get("titulo", ""),
                dados=data.get("dados", {}),
                descricao=data.get("descricao", ""),
                status=data.get("status", "ativo")
            )
        except Exception as e:
            return {"sucesso": False, "erro": str(e)}

    @registry.post(
        "/api/logistica/atualizar",
        summary="Atualizar item do módulo logistica",
        tags=[tag_name],
        description="Atualiza campos de um registro existente e emite evento de alteração.",
        body_schema=[
            {"name": "id", "type": "integer", "req": True, "desc": "ID do registro a atualizar"},
            {"name": "titulo", "type": "string", "req": False, "desc": "Novo título"},
            {"name": "descricao", "type": "string", "req": False, "desc": "Nova descrição"},
            {"name": "status", "type": "string", "req": False, "desc": "Novo status"},
            {"name": "dados", "type": "object", "req": False, "desc": "Novos dados"}
        ],
        body_example={"id": 1, "titulo": "Logistica Atualizado", "status": "concluido"},
        responses={
            "200": {"description": "Item atualizado com sucesso", "content": {"application/json": {"example": {"sucesso": True, "id": 1}}}}
        }
    )
    def atualizar(data):
        if not service:
            return {"sucesso": False, "erro": "Serviço indisponível"}
        item_id = int(data.get("id", 0))
        return service.atualizar(
            item_id=item_id,
            titulo=data.get("titulo"),
            dados=data.get("dados"),
            descricao=data.get("descricao"),
            status=data.get("status")
        )

    @registry.post(
        "/api/logistica/deletar",
        summary="Remover item do módulo logistica",
        tags=[tag_name],
        description="Exclui permanentemente um registro e publica evento de exclusão.",
        body_schema=[
            {"name": "id", "type": "integer", "req": True, "desc": "ID do registro a remover"}
        ],
        body_example={"id": 1},
        responses={
            "200": {"description": "Item removido com sucesso", "content": {"application/json": {"example": {"sucesso": True, "id": 1}}}}
        }
    )
    def deletar(data):
        if not service:
            return {"sucesso": False, "erro": "Serviço indisponível"}
        item_id = int(data.get("id", 0))
        return service.deletar(item_id)
