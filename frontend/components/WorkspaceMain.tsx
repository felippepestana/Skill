"use client";
import { useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  FileText, Upload, BookOpen, Clock, Edit3, Save, X, FolderOpen
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import {
  uploadArquivo, salvarRelatorio, salvarInstrucoes, obterDemanda, obterRelatorio
} from "@/lib/api";

type Tab = "relatorio" | "documentos" | "instrucoes" | "timeline";

export default function WorkspaceMain() {
  const { demandaAtiva, relatorio, setRelatorio, setDemandaAtiva } = useAppStore();
  const [tab, setTab] = useState<Tab>("relatorio");
  const [editando, setEditando] = useState(false);
  const [textoEdit, setTextoEdit] = useState("");
  const [instrucoes, setInstrucoes] = useState("");
  const [salvando, setSalvando] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  if (!demandaAtiva) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
        <FolderOpen className="w-12 h-12 text-gray-700 mb-4" />
        <p className="text-gray-500 text-sm">Selecione uma demanda na barra lateral</p>
        <p className="text-gray-700 text-xs mt-1">ou crie uma nova com o botão +</p>
      </div>
    );
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    for (const file of files) {
      await uploadArquivo(demandaAtiva.slug, file, "processo");
    }
    const detalhes = await obterDemanda(demandaAtiva.slug);
    setDemandaAtiva(detalhes);
  }

  async function handleSalvarRelatorio() {
    setSalvando(true);
    try {
      await salvarRelatorio(demandaAtiva.slug, textoEdit);
      setRelatorio(textoEdit);
      setEditando(false);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSalvando(false);
    }
  }

  async function handleSalvarInstrucoes() {
    setSalvando(true);
    try {
      await salvarInstrucoes(demandaAtiva.slug, instrucoes || demandaAtiva.instrucoes);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSalvando(false);
    }
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "relatorio",   label: "Relatório",    icon: <FileText className="w-3.5 h-3.5" /> },
    { id: "documentos",  label: "Documentos",   icon: <BookOpen className="w-3.5 h-3.5" /> },
    { id: "instrucoes",  label: "Instruções",   icon: <Edit3 className="w-3.5 h-3.5" /> },
    { id: "timeline",    label: "Linha do Tempo", icon: <Clock className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header da demanda */}
      <div className="px-6 py-4 border-b border-gray-800 shrink-0">
        <h2 className="font-semibold text-white text-sm">{demandaAtiva.nome}</h2>
        <p className="text-xs text-gray-500 mt-0.5">
          Criado em {new Date(demandaAtiva.criado_em).toLocaleDateString("pt-BR")}
          {demandaAtiva.ultima_analise && (
            <> · Última análise: {new Date(demandaAtiva.ultima_analise).toLocaleString("pt-BR")}</>
          )}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-4 pt-3 border-b border-gray-800 shrink-0">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs font-medium transition-colors
              ${tab === t.id
                ? "bg-gray-800 text-white border border-b-gray-800 border-gray-700"
                : "text-gray-500 hover:text-gray-300"
              }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Conteúdo da tab */}
      <div className="flex-1 overflow-y-auto">
        {tab === "relatorio" && (
          <div className="p-6">
            {!relatorio ? (
              <div className="text-center py-12">
                <FileText className="w-10 h-10 text-gray-700 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Nenhum relatório disponível</p>
                <p className="text-gray-700 text-xs mt-1">Inicie uma análise no painel de IA</p>
              </div>
            ) : editando ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-400">Editando relatório</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setEditando(false)}
                      className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded"
                    >
                      <X className="w-3 h-3" /> Cancelar
                    </button>
                    <button
                      onClick={handleSalvarRelatorio}
                      disabled={salvando}
                      className="flex items-center gap-1 text-xs bg-apex-600 hover:bg-apex-500 text-white px-3 py-1 rounded transition-colors"
                    >
                      <Save className="w-3 h-3" /> {salvando ? "Salvando…" : "Salvar"}
                    </button>
                  </div>
                </div>
                <textarea
                  value={textoEdit}
                  onChange={(e) => setTextoEdit(e.target.value)}
                  className="w-full h-[calc(100vh-300px)] bg-gray-800 border border-gray-700 rounded-lg
                             p-4 text-sm text-gray-200 font-mono resize-none focus:outline-none
                             focus:border-apex-600"
                />
              </div>
            ) : (
              <div>
                <div className="flex justify-end mb-3">
                  <button
                    onClick={() => { setTextoEdit(relatorio); setEditando(true); }}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300
                               bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    <Edit3 className="w-3 h-3" /> Editar
                  </button>
                </div>
                <div className="prose-juridico">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{relatorio}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "documentos" && (
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-medium text-white">Documentos da demanda</span>
              <button
                onClick={() => inputRef.current?.click()}
                className="flex items-center gap-1.5 text-xs bg-apex-600 hover:bg-apex-500 text-white
                           px-3 py-1.5 rounded-lg transition-colors"
              >
                <Upload className="w-3 h-3" /> Upload
              </button>
              <input ref={inputRef} type="file" multiple className="hidden" onChange={handleUpload} />
            </div>
            <pre className="text-xs text-gray-400 font-mono bg-gray-900 rounded-lg p-4 whitespace-pre-wrap">
              {demandaAtiva.arvore || "Nenhum documento ainda."}
            </pre>
          </div>
        )}

        {tab === "instrucoes" && (
          <div className="p-6 space-y-3">
            <p className="text-xs text-gray-500">
              Instruções e notas prioritárias para o squad durante a análise.
            </p>
            <textarea
              defaultValue={demandaAtiva.instrucoes}
              onChange={(e) => setInstrucoes(e.target.value)}
              placeholder="Ex: Foque na questão da prescrição. Ignore documentos anteriores a 2020."
              className="w-full h-48 bg-gray-800 border border-gray-700 rounded-lg p-4
                         text-sm text-gray-200 resize-none focus:outline-none focus:border-apex-600"
            />
            <button
              onClick={handleSalvarInstrucoes}
              disabled={salvando}
              className="flex items-center gap-1.5 text-xs bg-apex-600 hover:bg-apex-500 text-white
                         px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
            >
              <Save className="w-3 h-3" /> {salvando ? "Salvando…" : "Salvar instruções"}
            </button>
          </div>
        )}

        {tab === "timeline" && (
          <div className="p-6">
            {!demandaAtiva.timeline?.length ? (
              <p className="text-xs text-gray-600 text-center py-8">Nenhum evento registrado.</p>
            ) : (
              <div className="space-y-3">
                {(demandaAtiva.timeline as any[]).map((ev, i) => (
                  <div key={i} className="flex gap-3 items-start">
                    <div className="w-2 h-2 rounded-full bg-apex-500 mt-1.5 shrink-0" />
                    <div>
                      <p className="text-xs text-white">{ev.descricao ?? ev.tipo}</p>
                      <p className="text-[10px] text-gray-600 mt-0.5">
                        {new Date(ev.data).toLocaleString("pt-BR")}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
