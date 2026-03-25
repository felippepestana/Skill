"use client";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Zap, RefreshCw, Quote, AlertTriangle } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { criarWsAnalise, consultar, obterRelatorio } from "@/lib/api";

type PainelTab = "chat" | "citacoes" | "riscos";

export default function PainelIA() {
  const {
    demandaAtiva, relatorio, setRelatorio,
    progressoMsgs, addProgresso, clearProgresso,
    analisando, setAnalisando,
    chatHistory, addChatMsg, clearChat,
  } = useAppStore();

  const [tab, setTab] = useState<PainelTab>("chat");
  const [input, setInput] = useState("");
  const [instrucaoExtra, setInstrucaoExtra] = useState("");
  const [enviando, setEnviando] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fecharWsRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatHistory, progressoMsgs]);

  if (!demandaAtiva) {
    return (
      <aside className="w-[380px] flex flex-col bg-gray-900 border-l border-gray-800 shrink-0">
        <div className="flex-1 flex items-center justify-center">
          <p className="text-xs text-gray-600 text-center px-4">
            Selecione uma demanda para iniciar
          </p>
        </div>
      </aside>
    );
  }

  function iniciarAnalise(modo: "analisar" | "delta") {
    if (analisando) return;
    clearProgresso();
    setAnalisando(true);

    fecharWsRef.current = criarWsAnalise(
      demandaAtiva!.slug,
      modo,
      instrucaoExtra || undefined,
      (msg) => {
        if (msg.tipo === "progresso") addProgresso(msg.msg ?? "");
      },
      async (resultado) => {
        addProgresso("Análise concluída.");
        setAnalisando(false);
        try {
          const rel = await obterRelatorio(demandaAtiva!.slug);
          setRelatorio(rel);
        } catch {}
      },
      (err) => {
        addProgresso(`Erro: ${err}`);
        setAnalisando(false);
      },
    );
  }

  function cancelarAnalise() {
    fecharWsRef.current?.();
    setAnalisando(false);
    addProgresso("Análise cancelada.");
  }

  async function handleChat(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || enviando) return;
    const pergunta = input.trim();
    setInput("");
    addChatMsg("user", pergunta);
    setEnviando(true);
    try {
      const resposta = await consultar(demandaAtiva!.slug, pergunta);
      addChatMsg("assistant", resposta);
    } catch (err: any) {
      addChatMsg("assistant", `Erro: ${err.message}`);
    } finally {
      setEnviando(false);
    }
  }

  const tabs = [
    { id: "chat" as PainelTab, label: "Chat", icon: <Send className="w-3 h-3" /> },
    { id: "citacoes" as PainelTab, label: "Citações", icon: <Quote className="w-3 h-3" /> },
    { id: "riscos" as PainelTab, label: "Riscos", icon: <AlertTriangle className="w-3 h-3" /> },
  ];

  return (
    <aside className="w-[380px] flex flex-col bg-gray-900 border-l border-gray-800 shrink-0">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 shrink-0">
        <div className="flex items-center gap-2 mb-3">
          <div className={`w-2 h-2 rounded-full ${analisando ? "bg-green-400 animate-pulse" : "bg-gray-600"}`} />
          <span className="text-xs font-medium text-white">
            {analisando ? "Squad analisando…" : "Squad disponível"}
          </span>
        </div>

        {/* Botões de análise */}
        <div className="flex gap-2 mb-2">
          <button
            onClick={() => iniciarAnalise("analisar")}
            disabled={analisando}
            className="flex-1 flex items-center justify-center gap-1.5 text-xs
                       bg-apex-600 hover:bg-apex-500 disabled:opacity-40 text-white
                       py-2 rounded-lg transition-colors font-medium"
          >
            <Zap className="w-3 h-3" />
            Análise Completa
          </button>
          <button
            onClick={() => iniciarAnalise("delta")}
            disabled={analisando}
            className="flex-1 flex items-center justify-center gap-1.5 text-xs
                       bg-gray-700 hover:bg-gray-600 disabled:opacity-40 text-white
                       py-2 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Delta
          </button>
          {analisando && (
            <button
              onClick={cancelarAnalise}
              className="px-2 py-2 text-xs text-red-400 hover:text-red-300 bg-red-500/10
                         hover:bg-red-500/20 rounded-lg transition-colors"
            >
              ✕
            </button>
          )}
        </div>

        <input
          value={instrucaoExtra}
          onChange={(e) => setInstrucaoExtra(e.target.value)}
          placeholder="Instrução extra para esta análise (opcional)…"
          className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5
                     text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-apex-600"
        />
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-3 pt-2 border-b border-gray-800 shrink-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-t text-xs transition-colors
              ${tab === t.id ? "text-white bg-gray-800" : "text-gray-600 hover:text-gray-300"}`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Conteúdo */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {tab === "chat" && (
          <div className="p-4 space-y-3">
            {/* Progresso do squad */}
            {progressoMsgs.length > 0 && (
              <div className="bg-gray-800/50 rounded-lg p-3 space-y-1">
                {progressoMsgs.map((msg, i) => (
                  <p key={i} className={`text-xs font-mono ${
                    i === progressoMsgs.length - 1 && analisando ? "text-apex-400 animate-pulse" : "text-gray-500"
                  }`}>
                    {msg}
                  </p>
                ))}
              </div>
            )}

            {/* Histórico de chat */}
            {chatHistory.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-xl px-3 py-2 text-xs ${
                  msg.role === "user"
                    ? "bg-apex-600 text-white"
                    : "bg-gray-800 text-gray-300"
                }`}>
                  {msg.role === "assistant" ? (
                    <div className="prose-sm prose-invert">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  ) : msg.content}
                </div>
              </div>
            ))}

            {enviando && (
              <div className="flex justify-start">
                <div className="bg-gray-800 rounded-xl px-3 py-2">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <span key={i} className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce"
                            style={{ animationDelay: `${i * 0.1}s` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "citacoes" && (
          <div className="p-4 space-y-3">
            {!demandaAtiva.citacoes?.length ? (
              <p className="text-xs text-gray-600 text-center py-8">
                Citações aparecerão após a análise.
              </p>
            ) : (
              (demandaAtiva.citacoes as any[]).map((c, i) => (
                <div key={i} className="card p-3 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-apex-400 font-mono">{c.documento}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium
                      ${c.tipo === "precedente" ? "badge-ok" :
                        c.tipo === "fundamento_legal" ? "badge-atencao" :
                        c.tipo === "prova" ? "badge-urgente" : "badge-atencao"}`}>
                      {c.tipo}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 italic">"{c.trecho}"</p>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "riscos" && (
          <div className="p-4">
            <p className="text-xs text-gray-600 text-center py-8">
              Score de risco disponível após análise de inteligência.
            </p>
          </div>
        )}
      </div>

      {/* Input do chat */}
      {tab === "chat" && (
        <div className="p-3 border-t border-gray-800 shrink-0">
          <form onSubmit={handleChat} className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Consulte o squad sobre esta demanda…"
              disabled={analisando || enviando}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2
                         text-xs text-gray-200 placeholder-gray-600
                         focus:outline-none focus:border-apex-600 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || enviando || analisando}
              className="w-8 h-8 flex items-center justify-center bg-apex-600 hover:bg-apex-500
                         disabled:opacity-40 text-white rounded-lg transition-colors shrink-0"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
          {chatHistory.length > 0 && (
            <button
              onClick={clearChat}
              className="mt-1.5 text-[10px] text-gray-700 hover:text-gray-500 w-full text-center"
            >
              limpar histórico
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
