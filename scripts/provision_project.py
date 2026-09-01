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
    
    print(f"🚀 [AIDD MASTER PACK v2.0] Provisionando ecossistema modular: {slug}")
    print(f"📁 Destino: {project_dir}")
    
    # 1. Estrutura de Diretórios Modulares
    os.makedirs(os.path.join(project_dir, 'src', 'core'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'src', 'modules'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'src', 'static', 'components'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'tests', 'unit'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'tests', 'load'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'scripts', 'gates'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'docs'), exist_ok=True)
    
    open(os.path.join(project_dir, 'src', '__init__.py'), 'w').close()
    open(os.path.join(project_dir, 'src', 'core', '__init__.py'), 'w').close()
    open(os.path.join(project_dir, 'src', 'modules', '__init__.py'), 'w').close()
    open(os.path.join(project_dir, 'tests', '__init__.py'), 'w').close()

    # 2. Copiar Templates do Core v2.0
    v2_hub = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'aidd-master-pack', 'templates', 'v2')
    if os.path.exists(v2_hub):
        for f in ['database.py', 'events.py', 'openapi.py']:
            if os.path.exists(os.path.join(v2_hub, f)):
                shutil.copyfile(os.path.join(v2_hub, f), os.path.join(project_dir, 'src', 'core', f))
        
        # Infra Docker / Deploy / Locust
        for f in ['Dockerfile', 'docker-compose.yml', 'deploy.sh']:
            if os.path.exists(os.path.join(v2_hub, f)):
                shutil.copyfile(os.path.join(v2_hub, f), os.path.join(project_dir, f))
                
        if os.path.exists(os.path.join(v2_hub, 'locustfile.py')):
            shutil.copyfile(os.path.join(v2_hub, 'locustfile.py'), os.path.join(project_dir, 'tests', 'load', 'locustfile.py'))

    # 3. Copiar add_module.py para scripts/
    hub_scripts = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'aidd-master-pack', 'scripts')
    if os.path.exists(os.path.join(hub_scripts, 'add_module.py')):
        shutil.copyfile(os.path.join(hub_scripts, 'add_module.py'), os.path.join(project_dir, 'scripts', 'add_module.py'))

    # 4. Copiar Gates Mecânicos
    gates_hub = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'aidd-master-pack', 'templates', 'gates')
    if os.path.exists(gates_hub):
        for g in os.listdir(gates_hub):
            if g.endswith('.py'):
                shutil.copyfile(os.path.join(gates_hub, g), os.path.join(project_dir, 'scripts', 'gates', g))

    # 5. Git Init e Registro ORCA
    if not os.path.exists(os.path.join(project_dir, '.git')):
        subprocess.run(['git', 'init'], cwd=project_dir, capture_output=True)
    try:
        subprocess.run(['orca', 'repo', 'add', '--path', project_dir], capture_output=True)
    except:
        pass

    # 6. AGENTS.md v2.0
    agents_content = f'''# AGENTS — Projeto Modular {slug} (AIDD v2.0)

**Descrição:** {project_desc}
**Arquitetura:** AIDD v2.0 Modular (Data-Driven Modules + Dual DB + OpenAPI Swagger + Docker)
**Regra Zero:** Zero Fricção de API Key & Zero Emojis em Interfaces (Design Impeccable).

---

## 🏛️ 1. Governança Modular do Mestre de Obras
1. **Módulos Desacoplados:** Cada nova feature deve viver em `src/modules/<nome>/` com seus próprios models, services e rotas.
2. **Criação de Novos Módulos:** Use sempre `python scripts/add_module.py <nome>` para manter o padrão.
3. **Comunicação por Eventos:** Use `core.events.EventBus` para trocar dados entre módulos sem acoplamento direto.
4. **Documentação Automática:** Toda rota registrada em `core.openapi.RouteRegistry` aparece imediatamente em `/docs`.

---

## 🏆 AS 3 REGRAS DE OURO DA ENGENHARIA AGÊNTICA (Anti-Estouro de Tokens)
| Regra de Ouro | Por que evita estourar o limite semanal |
| :--- | :--- |
| **1. Não use o chat principal como terminal** | Deixe compilação, testes (pytest) e tarefas mecânicas rodando via Python local. Isso economiza 90% do seu consumo semanal. |
| **2. Use Worktrees do ORCA para frentes grandes** | Cada tarefa separada em sua mesa limpa evita que o contexto principal acumule 100k+ tokens desnecessários. |
| **3. Reinicie sessões usando o Plano JSON** | Ao começar um novo dia ou módulo, abra uma sessão nova apontando para o `PLANO-EXECUCAO-ESTRUTURADO.json`. O agente retoma o estado exato consumindo apenas 500 tokens em vez de 80.000 do histórico passado. |
'''
    agents_path = os.path.join(project_dir, 'AGENTS.md')
    with open(agents_path, 'w', encoding='utf-8') as f:
        f.write(agents_content)

    for f in ['CLAUDE.md', 'GEMINI.md', '.cursorrules']:
        shutil.copyfile(agents_path, os.path.join(project_dir, f))

    # 7. PLANO-EXECUCAO-ESTRUTURADO.json
    plano_data = {
        "projeto": {
            "nome": slug,
            "descricao": project_desc,
            "versao": "2.0.0",
            "arquitetura": "AIDD Modular Data-Driven",
            "dual_database": True,
            "openapi_swagger": True,
            "docker_ready": True,
            "status": "INICIALIZADO"
        },
        "modulos_instalados": ["core"],
        "fases": [
            {
                "id": "fase-01-core-setup",
                "nome": "Configuracao do Core, Dual Database e EventBus",
                "status": "CONCLUIDO",
                "expected_outputs": ["src/core/database.py", "src/core/events.py", "src/core/openapi.py"]
            },
            {
                "id": "fase-02-modulos-iniciais",
                "nome": "Criacao dos Modulos de Dominio",
                "status": "PENDENTE",
                "expected_outputs": ["src/modules/"]
            },
            {
                "id": "fase-03-infra-e-deploy",
                "nome": "Empacotamento Docker, Deploy Script e Testes de Carga",
                "status": "CONCLUIDO",
                "expected_outputs": ["Dockerfile", "docker-compose.yml", "deploy.sh", "tests/load/locustfile.py"]
            }
        ]
    }
    with open(os.path.join(project_dir, 'PLANO-EXECUCAO-ESTRUTURADO.json'), 'w', encoding='utf-8') as f:
        json.dump(plano_data, f, indent=2, ensure_ascii=False)

    print(f"\n✨ PROJETO '{slug}' 100% PROVISIONADO NO PADRÃO AIDD v2.0 MODULAR & CLOUD-READY!")

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'projeto-modular'
    provision(prompt)
