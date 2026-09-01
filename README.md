# AIDD Master Pack — AI-Driven Development Framework (v1.0)

> **Framework de Provisionamento e Orquestração Agêntica de Software com Zero Fricção de API Key, Economia Extrema de Tokens e Clean Architecture.**

---

## 🌟 Visão Geral

O **AIDD Master Pack** transforma uma ideia descrita em linguagem natural em um **projeto de software completo, funcional e testado em segundos**.

Ele une os conceitos de:
* **Tratado das 4 Camadas (Heverton Peres)**: Tela/UI, Harness/Segurança, LLM/Raciocínio e Tools/Determinismo.
* **Orquestração Multi-Agente com ORCA Worktrees**: Mesas de trabalho isoladas sem contaminação de contexto.
* **Design System Impeccable (Regra Zero Emojis)**: Interfaces limpas, profissionais e livres de clichês de IA.
* **Modo Zero API Key Pass-Through**: 90% do trabalho mecânico roda em Python local sem depender de chaves externas.

---

## 🏛️ As 4 Camadas do Tratado

* **Camada 1: Tela & UI** — Soberania em PT-BR, Prefix Caching de 90%, Zero Amnésia.
* **Camada 2: Harness & Segurança** — Circuit Breakers, Sandbox Reversível, Worktrees ORCA.
* **Camada 3: LLM & Raciocínio** — Caveman Ultra (Thinking em English Caveman denso).
* **Camada 4: Tools & Determinismo** — 90% Determinismo local em Python, SQLite WAL e Gates.

---

## 🏆 As 3 Regras de Ouro (Anti-Estouro de Tokens)

1. **Não use o chat principal como terminal:** Deixe compilação, testes (pytest) e tarefas mecânicas rodando via Python local. Isso economiza 90% do seu consumo semanal.
2. **Use Worktrees do ORCA para frentes grandes:** Cada tarefa separada em sua mesa limpa evita que o contexto principal acumule 100k+ tokens desnecessários.
3. **Reinicie sessões usando o Plano JSON:** Ao começar um novo dia ou módulo, abra uma sessão nova apontando para o `PLANO-EXECUCAO-ESTRUTURADO.json`. O agente retoma o estado exato consumindo apenas 500 tokens em vez de 80.000 do histórico passado.

---

## 🛡️ Gates Mecânicos de Validação (Zero Token)

Todos os projetos gerados incluem gates determinísticos em Python que barram código quebrado antes do commit:
* `G_SEGREDOS.py` — Analisa **Entropia de Shannon (> 4.6 bits)** e bloqueia credenciais/chaves expostas.
* `G_QUALIDADE.py` — Compila a sintaxe e valida a integridade com `py_compile`.
* `G_HARNESS_COMPAT.py` — Garante compatibilidade automática com 21 IDEs e harnesses.

---

## 🚀 Como Usar

### 1. Provisionar um Novo Projeto do Zero:
```bash
python scripts/provision_project.py "Meu Projeto Incrivel"
```

### 2. Rodar a Bateria de Gates Mecânicos:
```bash
pytest
python scripts/gates/G_SEGREDOS.py
python scripts/gates/G_QUALIDADE.py
```

---

## 📂 Exemplos Reais Incluídos

* `examples/plataforma-de-membros`: Área de membros completa com cursos, player de aulas, progresso e autenticação.
* `examples/catalogo-digital-whatsapp`: E-commerce/Catálogo com drawer de carrinho, painel admin e fechamento de pedidos via WhatsApp.

---

## 📄 Licença
Distribuído sob a licença **MIT**.
