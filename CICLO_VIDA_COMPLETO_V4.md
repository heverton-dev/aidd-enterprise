# Ciclo de Vida Completo do AIDD Master Pack v4.1

## 1. Visão Geral do Ciclo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 0: ACESSO E INSTALAÇÃO NO AMBIENTE DO USUÁRIO                          │
│ 1. Obtenção do Pacote: git clone ou link de pasta local                     │
│ 2. Bootstrap Automático: instalação de dependências e diagnóstico           │
│ 3. Verificação de Saúde do Runtime: detecção de ORCA ADE vs Subagentes      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: ENTRADA DO USUÁRIO (USER INPUT)                                     │
│ Comando CLI declarativo definindo o destino e os domínios de negócio:       │
│ $ python scripts/aidd.py compose ./meu-app "Meu App" crm erp faturamento    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 2: PROCESSAMENTO MECÂNICO (PROCESSING)                                 │
│ 1. Injeção de Governança (AGENTS.md, CLAUDE.md, GEMINI.md, 02_golden_rules) │
│ 2. Scaffolding do Shared Kernel (database.py WAL, events.py, openapi.py)    │
│ 3. Geração Atômica das Fatias Verticais (models, services, routes, UI)      │
│ 4. Geração dos Testes Unitários pytest por módulo (tests/unit/test_*.py)    │
│ 5. Compilação do Servidor Dinâmico src/server.py com RouteRegistry          │
│ 6. Execução e Bloqueio pelos 7 Quality Gates (exit 0 obrigatório)           │
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

| Fase | Ação | Comandos e Arquivos Envolvidos | O que Acontece nos Bastidores |
| :--- | :--- | :--- | :--- |
| **Fase 0: Acesso & Setup** | **Download & Bootstrap** | `git clone <repo>`<br>`cd aidd-master-pack-v4`<br>`python scripts/aidd.py setup` | Auto-instalação de dependências (`pytest`, `requests`), validação de Python (>= 3.9) e detecção de ambiente (ORCA vs Subagentes). |
| **Fase 1: Entrada (Input)** | **Declaração do Projeto** | `python scripts/aidd.py compose <destino> <nome> [modulos...]` | Recebe apenas o diretório de saída, nome da aplicação e lista de módulos de domínio. |
| **Fase 2: Processamento** | **Scaffolding Determinístico** | Execução de `compose_suite.py` e `add_module.py` | Injeta governança, gera o Shared Kernel, cria fatias verticais, monta os testes unitários e executa os 7 Quality Gates locais. |
| **Fase 3: Saída (Output)** | **Execução da Aplicação** | `cd <destino>`<br>`python src/server.py`<br>`python scripts/aidd.py audit --report` | Disponibiliza Super-App UI (`/`), Swagger Studio (`/docs`), MCP Server (`/mcp`), Webhook Studio (`/webhooks`) e Relatório Técnico auditado. |
