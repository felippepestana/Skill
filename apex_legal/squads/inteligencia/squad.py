"""
Squad Inteligência — APEX-LEGAL PERFORMANCE
============================================
Monitoramento contínuo, jurimetria e alertas estratégicos.

Agentes:
- jurimétra:        análise estatística de padrões jurisprudenciais
- monitor-processual: monitoramento de prazos, publicações DJe, movimentos
- analista-risco:   scoring de risco com histórico comparativo
"""

from __future__ import annotations

import anyio
from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    ResultMessage,
    TaskProgressMessage,
    query,
)


INTEL_AGENTS = {

    "jurimétra": AgentDefinition(
        description=(
            "Especialista em jurimetria — análise quantitativa de padrões "
            "jurisprudenciais, taxas de êxito por tese e tribunal, tempo médio "
            "de tramitação e probabilidades com base em dados históricos."
        ),
        prompt=(
            "Você é um jurimetrista especializado em análise estatística do direito. "
            "Para cada demanda, forneça:\n\n"
            "**1. Taxa de Êxito por Tese:**\n"
            "- Busque dados sobre o percentual de sucesso da tese principal em tribunais similares\n"
            "- Compare com a média nacional e regional\n"
            "- Identifique variações por câmara/turma específica\n\n"
            "**2. Tempo Médio de Tramitação:**\n"
            "- Prazo médio até sentença neste tipo de ação no tribunal\n"
            "- Prazo médio até acórdão em 2ª instância\n"
            "- Probabilidade de reforma em grau recursal\n\n"
            "**3. Padrões de Decisão:**\n"
            "- Perfil decisório do juízo (se identificável por jurisprudência pública)\n"
            "- Tendências recentes do tribunal na matéria\n"
            "- Impacto de teses repetitivas (art. 1.036 CPC)\n\n"
            "Use WebSearch para buscar dados em DataJud (datajud.cnj.jus.br), "
            "Jusbrasil, e relatórios estatísticos dos tribunais."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),

    "monitor-processual": AgentDefinition(
        description=(
            "Especialista em monitoramento processual. Acompanha prazos fatais, "
            "publicações no DJe, movimentos processuais e gera alertas de urgência."
        ),
        prompt=(
            "Você é um monitor processual especializado em gestão de prazos e alertas. "
            "Para cada demanda, verifique e reporte:\n\n"
            "**1. Prazos Críticos:**\n"
            "- Prazos fatais nos próximos 30 dias (com datas exatas)\n"
            "- Prazos para recursos (15 dias apelação, 15 dias agravo de instrumento)\n"
            "- Prazos para manifestações e impugnações\n\n"
            "**2. Publicações DJe:**\n"
            "- Verificar últimas publicações relacionadas à demanda\n"
            "- Identificar intimações e despachos pendentes\n"
            "- Confirmar ciência das partes\n\n"
            "**3. Movimentos Processuais:**\n"
            "- Status atual do processo (em andamento, concluso, aguardando)\n"
            "- Próxima audiência ou sessão de julgamento (se houver)\n"
            "- Perícias ou diligências em curso\n\n"
            "**4. Alertas de Urgência (classificação):**\n"
            "- 🔴 CRÍTICO: prazo fatal em até 5 dias\n"
            "- 🟡 URGENTE: prazo fatal em 6-15 dias\n"
            "- 🟢 ATENÇÃO: prazo fatal em 16-30 dias\n\n"
            "Gere um painel de alertas ordenado por urgência."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),

    "analista-risco": AgentDefinition(
        description=(
            "Especialista em scoring e análise de risco jurídico. "
            "Combina dados de jurimetria, análise estratégica e histórico "
            "da demanda para gerar um score de risco e probabilidades atualizadas."
        ),
        prompt=(
            "Você é um analista de risco jurídico que produz scoring quantificado. "
            "Com base em todos os dados disponíveis da demanda, gere:\n\n"
            "**Score de Risco (0-100):**\n"
            "- 0-30: Baixo risco (alta probabilidade de êxito)\n"
            "- 31-60: Risco moderado (resultado incerto)\n"
            "- 61-80: Risco elevado (probabilidade de derrota)\n"
            "- 81-100: Risco crítico (iminente sucumbência)\n\n"
            "**Componentes do Score:**\n"
            "1. Qualidade probatória (0-25 pts)\n"
            "2. Solidez jurídica da tese (0-25 pts)\n"
            "3. Histórico jurisprudencial (0-25 pts)\n"
            "4. Riscos processuais e formais (0-25 pts)\n\n"
            "**Probabilidades Atualizadas:**\n"
            "- P(êxito total): X%\n"
            "- P(êxito parcial): Y%\n"
            "- P(derrota): Z%\n"
            "- P(acordo favorável): W%\n\n"
            "**Fatores que mais impactam o score:**\n"
            "Liste os 3 maiores fatores de risco e os 3 maiores fatores de êxito.\n\n"
            "Seja objetivo e baseie o scoring em dados verificáveis."
        ),
        tools=["Read", "Grep", "Glob"],
    ),
}

_SYSTEM_PROMPT_INTEL = (
    "Você é o coordenador do squad de inteligência jurídica APEX-LEGAL. "
    "Orquestre os agentes para uma análise de inteligência completa:\n\n"
    "1. **jurimétra** — coleta dados estatísticos e padrões jurisprudenciais\n"
    "2. **monitor-processual** — verifica prazos, publicações e gera alertas\n"
    "3. **analista-risco** — consolida tudo em score de risco e probabilidades\n\n"
    "Produza um relatório de inteligência conciso com dashboard de riscos e alertas prioritários."
)


async def _executar_intel(
    ws: "DemandaWorkspace",
    callback_progresso: "callable | None" = None,
) -> str:
    """Executa análise de inteligência sobre uma demanda."""
    from analista_processual.workspace import DemandaWorkspace

    def _notificar(msg: str) -> None:
        if callback_progresso:
            try:
                callback_progresso(msg)
            except Exception:
                pass

    ultimo_rel = ws.ler_ultimo_relatorio()
    instrucoes = ws.ler_instrucoes()

    secoes = [
        f"# Análise de Inteligência — {ws.nome_original()}",
        "",
        "Realize análise de inteligência completa desta demanda: jurimetria, "
        "monitoramento de prazos e scoring de risco.",
        "",
    ]
    if ultimo_rel:
        secoes += [
            "## Relatório Estratégico (base)",
            "",
            ultimo_rel[:5000] + ("\n\n[truncado]" if len(ultimo_rel) > 5000 else ""),
            "",
        ]
    if instrucoes:
        secoes += ["## Instruções", "", instrucoes, ""]

    prompt_final = "\n".join(secoes)

    options = ClaudeAgentOptions(
        cwd=str(ws.caminho),
        allowed_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch", "Agent"],
        permission_mode="acceptEdits",
        agents=INTEL_AGENTS,
        system_prompt=_SYSTEM_PROMPT_INTEL,
        max_turns=20,
    )

    resultado = ""
    async for message in query(prompt=prompt_final, options=options):
        if isinstance(message, TaskProgressMessage):
            desc = message.description or ""
            agente = message.last_tool_name or ""
            if agente and desc:
                _notificar(f"@{agente}: {desc}")
        elif isinstance(message, ResultMessage):
            resultado = message.result

    return resultado


def executar(
    ws: "DemandaWorkspace",
    callback_progresso: "callable | None" = None,
) -> str:
    """Executa o squad de inteligência de forma síncrona."""
    return anyio.run(_executar_intel, ws, callback_progresso)
