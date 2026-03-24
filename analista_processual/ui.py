"""
Interface Web — Analista Processual
=====================================
Interface Gradio de três colunas inspirada no AI Drive / NotebookLM / ChatDOC:

  ┌────────────────┬──────────────────────────┬──────────────────────────────┐
  │  ESQUERDA      │  CENTRO                  │  DIREITA (tabs)              │
  │  ─────────     │  ──────                  │  ──────                      │
  │  Demandas      │  Chat com o squad        │  📊 Relatório (prev/editor)  │
  │  Documentos    │  (análise + consultas)   │  📎 Citações                 │
  │  Upload        │                          │  📅 Linha do Tempo           │
  │  Instruções    │                          │  ✍️  Gerar Documento         │
  └────────────────┴──────────────────────────┴──────────────────────────────┘

Execução:
  python -m analista_processual ui
  python -m analista_processual          (abre a UI por padrão)
"""

from __future__ import annotations

import threading
import queue
from pathlib import Path
from typing import Dict

import gradio as gr

from .workspace import (
    criar_demanda,
    listar_demandas,
    obter_demanda,
    pasta_base,
    DemandaWorkspace,
)
from .squad import executar_demanda, consultar_demanda
from . import auth as _auth


# ─── Estado por sessão (gr.State — sem compartilhamento entre usuários) ────────

class _Estado:
    """
    Estado isolado por sessão Gradio.
    Cada usuário autenticado tem sua própria instância via gr.State().
    NÃO usar como singleton de módulo.
    """

    def __init__(self) -> None:
        self.ws: DemandaWorkspace | None = None
        self.username: str = ""
        self._locks: Dict[str, threading.Lock] = {}
        self._locks_mutex: threading.Lock = threading.Lock()

    def lock_demanda(self, slug: str) -> threading.Lock:
        with self._locks_mutex:
            if slug not in self._locks:
                self._locks[slug] = threading.Lock()
            return self._locks[slug]

    def esta_analisando(self, slug: str) -> bool:
        lock = self.lock_demanda(slug)
        if lock.acquire(blocking=False):
            lock.release()
            return False
        return True


# ─── Helpers de renderização ──────────────────────────────────────────────────

_ICONES_TIPO: dict[str, str] = {
    "Petição Inicial": "⚖",
    "Contestação": "📋",
    "Réplica": "↩",
    "Sentença": "🏛",
    "Acórdão": "📜",
    "Despacho": "📌",
    "Decisão Interlocutória": "⚡",
    "Apelação": "📤",
    "Agravo": "📢",
    "Embargos": "🔒",
    "Mandado": "📯",
    "Intimação": "🔔",
    "Citação": "📨",
    "Contrato": "📄",
    "Procuração": "✍",
    "Nota Fiscal": "🧾",
    "Laudo Pericial": "🔬",
    "Ata de Audiência": "🎙",
    "Ofício": "📮",
}

_ICONES_EXT: dict[str, str] = {
    ".pdf": "📕",
    ".docx": "📘",
    ".txt": "📝",
    ".md": "📝",
    ".odt": "📗",
}

_ICONES_EVENTO: dict[str, str] = {
    "criacao": "🗂️",
    "documento": "📎",
    "relatorio": "📊",
    "analise": "🔍",
}


def _icone_tipo(tipo: str, ext: str = "") -> str:
    if tipo in _ICONES_TIPO:
        return _ICONES_TIPO[tipo]
    return _ICONES_EXT.get(ext.lower(), "📁")


def _arvore_markdown(ws: DemandaWorkspace | None) -> str:
    if not ws:
        return "_Selecione ou crie uma demanda para ver os documentos._"

    try:
        arvore = ws.arvore()
    except Exception:
        return "❌ Erro ao carregar documentos."

    linhas: list[str] = [f"**{arvore['nome']}**\n"]

    def _bloco(titulo: str, docs: list) -> list[str]:
        if not docs:
            return []
        out = [f"**{titulo}** ({len(docs)})\n"]
        for d in docs:
            status = "✔" if d.analisado else "○"
            icone = _icone_tipo(d.tipo, d.extensao)
            out.append(f"  {status} {icone} `{d.nome}`")
            out.append(f"      _{d.tipo} · {d.tamanho}_")
        return out + [""]

    linhas += _bloco("Peças do Processo", arvore["processo"])
    linhas += _bloco("Outros Documentos", arvore["documentos"])

    relatorios = arvore["relatorios"]
    if relatorios:
        linhas.append(f"**Relatórios** ({len(relatorios)})")
        for r in relatorios[:5]:
            linhas.append(f"  📊 `{r.name}`")
        linhas.append("")

    if arvore["ultima_analise"]:
        linhas.append(f"_Última análise: {arvore['ultima_analise'][:16]}_")

    return "\n".join(linhas)


def _renderizar_citacoes(ws: DemandaWorkspace | None) -> str:
    """Renderiza as citações do último relatório em Markdown."""
    if not ws:
        return "_Selecione uma demanda para ver as citações._"

    citacoes = ws.ler_citacoes()
    if not citacoes:
        return (
            "_Nenhuma citação rastreada ainda._\n\n"
            "As citações são extraídas automaticamente após a análise."
        )

    _icones_tipo_cit = {
        "fundamento_legal": "⚖",
        "prova": "🔍",
        "precedente": "🏛",
        "fato": "📌",
        "referencia": "📎",
    }

    linhas = [f"**{len(citacoes)} citação(ões) rastreada(s)**\n"]
    for i, c in enumerate(citacoes, 1):
        icone = _icones_tipo_cit.get(c.get("tipo", ""), "📎")
        doc = c.get("documento", "desconhecido")
        tipo = c.get("tipo", "referencia").replace("_", " ").title()
        trecho = c.get("trecho", "")
        linhas.append(f"**{i}. {icone} {tipo}** — `{doc}`")
        if trecho:
            # Trunca trechos longos
            trecho_exibido = trecho[:200] + "…" if len(trecho) > 200 else trecho
            linhas.append(f"> {trecho_exibido}")
        linhas.append("")

    return "\n".join(linhas)


def _renderizar_timeline(ws: DemandaWorkspace | None) -> str:
    """Renderiza a linha do tempo da demanda em Markdown."""
    if not ws:
        return "_Selecione uma demanda para ver a linha do tempo._"

    try:
        eventos = ws.timeline()
    except Exception:
        return "❌ Erro ao carregar linha do tempo."

    if not eventos:
        return "_Nenhum evento registrado ainda._"

    linhas = [f"**Linha do Tempo — {ws.nome_original()}**\n"]
    data_anterior = ""

    for ev in eventos:
        data = ev.get("data", "")[:10]
        hora = ev.get("data", "")[11:16]
        icone = _ICONES_EVENTO.get(ev.get("tipo", ""), "•")
        desc = ev.get("descricao", "")

        if data != data_anterior:
            linhas.append(f"\n**{data}**")
            data_anterior = data

        linha = f"  {icone} {desc}"
        if hora:
            linha += f" _{hora}_"
        linhas.append(linha)

    return "\n".join(linhas)


def _lista_demandas_choices(username: str | None = None) -> list[str]:
    return [ws.nome_original() for ws in listar_demandas(username)]


# ─── Handlers de evento ───────────────────────────────────────────────────────

def on_selecionar_demanda(nome: str, estado: _Estado):
    """Seleciona uma demanda e atualiza todos os painéis."""
    _vazio = (
        _arvore_markdown(None),
        "",
        gr.update(value="", interactive=False),
        gr.update(interactive=False),
        gr.update(interactive=False),
        "_Selecione uma demanda para ver as citações._",
        "_Selecione uma demanda para ver a linha do tempo._",
        estado,
    )
    if not nome:
        estado.ws = None
        return _vazio
    try:
        estado.ws = obter_demanda(nome, estado.username or None)
        instrucoes = estado.ws.ler_instrucoes()
        relatorio = estado.ws.ler_ultimo_relatorio()
        citacoes = _renderizar_citacoes(estado.ws)
        timeline = _renderizar_timeline(estado.ws)
        return (
            _arvore_markdown(estado.ws),
            relatorio,
            gr.update(value=instrucoes, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
            citacoes,
            timeline,
            estado,
        )
    except FileNotFoundError:
        estado.ws = None
        return _vazio


def on_criar_demanda(nome: str, lista_atual: list, estado: _Estado):
    """Cria nova demanda e atualiza a lista."""
    nome = nome.strip()
    if not nome:
        return gr.update(), lista_atual, "⚠️ Informe o nome da demanda.", estado
    try:
        ws = criar_demanda(nome, estado.username or None)
        estado.ws = ws
        novas = _lista_demandas_choices(estado.username or None)
        return (
            gr.update(choices=novas, value=nome),
            novas,
            f"✔ Demanda **{nome}** criada.\n\nAdicione documentos em:\n"
            f"- `{ws.pasta_processo}/`\n- `{ws.pasta_documentos}/`",
            estado,
        )
    except FileExistsError:
        return gr.update(), lista_atual, f"⚠️ Demanda '{nome}' já existe.", estado


def on_upload_arquivo(arquivos: list, pasta: str, estado: _Estado):
    """Processa upload de arquivos para a demanda selecionada."""
    if not estado.ws:
        return _arvore_markdown(None), "⚠️ Selecione uma demanda antes de enviar arquivos."
    if not arquivos:
        return _arvore_markdown(estado.ws), "Nenhum arquivo recebido."

    msgs = []
    pasta_destino = "processo" if pasta == "Peças do Processo" else "documentos"
    for arq in arquivos:
        try:
            doc = estado.ws.adicionar_documento(arq.name, pasta_destino)
            msgs.append(f"✔ `{doc.nome}` — {doc.tipo}")
        except Exception as e:
            msgs.append(f"✖ {Path(arq.name).name}: {e}")

    return _arvore_markdown(estado.ws), "\n".join(msgs)


def on_salvar_instrucoes(texto: str, estado: _Estado):
    """Sobrescreve o arquivo de instruções."""
    if not estado.ws:
        return "⚠️ Nenhuma demanda selecionada."
    estado.ws.arquivo_instrucoes.write_text(texto, encoding="utf-8")
    return "✔ Instruções salvas."


def _executar_em_thread(
    ws_snapshot: DemandaWorkspace,
    slug: str,
    modo_analise: bool,
    mensagem: str,
    instrucao_extra: str,
    lock_demanda: threading.Lock,
) -> "tuple[queue.Queue, threading.Thread, list, list]":
    """Executa a análise em thread e retorna a fila de progresso."""
    progresso_q: queue.Queue[str | None] = queue.Queue()
    resultado_holder: list[str] = [""]
    erro_holder: list[str] = [""]

    def _callback_prog(msg: str) -> None:
        progresso_q.put(msg)

    def _executar() -> None:
        with lock_demanda:
            try:
                if modo_analise:
                    resultado_holder[0] = executar_demanda(
                        ws_snapshot,
                        instrucao_extra=instrucao_extra or None,
                        modo_delta=False,
                        callback_progresso=_callback_prog,
                    )
                else:
                    resultado_holder[0] = consultar_demanda(ws_snapshot, mensagem)
            except Exception as e:
                erro_holder[0] = str(e)
            finally:
                progresso_q.put(None)

    t = threading.Thread(target=_executar, daemon=True)
    t.start()
    return progresso_q, t, resultado_holder, erro_holder


def on_chat(
    mensagem: str,
    historico: list[dict],
    modo_analise: bool,
    instrucao_extra: str,
    estado: _Estado,
):
    """
    Handler de chat com streaming de progresso.
    Yields: (historico, relatorio, arvore, citacoes, timeline)
    """
    _sem_demanda = (
        historico + [
            {"role": "user", "content": mensagem},
            {"role": "assistant", "content": "⚠️ Selecione uma demanda antes de iniciar."},
        ],
        "", "", "", "",
    )

    if not estado.ws:
        yield _sem_demanda
        return

    slug = estado.ws.nome
    if estado.esta_analisando(slug):
        yield (
            historico + [
                {"role": "user", "content": mensagem},
                {"role": "assistant", "content": "⏳ Análise em andamento para esta demanda. Aguarde."},
            ],
            "", "", "", "",
        )
        return

    ws_snapshot = estado.ws
    lock_demanda = estado.lock_demanda(slug)
    historico = historico + [{"role": "user", "content": mensagem}]
    yield historico + [{"role": "assistant", "content": "⏳ Iniciando…"}], "", "", "", ""

    progresso_q, thread, resultado_holder, erro_holder = _executar_em_thread(
        ws_snapshot, slug, modo_analise, mensagem, instrucao_extra, lock_demanda
    )

    # Streaming de progresso
    acumulado: list[str] = []
    while True:
        try:
            msg = progresso_q.get(timeout=0.5)
        except queue.Empty:
            continue
        if msg is None:
            break
        acumulado.append(f"- {msg}")
        prog_texto = "\n".join(acumulado)
        yield (
            historico + [{"role": "assistant", "content": f"⏳ **Em andamento…**\n\n{prog_texto}"}],
            "", "", "", "",
        )

    thread.join()

    resposta = f"❌ Erro: {erro_holder[0]}" if erro_holder[0] else (resultado_holder[0] or "Concluído.")
    relatorio = ws_snapshot.ler_ultimo_relatorio()
    citacoes = _renderizar_citacoes(ws_snapshot)
    timeline = _renderizar_timeline(ws_snapshot)
    arvore = _arvore_markdown(ws_snapshot)

    yield (
        historico + [{"role": "assistant", "content": resposta}],
        relatorio,
        arvore,
        citacoes,
        timeline,
    )


# ─── Construção da interface ──────────────────────────────────────────────────

CSS = """
/* Layout e separadores */
#coluna-esquerda { border-right: 1px solid var(--border-color-primary); padding-right: 14px; }
#coluna-direita  { border-left:  1px solid var(--border-color-primary); padding-left:  14px; }

/* Árvore de documentos */
#arvore-docs     { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.83em; line-height: 1.6; max-height: 320px; overflow-y: auto; }

/* Editor Markdown */
#editor-relatorio textarea { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.84em; }

/* Preview com scroll */
#preview-relatorio { max-height: 540px; overflow-y: auto; }
#preview-citacoes  { max-height: 480px; overflow-y: auto; }
#preview-timeline  { max-height: 480px; overflow-y: auto; }

/* Botão de análise em destaque */
.btn-analise { background: linear-gradient(135deg, #1a56db 0%, #1d4ed8 100%) !important; }

/* Status de análise */
.status-analisado { color: #16a34a; font-weight: 600; }
.status-pendente  { color: #ca8a04; }

/* Destaques */
.destaque-azul { color: #1a56db; font-weight: 600; }
"""

TITULO = "⚖️ Analista Processual"

_TIPOS_DOCUMENTO = [
    "Recurso de Apelação",
    "Petição Inicial",
    "Contestação",
    "Réplica",
    "Recurso Especial (STJ)",
    "Recurso Extraordinário (STF)",
    "Agravo Interno",
    "Embargos de Declaração",
    "Mandado de Segurança",
    "Habeas Corpus",
    "Notificação Extrajudicial",
    "Contrato",
    "Acordo / Distrato",
    "Parecer Jurídico",
]


def construir_ui() -> gr.Blocks:
    with gr.Blocks(
        title=TITULO,
        css=CSS,
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    ) as app:

        # Estado isolado por sessão — NÃO é singleton de módulo
        estado = gr.State(value=_Estado)

        # Cabeçalho
        with gr.Row():
            gr.Markdown(f"# {TITULO}")
            gr.Markdown(
                "Workspace jurídico com análise multi-agente (5 especialistas). "
                "Selecione ou crie uma demanda, adicione documentos e inicie a análise.",
                elem_classes=["destaque-azul"],
            )

        with gr.Row(equal_height=True):

            # ── Coluna esquerda: gerenciador de demandas ──────────────────────
            with gr.Column(scale=2, elem_id="coluna-esquerda"):
                gr.Markdown("## 📁 Demandas")

                with gr.Group():
                    demanda_dropdown = gr.Dropdown(
                        label="Demanda ativa",
                        choices=[],  # populado em on_load via request.username
                        interactive=True,
                        allow_custom_value=False,
                    )
                    with gr.Row():
                        nova_nome = gr.Textbox(
                            label="Nova demanda",
                            placeholder="Ex: Fulano vs Ciclano 2024",
                            scale=3,
                        )
                        btn_criar = gr.Button("＋ Criar", scale=1, variant="secondary")
                    msg_criacao = gr.Markdown("")

                gr.Markdown("---")
                gr.Markdown("## 📂 Documentos")

                arvore_docs = gr.Markdown(
                    _arvore_markdown(None),
                    elem_id="arvore-docs",
                )

                with gr.Accordion("➕ Adicionar documentos", open=False):
                    pasta_upload = gr.Radio(
                        ["Peças do Processo", "Outros Documentos"],
                        label="Destino",
                        value="Peças do Processo",
                    )
                    upload_btn = gr.File(
                        label="Arraste ou clique para enviar",
                        file_count="multiple",
                        file_types=[".pdf", ".txt", ".md", ".docx"],
                    )
                    msg_upload = gr.Markdown("")

                gr.Markdown("---")
                gr.Markdown("## 📝 Instruções")
                editor_instrucoes = gr.Textbox(
                    label="Instruções para o squad",
                    placeholder="Selecione uma demanda para editar as instruções.",
                    lines=6,
                    interactive=False,
                )
                with gr.Row():
                    btn_salvar_inst = gr.Button("💾 Salvar", size="sm")
                    msg_instrucoes = gr.Markdown("")

            # ── Coluna central: chat ──────────────────────────────────────────
            with gr.Column(scale=4):
                gr.Markdown("## 💬 Chat com o Squad")

                chatbot = gr.Chatbot(
                    label="Conversa",
                    type="messages",
                    height=460,
                    show_copy_button=True,
                    placeholder=(
                        "### ⚖️ Analista Processual\n"
                        "Selecione uma demanda e inicie a análise."
                    ),
                )

                with gr.Row():
                    chat_input = gr.Textbox(
                        label="Mensagem / Pergunta (Modo Consulta)",
                        placeholder="Faça uma pergunta sobre a demanda…",
                        lines=2,
                        scale=4,
                    )
                    btn_enviar = gr.Button("Enviar ▶", variant="primary", scale=1, interactive=False, elem_classes=["btn-analise"])

                with gr.Row():
                    modo_toggle = gr.Checkbox(
                        label="🔍 Modo Análise Completa — aciona os 5 agentes e gera relatório",
                        value=True,
                    )
                    btn_delta = gr.Button(
                        "⚡ Análise Delta (só novos docs)",
                        size="sm",
                        variant="secondary",
                        interactive=False,
                    )

                instrucao_extra_input = gr.Textbox(
                    label="Foco da análise (opcional — apenas no Modo Análise)",
                    placeholder="Ex: foque na questão da prescrição; analise os riscos trabalhistas",
                    lines=1,
                    visible=True,
                )

                gr.Markdown(
                    "_**5 agentes**: Leitor de Peças → Pesquisador Jurídico → "
                    "Estrategista → Advogado Orientador → Relator_"
                )

            # ── Coluna direita: painel com abas ──────────────────────────────
            with gr.Column(scale=3, elem_id="coluna-direita"):

                with gr.Tabs():

                    # Tab 1: Relatório
                    with gr.Tab("📊 Relatório"):
                        with gr.Tabs():
                            with gr.Tab("Preview"):
                                preview_relatorio = gr.Markdown(
                                    "_O relatório aparecerá aqui após a análise._",
                                    elem_id="preview-relatorio",
                                    height=500,
                                )
                            with gr.Tab("Editor"):
                                editor_relatorio = gr.Textbox(
                                    label="",
                                    lines=26,
                                    interactive=True,
                                    elem_id="editor-relatorio",
                                    placeholder="Relatório em Markdown…",
                                    show_copy_button=True,
                                )
                                with gr.Row():
                                    btn_salvar_rel = gr.Button("💾 Salvar versão", size="sm")
                                    msg_salvar_rel = gr.Markdown("")

                    # Tab 2: Citações
                    with gr.Tab("📎 Citações"):
                        gr.Markdown(
                            "_Citações extraídas automaticamente do relatório, rastreando "
                            "cada referência ao documento de origem._"
                        )
                        painel_citacoes = gr.Markdown(
                            "_Selecione uma demanda para ver as citações._",
                            elem_id="preview-citacoes",
                        )

                    # Tab 3: Linha do Tempo
                    with gr.Tab("📅 Linha do Tempo"):
                        gr.Markdown(
                            "_Cronologia automática de todos os eventos da demanda: "
                            "criação, documentos adicionados e análises realizadas._"
                        )
                        painel_timeline = gr.Markdown(
                            "_Selecione uma demanda para ver a linha do tempo._",
                            elem_id="preview-timeline",
                        )

                    # Tab 4: Gerar Documento
                    with gr.Tab("✍️ Gerar Documento"):
                        gr.Markdown(
                            "### Geração de Documentos Jurídicos\n"
                            "O squad documental (Redator + Revisor + Formatador) "
                            "gera peças processuais baseadas na análise da demanda."
                        )
                        tipo_doc_dropdown = gr.Dropdown(
                            label="Tipo de documento",
                            choices=_TIPOS_DOCUMENTO,
                            value="Recurso de Apelação",
                            interactive=True,
                        )
                        instrucoes_doc = gr.Textbox(
                            label="Instruções adicionais (opcional)",
                            placeholder="Ex: foque na tese de prescrição, use o precedente REsp 1.234.567",
                            lines=3,
                        )
                        btn_gerar_doc = gr.Button(
                            "✍️ Gerar Documento",
                            variant="secondary",
                            interactive=False,
                        )
                        progresso_doc = gr.Markdown("")
                        resultado_doc = gr.Markdown("")

        # ── Eventos ───────────────────────────────────────────────────────────

        # Carregar demandas do usuário ao abrir a sessão
        def _on_load(request: gr.Request, est: _Estado) -> tuple:
            username = request.username or ""
            est.username = username
            choices = _lista_demandas_choices(username or None)
            return gr.update(choices=choices, value=None), est

        app.load(
            _on_load,
            inputs=[estado],
            outputs=[demanda_dropdown, estado],
        )

        # Selecionar demanda
        demanda_dropdown.change(
            on_selecionar_demanda,
            inputs=[demanda_dropdown, estado],
            outputs=[
                arvore_docs, editor_relatorio, editor_instrucoes,
                btn_enviar, btn_delta,
                painel_citacoes, painel_timeline,
                estado,
            ],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        ).then(
            lambda: (gr.update(interactive=True), gr.update(interactive=True)),
            outputs=[btn_gerar_doc, btn_delta],
        )

        # Criar demanda
        def _on_criar(nome, lista, est):
            resultado = on_criar_demanda(nome, lista, est)
            # resultado: (gr.update(choices,value), novas_choices, msg, estado)
            return resultado[0], resultado[2], resultado[3]

        btn_criar.click(
            _on_criar,
            inputs=[nova_nome, demanda_dropdown, estado],
            outputs=[demanda_dropdown, msg_criacao, estado],
        )

        # Upload de arquivos
        upload_btn.upload(
            on_upload_arquivo,
            inputs=[upload_btn, pasta_upload, estado],
            outputs=[arvore_docs, msg_upload],
        )

        # Salvar instruções
        btn_salvar_inst.click(
            on_salvar_instrucoes,
            inputs=[editor_instrucoes, estado],
            outputs=[msg_instrucoes],
        )

        # Chat principal
        def _enviar_chat(msg, hist, modo, inst, est):
            yield from on_chat(msg, hist, modo, inst, est)

        btn_enviar.click(
            _enviar_chat,
            inputs=[chat_input, chatbot, modo_toggle, instrucao_extra_input, estado],
            outputs=[chatbot, editor_relatorio, arvore_docs, painel_citacoes, painel_timeline],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        ).then(
            lambda: "",
            outputs=[chat_input],
        )

        chat_input.submit(
            _enviar_chat,
            inputs=[chat_input, chatbot, modo_toggle, instrucao_extra_input, estado],
            outputs=[chatbot, editor_relatorio, arvore_docs, painel_citacoes, painel_timeline],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        ).then(
            lambda: "",
            outputs=[chat_input],
        )

        # Análise delta
        def _delta_chat(hist, est):
            if not est.ws:
                yield hist + [{"role": "assistant", "content": "⚠️ Selecione uma demanda."}], "", "", "", ""
                return

            slug = est.ws.nome
            if est.esta_analisando(slug):
                yield hist + [{"role": "assistant", "content": "⏳ Análise em andamento. Aguarde."}], "", "", "", ""
                return

            ws_snapshot = est.ws
            lock_demanda = est.lock_demanda(slug)
            progresso_q: queue.Queue[str | None] = queue.Queue()
            resultado_holder: list[str] = [""]
            erro_holder: list[str] = [""]

            def _cb(msg: str) -> None:
                progresso_q.put(msg)

            def _run() -> None:
                with lock_demanda:
                    try:
                        resultado_holder[0] = executar_demanda(
                            ws_snapshot,
                            instrucao_extra=None,
                            modo_delta=True,
                            callback_progresso=_cb,
                        )
                    except Exception as e:
                        erro_holder[0] = str(e)
                    finally:
                        progresso_q.put(None)

            historico = hist + [{"role": "user", "content": "⚡ Análise Delta (novos documentos)"}]
            yield historico + [{"role": "assistant", "content": "⏳ Verificando novos documentos…"}], "", "", "", ""
            threading.Thread(target=_run, daemon=True).start()

            acum: list[str] = []
            while True:
                try:
                    msg = progresso_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if msg is None:
                    break
                acum.append(f"- {msg}")
                yield historico + [{"role": "assistant", "content": "⏳ **Em andamento…**\n\n" + "\n".join(acum)}], "", "", "", ""

            resposta = f"❌ {erro_holder[0]}" if erro_holder[0] else (resultado_holder[0] or "Delta concluído.")
            relatorio = ws_snapshot.ler_ultimo_relatorio()
            citacoes = _renderizar_citacoes(ws_snapshot)
            timeline = _renderizar_timeline(ws_snapshot)
            yield (
                historico + [{"role": "assistant", "content": resposta}],
                relatorio, _arvore_markdown(ws_snapshot),
                citacoes, timeline,
            )

        btn_delta.click(
            _delta_chat,
            inputs=[chatbot, estado],
            outputs=[chatbot, editor_relatorio, arvore_docs, painel_citacoes, painel_timeline],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        )

        # Salvar relatório editado
        def _salvar_relatorio(texto: str, est: _Estado) -> str:
            if not est.ws:
                return "⚠️ Nenhuma demanda selecionada."
            caminho = est.ws.novo_caminho_relatorio()
            caminho.write_text(texto, encoding="utf-8")
            est.ws.registrar_analise(str(caminho))
            return f"✔ Salvo: `{caminho.name}`"

        btn_salvar_rel.click(
            _salvar_relatorio,
            inputs=[editor_relatorio, estado],
            outputs=[msg_salvar_rel],
        )

        # Sincronizar editor → preview ao editar
        editor_relatorio.change(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        )

        # Gerar documento com squad-documental
        def _gerar_documento(tipo_doc: str, instrucoes_extras: str, hist: list, est: _Estado):
            if not est.ws:
                yield hist, "⚠️ Selecione uma demanda.", ""
                return

            try:
                from squads.documental import executar_para_demanda
            except ImportError:
                yield hist, "❌ Squad documental não disponível.", ""
                return

            ws_snapshot = est.ws
            progresso_q: queue.Queue[str | None] = queue.Queue()
            resultado_holder: list[str] = [""]
            erro_holder: list[str] = [""]

            def _cb(msg: str) -> None:
                progresso_q.put(msg)

            def _run() -> None:
                try:
                    resultado_holder[0] = executar_para_demanda(
                        str(ws_snapshot.caminho),
                        tipo_doc,
                        instrucoes_extras,
                        _cb,
                    )
                except Exception as e:
                    erro_holder[0] = str(e)
                finally:
                    progresso_q.put(None)

            yield hist, "⏳ Iniciando squad documental…", ""
            threading.Thread(target=_run, daemon=True).start()

            acum: list[str] = []
            while True:
                try:
                    msg = progresso_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if msg is None:
                    break
                acum.append(f"- {msg}")
                yield hist, "⏳ **Gerando…**\n\n" + "\n".join(acum), ""

            if erro_holder[0]:
                yield hist, f"❌ Erro: {erro_holder[0]}", ""
            else:
                resultado = resultado_holder[0] or "Documento gerado."
                yield hist, "✔ Concluído.", resultado

        btn_gerar_doc.click(
            _gerar_documento,
            inputs=[tipo_doc_dropdown, instrucoes_doc, chatbot, estado],
            outputs=[chatbot, progresso_doc, resultado_doc],
        )

    return app


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def iniciar(
    host: str = "127.0.0.1",
    port: int = 7860,
    share: bool = False,
    abrir_browser: bool = True,
    com_auth: bool = True,
) -> None:
    """
    Inicializa e abre a interface web.

    Args:
        com_auth: Se True, exige login via banco de usuários (padrão).
                  Se False, abre sem autenticação (uso local/desenvolvimento).
    """
    print(f"\n{'─' * 60}")
    print(f"  ⚖️  Analista Processual — Interface Web")
    print(f"  Pasta base  : {pasta_base()}")
    print(f"  URL         : http://{host}:{port}")
    print(f"  Auth        : {'habilitada' if com_auth else 'DESABILITADA (modo local)'}")
    print(f"  Squad       : 5 agentes (leitor + pesquisador + estrategista + orientador + relator)")
    print(f"{'─' * 60}\n")
    app = construir_ui()
    app.launch(
        server_name=host,
        server_port=port,
        share=share,
        inbrowser=abrir_browser,
        show_error=False,  # não expõe stack traces ao usuário final
        auth=_auth.verificar_credenciais if com_auth else None,
        auth_message="⚖️ Analista Processual — Faça login para acessar o workspace.",
    )
