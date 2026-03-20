"""
AIOX Master Squad
=================
Orquestrador mestre que coordena múltiplos squads especializados.

O aiox-master é o agente principal que recebe tarefas de alto nível
e delega para os squads adequados conforme a necessidade.

Squads disponíveis:
- analista-processual: análise de processos jurídicos
"""

import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

from analista_processual.squad import SQUAD_AGENTS as ANALISTA_PROCESSUAL_AGENTS


# Agentes do squad analista-processual expostos para o aiox-master
_ANALISTA_PROCESSUAL_SQUAD = {
    f"analista-processual__{name}": agent
    for name, agent in ANALISTA_PROCESSUAL_AGENTS.items()
}

# Agente coordenador do squad analista-processual
_ANALISTA_PROCESSUAL_COORDENADOR = AgentDefinition(
    description=(
        "Coordenador do squad analista-processual. Orquestra os agentes "
        "leitor-de-pecas, pesquisador-juridico e relator-processual para realizar "
        "análise completa de processos jurídicos."
    ),
    prompt=(
        "Você é o coordenador do squad analista-processual. "
        "Orquestre os agentes especializados do seu squad para realizar "
        "uma análise jurídica completa: use 'analista-processual__leitor-de-pecas' "
        "para extrair informações dos documentos, "
        "'analista-processual__pesquisador-juridico' para fundamentação legal, "
        "e 'analista-processual__relator-processual' para consolidar o relatório. "
        "Retorne uma análise organizada e juridicamente fundamentada."
    ),
    tools=["Read", "Grep", "Glob", "Write", "Agent"],
)

# Todos os agentes disponíveis para o aiox-master
AIOX_MASTER_AGENTS = {
    "analista-processual": _ANALISTA_PROCESSUAL_COORDENADOR,
    **_ANALISTA_PROCESSUAL_SQUAD,
}


async def chamar_aiox_master(prompt: str, diretorio: str = ".") -> str:
    """
    Chama o aiox-master para executar uma tarefa complexa.

    O aiox-master analisa a tarefa e delega para os squads adequados.

    Args:
        prompt: Tarefa ou consulta a ser executada.
        diretorio: Diretório de trabalho.

    Returns:
        Resultado da execução orquestrada pelo aiox-master.
    """
    options = ClaudeAgentOptions(
        cwd=diretorio,
        allowed_tools=["Read", "Grep", "Glob", "Write", "Agent"],
        permission_mode="acceptEdits",
        agents=AIOX_MASTER_AGENTS,
        system_prompt=(
            "Você é o AIOX Master — o orquestrador mestre de todos os squads. "
            "Sua função é receber tarefas de alto nível, identificar quais squads "
            "e agentes são necessários, e coordenar a execução para entregar "
            "o melhor resultado possível. "
            "\n\nSquads disponíveis:\n"
            "- 'analista-processual': squad completo para análise jurídico-processual. "
            "  Seus sub-agentes são acessíveis diretamente como:\n"
            "  - 'analista-processual__leitor-de-pecas'\n"
            "  - 'analista-processual__pesquisador-juridico'\n"
            "  - 'analista-processual__relator-processual'\n"
            "\nPara tarefas jurídicas, delegue ao 'analista-processual'. "
            "Você pode chamar o squad inteiro ou agentes individuais conforme a necessidade. "
            "Sempre apresente resultados consolidados, claros e acionáveis."
        ),
        max_turns=30,
    )

    resultado = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            resultado = message.result

    return resultado


def executar(prompt: str, diretorio: str = ".") -> str:
    """Executa o aiox-master de forma síncrona."""
    return anyio.run(chamar_aiox_master, prompt, diretorio)


if __name__ == "__main__":
    import sys

    tarefa = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Apresente os squads disponíveis e suas capacidades."
    )

    print("=" * 60)
    print("AIOX MASTER")
    print("=" * 60)
    print(f"Tarefa: {tarefa}")
    print("-" * 60)

    resultado = executar(tarefa)
    print(resultado)
