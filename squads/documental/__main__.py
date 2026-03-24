"""CLI do squad documental."""

import sys
from . import executar, executar_para_demanda


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "Uso: python -m squads.documental <comando> [opções]\n\n"
            "Comandos:\n"
            "  gerar <tipo> [demanda]   — gera documento para demanda existente\n"
            "  prompt <texto>           — executa prompt livre no squad\n\n"
            "Exemplos:\n"
            "  python -m squads.documental gerar 'Recurso de Apelação' ~/demandas/caso_x\n"
            "  python -m squads.documental prompt 'Escreva uma petição de habeas corpus'"
        )
        return

    cmd = args[0].lower()

    if cmd == "gerar" and len(args) >= 2:
        tipo = args[1]
        caminho = args[2] if len(args) > 2 else "."
        print(f"📄 Gerando: {tipo}")
        resultado = executar_para_demanda(
            caminho, tipo,
            callback_progresso=lambda m: print(f"  ⟩ {m}"),
        )
        print("\n" + "=" * 60)
        print(resultado)

    elif cmd == "prompt" and len(args) >= 2:
        texto = " ".join(args[1:])
        print(f"📄 Prompt: {texto}")
        resultado = executar(
            texto,
            callback_progresso=lambda m: print(f"  ⟩ {m}"),
        )
        print("\n" + "=" * 60)
        print(resultado)

    else:
        print(f"Comando desconhecido: {cmd}", file=sys.stderr)
        sys.exit(1)


main()
