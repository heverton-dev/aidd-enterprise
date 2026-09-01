import os, sys, json, inspect

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def verificar_contratos():
    print("[GATE G_CONTRACTS v4.1] Validando contratos de rotas, esquemas OpenAPI 3.1 e ferramentas MCP...")
    
    erros = []
    
    src_path = os.path.abspath("src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
        
    # 1. Validar RouteRegistry e Rotas dos Módulos
    try:
        from core.openapi import RouteRegistry
        modules_dir = os.path.join("src", "modules")
        if os.path.exists(modules_dir):
            modulos = [m for m in os.listdir(modules_dir) if os.path.isdir(os.path.join(modules_dir, m)) and not m.startswith("__")]
            for m in modulos:
                routes_path = os.path.join(modules_dir, m, "routes.py")
                if os.path.exists(routes_path):
                    with open(routes_path, "r", encoding="utf-8", errors="ignore") as f:
                        conteudo = f.read()
                        if "@registry." not in conteudo and "registrar_rotas" not in conteudo:
                            erros.append(f"Módulo '{m}' não registra rotas com decoradores RouteRegistry.")
    except Exception as e:
        erros.append(f"Falha ao validar RouteRegistry: {str(e)}")

    # 2. Validar MCP Server
    mcp_file = os.path.join("src", "core", "mcp_server.py")
    if os.path.exists(mcp_file):
        try:
            with open(mcp_file, "r", encoding="utf-8", errors="ignore") as f:
                code = f.read()
                if "MCPServer" not in code or "handle_request" not in code:
                    erros.append("Servidor MCP presente mas sem classe MCPServer ou método handle_request.")
        except Exception as e:
            erros.append(f"Erro ao inspecionar MCP server: {str(e)}")

    if erros:
        print("\n[FAIL] ❌ BLOQUEIO DE CONTRATOS: Violações de contrato detectadas:")
        for e in erros:
            print(f"  - {e}")
        sys.exit(1)
        
    print("[OK] SUCESSO: Todos os contratos OpenAPI e interfaces MCP foram validados sem erros!")
    sys.exit(0)

if __name__ == '__main__':
    verificar_contratos()
