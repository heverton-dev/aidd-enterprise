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
│ Modo A (Linguagem Natural no Chat ou CLI):                                  │
│ $ python scripts/aidd.py "Crie uma aplicação de CRM e ERP de faturamento"   │
│                                                                             │
│ Modo B (Comando Declarativo):                                               │
│ $ python scripts/aidd.py plan "Crie um CRM e ERP"                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1.5: ESPECIFICAÇÃO & ALINHAMENTO ARQUITETURAL (SPEC / PLAN GATE)       │
│ 1. Geração de SPEC-ARQUITETURA.md e PLANO-EXECUCAO-ESTRUTURADO.json         │
│ 2. Revisão Interativa: Usuário aprova ou ajusta fatias e entidades          │
│ 3. Gatilho de Aprovação: $ python scripts/aidd.py apply --dir <pasta>       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 2: PROCESSAMENTO MECÂNICO (PROCESSING - 9 CAMADAS DE BLINDAGEM)        │
│ 1. Sanitização de Palavras Reservadas (Anti-Crash)                          │
│ 2. Scaffolding do Shared Kernel com SQLite WAL + busy_timeout = 5000        │
│ 3. Controle de Migrações de Schema (_schema_migrations)                     │
│ 4. Geração Atômica de Fatias Verticais com Seed Fixtures Determinísticas    │
│ 5. EventBus Pub/Sub com Validação de Contrato de Payload e Tracing UUID     │
│ 6. Servidor Dinâmico src/server.py com Port Fallback (3000..3025) e CORS    │
│ 7. Geração de Testes Unitários pytest com Asserções Compatíveis com Seeds   │
│ 8. Healthcheck Efêmero de Inicialização                                     │
│ 9. Execução dos 7 Quality Gates com Limpeza Automática de Cache (.pytest)   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 3: SAÍDA ENTREGUE E OPERACIONAL (OUTPUT)                               │
│ Servidor ativo com 4 Portais e Relatório Auditado (Nota A+ 100% Blindado)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detalhamento das 9 Melhorias da Fase 2 (Processamento)

| # | Melhoria Implementada | Risco Mitigado | Arquivos Modificados |
| :---: | :--- | :--- | :--- |
| **1** | **Port Fallback Dinâmico (3000..3025)** | Bloqueio de porta ocupada (`OSError: Address in use`). | `compose_suite.py` / `src/server.py` |
| **2** | **Carga Inicial de Dados (Seed Fixtures)** | Telas e KPIs vazios na primeira inicialização. | `add_module.py` (`models.py`) |
| **3** | **Healthcheck Efêmero de Inicialização** | Servidor subir com rotas quebradas sem aviso. | `templates/gates/G_TESTES.py` |
| **4** | **Sanitização de Palavras Reservadas** | Nomes como `import`, `class`, `test` causarem erros sintáticos. | `add_module.py` (`slugify`) |
| **5** | **SQLite `PRAGMA busy_timeout = 5000`** | Bloqueios de concorrência (`database is locked`). | `templates/v2/database.py` |
| **6** | **CORS Preflight Middleware (`OPTIONS`)** | Bloqueios de chamadas por frontends externos ou Postman. | `compose_suite.py` (`AppHandler`) |
| **7** | **Migration Tracker (`_schema_migrations`)** | Conflitos e drift de schema em atualizações. | `templates/v2/database.py` |
| **8** | **EventBus Envelope & UUID Tracing** | Eventos mal formatados ou sem rastro de auditoria. | `templates/v2/events.py` |
| **9** | **Limpeza Automática de Caches** | Acúmulo de arquivos residuais `.pytest_cache` e `__pycache__`. | `templates/gates/G_TESTES.py` |
