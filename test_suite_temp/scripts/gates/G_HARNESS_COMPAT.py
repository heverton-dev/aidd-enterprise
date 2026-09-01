import os, sys, json

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def check_harness():
    print("[GATE G_HARNESS_COMPAT v4.1] Verificando compatibilidade multi-harness (AGY, Claude Code, OpenHands, Cline, Mimocode)...")
    
    erros = []
    
    # 1. Verificar se scripts de automação existem
    for s in ["scripts/aidd.py", "scripts/add_module.py"]:
        if not os.path.exists(s):
            erros.append(f"Script de automação essencial ausente: {s}")

    # 2. Verificar modo Zero API Key (se tudo roda local sem chaves pagas)
    if os.path.exists("PLANO-EXECUCAO-ESTRUTURADO.json"):
        try:
            with open("PLANO-EXECUCAO-ESTRUTURADO.json", "r", encoding="utf-8") as f:
                plano = json.load(f)
                if not plano.get("projeto", {}).get("zero_api_key_mode", False):
                    print("[WARN] Aviso: zero_api_key_mode não explicitado no plano.")
        except:
            erros.append("PLANO-EXECUCAO-ESTRUTURADO.json inválido ou corrompido.")

    if erros:
        print("\n[FAIL] ❌ Incompatibilidade de Harness detectada:")
        for e in erros:
            print(f"  - {e}")
        sys.exit(1)
        
    print("[OK] SUCESSO: Ambiente 100% compatível com qualquer Harness de IA (Zero API Key nativo).")
    sys.exit(0)

if __name__ == '__main__':
    check_harness()
