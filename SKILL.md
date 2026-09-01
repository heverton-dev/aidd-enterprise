---
name: aidd-master-pack-v4
version: 4.0.0
description: AIDD v4.0 — Cross-Project Enterprise Monolith Suite (Unificação de Fatias Verticais Cross-Domain com EventBus, Webhooks, Swagger Studio OpenAPI 3.1, Servidor Nativo MCP e Super-App UI).
---

# 🌐 AIDD Master Pack v4.0 — Cross-Project Enterprise Architecture

O **AIDD v4.0** é o framework de engenharia agêntica para construção de **Suítes Empresariais Cross-Project** e **Monólitos Modulares de Alta Performance**. Ele une múltiplos domínios de negócio com isolamento de Clean Architecture, comunicação assíncrona por eventos, conformidade de segurança OWASP, documentação interativa ao vivo e conectividade total com modelos de IA.

---

## 🏆 As 4 Regras de Ouro do AIDD v4

1. **Clean Architecture & Isolamento de Fatias Verticais:** Cada domínio de negócio (`crm`, `erp`, `logistica`, `helpdesk`, `wms`, `membros`, `catalogo`) é estruturado como uma fatia vertical independente com seus próprios modelos, regras e rotas, comunicando-se exclusivamente via `EventBus` pub/sub.
2. **Full CRUD Diligente em 100% dos Módulos:** Toda entidade possui Create, Read, Update e Delete totalmente funcionais, persistidos no banco de dados SQLite WAL, com modais no front-end, feedback via Toasts e confirmações táteis.
3. **Quad-Pillars da Sincronização:**
   - **Super-App Front-End Impeccable:** Header de linha única, scrollbars de 4px, zero emojis, ícones vetoriais SVG Lucide, sem diálogos nativos de SO.
   - **Swagger Studio & OpenAPI 3.1 Nativo (`/docs`):** Todas as rotas registradas com esquemas de entrada/saída e testador de requisições ao vivo.
   - **Disparadores de Webhook em Tempo Real:** Disparo assíncrono com assinatura HMAC para cada evento de domínio.
   - **Servidor Nativo Universal MCP (`/mcp`):** Exposição de 100% das operações como ferramentas JSON-RPC 2.0 para Claude Desktop, Cursor e Antigravity.
4. **Economia Agêntica de Tokens:** Zero execução de comandos desnecessários no chat principal. Uso de scripts determinísticos locais para compilação, testes e gates de qualidade.

---

## 🚀 Comandos Principais do AIDD v4

```bash
# 1. Compor uma nova Suite Cross-Project com múltiplos domínios
python scripts/compose_suite.py <caminho_destino> <nome_suite> crm erp helpdesk logistica

# 2. Adicionar uma nova fatia vertical com Full CRUD, testes e eventos
python scripts/add_module.py faturamento

# 3. Executar os Gates Determinísticos de Qualidade e Segurança
python scripts/gates/G_QUALIDADE.py
python scripts/gates/G_SEGURANCA.py

# 4. Iniciar o servidor da suíte unificada
python src/server.py
```
