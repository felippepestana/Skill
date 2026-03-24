"""
Interface Web — Analista Processual
=====================================
Interface Gradio de três colunas inspirada no AI Drive / NotebookLM / ChatDOC:

  ┌────────────────┬──────────────────────────┬─────────────────────┐
  │  ESQUERDA      │  CENTRO                  │  DIREITA            │
  │  ─────────     │  ──────                  │  ──────             │
  │  Demandas      │  Chat com o squad        │  Preview do         │
  │  Documentos    │  (análise + consultas)   │  relatório          │
  │  Upload        │                          │  (editor Markdown)  │
  │  Instruções    │                          │                     │
  └────────────────┴──────────────────────────┴─────────────────────┘

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


# ─── Estado global da sessão ──────────────────────────────────────────────────

class _Estado:
    """Estado compartilhado da UI (mutável via referência)."""
    ws: DemandaWorkspace | None = None
    # Lock por demanda: impede análises simultâneas na mesma demanda
    _locks: Dict[str, threading.Lock] = {}
    _locks_mutex: threading.Lock = threading.Lock()

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

_estado = _Estado()


# ─── Helpers de formatação ────────────────────────────────────────────────────

def _icone_tipo(tipo: str) -> str:
    mapa = {
        "Petição Inicial": "📄",
        "Contestação": "📄",
        "Sentença": "⚖️",
        "Acórdão": "⚖️",
        "Contrato": "📋",
        "Nota Fiscal": "🧾",
        "Laudo Pericial": "🔬",
        "Ata de Audiência": "🎙️",
        "Procuração": "📜",
        "Ofício": "📬",
    }
    return mapa.get(tipo, "📎")


def _icone_ext(ext: str) -> str:
    return {"pdf": "🔴", "txt": "📝", "md": "📝", "docx": "💙", "xlsx": "💚"}.get(
        ext.lstrip("."), "📎"
    )


def _arvore_markdown(ws: DemandaWorkspace | None) -> str:
    if ws is None:
        return "_Selecione ou crie uma demanda._"

    arvore = ws.arvore()
    linhas = [f"### {arvore['nome']}", ""]

    def _bloco(titulo: str, docs: list) -> list[str]:
        if not docs:
            return [f"**{titulo}** — _nenhum_", ""]
        out = [f"**{titulo}**"]
        for d in docs:
            status = "✔" if d.analisado else "○"
            icone = _icone_tipo(d.tipo)
            out.append(f"  {status} {icone} {d.nome}")
            out.append(f"      _{d.tipo} · {d.tamanho}_")
        return out + [""]

    linhas += _bloco("Peças do Processo", arvore["processo"])
    linhas += _bloco("Outros Documentos", arvore["documentos"])

    relatorios = arvore["relatorios"]
    if relatorios:
        linhas.append("**Relatórios**")
        for r in relatorios[:5]:
            linhas.append(f"  📊 {r.name}")
        linhas.append("")

    if arvore["ultima_analise"]:
        linhas.append(f"_Última análise: {arvore['ultima_analise'][:16]}_")

    return "\n".join(linhas)


def _lista_demandas_choices() -> list[str]:
    return [ws.nome_original() for ws in listar_demandas()]


# ─── Handlers de evento ───────────────────────────────────────────────────────

def on_selecionar_demanda(nome: str):
    """Seleciona uma demanda e atualiza a UI."""
    if not nome:
        _estado.ws = None
        return (
            _arvore_markdown(None),
            "",
            gr.update(value="", interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )
    try:
        _estado.ws = obter_demanda(nome)
        instrucoes = _estado.ws.ler_instrucoes()
        relatorio = _estado.ws.ler_ultimo_relatorio()
        return (
            _arvore_markdown(_estado.ws),
            relatorio,
            gr.update(value=instrucoes, interactive=True),
            gr.update(interactive=True),
            gr.update(interactive=True),
        )
    except FileNotFoundError:
        return (
            "❌ Demanda não encontrada.",
            "",
            gr.update(value="", interactive=False),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )


def on_criar_demanda(nome: str, lista_atual: list):
    """Cria nova demanda e atualiza a lista."""
    nome = nome.strip()
    if not nome:
        return gr.update(), lista_atual, "⚠️ Informe o nome da demanda."
    try:
        ws = criar_demanda(nome)
        _estado.ws = ws
        novas = _lista_demandas_choices()
        return (
            gr.update(choices=novas, value=nome),
            novas,
            f"✔ Demanda **{nome}** criada.\n\nAdicione documentos nas pastas:\n"
            f"- `{ws.pasta_processo}/`\n- `{ws.pasta_documentos}/`",
        )
    except FileExistsError:
        return gr.update(), lista_atual, f"⚠️ Demanda '{nome}' já existe."


def on_upload_arquivo(arquivos: list, pasta: str):
    """Processa upload de arquivos para a demanda selecionada."""
    if not _estado.ws:
        return _arvore_markdown(None), "⚠️ Selecione uma demanda antes de enviar arquivos."

    if not arquivos:
        return _arvore_markdown(_estado.ws), "Nenhum arquivo recebido."

    msgs = []
    pasta_destino = "processo" if pasta == "Peças do Processo" else "documentos"
    for arq in arquivos:
        try:
            doc = _estado.ws.adicionar_documento(arq.name, pasta_destino)
            msgs.append(f"✔ {doc.nome} — {doc.tipo}")
        except Exception as e:
            msgs.append(f"✖ {Path(arq.name).name}: {e}")

    return _arvore_markdown(_estado.ws), "\n".join(msgs)


def on_salvar_instrucoes(texto: str):
    """Sobrescreve o arquivo de instruções."""
    if not _estado.ws:
        return "⚠️ Nenhuma demanda selecionada."
    _estado.ws.arquivo_instrucoes.write_text(texto, encoding="utf-8")
    return "✔ Instruções salvas."


def on_chat(
    mensagem: str,
    historico: list[dict],
    modo_analise: bool,
    instrucao_extra: str,
):
    """
    Processa mensagem do chat.
    - Se modo_analise=True: inicia análise completa do squad.
    - Se modo_analise=False: consulta pontual sobre a demanda.
    """
    if not _estado.ws:
        yield historico + [
            {"role": "user", "content": mensagem},
            {"role": "assistant", "content": "⚠️ Selecione uma demanda antes de iniciar."},
        ], "", ""
        return

    slug = _estado.ws.nome
    if _estado.esta_analisando(slug):
        yield historico + [
            {"role": "user", "content": mensagem},
            {"role": "assistant", "content": "⏳ Uma análise já está em andamento para esta demanda. Aguarde."},
        ], "", ""
        return

    historico = historico + [{"role": "user", "content": mensagem}]
    yield historico + [{"role": "assistant", "content": "⏳ Processando…"}], "", ""

    lock_demanda = _estado.lock_demanda(slug)
    progresso_q: queue.Queue[str] = queue.Queue()
    resultado_holder: list[str] = [""]
    erro_holder: list[str] = [""]
    ws_snapshot = _estado.ws  # captura referência estável para a thread

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
                progresso_q.put(None)  # sentinela de fim

    thread = threading.Thread(target=_executar, daemon=True)
    thread.start()

    # Streaming de progresso
    progresso_acumulado = []
    while True:
        try:
            msg = progresso_q.get(timeout=0.5)
        except queue.Empty:
            continue
        if msg is None:
            break
        progresso_acumulado.append(f"- {msg}")
        progresso_texto = "\n".join(progresso_acumulado)
        yield (
            historico + [{"role": "assistant", "content": f"⏳ **Em andamento…**\n\n{progresso_texto}"}],
            "",
            "",
        )

    thread.join()

    if erro_holder[0]:
        resposta = f"❌ Erro: {erro_holder[0]}"
    else:
        resposta = resultado_holder[0] or "Análise concluída."

    relatorio_atualizado = _estado.ws.ler_ultimo_relatorio() if _estado.ws else ""
    arvore_atualizada = _arvore_markdown(_estado.ws)

    yield (
        historico + [{"role": "assistant", "content": resposta}],
        relatorio_atualizado,
        arvore_atualizada,
    )


# ─── Construção da interface ──────────────────────────────────────────────────

CSS = """
#coluna-esquerda { border-right: 1px solid #e0e0e0; padding-right: 12px; }
#coluna-direita  { border-left:  1px solid #e0e0e0; padding-left:  12px; }
#arvore-docs     { font-family: monospace; font-size: 0.85em; }
#editor-relatorio textarea { font-family: monospace; font-size: 0.85em; }
.label-destaque  { font-weight: bold; color: #1a56db; }
"""

TITULO = "⚖️ Analista Processual"


def construir_ui() -> gr.Blocks:
    demandas_iniciais = _lista_demandas_choices()

    with gr.Blocks(
        title=TITULO,
        css=CSS,
        theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
    ) as app:

        gr.Markdown(f"# {TITULO}")
        gr.Markdown(
            "Workspace jurídico com análise multi-agente. "
            "Selecione ou crie uma demanda, adicione documentos e inicie a análise."
        )

        with gr.Row(equal_height=True):

            # ── Coluna esquerda: gerenciador de demandas ──────────────────────
            with gr.Column(scale=2, elem_id="coluna-esquerda"):
                gr.Markdown("## 📁 Demandas")

                with gr.Group():
                    demanda_dropdown = gr.Dropdown(
                        label="Demanda ativa",
                        choices=demandas_iniciais,
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
                btn_salvar_inst = gr.Button("💾 Salvar instruções", size="sm")
                msg_instrucoes = gr.Markdown("")

            # ── Coluna central: chat ──────────────────────────────────────────
            with gr.Column(scale=4):
                gr.Markdown("## 💬 Chat")

                chatbot = gr.Chatbot(
                    label="Conversa com o squad",
                    type="messages",
                    height=480,
                    show_copy_button=True,
                    avatar_images=(None, "https://www.anthropic.com/favicon.ico"),
                )

                with gr.Row():
                    chat_input = gr.Textbox(
                        label="Mensagem ou instrução",
                        placeholder=(
                            "Modo Análise: descreva o foco desejado (ou deixe em branco para análise completa)\n"
                            "Modo Consulta: faça uma pergunta sobre a demanda"
                        ),
                        lines=2,
                        scale=4,
                    )
                    btn_enviar = gr.Button("Enviar ▶", variant="primary", scale=1)

                with gr.Row():
                    modo_toggle = gr.Checkbox(
                        label="🔍 Modo Análise Completa (gera relatório)",
                        value=True,
                        interactive=True,
                    )
                    btn_delta = gr.Button(
                        "⚡ Análise Delta (só novos docs)",
                        size="sm",
                        variant="secondary",
                        interactive=False,
                    )

                gr.Markdown(
                    "_**Modo Análise**: aciona o squad completo e gera relatório estratégico.  \n"
                    "_**Modo Consulta**: responde perguntas usando o contexto existente._"
                )

            # ── Coluna direita: preview do relatório ──────────────────────────
            with gr.Column(scale=3, elem_id="coluna-direita"):
                gr.Markdown("## 📊 Relatório Estratégico")

                with gr.Tab("Preview"):
                    preview_relatorio = gr.Markdown(
                        "_O relatório aparecerá aqui após a análise._",
                        height=540,
                    )

                with gr.Tab("Editor"):
                    editor_relatorio = gr.Textbox(
                        label="",
                        lines=28,
                        interactive=True,
                        elem_id="editor-relatorio",
                        placeholder="O relatório em Markdown aparecerá aqui após a análise.",
                        show_copy_button=True,
                    )
                    with gr.Row():
                        btn_salvar_rel = gr.Button("💾 Salvar relatório", size="sm")
                        msg_salvar_rel = gr.Markdown("")

        # ── Eventos ───────────────────────────────────────────────────────────

        # Selecionar demanda
        demanda_dropdown.change(
            on_selecionar_demanda,
            inputs=[demanda_dropdown],
            outputs=[arvore_docs, editor_relatorio, editor_instrucoes, btn_enviar, btn_delta],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        )

        # Criar demanda
        btn_criar.click(
            on_criar_demanda,
            inputs=[nova_nome, demanda_dropdown],
            outputs=[demanda_dropdown, demanda_dropdown, msg_criacao],
        )

        # Upload de arquivos
        upload_btn.upload(
            on_upload_arquivo,
            inputs=[upload_btn, pasta_upload],
            outputs=[arvore_docs, msg_upload],
        )

        # Salvar instruções
        btn_salvar_inst.click(
            on_salvar_instrucoes,
            inputs=[editor_instrucoes],
            outputs=[msg_instrucoes],
        )

        # Chat principal (modo análise ou consulta)
        def _enviar_chat(msg, hist, modo, inst):
            yield from on_chat(msg, hist, modo, inst)

        btn_enviar.click(
            _enviar_chat,
            inputs=[chat_input, chatbot, modo_toggle, chat_input],
            outputs=[chatbot, editor_relatorio, arvore_docs],
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
            inputs=[chat_input, chatbot, modo_toggle, chat_input],
            outputs=[chatbot, editor_relatorio, arvore_docs],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        ).then(
            lambda: "",
            outputs=[chat_input],
        )

        # Análise delta
        def _delta_chat(hist):
            if not _estado.ws:
                yield hist + [{"role": "assistant", "content": "⚠️ Selecione uma demanda."}], "", ""
                return
            slug = _estado.ws.nome
            if _estado.esta_analisando(slug):
                yield hist + [{"role": "assistant", "content": "⏳ Análise em andamento. Aguarde."}], "", ""
                return
            ws_snapshot = _estado.ws
            lock_demanda = _estado.lock_demanda(slug)
            progresso_q: queue.Queue[str] = queue.Queue()
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
            yield historico + [{"role": "assistant", "content": "⏳ Verificando novos documentos…"}], "", ""
            threading.Thread(target=_run, daemon=True).start()
            acum = []
            while True:
                try:
                    msg = progresso_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                if msg is None:
                    break
                acum.append(f"- {msg}")
                yield historico + [{"role": "assistant", "content": f"⏳ **Em andamento…**\n\n" + "\n".join(acum)}], "", ""
            resposta = erro_holder[0] and f"❌ {erro_holder[0]}" or resultado_holder[0] or "Delta concluído."
            relatorio = ws_snapshot.ler_ultimo_relatorio()
            yield historico + [{"role": "assistant", "content": resposta}], relatorio, _arvore_markdown(ws_snapshot)

        btn_delta.click(
            _delta_chat,
            inputs=[chatbot],
            outputs=[chatbot, editor_relatorio, arvore_docs],
        ).then(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        )

        # Salvar relatório editado
        def _salvar_relatorio(texto: str) -> str:
            if not _estado.ws:
                return "⚠️ Nenhuma demanda selecionada."
            caminho = _estado.ws.novo_caminho_relatorio()
            caminho.write_text(texto, encoding="utf-8")
            _estado.ws.registrar_analise(str(caminho))
            return f"✔ Salvo: {caminho.name}"

        btn_salvar_rel.click(
            _salvar_relatorio,
            inputs=[editor_relatorio],
            outputs=[msg_salvar_rel],
        )

        # Sincronizar editor → preview ao editar
        editor_relatorio.change(
            lambda txt: txt,
            inputs=[editor_relatorio],
            outputs=[preview_relatorio],
        )

    return app


# ─── Ponto de entrada ─────────────────────────────────────────────────────────

def iniciar(
    host: str = "127.0.0.1",
    port: int = 7860,
    share: bool = False,
    abrir_browser: bool = True,
) -> None:
    """Inicializa e abre a interface web."""
    print(f"\n{'─' * 50}")
    print(f"  ⚖️  Analista Processual — Interface Web")
    print(f"  Pasta base: {pasta_base()}")
    print(f"  URL: http://{host}:{port}")
    print(f"{'─' * 50}\n")
    app = construir_ui()
    app.launch(
        server_name=host,
        server_port=port,
        share=share,
        inbrowser=abrir_browser,
        show_error=True,
    )
