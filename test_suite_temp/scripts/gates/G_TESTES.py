import os, sys, subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def testar():
    print("[GATE G_TESTES v4.1] Executando bateria de testes unitários com pytest...")
    
    test_dir = os.path.join("tests", "unit")
    if not os.path.exists(test_dir):
        print(f"[FAIL] ❌ Diretório de testes ausente: {test_dir}")
        sys.exit(1)
        
    test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
    if not test_files:
        print(f"[FAIL] ❌ Nenhum arquivo de teste encontrado em {test_dir}. Cobertura zero é estritamente proibida.")
        sys.exit(1)
        
    print(f"[*] {len(test_files)} arquivo(s) de teste localizados. Executando pytest...")
    
    cmd = [sys.executable, "-m", "pytest", "-v", test_dir]
    res = subprocess.run(cmd, capture_output=True, text=True)
    
    print(res.stdout)
    if res.stderr:
        print(res.stderr)
        
    if res.returncode != 0:
        print("\n[FAIL] ❌ BLOQUEIO DE QUALIDADE: Falhas detectadas na suíte de testes unitários!")
        sys.exit(res.returncode)
        
    print("[OK] SUCESSO: Todos os testes unitários passaram com 100% de sucesso (exit 0)!")
    sys.exit(0)

if __name__ == '__main__':
    testar()
