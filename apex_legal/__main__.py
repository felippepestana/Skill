"""
APEX-LEGAL PERFORMANCE — Entry point
=====================================
Uso:
  python -m apex_legal                    # FastAPI (padrão)
  python -m apex_legal api               # FastAPI explícito
  python -m apex_legal ui                # Interface Gradio (legado)
  python -m apex_legal adduser ...       # Gerenciar usuários (delega ao analista_processual)
"""

import sys


def main() -> None:
    args = sys.argv[1:]
    comando = args[0] if args else "api"

    if comando in ("api", "server", "serve"):
        host = "0.0.0.0"
        port = 8000
        reload = "--reload" in args
        for a in args:
            if a.startswith("--host="):
                host = a.split("=", 1)[1]
            if a.startswith("--port="):
                port = int(a.split("=", 1)[1])
        from apex_legal.core.api import iniciar
        print("=" * 60)
        print("⚖️  APEX-LEGAL PERFORMANCE — API v2.0")
        print(f"   http://{host}:{port}  |  docs: /docs")
        print("=" * 60)
        iniciar(host=host, port=port, reload=reload)

    elif comando == "ui":
        # Delega para a UI Gradio do analista_processual (legado)
        from analista_processual.__main__ import main as _main_gradio
        sys.argv = [sys.argv[0]] + args[1:]
        _main_gradio()

    else:
        # Outros comandos (adduser, listar, etc.) → delega ao analista_processual
        from analista_processual.__main__ import main as _main_cli
        _main_cli()


if __name__ == "__main__":
    main()
