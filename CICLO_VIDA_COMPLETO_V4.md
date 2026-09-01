# Ciclo de Vida Completo do AIDD Master Pack v4.1

## 1. Visão Geral do Ciclo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 0: ACESSO E INSTALAÇÃO NO AMBIENTE DO USUÁRIO                          │
│ 1. Obtenção do Pacote: git clone ou link de pasta local                     │
│ 2. Bootstrap Automático: instalação de dependências e diagnóstico           │
│ 3. Verificação de Saúde do Runtime: detecção de ORCA ADE vs Subagentes      │
│    $ python scripts/aidd.py setup                                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: ENTRADA DO USUÁRIO (USER INPUT - ZERO ATRITO & LINGUAGEM NATURAL)   │
│ Modo A (Linguagem Natural):                                                 │
│ $ python scripts/aidd.py "Crie uma aplicação de CRM e ERP de faturamento"   │
│                                                                             │
│ Modo B (Comando Declarativo):                                               │
│ $ python scripts/aidd.py compose ./meu-app "Meu App" crm erp faturamento    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 2: PROCESSAMENTO MECÂNICO (PROCESSING)                                 │
│ 1. Extração Automática de Entidades e Módulos de Negócio                    │
│ 2. Injeção de Governança (AGENTS.md, CLAUDE.md, GEMINI.md, 02_golden_rules) │
│ 3. Scaffolding do Shared Kernel (database.py WAL, events.py, openapi.py)    │
│ 4. Geração Atômica das Fatias Verticais (models, services, routes, UI)      │
│ 5. Geração dos Testes Unitários pytest por módulo (tests/unit/test_*.py)    │
│ 6. Compilação do Servidor Dinâmico src/server.py com RouteRegistry          │
│ 7. Execução e Bloqueio pelos 7 Quality Gates (exit 0 obrigatório)           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 3: SAÍDA ENTREGUE E OPERACIONAL (OUTPUT)                               │
│ Servidor ativo na porta 3000 com 4 Portais e Relatório Auditado             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detalhamento Passo a Passo

| Fase | Ação | Comandos e Exemplos | O que Acontece nos Bastidores |
| :--- | :--- | :--- | :--- |
| **Fase 0: Acesso & Setup** | **Download & Bootstrap** | `git clone <repo>`<br>`cd aidd-master-pack-v4`<br>`python scripts/aidd.py setup` | Auto-instalação de dependências (`pytest`, `requests`), validação de Python (>= 3.9) e detecção de ambiente (ORCA vs Subagentes). |
| **Fase 1: Entrada (Input)** | **Linguagem Natural (Zero Atrito)** | `python scripts/aidd.py "Crie um CRM e ERP com faturamento"`<br>*ou*<br>`python scripts/aidd.py compose ./app "App" crm erp` | O parser analisa o texto em linguagem natural, extrai as fatias verticais (`crm`, `erp`, `faturamento`) e aciona o motor determinístico. |
| **Fase 2: Processamento** | **Scaffolding Determinístico** | Execução de `compose_suite.py` e `add_module.py` | Injeta governança, gera o Shared Kernel, cria fatias verticais, monta os testes unitários e executa os 7 Quality Gates locais. |
| **Fase 3: Saída (Output)** | **Execução da Aplicação** | `cd <destino>`<br>`python src/server.py`<br>`python scripts/aidd.py audit --report` | Disponibiliza Super-App UI (`/`), Swagger Studio (`/docs`), MCP Server (`/mcp`), Webhook Studio (`/webhooks`) e Relatório Técnico auditado. |
