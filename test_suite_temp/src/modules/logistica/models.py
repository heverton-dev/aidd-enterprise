# -*- coding: utf-8 -*-
"""
Schema e inicialização de banco de dados para o módulo 'logistica'.
"""

import sqlite3


def init_schema(conn: sqlite3.Connection):
    """Cria a tabela e índices do módulo logistica se não existirem."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mod_logistica (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            dados_json TEXT,
            status TEXT DEFAULT 'ativo',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_logistica_ativo ON mod_logistica(ativo);
        CREATE INDEX IF NOT EXISTS idx_logistica_status ON mod_logistica(status);
    """)
    conn.commit()
