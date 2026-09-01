# 📦 AIDD Master Pack v4.0 (Enterprise Cross-Project Suite)

> **O Framework Definitivo para Monólitos Modulares, Clean Architecture e Integração Agêntica de Domínios de Negócio.**

---

## 🏛️ Visão Geral

A versão **4.0 (Cross-Project)** eleva o ecossistema AIDD ao nível corporativo de alta performance. Ela permite pegar múltiplos projetos independentes (CRM, ERP, Helpdesk, Logística, Catálogo, Membros) e unificá-los em uma única suíte empresarial robusta:

- **Isolamento de Domínios (Vertical Slices):** Sem acoplamento espaguete entre módulos.
- **EventBus Assíncrono:** Integração entre módulos orientada a eventos em tempo real.
- **Diligência Full CRUD:** Criação, leitura, atualização e exclusão em todas as fatias.
- **Swagger Studio OpenAPI 3.1 (`/docs`):** Documentação viva com testador ao vivo.
- **Model Context Protocol (`/mcp`):** 100% das operações exportadas para agentes de IA (Claude, Cursor, Antigravity).
- **Webhooks com HMAC:** Notificação para microsserviços e integrações externas.
- **Impeccable Design System:** Super-App UI com 4px scrollbars, header de linha única e zero emojis.

---

## 📂 Estrutura do Pacote

```
aidd-master-pack-v4/
├── scripts/
│   ├── aidd.py               # Micro-CLI de automação
│   ├── compose_suite.py      # Motor de Composição Cross-Project
│   ├── add_module.py         # Gerador atômico de fatias verticais
│   └── gates/                # Quality & Security Gates determinísticos
├── templates/
│   ├── rules/                # Regras determinísticas (01_regras, 02_slices, 03_impeccable, 04_cross_project)
│   └── v2/                   # Shared Kernel & Componentes UI
├── examples/
│   ├── enterprise-suite-v4/  # Suíte Corporativa Unificada de 5 Domínios
│   └── logistica-hub-v4/     # Suíte Logística & Frotas com 20 Tools MCP
├── README.md
└── SKILL.md
```

---

## 🚀 Como Iniciar

```bash
# Iniciar a suite de referência
cd examples/logistica-hub-v4
python src/server.py

# Acessar os portais
# - Aplicação Web: http://localhost:3000
# - Swagger Studio: http://localhost:3000/docs
# - Guia Oficial: http://localhost:3000/docs/guia
# - Portal MCP: http://localhost:3000/mcp
```
