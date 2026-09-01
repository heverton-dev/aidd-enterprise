import sqlite3

def init_all_schemas(conn: sqlite3.Connection):
    conn.executescript("""
        -- CONFIGURAÇÕES & WEBHOOKS
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );

        -- CRM: LEADS & PIPELINE
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT NOT NULL,
            empresa TEXT,
            score INTEGER DEFAULT 50,
            status TEXT DEFAULT 'novo',
            origem TEXT DEFAULT 'Website',
            valor_estimado REAL DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- ERP: LANÇAMENTOS FINANCEIROS
        CREATE TABLE IF NOT EXISTS lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            data_vencimento DATE NOT NULL,
            status TEXT DEFAULT 'pendente',
            entidade_nome TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- HELPDESK: TICKETS COM SLA
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE NOT NULL,
            assunto TEXT NOT NULL,
            descricao TEXT NOT NULL,
            cliente_nome TEXT NOT NULL,
            cliente_email TEXT NOT NULL,
            prioridade TEXT DEFAULT 'P3',
            status TEXT DEFAULT 'aberto',
            sla_limite_horas INTEGER DEFAULT 24,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- MEMBROS: USUÁRIOS & CURSOS
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            plano_ativo TEXT DEFAULT 'gratuito',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            thumbnail TEXT NOT NULL
        );

        -- CATÁLOGO: PRODUTOS & PEDIDOS
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco REAL NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT NOT NULL
        );
    """)
    conn.commit()
