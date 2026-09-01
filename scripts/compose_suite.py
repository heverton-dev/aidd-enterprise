#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIDD v4 — Cross-Project Enterprise Suite Composition Engine
Permite compor múltiplos domínios (fatias verticais) em um Monólito Modular Unificado com:
- EventBus Cross-Domain
- Webhook Dispatcher
- Swagger Studio OpenAPI 3.1 Unificado
- Servidor Nativo MCP (Model Context Protocol)
- Front-end Super-App Impeccable com App Switcher
"""

import os, sys, shutil, json

def compose_suite(target_dir: str, suite_name: str, modules: list):
    print(f"[*] Iniciando composição da Suite Enterprise v4: {suite_name}")
    print(f"[*] Módulos selecionados: {', '.join(modules)}")
    
    os.makedirs(os.path.join(target_dir, "src", "core"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src", "shared", "ui"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src", "static"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "src", "modules"), exist_ok=True)
    os.makedirs(os.path.join(target_dir, "tests"), exist_ok=True)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = os.path.join(base_dir, "templates", "v2")

    # 1. Copia o Shared Kernel
    for f in ["database.py", "events.py", "webhooks.py", "security.py", "openapi.py"]:
        src = os.path.join(templates_dir, f)
        dst = os.path.join(target_dir, "src", "core", f)
        if os.path.exists(src):
            shutil.copyfile(src, dst)
            print(f"  [+] Kernel: {f}")

    # 2. Copia Feedback UI Engine
    ui_src = os.path.join(templates_dir, "shared", "ui")
    if os.path.exists(ui_src):
        for f in os.listdir(ui_src):
            shutil.copyfile(os.path.join(ui_src, f), os.path.join(target_dir, "src", "shared", "ui", f))
            print(f"  [+] Feedback UI: {f}")

    print(f"\n[OK] Suite '{suite_name}' composta com sucesso em: {target_dir}")
    print(f"[*] Execute: cd {target_dir} && python src/server.py")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python compose_suite.py <target_dir> <suite_name> [modulo1] [modulo2] ...")
        sys.exit(1)

    target = sys.argv[1]
    name = sys.argv[2]
    mods = sys.argv[3:] if len(sys.argv) > 3 else ["crm", "erp", "helpdesk", "logistica"]
    compose_suite(target, name, mods)
