"""
CLI do AIOX Master — Orion
==========================
Executa o orquestrador mestre de todos os agentes e squads.

Uso:
  python -m aiox_master <tarefa>
  python -m aiox_master revisar <demanda>
  python -m aiox_master arquitetura <demanda>
  python -m aiox_master ux <demanda>
  python -m aiox_master db <demanda>

Exemplos:
  python -m aiox_master "Analise a arquitetura do projeto e sugira melhorias"
  python -m aiox_master revisar ~/demandas/fulano_vs_ciclano
  python -m aiox_master ux "Revisar interface do analista processual"
"""

import sys
from pathlib import Path
from . import executar


_COMANDOS_ESPECIAIS = {
    "revisar": (
        "Realize uma revisão completa da demanda jurídica em: {arg}\n\n"
        "Delegue ao @analyst para análise de contexto e ao @qa para "
        "revisão da qualidade. Em seguida, use @analista-processual para "
        "uma nova análise atualizada se necessário."
    ),
    "arquitetura": (
        "Analise a arquitetura do projeto em: {arg}\n\n"
        "Delegue ao @architect (Aria) para mapear a arquitetura atual, "
        "identificar problemas e propor melhorias. "
        "Depois delegue ao @dev (Dex) para estimar o esforço de implementação."
    ),
    "ux": (
        "Realize uma auditoria completa de UX/UI para: {arg}\n\n"
        "Delegue ao @ux-design-expert (Uma) para:\n"
        "1. Pesquisa de usabilidade e mapeamento de fluxos\n"
        "2. Identificação de problemas de acessibilidade (WCAG)\n"
        "3. Proposta de melhorias de design system\n"
        "4. Wireframes de alto nível para as melhorias sugeridas"
    ),
    "db": (
        "Analise e otimize o banco de dados / estrutura de armazenamento em: {arg}\n\n"
        "Delegue ao @data-engineer (Dara) para:\n"
        "1. Auditar o schema atual\n"
        "2. Identificar N+1 queries e gargalos de performance\n"
        "3. Propor otimizações e índices\n"
        "4. Planejar migrações seguras"
    ),
    "codigo": (
        "Realize uma revisão completa do código em: {arg}\n\n"
        "Delegue ao @qa (Quinn) para auditoria de qualidade e segurança, "
        "ao @dev (Dex) para identificar dívida técnica e melhorias, "
        "e ao @architect (Aria) para verificar aderência à arquitetura."
    ),
    "squad": (
        "Projete e crie um novo squad especializado para: {arg}\n\n"
        "Delegue ao @squad-creator (Craft) para:\n"
        "1. Definir os agentes necessários e suas responsabilidades\n"
        "2. Criar as definições de agentes (AgentDefinition)\n"
        "3. Definir o prompt do coordenador\n"
        "4. Validar o schema do squad"
    ),
}


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(
            "Uso: python -m aiox_master <tarefa>\n\n"
            "Atalhos:\n"
            + "\n".join(
                f"  {cmd:12s} <alvo>  — {desc.splitlines()[0]}"
                for cmd, desc in _COMANDOS_ESPECIAIS.items()
            )
            + "\n\nExemplos:\n"
            "  python -m aiox_master 'Analise o projeto e sugira melhorias'\n"
            "  python -m aiox_master ux 'interface do analista processual'"
        )
        return

    cmd = args[0].lower()
    alvo = " ".join(args[1:]) if len(args) > 1 else "."

    if cmd in _COMANDOS_ESPECIAIS:
        tarefa = _COMANDOS_ESPECIAIS[cmd].format(arg=alvo)
    else:
        tarefa = " ".join(args)

    print("=" * 70)
    print("👑 AIOX MASTER — Orion")
    print("=" * 70)
    print(f"Tarefa: {tarefa[:120]}…" if len(tarefa) > 120 else f"Tarefa: {tarefa}")
    print("-" * 70)

    resultado = executar(tarefa, diretorio=alvo if Path(alvo).is_dir() else ".")
    print(resultado)


main()
