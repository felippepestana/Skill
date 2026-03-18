"""
Squad Analista-Processual
=========================
Conjunto de agentes especializados em análise de processos.

Agentes:
  - Coordenador       : orquestra o squad e consolida os resultados
  - Mapeador          : mapeia etapas, entradas e saídas do processo
  - Avaliador         : avalia conformidade, riscos e gargalos
  - Documentador      : gera o relatório final estruturado

Uso:
    python squad.py "Descreva o processo que deseja analisar"
    python squad.py  # lê o processo de stdin
"""

from __future__ import annotations

import sys
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage


# ---------------------------------------------------------------------------
# Definições dos subagentes
# ---------------------------------------------------------------------------

MAPEADOR = AgentDefinition(
    description=(
        "Especialista em mapeamento de processos. "
        "Identifica todas as etapas, atores, entradas, saídas e decisões "
        "de um processo e os organiza em um fluxo claro e sequencial."
    ),
    prompt=(
        "Você é um analista de processos sênior especializado em mapeamento. "
        "Dado um processo descrito pelo usuário:\n"
        "1. Liste todas as etapas na ordem correta.\n"
        "2. Para cada etapa, indique: ator responsável, entradas necessárias, "
        "saídas produzidas e critérios de conclusão.\n"
        "3. Identifique pontos de decisão (gateways) e ramificações.\n"
        "4. Represente o fluxo em formato textual estruturado (pseudo-BPMN)."
    ),
    tools=["Read", "Glob"],
)

AVALIADOR = AgentDefinition(
    description=(
        "Especialista em avaliação de processos. "
        "Analisa conformidade, riscos, gargalos e oportunidades de melhoria "
        "em processos mapeados."
    ),
    prompt=(
        "Você é um analista de processos sênior especializado em avaliação. "
        "Dado o mapeamento de um processo:\n"
        "1. Identifique gargalos e pontos de ineficiência.\n"
        "2. Avalie riscos operacionais e de conformidade (compliance).\n"
        "3. Verifique se há etapas redundantes ou sem valor agregado.\n"
        "4. Liste oportunidades de melhoria priorizadas por impacto.\n"
        "5. Atribua uma pontuação de maturidade processual (0–5) com justificativa."
    ),
    tools=["Read", "Glob"],
)

DOCUMENTADOR = AgentDefinition(
    description=(
        "Especialista em documentação de processos. "
        "Consolida análises em relatórios claros, estruturados e acionáveis."
    ),
    prompt=(
        "Você é um analista de processos sênior especializado em documentação. "
        "Dadas as análises de mapeamento e avaliação:\n"
        "1. Produza um relatório executivo com sumário, achados-chave e "
        "recomendações.\n"
        "2. Inclua uma tabela de etapas do processo (etapa | ator | SLA sugerido).\n"
        "3. Liste os Top-5 riscos com probabilidade, impacto e plano de mitigação.\n"
        "4. Descreva um roadmap de melhorias em 3 horizontes (imediato / 90 dias / "
        "longo prazo).\n"
        "Formate o relatório em Markdown bem estruturado."
    ),
    tools=["Read", "Write", "Glob"],
)


# ---------------------------------------------------------------------------
# Prompt do coordenador
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
Você é o coordenador do Squad Analista-Processual.
Seu papel é orquestrar os subagentes para entregar uma análise completa de processos.

Fluxo de trabalho obrigatório:
1. Acione o agente **mapeador** para mapear o processo fornecido pelo usuário.
2. Passe o mapeamento ao agente **avaliador** para identificar riscos e melhorias.
3. Passe mapeamento + avaliação ao agente **documentador** para gerar o relatório final.
4. Apresente o relatório consolidado ao usuário.

Seja objetivo, estruturado e garanta que cada subagente receba contexto suficiente.
""".strip()


# ---------------------------------------------------------------------------
# Runner principal
# ---------------------------------------------------------------------------

async def run_squad(processo: str) -> None:
    print("\n=== Squad Analista-Processual ===\n")
    print(f"Processo recebido:\n{processo}\n")
    print("Iniciando análise...\n")

    options = ClaudeAgentOptions(
        model="claude-opus-4-6",
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Write", "Glob", "Agent"],
        agents={
            "mapeador": MAPEADOR,
            "avaliador": AVALIADOR,
            "documentador": DOCUMENTADOR,
        },
        max_turns=30,
        thinking={"type": "adaptive"},
    )

    async for message in query(prompt=processo, options=options):
        if isinstance(message, ResultMessage):
            print("\n=== Relatório Final ===\n")
            print(message.result)
            print(f"\n[Stop reason: {message.stop_reason}]")


def main() -> None:
    if len(sys.argv) > 1:
        processo = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        processo = sys.stdin.read().strip()
    else:
        print("Descreva o processo que deseja analisar (Ctrl+D para finalizar):")
        processo = sys.stdin.read().strip()

    if not processo:
        print("Erro: nenhum processo fornecido.", file=sys.stderr)
        sys.exit(1)

    anyio.run(run_squad, processo)


if __name__ == "__main__":
    main()
