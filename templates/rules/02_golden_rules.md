# 🐋 Protocolo de Orquestração com ORCA ADE & As 4 Regras de Ouro

**Arquitetura:** Processos e Mesas de Trabalho Independentes (ORCA CLI + AIDD v4.1)  
**Conceito Fundamental:** **Zero Contaminação de Contexto**. Cada IA atua em seu próprio processo/terminal e pasta isolada via Worktrees Git do ORCA.

---

## 📌 1. A Matriz Operacional do ORCA ADE

| Papel | O que FAZ | O que NUNCA FAZ |
| :--- | :--- | :--- |
| **Mestre de Obras (Maestro)** | - Roda no chat principal estéril e limpo.<br>- Decompõe épicos em tarefas atômicas.<br>- Cria Mesas Isoladas via `orca worktree create`.<br>- Audita com os gates locais (`python scripts/aidd.py audit`).<br>- Realiza o merge no branch principal (`git merge`). | - **PROIBIDO** gerar código longo e pesado no chat raiz.<br>- **PROIBIDO** rodar compilações pesadas no chat.<br>- **PROIBIDO** aceitar entregas sem validar gates (exit 0). |
| **Especialista da Mesa (Worktree)** | - Roda no processo isolado da Worktree.<br>- Executa com thinking **English Caveman ultra-denso**.<br>- Escreve a fatia vertical com Full CRUD e testes `pytest`.<br>- Comita os arquivos no branch da sua mesa. | - **PROIBIDO** alterar arquivos fora do seu escopo.<br>- **PROIBIDO** gerar atalhos monolíticos ou stubs vazios. |

---

## 🏆 As 4 Regras de Ouro da Engenharia Agêntica (Anti-Estouro de Tokens)

| Regra de Ouro | Como Aplicar na Prática | Por que evita estourar o limite |
| :--- | :--- | :--- |
| **1. Não use o chat principal como terminal** | Deixe testes (`pytest`), scaffolding (`add_module.py`) e gates mecânicos rodando localmente via Python. | Economiza 90% do consumo semanal de tokens. |
| **2. Use Worktrees do ORCA para frentes grandes** | Cada tarefa é aberta em sua mesa isolada (`orca worktree create --parent-worktree active`). | Evita que o contexto principal acumule 100k+ tokens desnecessários de logs e erros. |
| **3. Reinicie sessões usando o Plano JSON** | Ao começar um novo dia ou módulo, abra uma sessão nova apontando para o `PLANO-EXECUCAO-ESTRUTURADO.json`. | O agente retoma o estado exato consumindo apenas ~500 tokens em vez de 80.000 tokens de histórico. |
| **4. Governança Rígida por Gates Mecânicos** | A entrega só é aceita se todos os gates (`G_ESTRUTURA`, `G_TESTES`, `G_CONTRACTS`, `G_QUALIDADE`, `G_SEGREDOS`, `G_HARNESS_COMPAT`) retornarem exit 0. | Elimina alucinações e entregas incompletas na raiz. |

---

## 🛠️ Ciclo de Vida de uma Tarefa no ORCA ADE

```bash
# 1. Maestro registra o repositório no ORCA (se ainda não registrado)
orca repo add --path "C:/caminho/do/projeto"

# 2. Maestro cria a mesa de trabalho filha isolada
orca worktree create --name feature-modulo-x --repo id:<repoId> --parent-worktree active

# 3. Especialista atua na mesa isolada e realiza o commit
cd /caminho/worktree/feature-modulo-x
git add . && git commit -m "feat(modulo-x): implementa fatia vertical com Full CRUD e testes"

# 4. Maestro audita na mesa antes do merge
python scripts/aidd.py audit --report

# 5. Maestro faz o merge no branch principal e remove a mesa
git merge feature-modulo-x
orca worktree rm --worktree branch:feature-modulo-x
```
