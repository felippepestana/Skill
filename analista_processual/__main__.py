"""
CLI do Analista Processual
===========================
Uso:
  python -m analista_processual nova "Nome da Demanda"
  python -m analista_processual listar
  python -m analista_processual info "Nome da Demanda"
  python -m analista_processual analisar "Nome da Demanda"
  python -m analista_processual analisar "Nome da Demanda" "instrução pontual"
  python -m analista_processual instrucao "Nome da Demanda" "texto da instrução"
"""

import sys
from pathlib import Path

from .workspace import criar_demanda, listar_demandas, obter_demanda, pasta_base
from .squad import executar_demanda


# ─── Helpers de saída ─────────────────────────────────────────────────────────

SEP = "─" * 60


def _titulo(texto: str) -> None:
    print(f"\n{SEP}")
    print(f"  ⚖️  {texto}")
    print(SEP)


def _ok(msg: str) -> None:
    print(f"✔  {msg}")


def _err(msg: str) -> None:
    print(f"✖  {msg}", file=sys.stderr)


# ─── Comandos ─────────────────────────────────────────────────────────────────

def cmd_nova(nome: str) -> None:
    _titulo("Nova Demanda")
    try:
        ws = criar_demanda(nome)
        _ok(f"Demanda criada: {ws.caminho}")
        print()
        print("Próximos passos:")
        print(f"  1. Copie as peças processuais para:  {ws.pasta_processo}/")
        print(f"  2. Copie outros documentos para:     {ws.pasta_documentos}/")
        print(f"  3. Edite as instruções em:           {ws.arquivo_instrucoes}")
        print(f"  4. Execute a análise:")
        print(f"     python -m analista_processual analisar \"{nome}\"")
    except FileExistsError as e:
        _err(str(e))
        sys.exit(1)


def cmd_listar() -> None:
    _titulo("Demandas")
    base = pasta_base()
    print(f"Pasta base: {base}\n")
    demandas = listar_demandas()
    if not demandas:
        print("  Nenhuma demanda encontrada.")
        print(f"  Use: python -m analista_processual nova \"Nome da Demanda\"")
        return
    for ws in demandas:
        docs_total = len(ws.documentos_processo()) + len(ws.outros_documentos())
        ultima = ws.ultima_analise() or "—"
        print(f"  • {ws.nome}")
        print(f"    documentos: {docs_total}   última análise: {ultima}")
    print()


def cmd_info(nome: str) -> None:
    _titulo("Informações da Demanda")
    try:
        ws = obter_demanda(nome)
        print(ws.resumo())
        print()
        ultimo_rel = ws.ultimo_relatorio()
        if ultimo_rel:
            print(f"Último relatório: {ultimo_rel}")
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)


def cmd_analisar(nome: str, instrucao_extra: str | None = None) -> None:
    _titulo(f"Analisando: {nome}")
    try:
        ws = obter_demanda(nome)
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)

    print(ws.resumo())
    print(SEP)

    pdfs = ws.todos_pdfs()
    textos = ws.todos_textos()
    total_docs = len(pdfs) + len(textos)

    if total_docs == 0:
        _err(
            "Nenhum documento encontrado na demanda.\n"
            f"  Adicione arquivos em:\n"
            f"    {ws.pasta_processo}/\n"
            f"    {ws.pasta_documentos}/"
        )
        sys.exit(1)

    if instrucao_extra:
        print(f"\nInstrução adicional: {instrucao_extra}\n")

    print(f"\nIniciando análise de {total_docs} documento(s)…\n")

    resultado = executar_demanda(ws, instrucao_extra=instrucao_extra)

    print(SEP)
    print(resultado)
    print(SEP)

    ultimo_rel = ws.ultimo_relatorio()
    if ultimo_rel:
        _ok(f"Relatório salvo em: {ultimo_rel}")


def cmd_instrucao(nome: str, texto: str) -> None:
    _titulo("Adicionar Instrução")
    try:
        ws = obter_demanda(nome)
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)
    ws.adicionar_instrucao(texto)
    _ok(f"Instrução adicionada em: {ws.arquivo_instrucoes}")
    print()
    print("Para analisar com a nova instrução:")
    print(f"  python -m analista_processual analisar \"{nome}\"")


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def _uso() -> None:
    print(__doc__)
    sys.exit(1)


def main() -> None:
    args = sys.argv[1:]

    if not args:
        _uso()

    cmd = args[0].lower()

    if cmd == "nova":
        if len(args) < 2:
            _err("Informe o nome da demanda.")
            _uso()
        cmd_nova(" ".join(args[1:]))

    elif cmd == "listar":
        cmd_listar()

    elif cmd == "info":
        if len(args) < 2:
            _err("Informe o nome ou slug da demanda.")
            _uso()
        cmd_info(args[1])

    elif cmd == "analisar":
        if len(args) < 2:
            _err("Informe o nome ou slug da demanda.")
            _uso()
        nome = args[1]
        instrucao = args[2] if len(args) >= 3 else None
        cmd_analisar(nome, instrucao)

    elif cmd == "instrucao":
        if len(args) < 3:
            _err("Uso: instrucao \"nome da demanda\" \"texto da instrução\"")
            _uso()
        cmd_instrucao(args[1], " ".join(args[2:]))

    else:
        _err(f"Comando desconhecido: '{cmd}'")
        _uso()


if __name__ == "__main__":
    main()
