# -*- coding: utf-8 -*-
"""
Schema e inicialização de banco de dados para o módulo 'crm'.
"""

import sqlite3


def init_schema(conn: sqlite3.Connection):
    """Cria a tabela e índices do módulo crm se não existirem."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mod_crm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            dados_json TEXT,
            status TEXT DEFAULT 'ativo',
            ativo INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_crm_ativo ON mod_crm(ativo);
        CREATE INDEX IF NOT EXISTS idx_crm_status ON mod_crm(status);
    """)
    conn.commit()
