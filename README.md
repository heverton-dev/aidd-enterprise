# 📦 AIDD Master Pack v4.1 (Enterprise Modular Suite)

> **O Framework Definitivo para Monólitos Modulares, Clean Architecture, Fatias Verticais e Governança Anti-Atalhos por Gates Rígidos.**

---

## 🏛️ Visão Geral

A versão **4.1 (Enterprise Anti-Fail)** eleva o ecossistema AIDD ao nível máximo de robustez e determinismo. Ela resolve definitivamente as falhas de geração em IAs ao impor regras mecânicas inegociáveis:

- **Isolamento de Domínios (Vertical Slices):** Cada domínio de negócio reside em seu próprio pacote (`src/modules/<dominio>/`) com `models.py`, `services.py`, `routes.py`, testes `pytest` e componente UI.
- **EventBus Assíncrono:** Integração desacoplada orientada a eventos em tempo real.
- **Diligência Full CRUD:** Criação, Leitura, Atualização e Exclusão com testes unitários em 100% dos módulos.
- **Swagger Studio OpenAPI 3.1 (`/docs`):** Registro dinâmico com testador de rotas ao vivo.
- **Model Context Protocol (`/mcp`):** Ferramentas JSON-RPC 2.0 prontas para Claude, Cursor, Antigravity e OpenHands.
- **Webhooks com HMAC SHA-256:** Notificação com assinatura digital para microsserviços.
- **Impeccable Design System:** Super-App UI com 4px scrollbars, header de linha única e zero emojis.
- **Suíte de Gates Rígidos:** `G_ESTRUTURA`, `G_QUALIDADE`, `G_TESTES`, `G_CONTRACTS`, `G_SEGREDOS`, `G_HARNESS_COMPAT`.

---

## 📂 Estrutura do Pacote

```
aidd-master-pack-v4/
├── scripts/
│   ├── aidd.py               # CLI unificada (init, add-module, compose, test, audit, deploy)
│   ├── compose_suite.py      # Motor de Composição Enterprise Modular
│   ├── add_module.py         # Gerador atômico de Fatias Verticais
│   ├── provision_project.py  # Provisionador de projetos modulares
│   └── gates/                # Suíte de Quality Gates Rígidos
│       ├── G_ESTRUTURA.py
│       ├── G_QUALIDADE.py
│       ├── G_TESTES.py
│       ├── G_CONTRACTS.py
│       ├── G_SEGREDOS.py
│       └── G_HARNESS_COMPAT.py
├── templates/
│   ├── gates/                # Templates dos Quality Gates
│   ├── rules/                # Regras determinísticas (01_layers, 02_golden_rules, 03_impeccable, 04_cross_project)
│   └── v2/                   # Shared Kernel, MCP Server, OpenAPI & UI Components
├── examples/                 # Suítes de referência enterprise
├── README.md
└── SKILL.md
```

---

## 🚀 Como Iniciar

```bash
# 1. Compor uma nova Suite Enterprise (ex: CRM, ERP, Helpdesk, Logística)
python scripts/aidd.py compose ./minha-suite "Minha Suite" crm erp helpdesk logistica

# 2. Entrar na pasta da suite
cd minha-suite

# 3. Rodar a bateria de testes unitários
python scripts/aidd.py test

# 4. Executar os Gates de Qualidade e gerar Relatório Factual
python scripts/aidd.py audit --report

# 5. Iniciar a aplicação
python src/server.py
```
