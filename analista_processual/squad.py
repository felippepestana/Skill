"""
Squad Analista-Processual
=========================
Multi-agent squad para análise de processos jurídicos e documentos processuais.

Agentes do squad:
- analista-processual: coordenador geral, analisa o processo completo
- leitor-de-pecas: especializado em leitura e extração de informações de peças processuais
- pesquisador-juridico: pesquisa jurisprudência e legislação relevante
- relator-processual: gera relatórios e resumos do processo
"""

import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage


SQUAD_AGENTS = {
    "leitor-de-pecas": AgentDefinition(
        description=(
            "Especialista em leitura e extração de informações de peças processuais. "
            "Identifica partes, pedidos, fundamentos e datas em petições, despachos, "
            "sentenças e acórdãos."
        ),
        prompt=(
            "Você é um especialista em leitura de peças processuais. "
            "Ao analisar um documento, extraia: partes envolvidas, tipo de peça, "
            "data, pedidos principais, fundamentos jurídicos, e decisões relevantes. "
            "Apresente as informações de forma estruturada e objetiva."
        ),
        tools=["Read", "Grep"],
    ),
    "pesquisador-juridico": AgentDefinition(
        description=(
            "Especialista em pesquisa jurídica. Busca jurisprudência, legislação "
            "e doutrina relevantes para o caso em análise."
        ),
        prompt=(
            "Você é um pesquisador jurídico especializado. "
            "Para cada questão jurídica apresentada, identifique: legislação aplicável, "
            "jurisprudência relevante dos tribunais superiores, princípios jurídicos "
            "pertinentes, e posicionamentos doutrinários. "
            "Organize as referências por relevância e atualidade."
        ),
        tools=["Read", "Grep", "Glob"],
    ),
    "relator-processual": AgentDefinition(
        description=(
            "Especialista em elaboração de relatórios processuais. "
            "Consolida as análises e gera relatórios estruturados sobre o processo."
        ),
        prompt=(
            "Você é um relator processual experiente. "
            "Com base nas análises fornecidas, elabore relatórios claros e objetivos "
            "que incluam: resumo do processo, histórico processual, questões jurídicas "
            "identificadas, análise de mérito, e conclusões. "
            "Use linguagem técnica-jurídica precisa e formatação profissional."
        ),
        tools=["Read", "Write"],
    ),
}


async def abrir_squad(prompt: str, diretorio: str = ".") -> str:
    """
    Abre o squad analista-processual para analisar um processo.

    Args:
        prompt: Descrição da tarefa ou consulta processual a ser analisada.
        diretorio: Diretório de trabalho com os documentos do processo.

    Returns:
        Resultado da análise do squad.
    """
    options = ClaudeAgentOptions(
        cwd=diretorio,
        allowed_tools=["Read", "Grep", "Glob", "Write", "Agent"],
        permission_mode="acceptEdits",
        agents=SQUAD_AGENTS,
        system_prompt=(
            "Você é o coordenador do squad analista-processual. "
            "Seu papel é orquestrar os agentes especializados para realizar "
            "uma análise completa e precisa do processo jurídico. "
            "Utilize os agentes disponíveis conforme necessário: "
            "use o 'leitor-de-pecas' para extrair informações dos documentos, "
            "o 'pesquisador-juridico' para fundamentação legal, "
            "e o 'relator-processual' para consolidar o relatório final. "
            "Sempre apresente uma análise organizada, objetiva e juridicamente fundamentada."
        ),
        max_turns=20,
    )

    resultado = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            resultado = message.result

    return resultado


def executar(prompt: str, diretorio: str = ".") -> str:
    """Executa o squad analista-processual de forma síncrona."""
    return anyio.run(abrir_squad, prompt, diretorio)


if __name__ == "__main__":
    import sys

    tarefa = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Analise os documentos processuais disponíveis e gere um relatório completo "
        "com as principais informações, questões jurídicas e recomendações."
    )

    print("=" * 60)
    print("SQUAD ANALISTA-PROCESSUAL")
    print("=" * 60)
    print(f"Tarefa: {tarefa}")
    print("-" * 60)

    resultado = executar(tarefa)
    print(resultado)
