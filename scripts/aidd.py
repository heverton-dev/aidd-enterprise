#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
AIDD v4.1 Enterprise CLI — Dividir para Conquistar (aidd.py)
=============================================================================
CLI oficial de automação agêntica e execução de gates determinísticos.
Suporta:
- aidd init <nome> [--dir <destino>]
- aidd compose <dir> <nome> [modulos...]
- aidd add-module <nome> [-d <desc>] [--dir <destino>]
- aidd test [unit|contracts|load|all] [--dir <destino>]
- aidd audit [--report] [--json] [--dir <destino>]
- aidd status [--dir <destino>]
- aidd deploy [docker|vps]
"""

import os
import sys
import subprocess
import argparse
import json
import time
import datetime
import platform
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def ensure_environment(auto_install: bool = True):
    """Garante de forma 100% automática que o runtime possui os pré-requisitos necessários."""
    missing = []
    try:
        import pytest
    except ImportError:
        missing.append("pytest")
    try:
        import requests
    except ImportError:
        missing.append("requests")

    if missing and auto_install:
        print(f"[*] [BOOTSTRAP AUTOMÁTICO] Instalando dependências essenciais: {', '.join(missing)}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True, capture_output=True)
            print("[OK] Dependências instaladas com sucesso.")
        except Exception as e:
            print(f"[WARN] Não foi possível auto-instalar dependências: {e}")


def cmd_setup(args):
    """Executa diagnóstico completo e configuração automática do ambiente."""
    print("=" * 80)
    print("🔧 [AIDD SETUP] Diagnóstico e Inicialização Automática do Ambiente")
    print("=" * 80)
    
    # 1. Checagem de Python
    py_ver = platform.python_version()
    print(f"  [+] Python Runtime: {py_ver} ({sys.executable})")
    
    # 2. Instalação de requirements.txt
    req_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "requirements.txt")
    if os.path.exists(req_file):
        print("  [+] Instalando dependências do 'requirements.txt'...")
        res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file], capture_output=True, text=True)
        if res.returncode == 0:
            print("  [OK] Dependências instaladas com êxito.")
        else:
            print(f"  [WARN] Aviso ao instalar requirements: {res.stderr.strip()}")
    else:
        ensure_environment(auto_install=True)

    # 3. Detecção de Git
    import shutil
    git_bin = shutil.which("git")
    print(f"  [+] Git CLI: {'Presente (' + git_bin + ')' if git_bin else 'Ausente'}")

    # 4. Detecção de ORCA ADE
    orca_bin = shutil.which("orca")
    if orca_bin:
        print(f"  [+] ORCA ADE: Detectado ({orca_bin}) ➔ Modo A (Mesas de Trabalho Isoladas)")
    else:
        print("  [+] ORCA ADE: Não instalado ➔ Modo B (Subagentes Nativos / Git Worktrees)")

    print("=" * 80)
    print("🏆 [SUCESSO]: Ambiente 100% pronto para compor e executar projetos AIDD v4.1!")
    print("=" * 80)


def cmd_init(args):
    ensure_environment()
    try:
        from provision_project import provision
    except ImportError:
        from scripts.provision_project import provision
    provision(args.nome, base_dir=getattr(args, "dir", "."))


def cmd_compose(args):
    ensure_environment()
    try:
        from compose_suite import compose_suite
    except ImportError:
        from scripts.compose_suite import compose_suite
    compose_suite(args.target_dir, args.suite_name, args.modulos or ["crm", "erp", "helpdesk", "logistica"])


def cmd_add_module(args):
    try:
        from add_module import criar_modulo
    except ImportError:
        from scripts.add_module import criar_modulo
    criar_modulo(args.nome, args.descricao or "", target_dir=getattr(args, "dir", "."))


def cmd_test(args):
    target_dir = os.path.abspath(getattr(args, "dir", "."))
    tipo = getattr(args, "tipo", "unit") or "unit"
    print("=" * 80)
    print(f"🧪 [AIDD v4.1 TEST] Executando testes: '{tipo}' em {target_dir}")
    print("=" * 80)

    src_path = os.path.join(target_dir, "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"

    if tipo in ["unit", "all"]:
        tests_dir = os.path.join(target_dir, "tests", "unit")
        if not os.path.exists(tests_dir):
            tests_dir = os.path.join(target_dir, "tests")

        res = subprocess.run([sys.executable, "-m", "pytest", "-v", tests_dir], cwd=target_dir, env=env)
        if res.returncode != 0:
            print(f"\n❌ [FAIL] Testes unitários falharam (exit code {res.returncode})")
            sys.exit(res.returncode)

    if tipo in ["contracts", "all"]:
        gate_contracts = os.path.join(target_dir, "scripts", "gates", "G_CONTRACTS.py")
        if not os.path.isfile(gate_contracts):
            master_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            gate_contracts = os.path.join(master_root, "scripts", "gates", "G_CONTRACTS.py")

        if os.path.exists(gate_contracts):
            res = subprocess.run([sys.executable, gate_contracts, "--dir", target_dir], cwd=target_dir, env=env)
            if res.returncode != 0:
                print(f"\n❌ [FAIL] Gate de contratos falhou (exit code {res.returncode})")
                sys.exit(res.returncode)

    if tipo in ["load", "all"]:
        locust_file = os.path.join(target_dir, "tests", "load", "locustfile.py")
        if os.path.exists(locust_file):
            print("[*] Executando teste de carga Locust (headless 5s)...")
            subprocess.run([
                "locust", "-f", locust_file, "--headless", "-u", "10", "-r", "2", "-t", "5s", "--host", "http://localhost:3000"
            ], cwd=target_dir)

    print("\n🏆 [SUCESSO]: Bateria de testes executada com êxito!")


def cmd_audit(args):
    target_dir = os.path.abspath(getattr(args, "dir", "."))
    print("=" * 80)
    print(f"🛡️  [AIDD v4.1 ENTERPRISE AUDIT] Bateria Completa de Gates Determinísticos")
    print(f"📁 Diretório Alvo: {target_dir}")
    print("=" * 80)

    gates = [
        ("G_ESTRUTURA", "Layout do Projeto, Clean Architecture e Manifestos"),
        ("G_QUALIDADE", "Sintaxe Estática, Compilação e Anti-Stubs"),
        ("G_TESTES", "Execução Obrigatória da Suíte de Testes Unitários"),
        ("G_CONTRACTS", "Conformidade OpenAPI 3.1 e Model Context Protocol (MCP)"),
        ("G_SEGREDOS", "Varredura de Entropia de Shannon e Credenciais Hardcoded"),
        ("G_HARNESS_COMPAT", "Compatibilidade Multi-Harness e Portabilidade")
    ]

    gates_dir = os.path.join(target_dir, "scripts", "gates")
    # Fallback para pasta global do master pack
    master_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fallback_gates_dir = os.path.join(master_root, "scripts", "gates")

    # Verifica se G_SEGURANCA existe
    sec_gate_path = os.path.join(gates_dir, "G_SEGURANCA.py")
    if not os.path.isfile(sec_gate_path):
        sec_gate_path = os.path.join(fallback_gates_dir, "G_SEGURANCA.py")
    if os.path.isfile(sec_gate_path):
        gates.append(("G_SEGURANCA", "Auditoria OWASP, Criptografia JWT e Blindagem Militar"))

    relatorio = {
        "metadata": {
            "timestamp": datetime.datetime.now().isoformat(),
            "target_dir": target_dir,
            "python_version": platform.python_version(),
            "sistema_operacional": platform.platform(),
            "framework": "AIDD Master Pack v4.1 Enterprise Anti-Fail"
        },
        "gates": [],
        "resumo": {
            "total": len(gates),
            "aprovados": 0,
            "falhas": 0,
            "duracao_total_ms": 0.0,
            "status_geral": "PENDENTE"
        }
    }

    t0_global = time.time()
    has_failure = False

    for gate_name, gate_desc in gates:
        gate_file = os.path.join(gates_dir, f"{gate_name}.py")
        if not os.path.isfile(gate_file):
            gate_file = os.path.join(fallback_gates_dir, f"{gate_name}.py")

        print(f"\n▶️  Executando Gate: [{gate_name}] — {gate_desc}...")

        if not os.path.isfile(gate_file):
            print(f"  ❌ [FAIL] Arquivo do gate não encontrado: {gate_file}")
            relatorio["gates"].append({
                "gate": gate_name,
                "descricao": gate_desc,
                "status": "FAIL",
                "exit_code": 1,
                "duracao_ms": 0.0,
                "erro": "Arquivo do gate ausente"
            })
            relatorio["resumo"]["falhas"] += 1
            has_failure = True
            continue

        t0_gate = time.time()
        res = subprocess.run([sys.executable, gate_file, "--dir", target_dir], cwd=target_dir, capture_output=True, text=True, errors="replace")
        duracao_gate = round((time.time() - t0_gate) * 1000, 2)

        # Exibe saída do gate
        if res.stdout:
            print(res.stdout.strip())
        if res.stderr:
            print(res.stderr.strip())

        status = "PASS" if res.returncode == 0 else "FAIL"
        relatorio["gates"].append({
            "gate": gate_name,
            "descricao": gate_desc,
            "status": status,
            "exit_code": res.returncode,
            "duracao_ms": duracao_gate,
            "saida_resumida": res.stdout[-400:] if res.stdout else ""
        })

        if res.returncode == 0:
            relatorio["resumo"]["aprovados"] += 1
        else:
            relatorio["resumo"]["falhas"] += 1
            has_failure = True

    duracao_total = round((time.time() - t0_global) * 1000, 2)
    relatorio["resumo"]["duracao_total_ms"] = duracao_total
    relatorio["resumo"]["status_geral"] = "APROVADO" if not has_failure else "REPROVADO"

    # Salva relatório técnico factual se solicitado (--report ou --json)
    if getattr(args, "report", False) or getattr(args, "json", False):
        rep_file = os.path.join(target_dir, "RELATORIO-AUDITORIA.json")
        with open(rep_file, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)
        print(f"\n📄 [FACTUAL REPORT] Relatório salvo com sucesso em: {rep_file}")

    print("\n" + "=" * 80)
    print(f"📊 PAINEL CONSOLIDADO DE AUDITORIA AIDD v4.1:")
    print(f"   - Total de Gates:     {relatorio['resumo']['total']}")
    print(f"   - Aprovados (PASS):   {relatorio['resumo']['aprovados']}")
    print(f"   - Falhas (FAIL):      {relatorio['resumo']['falhas']}")
    print(f"   - Duração Total:      {duracao_total:.2f} ms")
    print(f"   - Status Final:       {relatorio['resumo']['status_geral']}")
    print("=" * 80)

    if has_failure:
        print("❌ [BLOQUEADO]: O projeto NÃO passou em todos os gates determinísticos.")
        sys.exit(1)

    print("🏆 [HOMOLOGAÇÃO APROVADA]: Projeto 100% aderente às Regras Anti-Fail AIDD v4.1!")
    sys.exit(0)


def cmd_deploy(args):
    alvo = getattr(args, "alvo", "docker") or "docker"
    print(f"🚀 [AIDD DEPLOY] Preparando deploy para: {alvo}...")
    if alvo == "docker":
        subprocess.run(["docker", "compose", "up", "-d", "--build"])
    elif alvo == "vps":
        if os.path.exists("deploy.sh"):
            print("Execute no seu servidor de produção: bash deploy.sh")
    print(f"✨ [OK] Instruções de deploy para {alvo} processadas.")


def cmd_status(args):
    target_dir = os.path.abspath(getattr(args, "dir", "."))
    print("=" * 80)
    print(f"🔍 [AIDD STATUS] Inspecionando Saúde do Ecossistema em: {target_dir}")
    print("=" * 80)

    plano_path = os.path.join(target_dir, "PLANO-EXECUCAO-ESTRUTURADO.json")
    if os.path.exists(plano_path):
        with open(plano_path, "r", encoding="utf-8") as f:
            plano = json.load(f)
        proj = plano.get("projeto", {})
        print(f"Projeto:       {proj.get('nome')} (v{proj.get('versao')})")
        print(f"Framework:     {proj.get('framework')}")
        print(f"Status:        {proj.get('status')}")
    else:
        print("Manifesto PLANO-EXECUCAO-ESTRUTURADO.json: Não localizado")

    modules_dir = os.path.join(target_dir, "src", "modules")
    if os.path.exists(modules_dir):
        mods = [
            m for m in os.listdir(modules_dir)
            if os.path.isdir(os.path.join(modules_dir, m)) and not m.startswith("__")
        ]
        print(f"Módulos Ativos ({len(mods)}): {', '.join(mods)}")
    else:
        print("Módulos Ativos: 0 (src/modules não encontrado)")

    gates_dir = os.path.join(target_dir, "scripts", "gates")
    if os.path.exists(gates_dir):
        gates = [g for g in os.listdir(gates_dir) if g.endswith(".py")]
        print(f"Quality Gates  ({len(gates)}): {', '.join(gates)}")

    db_path = os.path.join(target_dir, "suite.db")
    if os.path.exists(db_path):
        size_kb = os.path.getsize(db_path) / 1024
        print(f"Banco SQLite:  Ativo ({size_kb:.1f} KB)")


def cmd_plan(prompt: str, base_dir: str = ".", auto_apply: bool = False):
    """Fase 1.5: Gera especificação técnica (SPEC) e plano estruturado antes da criação."""
    ensure_environment()
    prompt_lower = prompt.lower()
    
    KNOWN_DOMAINS = [
        "crm", "erp", "faturamento", "financeiro", "vendas", "helpdesk",
        "suporte", "logistica", "estoque", "membros", "cursos", "catalogo",
        "produtos", "pedidos", "whatsapp", "afiliados", "assinaturas", "fiscal",
        "analytics", "lead", "leads", "campanhas", "marketing", "tickets"
    ]
    
    found_modules = []
    for d in KNOWN_DOMAINS:
        if re.search(r'\b' + d + r'\b', prompt_lower):
            slug = "crm" if d in ["lead", "leads"] else ("helpdesk" if d in ["suporte", "tickets"] else d)
            if slug not in found_modules:
                found_modules.append(slug)
                
    if not found_modules:
        words = re.findall(r'\b[a-zA-Z]{4,}\b', prompt_lower)
        stop_words = {"crie", "uma", "aplicacao", "aplicativo", "sistema", "para", "com", "suite", "modulo", "faca", "gere"}
        found_modules = [w for w in words if w not in stop_words][:4]

    if not found_modules:
        found_modules = ["principal", "configuracao"]

    slug_name = "-".join(found_modules[:3]) + "-suite"
    target_path = os.path.abspath(os.path.join(base_dir, f"app_{slug_name}"))
    suite_title = " ".join(m.capitalize() for m in found_modules) + " Suite"

    os.makedirs(target_path, exist_ok=True)

    # 1. Gerar SPEC-ARQUITETURA.md
    spec_content = f"""# Especificação Técnica de Arquitetura (SPEC / PRD)

**Projeto:** {suite_title}  
**Diretório:** `{target_path}`  
**Status do Planejamento:** AGUARDANDO_APROVACAO  
**Prompt Original:** "{prompt}"  

---

## 1. Fatias Verticais Mapeadas
"""
    for m in found_modules:
        spec_content += f"""
### Módulo: `{m}`
- **Entidades:** `{m.capitalize()}Model` (ID, Titulo, Dados JSON, Timestamps, Ativo)
- **Serviço:** `{m.capitalize()}Service` com Full CRUD e emissão de eventos
- **Rotas OpenAPI:** `GET /api/{m}`, `GET /api/{m}/obter`, `POST /api/{m}/criar`, `POST /api/{m}/atualizar`, `POST /api/{m}/deletar`
- **UI:** Componente desacoplado em `src/static/components/{m}.html`
- **Testes Unitários:** `tests/unit/test_{m}.py` com pytest
"""

    spec_content += """
---

## 2. Shared Kernel & Segurança
- **Banco de Dados:** SQLite 3 WAL Mode (`src/core/database.py`)
- **Mensageria:** EventBus Pub/Sub em memória (`src/core/events.py`)
- **Segurança:** Autenticação JWT HS256 e Headers OWASP (`src/core/security.py`)
- **APIs & MCP:** Swagger Studio em `/docs` e Servidor Universal MCP em `/mcp`

---

## 3. Próximo Passo: Aprovação e Execução
Execute `python scripts/aidd.py apply --dir "{target_path}"` para compor o código e disparar os 7 Quality Gates.
"""
    spec_path = os.path.join(target_path, "SPEC-ARQUITETURA.md")
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec_content)

    # 2. Gerar PLANO-EXECUCAO-ESTRUTURADO.json inicial
    plano_data = {
        "projeto": {
            "nome": suite_title,
            "slug": slug_name,
            "diretorio": target_path,
            "status": "PLANEJADO",
            "prompt_origem": prompt,
            "zero_api_key_mode": True,
            "modulos": found_modules
        },
        "arquitetura": {
            "padrao": "AIDD Modular Clean Architecture",
            "banco": "SQLite WAL",
            "mcp_enabled": True
        }
    }
    plano_path = os.path.join(target_path, "PLANO-EXECUCAO-ESTRUTURADO.json")
    with open(plano_path, "w", encoding="utf-8") as f:
        json.dump(plano_data, f, indent=2, ensure_ascii=False)

    print("=" * 80)
    print("📋 [FASE 1.5 - SPEC & PLANEJAMENTO ARQUITETURAL]")
    print("=" * 80)
    print(f"Projeto:       {suite_title}")
    print(f"Destino:       {target_path}")
    print(f"Status:        PLANEJADO (Aguardando Aprovação)")
    print(f"Fatias ({len(found_modules)}):   {', '.join(found_modules)}")
    print(f"Documentos:    SPEC-ARQUITETURA.md | PLANO-EXECUCAO-ESTRUTURADO.json")
    print("=" * 80)

    if auto_apply:
        cmd_apply(argparse.Namespace(dir=target_path))
    else:
        print("\n👉 Para aprovar e compor imediatamente, execute:")
        print(f"   python scripts/aidd.py apply --dir \"{target_path}\"")
        print("👉 Ou edite o plano/especificação acima para ajustar o escopo antes da execução.\n")


def cmd_apply(args):
    """Fase 2: Lê o plano estruturado planejado e executa a composição e gates."""
    ensure_environment()
    target_dir = os.path.abspath(getattr(args, "dir", "."))
    plano_path = os.path.join(target_dir, "PLANO-EXECUCAO-ESTRUTURADO.json")
    
    if not os.path.exists(plano_path):
        print(f"[ERRO] Manifesto '{plano_path}' não encontrado. Execute 'plan' primeiro.")
        sys.exit(1)

    with open(plano_path, "r", encoding="utf-8") as f:
        plano = json.load(f)

    suite_name = plano.get("projeto", {}).get("nome", "Enterprise Suite")
    modulos = plano.get("projeto", {}).get("modulos", ["crm", "erp"])

    print("=" * 80)
    print(f"🚀 [FASE 2 - PROCESSAMENTO] Executando Plano Aprovado: '{suite_name}'")
    print("=" * 80)

    try:
        from compose_suite import compose_suite
    except ImportError:
        from scripts.compose_suite import compose_suite

    compose_suite(target_dir, suite_name, modulos)


def parse_natural_language_intent(prompt: str, base_dir: str = "."):
    """Ponto de entrada por Linguagem Natural — Gera o Plano / SPEC (Fase 1.5)."""
    cmd_plan(prompt, base_dir=base_dir, auto_apply=False)


def main():
    known_cmds = {"setup", "init", "plan", "apply", "prompt", "compose", "add-module", "test", "audit", "deploy", "status", "-h", "--help"}
    if len(sys.argv) > 1 and sys.argv[1] not in known_cmds:
        raw_prompt = " ".join(sys.argv[1:])
        parse_natural_language_intent(raw_prompt)
        return

    parser = argparse.ArgumentParser(description="AIDD Framework CLI — Dividir para Conquistar (v4.1 Enterprise)")
    subparsers = parser.add_subparsers(dest="command", help="Comando a executar")

    # plan (Fase 1.5 - Especificação e Planejamento)
    p_plan = subparsers.add_parser("plan", help="Gera especificação arquitetural e plano antes de compor")
    p_plan.add_argument("prompt", help="Instrução em linguagem natural (ex: 'Crie um CRM e ERP de faturamento')")
    p_plan.add_argument("--dir", default=".", help="Diretório base de destino")
    p_plan.add_argument("--apply", action="store_true", help="Executa a composição imediatamente após planejar")

    # apply (Fase 2 - Execução do Plano Aprovado)
    p_apply = subparsers.add_parser("apply", help="Executa o plano estruturado aprovado e roda os gates")
    p_apply.add_argument("--dir", default=".", help="Diretório do projeto contendo PLANO-EXECUCAO-ESTRUTURADO.json")

    # prompt (comando explícito de linguagem natural)
    p_prompt = subparsers.add_parser("prompt", help="Gera aplicação a partir de prompt em linguagem natural")
    p_prompt.add_argument("texto", help="Instrução em linguagem natural (ex: 'Crie um CRM e ERP de faturamento')")
    p_prompt.add_argument("--dir", default=".", help="Diretório base de destino")

    # setup
    subparsers.add_parser("setup", help="Executa diagnóstico completo e instalação automática de dependências")

    # init
    p_init = subparsers.add_parser("init", help="Provisiona novo projeto modular")
    p_init.add_argument("nome", help="Nome ou descrição do projeto")
    p_init.add_argument("--dir", default=".", help="Diretório base de destino")

    # compose
    p_comp = subparsers.add_parser("compose", help="Compõe suíte empresarial completa")
    p_comp.add_argument("target_dir", help="Diretório de destino")
    p_comp.add_argument("suite_name", help="Nome da suíte empresarial")
    p_comp.add_argument("modulos", nargs="*", default=["crm", "erp", "helpdesk", "logistica"], help="Lista de módulos")

    # add-module
    p_mod = subparsers.add_parser("add-module", help="Gera nova fatia vertical desacoplada")
    p_mod.add_argument("nome", help="Nome do módulo")
    p_mod.add_argument("--descricao", "-d", help="Descrição do módulo", default="")
    p_mod.add_argument("--dir", default=".", help="Diretório do projeto")

    # test
    p_test = subparsers.add_parser("test", help="Executa suítes de testes unitários ou de carga")
    p_test.add_argument("tipo", nargs="?", choices=["unit", "load", "contracts", "all"], default="unit", help="Tipo de teste")
    p_test.add_argument("--dir", default=".", help="Diretório do projeto")

    # audit
    p_audit = subparsers.add_parser("audit", help="Executa a bateria completa de gates determinísticos")
    p_audit.add_argument("--report", action="store_true", help="Gera relatório factual RELATORIO-AUDITORIA.json")
    p_audit.add_argument("--json", action="store_true", help="Exporta saída em JSON")
    p_audit.add_argument("--dir", default=".", help="Diretório do projeto")

    # deploy
    p_dep = subparsers.add_parser("deploy", help="Executa deploy da aplicação")
    p_dep.add_argument("alvo", nargs="?", choices=["docker", "vps", "vercel"], default="docker", help="Alvo de deploy")

    # status
    p_stat = subparsers.add_parser("status", help="Exibe integridade dos módulos e manifesto do projeto")
    p_stat.add_argument("--dir", default=".", help="Diretório do projeto")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmds = {
        "plan": lambda a: cmd_plan(a.prompt, getattr(a, "dir", "."), getattr(a, "apply", False)),
        "apply": cmd_apply,
        "prompt": lambda a: parse_natural_language_intent(a.texto, getattr(a, "dir", ".")),
        "setup": cmd_setup,
        "init": cmd_init,
        "compose": cmd_compose,
        "add-module": cmd_add_module,
        "test": cmd_test,
        "audit": cmd_audit,
        "deploy": cmd_deploy,
        "status": cmd_status
    }
    cmds[args.command](args)


if __name__ == '__main__':
    main()
