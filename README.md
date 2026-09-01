# AIDD Master Pack v2.0 — Enterprise Modular & Cloud-Ready Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Architecture: AIDD v2.0 Modular](https://img.shields.io/badge/Architecture-AIDD%20v2.0%20Modular-emerald.svg)](#-arquitetura-modular-data-driven)
[![OpenAPI / Swagger](https://img.shields.io/badge/API-OpenAPI%203.0%20%2F%20Swagger-cyan.svg)](#-documentacao-openapi-e-swagger-ui)
[![Deploy: Docker / VPS](https://img.shields.io/badge/Deploy-Docker%20%2F%20VPS%20(Hetzner)-purple.svg)](#-deploy-multi-cloud-e-docker)

> **Framework Empresarial de Provisionamento, Modularidade sob Demanda e Orquestração Agêntica com Zero Fricção de API Key, Dual Database (SQLite/Postgres) e Design Impeccable (Zero Emojis).**

---

## 🌟 O Que Há de Novo na v2.0

1. **Modularidade sob Demanda (`python scripts/add_module.py <nome>`):**
   - O usuário pode criar novos módulos independentes a qualquer momento com 1 comando.
   - Cada módulo contém seu schema de banco, regras de negócio, rotas REST, componentes visuais e testes automatizados.
2. **Dual Database Engine:**
   - **Desenvolvimento:** SQLite WAL mode (Zero configuração local).
   - **Produção:** PostgreSQL / Supabase chaveado via `DATABASE_URL`.
3. **OpenAPI 3.0 & Swagger UI Automático (`/docs`):**
   - Todas as rotas de todos os módulos aparecem auto-documentadas interativamente.
4. **Testes de Carga (Locust) e E2E (Playwright):**
   - `tests/load/locustfile.py` para simular 10.000 requisições simultâneas.
5. **Infraestrutura Cloud-Ready:**
   - `Dockerfile` multi-stage, `docker-compose.yml` e script de deploy em VPS Hetzner/Contabo (`deploy.sh`).
6. **Design Impeccable (Regra Zero Emojis):**
   - Interfaces corporativas com ícones vetoriais SVG e acabamento de alto nível.

---

## 🏛️ Estrutura de Diretórios Modular

```
projeto-v2/
├── src/
│   ├── core/                  # Database Dual, EventBus, OpenAPI Generator
│   ├── modules/               # Módulos Desacoplados (Auth, Cupons, Afiliados...)
│   │   └── <modulo>/
│   │       ├── models.py      # Schemas e Tabelas SQLite/Postgres
│   │       ├── services.py    # Regras de Negócio e Casos de Uso
│   │       └── routes.py      # Endpoints REST e Contratos
│   └── static/                # Frontend SPA Impeccable com Componentes
├── tests/
│   ├── unit/                  # Testes unitários de cada módulo
│   └── load/locustfile.py     # Testes de estresse com Locust
├── scripts/
│   ├── provision_project.py   # Gerador do Projeto Base
│   ├── add_module.py          # Criador Dinâmico de Módulos
│   └── gates/                 # Gates Mecânicos (Shannon Entropy, Qualidade)
├── Dockerfile & docker-compose.yml # Containers de Produção
└── deploy.sh                  # Deploy em VPS Hetzner / Contabo
```

---

## 🚀 Como Usar

### 1. Criar um Novo Projeto Modular:
```bash
python scripts/provision_project.py "Minha Plataforma Modular"
```

### 2. Adicionar um Novo Módulo sob Demanda:
```bash
python scripts/add_module.py cupons "Gerenciador de Cupons de Desconto"
```

### 3. Rodar Testes Unitários de Todos os Módulos:
```bash
pytest
```

### 4. Subir em Produção via Docker:
```bash
docker compose up -d
```

---

## 📄 Licença
Distribuído sob a licença **MIT** (Heverton Peres).
