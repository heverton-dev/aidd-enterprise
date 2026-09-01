# -*- coding: utf-8 -*-
"""
Serviço de regras de negócio Full CRUD e publicação de eventos para o módulo 'helpdesk'.
"""

import json
from typing import Optional, List, Dict, Any


class HelpdeskService:
    def __init__(self, db, events=None):
        self.db = db
        self.events = events

    def listar(self, apenas_ativos: bool = True, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM mod_helpdesk WHERE 1=1"
            params = []
            if apenas_ativos:
                query += " AND ativo = 1"
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY id DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def obter_por_id(self, item_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM mod_helpdesk WHERE id = ?", (item_id,)).fetchone()
            return dict(row) if row else None

    def criar(self, titulo: str, dados: Optional[Dict[str, Any]] = None, descricao: str = "", status: str = "ativo") -> Dict[str, Any]:
        titulo_limpo = (titulo or "").strip()
        if not titulo_limpo:
            raise ValueError("O título do item é obrigatório")

        dados_dict = dados if dados is not None else {}
        with self.db.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO mod_helpdesk (titulo, descricao, dados_json, status, ativo)
                VALUES (?, ?, ?, ?, 1)
                """,
                (titulo_limpo, descricao.strip(), json.dumps(dados_dict, ensure_ascii=False), status)
            )
            conn.commit()
            novo_id = cur.lastrowid

        payload = {
            "id": novo_id,
            "titulo": titulo_limpo,
            "descricao": descricao,
            "status": status,
            "dados": dados_dict
        }

        if self.events:
            self.events.emit("helpdesk_criado", payload)

        return {"sucesso": True, "id": novo_id, "item": payload}

    def atualizar(self, item_id: int, titulo: Optional[str] = None, dados: Optional[Dict[str, Any]] = None, descricao: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM mod_helpdesk WHERE id = ?", (item_id,)).fetchone()
            if not row:
                return {"sucesso": False, "erro": "Item não encontrado"}

            novo_titulo = titulo.strip() if titulo is not None else row["titulo"]
            nova_desc = descricao.strip() if descricao is not None else row["descricao"]
            novo_status = status if status is not None else row["status"]
            novos_dados = json.dumps(dados, ensure_ascii=False) if dados is not None else row["dados_json"]

            conn.execute(
                """
                UPDATE mod_helpdesk
                SET titulo = ?, descricao = ?, dados_json = ?, status = ?, atualizado_em = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (novo_titulo, nova_desc, novos_dados, novo_status, item_id)
            )
            conn.commit()

        payload = {
            "id": item_id,
            "titulo": novo_titulo,
            "descricao": nova_desc,
            "status": novo_status
        }

        if self.events:
            self.events.emit("helpdesk_atualizado", payload)

        return {"sucesso": True, "id": item_id, "item": payload}

    def deletar(self, item_id: int) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM mod_helpdesk WHERE id = ?", (item_id,)).fetchone()
            if not row:
                return {"sucesso": False, "erro": "Item não encontrado"}
            conn.execute("DELETE FROM mod_helpdesk WHERE id = ?", (item_id,))
            conn.commit()

        if self.events:
            self.events.emit("helpdesk_deletado", {"id": item_id})

        return {"sucesso": True, "id": item_id}
