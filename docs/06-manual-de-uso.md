# 06. Manual de Uso: Comandos CLI, APIs e Servidor MCP

> **Framework:** AIDD Master Enterprise  
> **Referência:** Guia de referência operacional para desenvolvedores humanos e agentes de IA.

---

## 1. Comandos CLI Unificados (`scripts/aidd.py`)

A ferramenta `scripts/aidd.py` é o ponto de entrada único para todas as operações do ecossistema:

### `setup` — Pre-Flight & Fleet Discovery
```bash
python scripts/aidd.py setup
```
* Valida a instalação do Python, dependências do `requirements.txt` e permissões de escrita.
* Varre o `$PATH` em busca de agentes de IA instalados (Claude, Antigravity, Codex, etc.).
* Prepara o ambiente para composição segura.

### `compose-orca` — Composição Modular via Subagentes Efêmeros
```bash
python scripts/aidd.py compose-orca crm erp billing helpdesk
```
* Dispara a engine de subagentes com descarte de contexto (*Context-Purge*).
* Cria cada módulo em isolamento físico com modelos, serviços, rotas e testes unitários.
* Salva o manifesto de build em `COMPOSE-ORCA-MANIFEST.json`.

### `compose` — Composição Determinística Tradicional
```bash
python scripts/aidd.py compose --suite "Enterprise Hub" --db sqlite crm erp logistica
```
* Parâmetros opcionais:
  - `--db sqlite`: Usa SQLite WAL mode local (padrão).
  - `--db postgres`: Prepara a infraestrutura para PostgreSQL / Supabase.
  - `--dir <caminho>`: Define o diretório de destino.

### `add-module` — Adição Atômica de Nova Fatia
```bash
python scripts/aidd.py add-module faturamento
```
* Cria a estrutura completa de uma nova fatia vertical em `src/modules/faturamento/`.
* Conecta a nova fatia ao EventBus e ao Swagger Studio automaticamente.

### `test` — Execução da Suíte de Testes
```bash
python scripts/aidd.py test
# Ou diretamente pelo pytest:
python -m pytest tests/ -v
```
* Executa todos os testes unitários da pasta `tests/` com relatório detalhado.

### `audit` — Auditoria dos Gates
```bash
python scripts/aidd.py audit --report
```
* Executa a validação dos Quality Gates e gera o relatório consolidado de blindagem.

---

## 2. Portais e Endpoints da Aplicação em Execução

Ao iniciar o servidor da aplicação (`python src/server.py`), quatro portais são disponibilizados localmente:

### 1. Super-App SPA (`http://localhost:8000/`)
* Interface unificada de front-end com design corporativo Impeccable UI.
* Permite alternar entre os módulos da suíte através de abas sem recarregar a página.

### 2. Swagger Studio OpenAPI 3.1 (`http://localhost:8000/docs`)
* Documentação viva e interativa de todas as rotas REST do sistema.
* Permite autenticação via Bearer Token JWT e execução de chamadas HTTP diretamente no navegador.

### 3. Model Context Protocol Server (`http://localhost:8000/mcp`)
* Servidor JSON-RPC 2.0 nativo pronto para conectar IAs externas (Claude Desktop, Cursor, Antigravity).
* Expõe as ferramentas de CRUD dos módulos de domínio com schemas tipados.

### 4. Webhook Configuration Studio (`http://localhost:8000/webhooks`)
* Painel de controle para cadastrar URLs de microsserviços externos para receber eventos do EventBus com assinatura digital HMAC SHA-256.

---

## 3. Slash Commands no Chat de Qualquer IDE

Se você estiver em um chat de IA (Antigravity, Cursor, Claude Code), você pode acionar os comandos rápidos:

* `/compose crm erp billing`: Converte o pedido e executa a composição imediata dos módulos solicitados.
* `/resumo-sessao`: Registra e exporta todo o histórico factual da sessão atual em um arquivo Markdown estruturado dentro de `secoes/`.
* `/gate`: Executa a bateria de validação dos 10 Quality Gates.
