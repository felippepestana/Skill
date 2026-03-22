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
"""

import os
import anyio
import anthropic
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage


# ─── Fontes jurídicas para pesquisa online ────────────────────────────────────

FONTES_JURIDICAS = [
    "stf.jus.br",          # Supremo Tribunal Federal
    "stj.jus.br",          # Superior Tribunal de Justiça
    "tst.jus.br",          # Tribunal Superior do Trabalho
    "lexml.gov.br",         # LexML — legislação federal e estadual
    "planalto.gov.br",      # Portal da Legislação Federal
    "jusbrasil.com.br",     # JusBrasil — jurisprudência consolidada
    "conjur.com.br",        # Consultor Jurídico — doutrina e notícias
]


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
            "e gera relatórios técnico-jurídicos estruturados em Markdown."
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
            "7. **Conclusões e Recomendações** — posicionamento técnico e próximos passos\n\n"
            "Use linguagem técnico-jurídica precisa. Formate o relatório em Markdown "
            "com cabeçalhos, tabelas e listas onde apropriado. "
            "Salve o relatório em arquivo .md quando um diretório de saída for fornecido."
        ),
        tools=["Read", "Write", "Grep", "Glob"],
    ),
}


# ─── Suporte a PDF via Files API ──────────────────────────────────────────────

def carregar_pdf(caminho_pdf: str) -> dict:
    """
    Faz upload de um PDF para a Files API e retorna o bloco de documento
    pronto para uso no Messages API.

    Args:
        caminho_pdf: Caminho local para o arquivo PDF.

    Returns:
        Bloco de conteúdo com referência ao file_id para uso na API.
    """
    client = anthropic.Anthropic()

    with open(caminho_pdf, "rb") as f:
        uploaded = client.beta.files.upload(
            file=(os.path.basename(caminho_pdf), f, "application/pdf"),
        )

    return {
        "type": "document",
        "source": {"type": "file", "file_id": uploaded.id},
        "title": os.path.basename(caminho_pdf),
    }


def analisar_pdf_direto(caminho_pdf: str, pergunta: str = None) -> str:
    """
    Analisa um PDF diretamente via Files API + Messages API com Opus 4.6.
    Use quando quiser analisar um único PDF sem acionar o squad completo.

    Args:
        caminho_pdf: Caminho local para o arquivo PDF.
        pergunta: Pergunta ou instrução específica sobre o documento.

    Returns:
        Análise do documento pelo modelo.
    """
    client = anthropic.Anthropic()
    doc_block = carregar_pdf(caminho_pdf)

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
        betas=["files-api-2025-04-14"],
    ) as stream:
        return stream.get_final_message().content[0].text


# ─── Orquestrador principal ───────────────────────────────────────────────────

async def abrir_squad(
    prompt: str,
    diretorio: str = ".",
    pdfs: list[str] = None,
) -> str:
    """
    Abre o squad analista-processual para analisar um processo.

    Args:
        prompt:    Descrição da tarefa ou consulta processual.
        diretorio: Diretório de trabalho com os documentos do processo.
        pdfs:      Lista opcional de caminhos de PDFs a incluir na análise.

    Returns:
        Resultado da análise orquestrada pelo squad.
    """
    # Se PDFs foram fornecidos, extrai o texto deles primeiro e anexa ao prompt
    contexto_pdfs = ""
    if pdfs:
        client = anthropic.Anthropic()
        for pdf_path in pdfs:
            doc_block = carregar_pdf(pdf_path)

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
                betas=["files-api-2025-04-14"],
            ) as stream:
                texto_extraido = stream.get_final_message().content[0].text

            nome = os.path.basename(pdf_path)
            contexto_pdfs += f"\n\n---\n### Documento: {nome}\n\n{texto_extraido}"

    prompt_final = prompt
    if contexto_pdfs:
        prompt_final = f"{prompt}\n\n## Documentos PDF fornecidos:{contexto_pdfs}"

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
    pdfs: list[str] = None,
) -> str:
    """Executa o squad analista-processual de forma síncrona."""
    return anyio.run(abrir_squad, prompt, diretorio, pdfs)


if __name__ == "__main__":
    import sys

    # Separa argumentos: PDFs começam com "--pdf"
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
