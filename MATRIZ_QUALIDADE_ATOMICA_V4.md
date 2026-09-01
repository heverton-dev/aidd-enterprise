# Matriz Atômica de Qualidade do AIDD Master Pack v4.1

## 1. Critérios de Qualidade por Camada de Entrega

### A. Camada de Persistência & Banco de Dados (`models.py` / `database.py`)
- **Concorrência Segura:** SQLite inicializado em modo WAL (`PRAGMA journal_mode=WAL;`), `synchronous=NORMAL` e `busy_timeout=5000`.
- **Integridade Relacional:** `PRAGMA foreign_keys=ON;` ativado por padrão em todas as conexões.
- **Zero SQL Injection:** 100% das queries utilizam parametrização com placeholders (`?` ou `%s`). Interpolação de strings é proibida.
- **Seed Fixtures Determinísticas:** A função `init_schema()` popula automaticamente 2 registros de exemplo se a tabela estiver vazia.
- **Versionamento de Schema:** Tabela interna `_schema_migrations` registrando versões de schema aplicadas por módulo.
- **Gate Validador:** `G_ESTRUTURA`, `G_TESTES` e `G_SEGURANCA`.

---

### B. Camada de Front-End & Design System (`components/*.html` / `Impeccable UI`)
- **Padrão Impeccable UI:** Layout responsivo em Tailwind CSS com paleta Slate/Indigo, bordas sutis (`border-slate-800`), sombras de elevação e cantos arredondados (`rounded-xl`).
- **Zero Emojis & Ícones Vetoriais:** Proibição de emojis como ícones funcionais. Uso exclusivo de SVGs Lucide vetoriais escaláveis.
- **Zero Diálogos Nativos de SO:** Proibição de `alert()`, `confirm()` ou `prompt()`. Uso obrigatório de Modais HTML customizados e Toasts assíncronos de feedback (Sucesso/Erro/Info).
- **Scrollbars & Header:** Scrollbars ultrafinas de 4px customizadas via CSS e Header de navegação unificado de linha única.
- **Isolamento de Componente:** Cada módulo possui seu próprio componente visual isolado em `src/static/components/<modulo>.html` com escopo local.
- **Gate Validador:** `G_ESTRUTURA` e `G_QUALIDADE`.

---

### C. Camada de Back-End & Regras de Negócio (`services.py`)
- **Full CRUD Diligente:** Toda entidade implementa 5 métodos reais: `listar()`, `obter_por_id()`, `criar()`, `atualizar()`, `deletar()`.
- **Anti-Stubs:** Proibição de marcadores vazios (`pass`, `...`, `NotImplementedError`, `TODO`). Todo código é compilável e funcional.
- **Desacoplamento HTTP:** O serviço não recebe objetos HTTP (`request`, `headers`); recebe apenas dicionários ou tipos primitivos tipados.
- **Emissão de Eventos:** Toda mutação de estado (`criar`, `atualizar`, `deletar`) emite um evento no `EventBus` pub/sub com rastreabilidade UUID.
- **Gate Validador:** `G_QUALIDADE`, `G_TESTES` e `G_CONTRACTS`.

---

### D. Camada de Rotas & Contratos de API (`routes.py` / `openapi.py`)
- **OpenAPI 3.1 Dinâmico:** Todas as rotas são declaradas via `@registry.get` e `@registry.post` com `summary`, `tags`, `body_schema` e `responses`.
- **Swagger Studio Vivo:** Interface Swagger UI em `/docs` que permite execução interativa das rotas diretamente pelo navegador.
- **Universal MCP JSON-RPC 2.0:** O servidor `/mcp` expõe ferramentas dinâmicas para cada módulo (`mod_<modulo>_listar`, `mod_<modulo>_criar`, etc.) com inputSchema validado.
- **CORS Preflight Middleware:** Resposta automática a requisições `OPTIONS` com headers `Access-Control-Allow-Origin: *`.
- **Gate Validador:** `G_CONTRACTS` e `G_HARNESS_COMPAT`.

---

### E. Camada de Integração Cross-Domain (`events.py` / `webhooks.py`)
- **Envelope Padronizado:** Cada evento transita com: `event_id` (UUID), `event_name`, `timestamp` (ISO UTC), `origin_module` e `data`.
- **Isolamento de Erros:** Falha em um listener de evento não interrompe a execução do serviço principal.
- **Webhooks com HMAC SHA-256:** Disparos externos assíncronos assinados criptograficamente no cabeçalho `X-Hub-Signature-256`.
- **Gate Validador:** `G_TESTES` e `G_SEGURANCA`.

---

### F. Camada de Testabilidade & Homologação (`tests/unit/` / `scripts/gates/`)
- **Cobertura 100% de Fluxo CRUD:** Cada fatia vertical possui um arquivo `tests/unit/test_<modulo>.py` cobrindo Create, Read, List, Update, Delete e Validação de Título.
- **Isolamento por Fixture:** Cada teste roda contra um banco SQLite efêmero em `tmp_path`, garantindo independência total.
- **Bloqueio Determinístico:** A entrega falha com código 1 se 0 testes forem encontrados ou se qualquer asserção falhar.
- **Auditoria Factual:** Geração do relatório `RELATORIO-AUDITORIA.json` contendo métricas reais (duração em ms, status dos 7 gates, nota de segurança).
- **Gate Validador:** `G_TESTES` e `aidd audit --report`.

---

## 2. Tabela Consolidada dos 7 Quality Gates Mecânicos

| Gate | O que Audita no Código Real | Condição de Bloqueio |
| :--- | :--- | :--- |
| **1. G_ESTRUTURA** | Fatias em `src/modules`, layout e manifestos. | Falta de fatias ou manifestos JSON corrompidos. |
| **2. G_QUALIDADE** | Compilação `py_compile` e varredura AST contra stubs. | Erro de sintaxe ou stubs vazios (`pass`, `...`). |
| **3. G_TESTES** | Execução real com `pytest` em `tests/unit/` e healthcheck. | Qualquer teste FAILED ou 0 testes encontrados. |
| **4. G_CONTRACTS** | Conformidade `RouteRegistry`, OpenAPI 3.1 e MCP Server. | Violação de contrato ou schema JSON inválido. |
| **5. G_SEGREDOS** | Entropia de Shannon ($H > 4.75$) e Regex contra chaves. | Chave de API, segredo ou token hardcoded. |
| **6. G_HARNESS_COMPAT** | Zero API Key e compatibilidade CLI/SO multiplataforma. | Dependência externa paga ou comando quebrado. |
| **7. G_SEGURANCA** | 7 Camadas: OWASP, JWT HS256, Zero SQLi, SQLite WAL, etc. | Qualquer vulnerabilidade detectada (Score < 100%). |
