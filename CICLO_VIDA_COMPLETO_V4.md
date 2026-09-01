# Ciclo de Vida Completo do AIDD Master Pack v4.1 (Nível Ultra)

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
│ FASE 2: PROCESSAMENTO MECÂNICO (PROCESSING - ELITE AGENTIC ENGINE)          │
│ 1. Linter AST Anti-Acoplamento & Zero Connection Leak                       │
│ 2. Scaffolding do Shared Kernel com SQLite WAL + busy_timeout = 5000        │
│ 3. Controle de Migrações de Schema (_schema_migrations)                     │
│ 4. Geração Atômica de Fatias Verticais com Seed Fixtures Determinísticas    │
│ 5. EventBus Pub/Sub com Validação de Contrato de Payload e Tracing UUID     │
│ 6. Servidor Dinâmico src/server.py com Port Fallback (3000..3025) e CORS    │
│ 7. Geração de Testes com Asserção Forte de Mutação de Estado                │
│ 8. Linter de Acessibilidade & Impeccable UI (WCAG 2.1)                      │
│ 9. Snapshot SHA-256 de Contratos OpenAPI e MCP                              │
│ 10. Execução dos 7 Quality Gates com Limpeza Automática de Cache            │
│ 11. Benchmark Concorrente ($ python scripts/aidd.py bench -n 100)           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 3: SAÍDA ENTREGUE E OPERACIONAL (OUTPUT)                               │
│ Servidor ativo com 4 Portais e Relatório Auditado (Nota A+ 100% Blindado)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detalhamento das Diretrizes de Elite (Nível Ultra)

| # | Diretriz de Elite | Risco Eliminado | Arquivo Validador |
| :---: | :--- | :--- | :--- |
| **1** | **Linter AST Anti-Acoplamento** | Módulos importando diretamente código de outros módulos. | `G_ESTRUTURA.py` |
| **2** | **Zero Connection Leak** | Conexões SQLite abertas sem context manager. | `G_ESTRUTURA.py` |
| **3** | **Snapshot SHA-256 de Contratos** | Quebra acidental de contratos de API e ferramentas MCP. | `G_CONTRACTS.py` |
| **4** | **Linter Impeccable UI & WCAG 2.1** | Componentes com diálogos nativos (`alert`) ou botões sem type. | `G_QUALIDADE.py` |
| **5** | **Testes de Mutação Forte** | Falsos-positivos em testes unitários de CRUD. | `add_module.py` |
| **6** | **Benchmark de Carga (`aidd bench`)** | Degradação de performance sob concorrência local. | `aidd.py` |
| **7** | **Auto-Remediação (`aidd heal`)** | Arquivos corrompidos ou manifestos dessincronizados. | `aidd.py` |
| **8** | **Port Fallback & CORS Nativo** | Conflito de portas e bloqueio de clientes frontend externos. | `compose_suite.py` |
| **9** | **Injeção Cirúrgica de Contexto** | Desperdício de tokens em prompts de subagentes. | `SKILL.md` |
