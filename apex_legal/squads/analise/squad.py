"""
Squad Analise — APEX-LEGAL PERFORMANCE
=======================================
Expande o squad analista-processual com 3 agentes especializados adicionais:
- especialista-cnj:   normas CNJ, resoluções, BNMP, metas tribunais
- tributarista:       direito tributário federal/estadual, PGFN, SEFAZ
- trabalhista:        CLT, TST, NR-17, prazos trabalhistas, FGTS

Total: 8 agentes especializados.
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

# Importa os 5 agentes base + infraestrutura do pacote original
from analista_processual.squad import (
    SQUAD_AGENTS as _AGENTES_BASE,
    executar_demanda,
    consultar_demanda,
    _analisar_demanda,
    _consultar_demanda,
    _SYSTEM_PROMPT_SQUAD,
    _SYSTEM_PROMPT_CHAT,
    FONTES_JURIDICAS,
)
from analista_processual.workspace import DemandaWorkspace


# ─── Novos agentes especializados ─────────────────────────────────────────────

_AGENTES_NOVOS = {

    "especialista-cnj": AgentDefinition(
        description=(
            "Especialista em normas e resoluções do CNJ (Conselho Nacional de Justiça). "
            "Verifica conformidade com metas do CNJ, resoluções vigentes, BNMP "
            "(Banco Nacional de Monitoramento de Prisões) e prazos regulatórios."
        ),
        prompt=(
            "Você é um especialista nas normas do Conselho Nacional de Justiça (CNJ). "
            "Para cada demanda analisada, verifique e informe:\n\n"
            "**1. Resoluções CNJ Aplicáveis:**\n"
            "- Identifique resoluções CNJ relevantes ao caso (ex: Res. 185, 354, 372, 465)\n"
            "- Verifique conformidade com as normas de tramitação eletrônica (PJe, e-SAJ)\n"
            "- Indique resoluções sobre gestão de prazos e metas dos tribunais\n\n"
            "**2. Metas do CNJ:**\n"
            "- Meta 1: julgamento dos processos distribuídos no corrente ano\n"
            "- Meta 2: julgamento de processos mais antigos\n"
            "- Impacto das metas no andamento da demanda\n\n"
            "**3. BNMP (se aplicável):**\n"
            "- Verificar conformidade em casos com privação de liberdade\n"
            "- Prazos de prisão preventiva e revisão obrigatória\n\n"
            "**4. Precedentes Vinculantes:**\n"
            "- IRDRs (Incidentes de Resolução de Demandas Repetitivas) aplicáveis\n"
            "- IACs (Incidentes de Assunção de Competência)\n"
            "- Recursos repetitivos (Art. 1.036 CPC)\n\n"
            "Busque informações atualizadas em cnj.jus.br e no PJe do tribunal competente."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),

    "tributarista": AgentDefinition(
        description=(
            "Especialista em direito tributário federal e estadual. "
            "Analisa obrigações fiscais, autos de infração, execuções fiscais, "
            "parcelamentos, PGFN, SEFAZ, SIMPLES Nacional e contencioso administrativo."
        ),
        prompt=(
            "Você é um tributarista com especialização em contencioso fiscal. "
            "Ao analisar demandas tributárias, forneça:\n\n"
            "**1. Identificação do Crédito Tributário:**\n"
            "- Natureza do tributo (IRPJ, CSLL, PIS, COFINS, ICMS, ISS, etc.)\n"
            "- Competência (federal, estadual, municipal)\n"
            "- Período de apuração e valores (principal + multa + juros Selic)\n\n"
            "**2. Prescrição e Decadência:**\n"
            "- Prazo decadencial (5 anos do fato gerador — art. 150/173 CTN)\n"
            "- Prazo prescricional (5 anos do lançamento — art. 174 CTN)\n"
            "- Causas de interrupção e suspensão\n\n"
            "**3. Defesas Disponíveis:**\n"
            "- Administrativas: impugnação, recursos ao CARF, câmaras de julgamento\n"
            "- Judiciais: ação anulatória, mandado de segurança, exceção de pré-executividade\n"
            "- Garantias do juízo: depósito, fiança, seguro-garantia\n\n"
            "**4. Jurisprudência Tributária:**\n"
            "- Súmulas do STJ e STF aplicáveis\n"
            "- Decisões do CARF e CSRF relevantes\n"
            "- Parecer PGFN/SEI se houver dispensa de contestar\n\n"
            "Fontes: receita.economia.gov.br, pgfn.gov.br, carf.economia.gov.br, "
            "stj.jus.br (tributário), stf.jus.br (constitucional tributário)."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),

    "trabalhista": AgentDefinition(
        description=(
            "Especialista em direito do trabalho e processo trabalhista. "
            "Analisa vínculos empregatícios, verbas rescisórias, FGTS, "
            "NRs de segurança, prazos CLT/TST e execução trabalhista."
        ),
        prompt=(
            "Você é um especialista em direito do trabalho com foco em contencioso. "
            "Para demandas trabalhistas, analise:\n\n"
            "**1. Vínculo e Direitos Básicos:**\n"
            "- Natureza do vínculo (CLT, terceirizado, PJ, autônomo, cooperado)\n"
            "- Verbas rescisórias devidas (13º, férias + 1/3, aviso prévio, FGTS + 40%)\n"
            "- Horas extras, adicional noturno, insalubridade, periculosidade\n\n"
            "**2. Prazos Trabalhistas:**\n"
            "- Prescrição bienal (2 anos da extinção) e quinquenal (5 anos retroativos)\n"
            "- Prazos para pagamento de verbas rescisórias (art. 477 CLT)\n"
            "- Prazo para homologação/quitação (art. 477, §6º CLT)\n\n"
            "**3. Jurisprudência TST:**\n"
            "- Súmulas TST aplicáveis (ex: Súm. 331 — terceirização; Súm. 437 — IRCT)\n"
            "- OJs (Orientações Jurisprudenciais) da SDI-1 e SDI-2\n"
            "- Precedentes normativos relevantes\n\n"
            "**4. Reforma Trabalhista (Lei 13.467/2017):**\n"
            "- Impacto nos direitos: teletrabalho, jornada 12x36, banco de horas\n"
            "- Prevalência do negociado sobre o legislado (art. 611-A e 611-B CLT)\n"
            "- Responsabilidade na terceirização irrestrita (art. 4º-A Lei 6.019/74)\n\n"
            "**5. Execução Trabalhista:**\n"
            "- Garantia do juízo (depósito recursal — art. 899 CLT)\n"
            "- Penhora online (BACENJUD / SISBAJUD)\n"
            "- Desconsideração da personalidade jurídica (art. 855-A CLT)\n\n"
            "Fontes: tst.jus.br, trt[nº].jus.br, planalto.gov.br (CLT atualizada)."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),
}

# ─── Squad completo: 8 agentes ─────────────────────────────────────────────────

SQUAD_AGENTS = {**_AGENTES_BASE, **_AGENTES_NOVOS}

_SYSTEM_PROMPT_APEX = (
    "Você é o coordenador do squad APEX-LEGAL PERFORMANCE (8 agentes especializados). "
    "Orquestre os agentes em ordem para uma análise jurídica completa e estratégica:\n\n"
    "1. **leitor-de-pecas** — extrai informações estruturadas de todos os documentos\n"
    "2. **pesquisador-juridico** — busca jurisprudência, legislação e doutrina (STF/STJ/TJs)\n"
    "3. **especialista-cnj** — verifica normas CNJ, resoluções, IRDRs e precedentes vinculantes\n"
    "4. **tributarista** — analisa aspectos tributários se houver créditos fiscais ou execuções\n"
    "5. **trabalhista** — analisa aspectos trabalhistas se houver vínculo/verbas envolvidos\n"
    "6. **estrategista-processual** — avalia riscos, oportunidades e projeta cenários com %\n"
    "7. **advogado-orientador** — define plano de ação prático com prazos e prioridades\n"
    "8. **relator-processual** — consolida tudo no relatório estratégico final (salva em arquivo)\n\n"
    "**Regras:**\n"
    "- Acione tributarista e trabalhista apenas se o caso envolver essas áreas\n"
    "- O relatório DEVE ser salvo no caminho especificado via ferramenta Write\n"
    "- Priorize instruções explícitas do usuário ao direcionar os agentes\n"
    "- O relator inclui sempre o bloco ```citacoes``` com rastreamento de fontes"
)


# ─── Funções públicas ──────────────────────────────────────────────────────────

async def _analisar_apex(
    ws: DemandaWorkspace,
    instrucao_extra: str | None = None,
    modo_delta: bool = False,
    callback_progresso: "callable | None" = None,
) -> str:
    """Análise com os 8 agentes APEX."""
    # Substituímos SQUAD_AGENTS e system_prompt na chamada interna
    # reutilizando toda a infraestrutura de _analisar_demanda
    from analista_processual.squad import (
        _extrair_pdfs_da_demanda,
        _montar_prompt_analise,
        _extrair_e_registrar_citacoes,
    )

    def _notificar(msg: str) -> None:
        if callback_progresso:
            try:
                callback_progresso(msg)
            except Exception:
                pass

    _notificar("Sincronizando índice de documentos…")
    ws.sincronizar_indice()

    if modo_delta:
        novos = ws.documentos_novos()
        if not novos:
            return "Nenhum documento novo ou modificado. Análise delta dispensada."
        _notificar(f"Modo delta: {len(novos)} documento(s) novo(s) ou modificado(s).")

    _notificar("Extraindo PDFs…")
    contexto_pdfs, _ = await _extrair_pdfs_da_demanda(ws, apenas_novos=modo_delta)

    caminho_relatorio = ws.novo_caminho_relatorio()
    prompt_final = _montar_prompt_analise(
        ws, instrucao_extra, contexto_pdfs, str(caminho_relatorio), modo_delta
    )

    _notificar("Iniciando análise APEX-LEGAL (8 agentes)…")
    options = ClaudeAgentOptions(
        cwd=str(ws.caminho),
        allowed_tools=["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch", "Agent"],
        permission_mode="acceptEdits",
        agents=SQUAD_AGENTS,
        system_prompt=_SYSTEM_PROMPT_APEX,
        max_turns=40,
    )

    resultado = ""
    async for message in query(prompt=prompt_final, options=options):
        if isinstance(message, TaskProgressMessage):
            agente = message.last_tool_name or ""
            desc = message.description or ""
            if agente and desc:
                _notificar(f"@{agente}: {desc}")
            elif agente:
                _notificar(f"@{agente} em execução…")
            elif desc:
                _notificar(desc)
        elif isinstance(message, ResultMessage):
            resultado = message.result

    ws.registrar_analise(str(caminho_relatorio))
    ws.marcar_todos_analisados()
    _extrair_e_registrar_citacoes(ws, caminho_relatorio, resultado)
    _notificar(f"Relatório salvo: {caminho_relatorio.name}")
    return resultado


def executar(
    prompt: str,
    diretorio: str = ".",
    pdfs: list[str] | None = None,
) -> str:
    """Executa o squad APEX (8 agentes) de forma síncrona para um prompt livre."""
    from analista_processual.squad import abrir_squad as _abrir
    # Para prompt livre, reutiliza a infraestrutura original com os 8 agentes
    import anyio as _anyio

    async def _run():
        options = ClaudeAgentOptions(
            cwd=diretorio,
            allowed_tools=["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch", "Agent"],
            permission_mode="acceptEdits",
            agents=SQUAD_AGENTS,
            system_prompt=_SYSTEM_PROMPT_APEX,
            max_turns=40,
        )
        resultado = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                resultado = message.result
        return resultado

    return _anyio.run(_run)


def executar_demanda_apex(
    ws: DemandaWorkspace,
    instrucao_extra: str | None = None,
    modo_delta: bool = False,
    callback_progresso: "callable | None" = None,
) -> str:
    """Executa análise APEX-LEGAL completa (8 agentes) de uma demanda."""
    return anyio.run(_analisar_apex, ws, instrucao_extra, modo_delta, callback_progresso)
