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
    
    # 1. Estrutura de Diretórios Modulares + Shared Kernel
    os.makedirs(os.path.join(project_dir, 'src', 'core'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'src', 'shared'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'src', 'modules'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'src', 'static', 'components'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'tests', 'unit'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'tests', 'load'), exist_ok=True)
    os.makedirs(os.path.join(project_dir, 'scripts', 'gates'), exist_ok=True)
    
    open(os.path.join(project_dir, 'src', '__init__.py'), 'w').close()
    open(os.path.join(project_dir, 'src', 'core', '__init__.py'), 'w').close()
    open(os.path.join(project_dir, 'src', 'modules', '__init__.py'), 'w').close()

    # 2. Copiar Core v2 + Shared Kernel
    v2_hub = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'aidd-master-pack', 'templates', 'v2')
    if os.path.exists(v2_hub):
        for f in ['database.py', 'events.py', 'openapi.py', 'webhooks.py']:
            if os.path.exists(os.path.join(v2_hub, f)):
                shutil.copyfile(os.path.join(v2_hub, f), os.path.join(project_dir, 'src', 'core', f))
        
        shared_src = os.path.join(v2_hub, 'shared')
        if os.path.exists(shared_src):
            shutil.copytree(shared_src, os.path.join(project_dir, 'src', 'shared'), dirs_exist_ok=True)

        for f in ['Dockerfile', 'docker-compose.yml', 'deploy.sh']:
            if os.path.exists(os.path.join(v2_hub, f)):
                shutil.copyfile(os.path.join(v2_hub, f), os.path.join(project_dir, f))
                
        if os.path.exists(os.path.join(v2_hub, 'locustfile.py')):
            shutil.copyfile(os.path.join(v2_hub, 'locustfile.py'), os.path.join(project_dir, 'tests', 'load', 'locustfile.py'))

    # 3. Copiar scripts (aidd.py, add_module.py)
    hub_scripts = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'aidd-master-pack', 'scripts')
    for s in ['aidd.py', 'add_module.py']:
        if os.path.exists(os.path.join(hub_scripts, s)):
            shutil.copyfile(os.path.join(hub_scripts, s), os.path.join(project_dir, 'scripts', s))

    # 4. Copiar Gates Mecânicos
    gates_hub = os.path.join(os.path.expanduser('~'), '.agents', 'skills', 'aidd-master-pack', 'templates', 'gates')
    if os.path.exists(gates_hub):
        for g in os.listdir(gates_hub):
            if g.endswith('.py'):
                shutil.copyfile(os.path.join(gates_hub, g), os.path.join(project_dir, 'scripts', 'gates', g))

    # 5. Git Init
    if not os.path.exists(os.path.join(project_dir, '.git')):
        subprocess.run(['git', 'init'], cwd=project_dir, capture_output=True)

    print(f"✨ PROJETO '{slug}' 100% PROVISIONADO COM SHARED KERNEL & WEBHOOKS!")

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'projeto-modular'
    provision(prompt)
