def init_all_schemas(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT UNIQUE NOT NULL,
            modelo TEXT NOT NULL,
            motorista TEXT NOT NULL,
            capacidade_kg REAL NOT NULL,
            status TEXT DEFAULT 'disponivel', -- disponivel, em_rota, manutencao
            km_atual REAL DEFAULT 0,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS entregas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_rastreio TEXT UNIQUE NOT NULL,
            destinatario TEXT NOT NULL,
            cidade_destino TEXT NOT NULL,
            valor_frete REAL NOT NULL,
            peso_kg REAL NOT NULL,
            status TEXT DEFAULT 'pendente', -- pendente, coletado, em_transito, entregue
            veiculo_id INTEGER,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS estoque_wms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            descricao TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            posicao_palete TEXT NOT NULL,
            valor_unitario REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS fretes_financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL, -- receita, despesa
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            status TEXT DEFAULT 'pendente', -- pendente, pago
            data_vencimento TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS incidentes_sla (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocolo TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            veiculo_placa TEXT,
            prioridade TEXT DEFAULT 'P3', -- P1 (2h), P2 (4h), P3 (24h)
            status TEXT DEFAULT 'aberto', -- aberto, resolvido
            sla_horas INTEGER DEFAULT 24,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );
    """)

    # Seed inicial
    if conn.execute("SELECT COUNT(*) FROM veiculos").fetchone()[0] == 0:
        conn.execute("INSERT INTO veiculos (placa, modelo, motorista, capacidade_kg, status, km_atual) VALUES ('BRA2E19', 'Volvo FH 540', 'Marcos Vinicius', 32000, 'disponivel', 142500)")
        conn.execute("INSERT INTO veiculos (placa, modelo, motorista, capacidade_kg, status, km_atual) VALUES ('KLP9A88', 'Scania R450', 'Carlos Eduardo', 28000, 'em_rota', 89300)")

    if conn.execute("SELECT COUNT(*) FROM estoque_wms").fetchone()[0] == 0:
        conn.execute("INSERT INTO estoque_wms (sku, descricao, quantidade, posicao_palete, valor_unitario) VALUES ('SKU-LOG-101', 'Bobinas de Aço Inox', 450, 'RUA-A-04', 1850.0)")
        conn.execute("INSERT INTO estoque_wms (sku, descricao, quantidade, posicao_palete, valor_unitario) VALUES ('SKU-LOG-202', 'Painéis Solares 550W', 1200, 'RUA-B-12', 640.0)")

    if conn.execute("SELECT COUNT(*) FROM entregas").fetchone()[0] == 0:
        conn.execute("INSERT INTO entregas (codigo_rastreio, destinatario, cidade_destino, valor_frete, peso_kg, status, veiculo_id) VALUES ('BR-LOG-9821', 'Indústrias BioMed S/A', 'Campinas/SP', 8500.0, 14000, 'em_transito', 2)")
        conn.execute("INSERT INTO entregas (codigo_rastreio, destinatario, cidade_destino, valor_frete, peso_kg, status, veiculo_id) VALUES ('BR-LOG-4310', 'SolarTech Distribuidora', 'Curitiba/PR', 14200.0, 22000, 'pendente', 1)")

    if conn.execute("SELECT COUNT(*) FROM fretes_financeiro").fetchone()[0] == 0:
        conn.execute("INSERT INTO fretes_financeiro (tipo, descricao, valor, status, data_vencimento) VALUES ('receita', 'Frete BR-LOG-9821 (BioMed)', 8500.0, 'pago', '2026-09-10')")
        conn.execute("INSERT INTO fretes_financeiro (tipo, descricao, valor, status, data_vencimento) VALUES ('despesa', 'Abastecimento Frota Posto Ipiranga', 3420.0, 'pago', '2026-09-02')")

    conn.commit()
