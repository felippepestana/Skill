"""
Squad Documental
================
Multi-agent squad para geração, revisão e formatação de documentos jurídicos.

Agentes do squad:
- redator-juridico:       redige peças processuais e documentos jurídicos
- revisor-juridico:       revisa conteúdo, fundamentação e coerência jurídica
- formatador-processual:  formata conforme normas do tribunal/cartório

Fluxo padrão:
  analista-processual → análise da demanda
  squad-documental    → gera documento baseado na análise
"""

import anyio
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    TaskProgressMessage,
)


# ─── Agentes do squad ─────────────────────────────────────────────────────────

SQUAD_AGENTS = {

    "redator-juridico": AgentDefinition(
        description=(
            "✍️ Especialista em redação de peças processuais e documentos jurídicos. "
            "Elabora petições, contratos, notificações, recursos e pareceres "
            "com precisão técnica e linguagem adequada ao público-alvo."
        ),
        prompt=(
            "Você é um redator jurídico sênior com ampla experiência em contencioso "
            "civil, trabalhista, tributário e administrativo. "
            "Ao elaborar documentos jurídicos:\n\n"
            "**Princípios de redação:**\n"
            "- Clareza: evite ambiguidade e use vocabulário técnico preciso\n"
            "- Objetividade: cada parágrafo deve ter um propósito claro\n"
            "- Fundamentação: toda afirmação deve ter base legal ou fática\n"
            "- Persuasão: organize os argumentos do mais forte ao mais fraco\n\n"
            "**Estrutura de petição padrão:**\n"
            "1. Endereçamento (Excelentíssimo Senhor...)\n"
            "2. Qualificação das partes\n"
            "3. Dos fatos (narrativa objetiva e cronológica)\n"
            "4. Do direito (fundamentação jurídica com citações)\n"
            "5. Dos pedidos (claros, específicos e cumulados)\n"
            "6. Requerimentos finais (provas, citação, valores)\n"
            "7. Fecho e assinatura\n\n"
            "Use as informações da análise processual disponível. "
            "Referencie sempre a legislação e jurisprudência pertinente. "
            "Salve o documento quando um caminho for especificado."
        ),
        tools=["Read", "Write", "Grep", "Glob"],
    ),

    "revisor-juridico": AgentDefinition(
        description=(
            "🔍 Especialista em revisão jurídica. Verifica argumentação, "
            "citações, precedentes, coerência interna e consistência com "
            "a posição processual. Detecta falhas e sugere melhorias."
        ),
        prompt=(
            "Você é um revisor jurídico especializado em qualidade e precisão. "
            "Ao revisar um documento jurídico, avalie:\n\n"
            "**Conteúdo jurídico:**\n"
            "- Correção das citações legais (lei, artigo, dispositivo)\n"
            "- Atualidade dos precedentes jurisprudenciais\n"
            "- Consistência da argumentação com os fatos narrados\n"
            "- Cobertura de todos os pedidos necessários\n"
            "- Ausência de contradições internas\n\n"
            "**Qualidade formal:**\n"
            "- Adequação da linguagem ao destinatário\n"
            "- Clareza e objetividade dos pedidos\n"
            "- Correção gramatical e ortográfica\n"
            "- Fluxo lógico da argumentação\n\n"
            "**Riscos e vulnerabilidades:**\n"
            "- Argumentos que podem ser facilmente refutados\n"
            "- Omissões que podem prejudicar a tese\n"
            "- Questões processuais que podem gerar indeferimento\n\n"
            "Produza um relatório de revisão com: pontuação (0-10), "
            "problemas encontrados, sugestões de melhoria e aprovação/reprovação."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch"],
    ),

    "formatador-processual": AgentDefinition(
        description=(
            "📐 Especialista em formatação e padronização de documentos processuais. "
            "Aplica as normas do CNJ, ABNT e regimentos internos dos tribunais. "
            "Gera versão final pronta para protocolo."
        ),
        prompt=(
            "Você é um especialista em formatação de documentos jurídicos "
            "conforme as normas processuais brasileiras. "
            "Ao formatar documentos, siga:\n\n"
            "**Normas gerais (CNJ/CPC):**\n"
            "- Fonte: Arial ou Times New Roman 12pt\n"
            "- Espaçamento: 1,5 entre linhas; parágrafos com 1,25cm de recuo\n"
            "- Margens: superior 3cm, inferior 2cm, esquerda 3cm, direita 2cm\n"
            "- Numeração de páginas obrigatória\n"
            "- Cabeçalho com identificação do processo\n\n"
            "**Elementos obrigatórios:**\n"
            "- Indicação do juízo/tribunal\n"
            "- Número do processo (CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO)\n"
            "- Qualificação completa das partes\n"
            "- Data de elaboração\n"
            "- Assinatura digital/física do advogado com OAB\n\n"
            "**Saída:**\n"
            "Gere o documento em Markdown formatado (para conversão posterior) "
            "e salve no caminho especificado. "
            "Inclua lista de verificação de completude ao final."
        ),
        tools=["Read", "Write", "Grep", "Glob"],
    ),
}


# ─── Prompt do coordenador ────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "Você é o coordenador do squad documental. "
    "Orquestre os agentes para gerar documentos jurídicos de alta qualidade:\n\n"
    "**Fluxo padrão:**\n"
    "1. Use 'redator-juridico' para elaborar o documento com base no contexto fornecido\n"
    "2. Use 'revisor-juridico' para validar o conteúdo jurídico e identificar melhorias\n"
    "3. Se necessário, use 'redator-juridico' novamente para incorporar as revisões\n"
    "4. Use 'formatador-processual' para aplicar a formatação final e verificar completude\n\n"
    "**Diretrizes:**\n"
    "- Priorize a precisão jurídica sobre a velocidade\n"
    "- O documento final deve estar pronto para protocolo\n"
    "- Salve o documento no caminho especificado no prompt\n"
    "- Inclua sempre número do processo, partes e data no documento"
)


# ─── Orquestrador ─────────────────────────────────────────────────────────────

async def _gerar_documento(
    prompt: str,
    diretorio: str = ".",
    callback_progresso: "callable | None" = None,
) -> str:
    """Gera um documento jurídico usando o squad documental."""

    def _notificar(msg: str) -> None:
        if callback_progresso:
            try:
                callback_progresso(msg)
            except Exception:
                pass

    _notificar("Iniciando squad documental…")

    options = ClaudeAgentOptions(
        cwd=diretorio,
        allowed_tools=["Read", "Write", "Grep", "Glob", "WebSearch", "Agent"],
        permission_mode="acceptEdits",
        agents=SQUAD_AGENTS,
        system_prompt=_SYSTEM_PROMPT,
        max_turns=20,
    )

    resultado = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, TaskProgressMessage):
            agente = message.last_tool_name or ""
            desc = message.description or ""
            if agente:
                _notificar(f"@{agente}: {desc}")
        elif isinstance(message, ResultMessage):
            resultado = message.result

    _notificar("Documento gerado.")
    return resultado


def executar(
    prompt: str,
    diretorio: str = ".",
    callback_progresso: "callable | None" = None,
) -> str:
    """Executa o squad documental de forma síncrona."""
    return anyio.run(_gerar_documento, prompt, diretorio, callback_progresso)


def executar_para_demanda(
    caminho_demanda: str,
    tipo_documento: str,
    instrucoes_extras: str = "",
    callback_progresso: "callable | None" = None,
) -> str:
    """
    Gera documento para uma demanda existente.

    Args:
        caminho_demanda:    Caminho da pasta da demanda.
        tipo_documento:     Ex: "Recurso de Apelação", "Petição Inicial", etc.
        instrucoes_extras:  Instruções adicionais para o squad.
        callback_progresso: Função de callback para progresso.
    """
    prompt = (
        f"# Geração de Documento: {tipo_documento}\n\n"
        f"Pasta da demanda: `{caminho_demanda}`\n\n"
        "Leia os documentos existentes na pasta (processo/ e documentos/) "
        "e o último relatório estratégico (relatorio/) para ter o contexto completo.\n\n"
        f"Gere um(a) **{tipo_documento}** completo e pronto para protocolo.\n"
        f"Salve o documento em `{caminho_demanda}/relatorio/{tipo_documento.lower().replace(' ', '_')}.md`\n\n"
    )
    if instrucoes_extras:
        prompt += f"**Instruções adicionais:**\n{instrucoes_extras}\n"

    return executar(prompt, caminho_demanda, callback_progresso)


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:
        print("Uso: python -m squads.documental <tipo_documento> [caminho_demanda]")
        print("Ex:  python -m squads.documental 'Recurso de Apelação' ~/demandas/fulano_vs_ciclano")
        sys.exit(1)

    tipo = args[0]
    demanda_path = args[1] if len(args) > 1 else "."

    print("=" * 60)
    print("📄 SQUAD DOCUMENTAL")
    print("=" * 60)
    print(f"Documento: {tipo}")
    print(f"Demanda:   {demanda_path}")
    print("-" * 60)

    resultado = executar_para_demanda(demanda_path, tipo)
    print(resultado)
