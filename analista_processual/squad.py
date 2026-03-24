"""
Squad Analista-Processual
=========================
Multi-agent squad para análise de processos jurídicos e documentos processuais.

Agentes do squad:
- leitor-de-pecas:      leitura e extração estruturada de peças processuais (suporta PDF)
- pesquisador-juridico: pesquisa online de jurisprudência, legislação e doutrina
- relator-processual:   consolida análises e gera relatórios técnico-jurídicos

Capacidades adicionais:
- Suporte a PDF via Files API (anthropic-beta: files-api-2025-04-14)
- Busca web de jurisprudência em STF, STJ, TJs e bases legais (LexML, JusBrasil, etc.)
- Workspace por demanda — pasta base com subpastas processo/, documentos/, relatorio/
"""

import os
import anyio
import anthropic
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ResultMessage,
    TaskProgressMessage,
)

from .workspace import DemandaWorkspace


# ─── Constantes ───────────────────────────────────────────────────────────────

FILES_API_BETA = "files-api-2025-04-14"

FONTES_JURIDICAS = [
    "stf.jus.br",       # Supremo Tribunal Federal
    "stj.jus.br",       # Superior Tribunal de Justiça
    "tst.jus.br",       # Tribunal Superior do Trabalho
    "lexml.gov.br",     # LexML — legislação federal e estadual
    "planalto.gov.br",  # Portal da Legislação Federal
    "jusbrasil.com.br", # JusBrasil — jurisprudência consolidada
    "conjur.com.br",    # Consultor Jurídico — doutrina e notícias
]


# ─── Helpers internos ─────────────────────────────────────────────────────────

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    """Retorna o cliente Anthropic compartilhado (lazy singleton)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _texto_da_resposta(message: anthropic.types.Message) -> str:
    """Extrai o texto de uma mensagem, ignorando blocos de thinking."""
    block = next((b for b in message.content if b.type == "text"), None)
    if block is None:
        raise ValueError("Resposta do modelo não contém bloco de texto.")
    return block.text


# ─── Agentes do squad ─────────────────────────────────────────────────────────

SQUAD_AGENTS = {

    "leitor-de-pecas": AgentDefinition(
        description=(
            "Especialista em leitura e extração de informações de peças processuais. "
            "Suporta arquivos de texto (.txt, .md) e PDFs. "
            "Identifica partes, pedidos, fundamentos e datas em petições, despachos, "
            "sentenças e acórdãos."
        ),
        prompt=(
            "Você é um especialista em leitura de peças processuais. "
            "Ao analisar um documento, extraia e estruture:\n"
            "- Tipo da peça (petição inicial, contestação, sentença, acórdão, etc.)\n"
            "- Partes envolvidas (autor, réu, terceiros, advogados, juízo)\n"
            "- Datas relevantes (distribuição, intimações, prazos, decisões)\n"
            "- Pedidos principais e subsidiários\n"
            "- Fundamentos jurídicos invocados\n"
            "- Decisões e determinações\n"
            "- Provas e documentos mencionados\n\n"
            "Para arquivos PDF, use a ferramenta Read — o sistema lida com a extração "
            "automaticamente. Apresente as informações de forma estruturada e objetiva."
        ),
        tools=["Read", "Grep", "Glob"],
    ),

    "pesquisador-juridico": AgentDefinition(
        description=(
            "Especialista em pesquisa jurídica online. Busca jurisprudência nos tribunais "
            "superiores (STF, STJ, TST), legislação federal e estadual, e doutrina relevante. "
            "Utiliza WebSearch e WebFetch para fontes atualizadas."
        ),
        prompt=(
            "Você é um pesquisador jurídico especializado com acesso à internet. "
            "Para cada questão jurídica apresentada, pesquise e compile:\n\n"
            "1. **Legislação aplicável** — leis, códigos, decretos e regulamentos pertinentes "
            "(busque em planalto.gov.br e lexml.gov.br)\n"
            "2. **Jurisprudência dos tribunais superiores** — STF (controle de constitucionalidade, "
            "repercussão geral), STJ (recurso especial, súmulas), TST (matéria trabalhista) "
            "(busque em stf.jus.br, stj.jus.br, tst.jus.br)\n"
            "3. **Jurisprudência dos TJs** — tribunais estaduais relevantes ao caso\n"
            "4. **Súmulas e enunciados** — vinculantes e persuasivos aplicáveis\n"
            "5. **Doutrina e princípios** — posicionamentos doutrinários atuais\n\n"
            f"Fontes prioritárias: {', '.join(FONTES_JURIDICAS)}\n\n"
            "Organize as referências por relevância, indicando sempre: tribunal/fonte, "
            "número do processo/lei/súmula, data e ementa/resumo. "
            "Priorize decisões recentes (últimos 5 anos) e jurisprudência consolidada."
        ),
        tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
    ),

    "relator-processual": AgentDefinition(
        description=(
            "Especialista em elaboração de relatórios processuais. "
            "Consolida as análises do leitor-de-pecas e pesquisador-juridico "
            "e gera relatórios técnico-jurídicos estruturados em Markdown "
            "com citações rastreadas por documento e página."
        ),
        prompt=(
            "Você é um relator processual experiente. "
            "Com base nas análises fornecidas, elabore um relatório completo que inclua:\n\n"
            "## Estrutura do Relatório\n\n"
            "1. **Identificação do Processo** — número, vara/tribunal, partes, advogados\n"
            "2. **Resumo Executivo** — síntese em até 5 linhas do caso\n"
            "3. **Histórico Processual** — cronologia dos atos processuais relevantes\n"
            "4. **Questões Jurídicas Identificadas** — teses principais e subsidiárias\n"
            "5. **Fundamentação Legal** — legislação e jurisprudência aplicável\n"
            "6. **Análise de Mérito** — pontos fortes, pontos fracos, riscos\n"
            "7. **Análise Estratégica** — riscos, oportunidades, cenários (otimista/realista/pessimista)\n"
            "8. **Orientações Práticas** — medidas urgentes, plano de ação, prazos críticos\n"
            "9. **Conclusões e Recomendações** — posicionamento técnico e próximos passos\n\n"
            "## Citações Rastreadas\n\n"
            "Ao final do relatório, inclua um bloco de citações no formato:\n\n"
            "```citacoes\n"
            "documento: nome_do_arquivo.pdf\n"
            "trecho: texto citado ou referenciado\n"
            "tipo: fundamento_legal|prova|precedente|fato\n"
            "---\n"
            "documento: outro_arquivo.pdf\n"
            "trecho: outro trecho\n"
            "tipo: fato\n"
            "```\n\n"
            "Use linguagem técnico-jurídica precisa. Formate em Markdown com cabeçalhos, "
            "tabelas e listas. Salve o relatório no caminho especificado no prompt."
        ),
        tools=["Read", "Write", "Grep", "Glob"],
    ),

    "estrategista-processual": AgentDefinition(
        description=(
            "⚔️ Especialista em estratégia jurídico-processual. "
            "Avalia riscos, oportunidades, vulnerabilidades e projeta cenários de "
            "desfecho com probabilidades estimadas. Trabalha com base na análise "
            "do leitor-de-pecas e pesquisador-juridico."
        ),
        prompt=(
            "Você é um estrategista jurídico sênior com 20+ anos de experiência "
            "em litígios complexos. "
            "Com base nos documentos e pesquisa jurídica disponíveis, elabore "
            "uma avaliação estratégica completa:\n\n"
            "**1. Posicionamento das partes:**\n"
            "- Pontos fortes e fracos de cada parte\n"
            "- Qualidade das provas e coerência dos fundamentos\n"
            "- Vulnerabilidades processuais identificadas\n\n"
            "**2. Riscos e Oportunidades:**\n"
            "- Principais riscos de sucumbência (com fatores)\n"
            "- Oportunidades processuais não exploradas\n"
            "- Precedentes favoráveis e desfavoráveis\n\n"
            "**3. Projeção de Cenários:**\n"
            "- Cenário otimista (probabilidade %): condições e desfecho\n"
            "- Cenário realista (probabilidade %): condições e desfecho\n"
            "- Cenário pessimista (probabilidade %): condições e desfecho\n\n"
            "**4. Viabilidade de Acordo:**\n"
            "- Conveniência de negociação extrajudicial\n"
            "- Condições mínimas e máximas aceitáveis\n\n"
            "Seja objetivo e use probabilidades percentuais quando possível. "
            "Fundamente cada afirmação nos documentos ou precedentes analisados."
        ),
        tools=["Read", "Grep", "Glob"],
    ),

    "advogado-orientador": AgentDefinition(
        description=(
            "🎯 Especialista em orientação jurídica prática. "
            "Transforma a análise e estratégia em recomendações concretas e "
            "acionáveis com prazos, prioridades e plano de ação para o advogado."
        ),
        prompt=(
            "Você é um advogado orientador com especialização em contencioso "
            "civil, trabalhista e tributário. "
            "Produza um plano de ação prático e objetivo:\n\n"
            "**1. Medidas Urgentes (próximos 7 dias):**\n"
            "- Ações imediatas com prazos fatais\n"
            "- Providências processuais inadiáveis\n"
            "- Documentos ou provas a obter urgentemente\n\n"
            "**2. Plano de Ação (próximas 4-8 semanas):**\n"
            "- Estratégia processual recomendada (passo a passo)\n"
            "- Diligências probatórias e prazos\n"
            "- Requerimentos e petições a protocolar\n\n"
            "**3. Monitoramento Contínuo:**\n"
            "- Prazos processuais a acompanhar\n"
            "- Publicações a monitorar no DJe\n"
            "- Riscos que exigem atenção especial\n\n"
            "**4. Comunicação com o Cliente:**\n"
            "- Pontos a esclarecer com o cliente\n"
            "- Expectativas a alinhar sobre prazos e resultados\n\n"
            "Seja direto e prático. O cliente precisa saber exatamente "
            "o que fazer e quando."
        ),
        tools=["Read", "Grep", "Glob"],
    ),
}


# ─── Suporte a PDF via Files API ──────────────────────────────────────────────

def carregar_pdf(
    caminho_pdf: str,
    client: anthropic.Anthropic | None = None,
) -> dict:
    """
    Faz upload de um PDF para a Files API e retorna o bloco de documento
    pronto para uso no Messages API.
    """
    client = client or _get_client()
    nome = os.path.basename(caminho_pdf)

    with open(caminho_pdf, "rb") as f:
        uploaded = client.beta.files.upload(
            file=(nome, f, "application/pdf"),
        )

    return {
        "type": "document",
        "source": {"type": "file", "file_id": uploaded.id},
        "title": nome,
    }


def analisar_pdf_direto(
    caminho_pdf: str,
    pergunta: str | None = None,
    client: anthropic.Anthropic | None = None,
) -> str:
    """
    Analisa um PDF diretamente via Files API + Messages API com Opus 4.6.
    Use quando quiser analisar um único PDF sem acionar o squad completo.
    """
    client = client or _get_client()
    doc_block = carregar_pdf(caminho_pdf, client)

    instrucao = pergunta or (
        "Analise esta peça processual e extraia: tipo da peça, partes envolvidas, "
        "datas relevantes, pedidos principais, fundamentos jurídicos e decisões."
    )

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": instrucao},
                doc_block,
            ],
        }],
        betas=[FILES_API_BETA],
    ) as stream:
        return _texto_da_resposta(stream.get_final_message())


async def _extrair_pdf_para_texto(
    pdf_path: str,
    client: anthropic.Anthropic,
) -> tuple[str, str]:
    """Faz upload e extração de texto de um PDF. Retorna (nome, texto_extraido)."""
    def _sync() -> tuple[str, str]:
        doc_block = carregar_pdf(pdf_path, client)
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extraia o texto completo desta peça processual de forma "
                            "estruturada para análise jurídica posterior."
                        ),
                    },
                    doc_block,
                ],
            }],
            betas=[FILES_API_BETA],
        ) as stream:
            return os.path.basename(pdf_path), _texto_da_resposta(stream.get_final_message())

    return await anyio.to_thread.run_sync(_sync)


# ─── Orquestrador principal ───────────────────────────────────────────────────

async def abrir_squad(
    prompt: str,
    diretorio: str = ".",
    pdfs: list[str] | None = None,
) -> str:
    """
    Abre o squad analista-processual para analisar um processo.

    Args:
        prompt:    Descrição da tarefa ou consulta processual.
        diretorio: Diretório de trabalho com os documentos do processo.
        pdfs:      Lista opcional de caminhos de PDFs a incluir na análise.
    """
    contexto_pdfs = ""
    if pdfs:
        client = _get_client()
        partes: list[str] = [""] * len(pdfs)

        async def _processar(i: int, pdf_path: str) -> None:
            nome, texto = await _extrair_pdf_para_texto(pdf_path, client)
            partes[i] = f"\n\n---\n### Documento: {nome}\n\n{texto}"

        async with anyio.create_task_group() as tg:
            for i, pdf_path in enumerate(pdfs):
                tg.start_soon(_processar, i, pdf_path)

        contexto_pdfs = "".join(partes)

    prompt_final = (
        f"{prompt}\n\n## Documentos PDF fornecidos:{contexto_pdfs}"
        if contexto_pdfs
        else prompt
    )

    options = ClaudeAgentOptions(
        cwd=diretorio,
        allowed_tools=["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch", "Agent"],
        permission_mode="acceptEdits",
        agents=SQUAD_AGENTS,
        system_prompt=(
            "Você é o coordenador do squad analista-processual. "
            "Orquestre os agentes especializados para realizar uma análise jurídica completa:\n\n"
            "1. Use 'leitor-de-pecas' para extrair e estruturar informações dos documentos\n"
            "2. Use 'pesquisador-juridico' para buscar jurisprudência e legislação online\n"
            "3. Use 'relator-processual' para consolidar tudo em um relatório final\n\n"
            "Sempre apresente uma análise organizada, objetiva e juridicamente fundamentada. "
            "Quando PDFs forem fornecidos, o texto já foi extraído e está disponível no prompt."
        ),
        max_turns=25,
    )

    resultado = ""
    async for message in query(prompt=prompt_final, options=options):
        if isinstance(message, ResultMessage):
            resultado = message.result

    return resultado


def executar(
    prompt: str,
    diretorio: str = ".",
    pdfs: list[str] | None = None,
) -> str:
    """Executa o squad analista-processual de forma síncrona."""
    return anyio.run(abrir_squad, prompt, diretorio, pdfs)


# ─── Integração com Workspace ─────────────────────────────────────────────────

_SYSTEM_PROMPT_SQUAD = (
    "Você é o coordenador do squad analista-processual (5 agentes especializados). "
    "Orquestre os agentes em ordem para uma análise jurídica completa e estratégica:\n\n"
    "1. **leitor-de-pecas** — lê todos os documentos e extrai informações estruturadas\n"
    "2. **pesquisador-juridico** — busca jurisprudência, legislação e doutrina relevante\n"
    "3. **estrategista-processual** — avalia riscos, oportunidades e projeta cenários\n"
    "4. **advogado-orientador** — define plano de ação prático com prazos e prioridades\n"
    "5. **relator-processual** — consolida tudo no relatório estratégico final (salva em arquivo)\n\n"
    "**Regras:**\n"
    "- O relatório DEVE ser salvo no caminho especificado no prompt via ferramenta Write\n"
    "- Considere TODAS as instruções do usuário ao direcionar cada agente\n"
    "- Se houver 'Instrução Adicional (prioridade alta)', priorize-a\n"
    "- O relator deve incluir o bloco ```citacoes``` rastreando as fontes documentais"
)

_SYSTEM_PROMPT_CHAT = (
    "Você é um assistente jurídico especializado com acesso ao contexto completo "
    "desta demanda. Responda de forma objetiva e fundamentada, citando os documentos "
    "e o relatório estratégico quando relevante. Use linguagem técnico-jurídica precisa. "
    "Quando necessário, consulte os agentes especializados:\n"
    "- 'pesquisador-juridico': para buscar jurisprudência ou legislação adicional\n"
    "- 'leitor-de-pecas': para extrair informações específicas de um documento"
)


async def _extrair_pdfs_da_demanda(
    ws: "DemandaWorkspace",
    apenas_novos: bool = False,
) -> tuple[str, list[str]]:
    """
    Extrai texto dos PDFs da demanda.

    Args:
        ws:           Workspace da demanda.
        apenas_novos: Se True, processa apenas documentos não analisados ainda (modo delta).

    Returns:
        (contexto_pdfs_texto, lista_de_caminhos_processados)
    """
    from .workspace import DocIndexado

    if apenas_novos:
        docs_alvo = [d for d in ws.documentos_novos() if d.extensao == ".pdf"]
        pdfs = [d.caminho for d in docs_alvo]
    else:
        pdfs = ws.todos_pdfs()

    if not pdfs:
        return "", []

    client = _get_client()
    partes: list[str] = [""] * len(pdfs)

    async def _processar(i: int, pdf_path: str) -> None:
        nome, texto = await _extrair_pdf_para_texto(pdf_path, client)
        pasta = "processo" if f"{os.sep}processo{os.sep}" in pdf_path else "documentos"
        tipo = ""
        try:
            from .workspace import classificar_tipo_peca
            tipo = f" · {classificar_tipo_peca(nome)}"
        except Exception:
            pass
        partes[i] = f"\n\n---\n### [{pasta}]{tipo} — {nome}\n\n{texto}"

    async with anyio.create_task_group() as tg:
        for i, pdf_path in enumerate(pdfs):
            tg.start_soon(_processar, i, pdf_path)

    return "".join(partes), pdfs


def _montar_prompt_analise(
    ws: "DemandaWorkspace",
    instrucao_extra: str | None,
    contexto_pdfs: str,
    caminho_relatorio: str,
    modo_delta: bool = False,
) -> str:
    """Monta o prompt completo para análise de demanda."""
    instrucoes_salvas = ws.ler_instrucoes()
    textos = ws.todos_textos()

    secoes: list[str] = [
        f"# {'Atualização da Análise' if modo_delta else 'Análise'} da Demanda: {ws.nome_original()}",
        "",
    ]

    if modo_delta:
        secoes += [
            "Esta é uma **atualização incremental** — novos documentos foram adicionados.",
            "Integre as novas informações ao relatório estratégico existente.",
            "",
        ]
    else:
        secoes += [
            "Realize uma análise jurídica completa de todos os documentos desta demanda.",
            "",
        ]

    if instrucoes_salvas:
        secoes += ["## Instruções e Notas do Usuário", "", instrucoes_salvas, ""]

    if instrucao_extra:
        secoes += ["## Instrução Adicional (prioridade alta)", "", instrucao_extra, ""]

    if modo_delta:
        ultimo_rel = ws.ler_ultimo_relatorio()
        if ultimo_rel:
            secoes += [
                "## Relatório Estratégico Existente (referência)",
                "",
                ultimo_rel[:4000] + ("\n\n[... truncado ...]" if len(ultimo_rel) > 4000 else ""),
                "",
            ]

    if textos:
        secoes += ["## Documentos de Texto", ""]
        for t in textos:
            try:
                from .workspace import classificar_tipo_peca
                tipo = classificar_tipo_peca(os.path.basename(t))
            except Exception:
                tipo = "Documento"
            secoes.append(f"- `{t}` ({tipo})  ← leia com a ferramenta Read")
        secoes.append("")

    if contexto_pdfs:
        secoes += ["## Documentos PDF (texto extraído)", contexto_pdfs, ""]

    secoes += [
        "## Saída esperada",
        "",
        f"Salve o relatório estratégico completo em: `{caminho_relatorio}`",
        "Use a ferramenta Write para gravar o arquivo Markdown.",
    ]

    return "\n".join(secoes)


def _extrair_e_registrar_citacoes(
    ws: "DemandaWorkspace",
    caminho_relatorio: "Path",
    resultado_texto: str,
) -> None:
    """
    Extrai citações do bloco ```citacoes``` no relatório e registra no workspace.
    Formato esperado no relatório:
      ```citacoes
      documento: nome.pdf
      trecho: texto referenciado
      tipo: fundamento_legal|prova|precedente|fato
      ---
      ```
    """
    import re as _re

    citacoes: list[dict] = []
    bloco = _re.search(r"```citacoes\s*(.*?)```", resultado_texto, _re.DOTALL | _re.IGNORECASE)

    if bloco:
        texto_bloco = bloco.group(1)
        entradas = texto_bloco.strip().split("---")
        for entrada in entradas:
            campos: dict = {}
            for linha in entrada.strip().splitlines():
                if ":" in linha:
                    chave, _, valor = linha.partition(":")
                    campos[chave.strip().lower()] = valor.strip()
            if campos.get("documento"):
                citacoes.append({
                    "documento": campos.get("documento", ""),
                    "trecho": campos.get("trecho", ""),
                    "tipo": campos.get("tipo", "referencia"),
                })

    # Também tenta ler o arquivo salvo se o resultado não tem as citações
    if not citacoes and caminho_relatorio.exists():
        conteudo = caminho_relatorio.read_text(encoding="utf-8")
        bloco = _re.search(r"```citacoes\s*(.*?)```", conteudo, _re.DOTALL | _re.IGNORECASE)
        if bloco:
            texto_bloco = bloco.group(1)
            entradas = texto_bloco.strip().split("---")
            for entrada in entradas:
                campos = {}
                for linha in entrada.strip().splitlines():
                    if ":" in linha:
                        chave, _, valor = linha.partition(":")
                        campos[chave.strip().lower()] = valor.strip()
                if campos.get("documento"):
                    citacoes.append({
                        "documento": campos.get("documento", ""),
                        "trecho": campos.get("trecho", ""),
                        "tipo": campos.get("tipo", "referencia"),
                    })

    if citacoes:
        ws.registrar_citacoes(str(caminho_relatorio), citacoes)


async def _analisar_demanda(
    ws: "DemandaWorkspace",
    instrucao_extra: str | None = None,
    modo_delta: bool = False,
    callback_progresso: "callable | None" = None,
) -> str:
    """
    Analisa os documentos de uma demanda e salva o relatório estratégico.

    Args:
        ws:                  Workspace da demanda.
        instrucao_extra:     Instrução pontual (não salva permanentemente).
        modo_delta:          Se True, processa apenas documentos novos/modificados.
        callback_progresso:  Função chamada com mensagens de progresso (para UI).
    """
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
    contexto_pdfs, pdfs_processados = await _extrair_pdfs_da_demanda(
        ws, apenas_novos=modo_delta
    )

    caminho_relatorio = ws.novo_caminho_relatorio()
    prompt_final = _montar_prompt_analise(
        ws, instrucao_extra, contexto_pdfs, str(caminho_relatorio), modo_delta
    )

    _notificar("Iniciando análise com o squad…")
    options = ClaudeAgentOptions(
        cwd=str(ws.caminho),
        allowed_tools=["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch", "Agent"],
        permission_mode="acceptEdits",
        agents=SQUAD_AGENTS,
        system_prompt=_SYSTEM_PROMPT_SQUAD,
        max_turns=30,
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

    # Extrai citações do relatório gerado e registra no workspace
    _extrair_e_registrar_citacoes(ws, caminho_relatorio, resultado)

    _notificar(f"Relatório salvo: {caminho_relatorio.name}")

    return resultado


async def _consultar_demanda(
    ws: "DemandaWorkspace",
    pergunta: str,
) -> str:
    """
    Modo chat: faz uma pergunta sobre a demanda sem gerar novo relatório.
    Usa o relatório existente + documentos como contexto.
    """
    ultimo_rel = ws.ler_ultimo_relatorio()
    instrucoes = ws.ler_instrucoes()

    secoes: list[str] = [
        f"# Consulta sobre a Demanda: {ws.nome_original()}",
        "",
        f"**Pergunta do usuário:** {pergunta}",
        "",
    ]

    if ultimo_rel:
        secoes += [
            "## Relatório Estratégico (contexto)",
            "",
            ultimo_rel[:6000] + ("\n\n[... truncado ...]" if len(ultimo_rel) > 6000 else ""),
            "",
        ]

    if instrucoes:
        secoes += ["## Instruções e Notas", "", instrucoes, ""]

    docs = ws.sincronizar_indice()
    if docs:
        secoes += ["## Documentos disponíveis", ""]
        for d in docs:
            secoes.append(f"- [{d.pasta}] `{d.nome}` — {d.tipo}")
        secoes += [
            "",
            "Use a ferramenta Read para acessar o conteúdo de qualquer documento acima.",
        ]

    prompt_final = "\n".join(secoes)

    options = ClaudeAgentOptions(
        cwd=str(ws.caminho),
        allowed_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch", "Agent"],
        permission_mode="acceptEdits",
        agents=SQUAD_AGENTS,
        system_prompt=_SYSTEM_PROMPT_CHAT,
        max_turns=15,
    )

    resultado = ""
    async for message in query(prompt=prompt_final, options=options):
        if isinstance(message, ResultMessage):
            resultado = message.result

    return resultado


def executar_demanda(
    ws: "DemandaWorkspace",
    instrucao_extra: str | None = None,
    modo_delta: bool = False,
    callback_progresso: "callable | None" = None,
) -> str:
    """
    Executa a análise completa de uma demanda de forma síncrona.

    Args:
        ws:                  Workspace da demanda.
        instrucao_extra:     Instrução pontual para esta análise (não salva).
        modo_delta:          Se True, reprocessa apenas docs novos/modificados.
        callback_progresso:  Função chamada com mensagens de progresso (para UI).
    """
    return anyio.run(_analisar_demanda, ws, instrucao_extra, modo_delta, callback_progresso)


def consultar_demanda(
    ws: "DemandaWorkspace",
    pergunta: str,
) -> str:
    """
    Modo chat: pergunta ao squad sobre a demanda sem gerar novo relatório.
    Ideal para consultas pontuais após a análise inicial.
    """
    return anyio.run(_consultar_demanda, ws, pergunta)


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    pdfs_cli = [a for a in args if a.endswith(".pdf")]
    outros = [a for a in args if not a.endswith(".pdf")]

    tarefa = " ".join(outros) if outros else (
        "Analise os documentos processuais disponíveis e gere um relatório completo "
        "com as principais informações, questões jurídicas e recomendações."
    )

    print("=" * 60)
    print("⚖️  SQUAD ANALISTA-PROCESSUAL")
    print("=" * 60)
    print(f"Tarefa: {tarefa}")
    if pdfs_cli:
        print(f"PDFs:   {', '.join(pdfs_cli)}")
    print("-" * 60)

    resultado = executar(tarefa, pdfs=pdfs_cli or None)
    print(resultado)
