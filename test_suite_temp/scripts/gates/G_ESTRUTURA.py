import os, sys, json, re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def verificar():
    print("[GATE G_ESTRUTURA v4.1] Validando conformidade arquitetural e fatias verticais...")
    erros = []
    
    # 1. Verificar diretórios estruturais obrigatórios
    dirs_obrigatorios = [
        os.path.join("src", "core"),
        os.path.join("src", "modules"),
        os.path.join("src", "static"),
        os.path.join("tests", "unit")
    ]
    for d in dirs_obrigatorios:
        if not os.path.exists(d) or not os.path.isdir(d):
            erros.append(f"Diretório estrutural ausente: {d}")

    # 2. Verificar arquivos essenciais de governança
    arquivos_governanca = [
        "requirements.txt",
        "PLANO-EXECUCAO-ESTRUTURADO.json"
    ]
    for a in arquivos_governanca:
        if not os.path.exists(a):
            erros.append(f"Arquivo de governança ausente na raiz: {a}")

    # 3. Validar Fatias Verticais (src/modules)
    modules_dir = os.path.join("src", "modules")
    if os.path.exists(modules_dir):
        modulos = [
            m for m in os.listdir(modules_dir)
            if os.path.isdir(os.path.join(modules_dir, m)) and not m.startswith("__")
        ]
        if not modulos:
            erros.append("Nenhum módulo vertical encontrado em 'src/modules/'. Monólitos acoplados sem módulos são estritamente proibidos.")
        else:
            for m in modulos:
                m_path = os.path.join(modules_dir, m)
                for req_file in ["models.py", "services.py", "routes.py"]:
                    f_full = os.path.join(m_path, req_file)
                    if not os.path.exists(f_full):
                        erros.append(f"Módulo '{m}' incompleto: arquivo ausente '{req_file}'")
                        
                # Verificar se o teste unitário correspondente existe
                test_file = os.path.join("tests", "unit", f"test_{m}.py")
                if not os.path.exists(test_file):
                    erros.append(f"Módulo '{m}' sem teste unitário correspondente: '{test_file}'")

    # 4. Validar Core Kernel
    core_dir = os.path.join("src", "core")
    if os.path.exists(core_dir):
        for kf in ["database.py", "events.py", "openapi.py"]:
            kf_full = os.path.join(core_dir, kf)
            if not os.path.exists(kf_full):
                erros.append(f"Arquivo essencial do Core Kernel ausente: {kf_full}")

    # 5. Resultado
    if erros:
        print("\n[FAIL] ❌ BLOQUEIO DE ESTRUTURA: Foram detectadas não-conformidades graves:")
        for e in erros:
            print(f"  - {e}")
        print("\nRegra de Ouro: Todo projeto AIDD v4+ exige fatias verticais isoladas em src/modules/ com testes unitários.")
        sys.exit(1)
        
    print("[OK] SUCESSO: Layout arquitetural e fatias verticais 100% em conformidade com o padrão AIDD v4.1!")
    sys.exit(0)

if __name__ == '__main__':
    verificar()
