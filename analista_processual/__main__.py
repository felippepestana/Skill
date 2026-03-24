"""
CLI + Launcher — Analista Processual
======================================
Sem argumentos → abre a interface web.

Comandos disponíveis:
  ui [--host H] [--port P] [--no-auth]  Abre a interface web (padrão)
  nova   <nome>                          Cria nova demanda
  listar                                 Lista todas as demandas
  info   <nome>                          Exibe detalhes de uma demanda
  analisar <nome> [instrução]            Analisa via CLI (sem UI)
  delta  <nome> [instrução]              Análise delta (só novos docs)
  instrucao <nome> <texto>               Adiciona instrução permanente
  consultar <nome> <pergunta>            Pergunta pontual sobre a demanda
  adduser <username> <password> <email>  Cadastra novo usuário
  listusers                              Lista todos os usuários
  setplan <username> <plano>             Altera plano (free/pro/enterprise)

Exemplos:
  python -m analista_processual
  python -m analista_processual --host 0.0.0.0 --port 7860
  python -m analista_processual --no-auth           (modo local sem login)
  python -m analista_processual nova "Fulano vs Ciclano 2024"
  python -m analista_processual analisar "Fulano vs Ciclano" "foque na prescrição"
  python -m analista_processual consultar "Fulano vs Ciclano" "quais são os riscos?"
  python -m analista_processual adduser joao senha123 joao@escritorio.com
  python -m analista_processual listusers
  python -m analista_processual setplan joao pro
"""

import sys
from pathlib import Path

from .workspace import criar_demanda, listar_demandas, obter_demanda, pasta_base
from .squad import executar_demanda, consultar_demanda
from . import auth as _auth


# ─── Helpers de saída ─────────────────────────────────────────────────────────

SEP = "─" * 60


def _titulo(texto: str) -> None:
    print(f"\n{SEP}\n  ⚖️  {texto}\n{SEP}")


def _ok(msg: str) -> None:
    print(f"✔  {msg}")


def _err(msg: str) -> None:
    print(f"✖  {msg}", file=sys.stderr)


# ─── Comandos CLI ─────────────────────────────────────────────────────────────

def cmd_ui(host: str = "127.0.0.1", port: int = 7860, com_auth: bool = True) -> None:
    from .ui import iniciar
    iniciar(host=host, port=port, abrir_browser=(host in ("127.0.0.1", "localhost")), com_auth=com_auth)


def cmd_nova(nome: str) -> None:
    _titulo("Nova Demanda")
    try:
        ws = criar_demanda(nome)
        _ok(f"Demanda criada: {ws.caminho}")
        print(f"\n  1. Copie peças processuais para:  {ws.pasta_processo}/")
        print(f"  2. Copie outros documentos para:  {ws.pasta_documentos}/")
        print(f"  3. Edite as instruções em:        {ws.arquivo_instrucoes}")
        print(f"\n  Analisar via UI:   python -m analista_processual")
        print(f"  Analisar via CLI:  python -m analista_processual analisar \"{nome}\"")
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
        print("  Use: python -m analista_processual nova \"Nome da Demanda\"")
        return
    for ws in demandas:
        docs = ws.sincronizar_indice()
        analisados = sum(1 for d in docs if d.analisado)
        ultima = ws.ultima_analise() or "—"
        print(f"  • {ws.nome_original()}")
        print(f"    {len(docs)} doc(s) | {analisados} analisados | última análise: {ultima}")
    print()


def cmd_info(nome: str) -> None:
    _titulo("Informações da Demanda")
    try:
        ws = obter_demanda(nome)
        print(ws.resumo())
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)


def cmd_analisar(nome: str, instrucao: str | None = None, delta: bool = False) -> None:
    _titulo(f"{'Análise Delta' if delta else 'Analisando'}: {nome}")
    try:
        ws = obter_demanda(nome)
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)

    print(ws.resumo())
    print(SEP)

    docs = ws.sincronizar_indice()
    if not docs:
        _err(
            "Nenhum documento encontrado.\n"
            f"  Adicione arquivos em:\n"
            f"    {ws.pasta_processo}/\n"
            f"    {ws.pasta_documentos}/"
        )
        sys.exit(1)

    if instrucao:
        print(f"\nInstrução adicional: {instrucao}\n")

    def _progresso(msg: str) -> None:
        print(f"  → {msg}")

    resultado = executar_demanda(
        ws,
        instrucao_extra=instrucao,
        modo_delta=delta,
        callback_progresso=_progresso,
    )

    print(f"\n{SEP}")
    print(resultado)
    print(SEP)

    ultimo_rel = ws.ultimo_relatorio()
    if ultimo_rel:
        _ok(f"Relatório salvo: {ultimo_rel}")


def cmd_instrucao(nome: str, texto: str) -> None:
    _titulo("Adicionar Instrução")
    try:
        ws = obter_demanda(nome)
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)
    ws.adicionar_instrucao(texto)
    _ok(f"Instrução adicionada: {ws.arquivo_instrucoes}")


def cmd_consultar(nome: str, pergunta: str) -> None:
    _titulo(f"Consultando: {nome}")
    try:
        ws = obter_demanda(nome)
    except FileNotFoundError as e:
        _err(str(e))
        sys.exit(1)
    print(f"Pergunta: {pergunta}\n{SEP}\n")
    resposta = consultar_demanda(ws, pergunta)
    print(resposta)
    print(SEP)


def cmd_adduser(username: str, password: str, email: str, plano: str = "free") -> None:
    _titulo("Cadastrar Usuário")
    try:
        _auth.registrar_usuario(username, password, email, plano)
        _ok(f"Usuário '{username}' ({email}) cadastrado com plano '{plano}'.")
        print(f"\n  Banco: {_auth._db_path()}")
    except ValueError as e:
        _err(str(e))
        sys.exit(1)


def cmd_listusers() -> None:
    _titulo("Usuários Cadastrados")
    usuarios = _auth.listar_usuarios()
    if not usuarios:
        print("  Nenhum usuário cadastrado.")
        print(f"\n  Cadastre com: python -m analista_processual adduser <user> <senha> <email>")
        return
    print(f"  {'Username':<20} {'E-mail':<30} {'Plano':<12} {'Ativo'}")
    print(f"  {'-'*20} {'-'*30} {'-'*12} {'-'*5}")
    for u in usuarios:
        ativo = "✔" if u["ativo"] else "✖"
        print(f"  {u['username']:<20} {u['email']:<30} {u['plano']:<12} {ativo}")
    print()


def cmd_setplan(username: str, plano: str) -> None:
    _titulo("Alterar Plano")
    try:
        _auth.alterar_plano(username, plano)
        _ok(f"Plano de '{username}' alterado para '{plano}'.")
    except ValueError as e:
        _err(str(e))
        sys.exit(1)


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def _uso() -> None:
    print(__doc__)
    sys.exit(1)


def main() -> None:
    args = sys.argv[1:]

    # Flags globais: --host, --port, --no-auth
    host = "127.0.0.1"
    port = 7860
    com_auth = True
    args_filtrados = []
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            try:
                port = int(args[i + 1])
            except ValueError:
                _err(f"Porta inválida: {args[i + 1]}")
                sys.exit(1)
            i += 2
        elif args[i] == "--no-auth":
            com_auth = False
            i += 1
        else:
            args_filtrados.append(args[i])
            i += 1
    args = args_filtrados

    # Sem argumentos → UI web
    if not args or args[0].lower() in ("ui", "web"):
        cmd_ui(host=host, port=port, com_auth=com_auth)
        return

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
            _err("Informe o nome da demanda.")
            _uso()
        cmd_info(args[1])

    elif cmd == "analisar":
        if len(args) < 2:
            _err("Informe o nome da demanda.")
            _uso()
        instrucao = args[2] if len(args) >= 3 else None
        cmd_analisar(args[1], instrucao, delta=False)

    elif cmd == "delta":
        if len(args) < 2:
            _err("Informe o nome da demanda.")
            _uso()
        instrucao = args[2] if len(args) >= 3 else None
        cmd_analisar(args[1], instrucao, delta=True)

    elif cmd == "instrucao":
        if len(args) < 3:
            _err("Uso: instrucao \"nome\" \"texto\"")
            _uso()
        cmd_instrucao(args[1], " ".join(args[2:]))

    elif cmd == "consultar":
        if len(args) < 3:
            _err("Uso: consultar \"nome\" \"pergunta\"")
            _uso()
        cmd_consultar(args[1], " ".join(args[2:]))

    elif cmd == "adduser":
        if len(args) < 4:
            _err("Uso: adduser <username> <senha> <email> [plano]")
            _uso()
        plano = args[4] if len(args) >= 5 else "free"
        cmd_adduser(args[1], args[2], args[3], plano)

    elif cmd == "listusers":
        cmd_listusers()

    elif cmd == "setplan":
        if len(args) < 3:
            _err("Uso: setplan <username> <plano>")
            _uso()
        cmd_setplan(args[1], args[2])

    else:
        _err(f"Comando desconhecido: '{cmd}'")
        _uso()


if __name__ == "__main__":
    main()
