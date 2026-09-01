# 📦 aidd-master-pack-v4 (v4.0.0)

> **AIDD v4.0 — Cross-Project Enterprise Monolith Suite (Unificação de 5 Domínios: CRM, ERP, Helpdesk, Cursos e Catálogo com EventBus Cross-Domain e Super-App UI).**

---

## 🏛️ Estrutura do Pacote

```
aidd-master-pack-v4/
├── scripts/
│   ├── aidd.py               # Micro-CLI do framework
│   ├── add_module.py         # Gerador atômico de fatias verticais
│   └── gates/                # Quality & Security Gates determinísticos
├── templates/                # Templates e Shared Kernel da versão 4.0.0
├── examples/                 # Projetos de referência e exemplos oficiais
├── README.md                 # Especificação técnica do pacote 4.0.0
└── SKILL.md                  # Skill agêntica para Antigravity / Cursor / Claude
```

## 🚀 Instalação e Uso Rápido

```bash
# Executar gates de qualidade
python scripts/gates/G_QUALIDADE.py

# Criar um novo módulo vertical
python scripts/add_module.py financeiro
```
