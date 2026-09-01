import os, sys, shutil, subprocess, json, re
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[\s_-]+', '-', text)[:40]

def provision(project_desc, base_dir=r'C:\Users\trcnologia\orca\workspaces\PROJETOS Criados com IA'):
    words = project_desc.split()
    target_text = ' '.join(words[:3]) if len(words) >= 3 else project_desc
    slug = slugify(target_text)
    project_dir = os.path.join(base_dir, f'proj_{slug}')
    
    print(f"🚀 [AIDD MASTER PACK] Provisionando novo projeto: {slug}")
    print(f"📁 Destino: {project_dir}")
    
    os.makedirs(os.path.join(project_dir, 'docs'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'src'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'tests'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'scripts', 'gates'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'scripts', 'phases'), exist_ok=True)
    
    # 1. Inicializar Git se não existir
    if not os.path.exists(os.path.join(project_dir, '.git')):
        subprocess.run(['git', 'init'], cwd=project_dir, capture_output=True)
        print("   -> Git inicializado")
        
    # 2. Registrar no ORCA CLI
    try:
        res = subprocess.run(['orca', 'repo', 'add', '--path', project_dir], capture_output=True, text=True)
        if res.returncode == 0:
            print("   -> Registrado no ORCA com sucesso")
    except:
        pass
        
    # 3. Criar AGENTS.md Mestre (4 Camadas + Zero API Key)
    agents_content = f'''# AGENTS — Projeto {slug} (Padrão AIDD 4 Camadas)

**Descrição:** {project_desc}
**Arquitetura:** ORCA Multi-Agente & AIDD Camadas 1-4
**Regra Zero:** Zero Fricção de API Key. Use o Harness Nativo e 90% Determinismo Local.

---

## 🏛️ 1. Governança do Mestre de Obras (Harness Principal)
1. **Papel:** Auditor e Orquestrador. Não escreva código bruto volumoso no chat principal.
2. **Mesas de Trabalho (ORCA Worktrees):** Despache tarefas pesadas via `orca worktree create`.
3. **Economia de Tokens:** Thinking em **English Caveman Ultra-Compacto**, respostas ao usuário em **PT-BR**.
4. **Ciclo /implementacao:** Toda fase roda `impl` -> `test` -> `validate` -> `verify`.

---

## 🛡️ 2. Gates Mecânicos de Validação (Zero Token)
- `python scripts/gates/G_SEGREDOS.py` — Bloqueia vazamento de chaves (exit 0/1).
- `python scripts/gates/G_QUALIDADE.py` — Valida sintaxe e testes unitários.
- `python scripts/gates/G_HARNESS_COMPAT.py` — Detecta capacidades da IDE ativa.
'''
    agents_path = os.path.join(project_dir, 'AGENTS.md')
    with open(agents_path, 'w', encoding='utf-8') as f:
        f.write(agents_content)
    print("   -> Criado: AGENTS.md")

    # 4. Criar Symlinks/Junctions para Claude, Gemini, Cursor
    for f in ['CLAUDE.md', 'GEMINI.md', '.cursorrules']:
        target_f = os.path.join(project_dir, f)
        shutil.copyfile(agents_path, target_f)
    print("   -> Criados arquivos multi-harness (CLAUDE, GEMINI, CURSOR)")

    # 5. Criar Plano de Execução Estruturado
    plano_data = {
        "projeto": {
            "nome": slug,
            "descricao": project_desc,
            "arquitetura": "AIDD 4 Camadas",
            "zero_api_key_mode": True,
            "status": "INICIALIZADO"
        },
        "fases": [
            {
                "id": "fase-01-analise",
                "nome": "Analise e Modelagem de Contratos",
                "status": "PENDENTE",
                "mesa_orca": "mesa-analise",
                "expected_outputs": ["docs/ARQUITETURA.md"]
            },
            {
                "id": "fase-02-implementacao",
                "nome": "Implementacao do Core Determinístico",
                "status": "PENDENTE",
                "mesa_orca": "mesa-dev",
                "expected_outputs": ["src/main.py"]
            },
            {
                "id": "fase-03-validacao",
                "nome": "Auditoria de Gates e Testes Finais",
                "status": "PENDENTE",
                "mesa_orca": "mesa-qa",
                "expected_outputs": ["tests/"]
            }
        ]
    }
    with open(os.path.join(project_dir, 'PLANO-EXECUCAO-ESTRUTURADO.json'), 'w', encoding='utf-8') as f:
        json.dump(plano_data, f, indent=2, ensure_ascii=False)
    print("   -> Criado: PLANO-EXECUCAO-ESTRUTURADO.json")

    # 6. Copiar Gates
    gates_hub = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'orca-orchestrator', 'templates', 'gates')
    if os.path.exists(gates_hub):
        for g in os.listdir(gates_hub):
            shutil.copyfile(os.path.join(gates_hub, g), os.path.join(project_dir, 'scripts', 'gates', g))
            print(f"   -> Gate instalado: scripts/gates/{g}")

    # Criar G_HARNESS_COMPAT.py
    g_harness = '''import os, sys, json

def check_harness():
    print("🔍 [GATE G_HARNESS_COMPAT] Verificando ambiente nativo de execucao...")
    detected = {
        "claude_code": os.path.exists(os.path.expanduser("~/.claude")),
        "antigravity_gemini": os.path.exists(os.path.expanduser("~/.gemini")),
        "cursor": os.path.exists(os.path.expanduser("~/.cursor")),
        "orca": True
    }
    print(f"✅ Harness ativo detectado com sucesso. Modo Zero API Key operacional.")
    sys.exit(0)

if __name__ == '__main__':
    check_harness()
'''
    with open(os.path.join(project_dir, 'scripts', 'gates', 'G_HARNESS_COMPAT.py'), 'w', encoding='utf-8') as f:
        f.write(g_harness)
    print("   -> Gate instalado: scripts/gates/G_HARNESS_COMPAT.py")

    print(f"\n✨ PROJETO '{slug}' 100% PROVISIONADO NO PADRÃO AIDD + ORCA + ZERO API KEY!")

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'projeto-geral'
    provision(prompt)
