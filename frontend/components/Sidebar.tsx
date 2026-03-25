"use client";
import { useEffect, useState } from "react";
import { Scale, Plus, LogOut, FileText, Clock } from "lucide-react";
import { listarDemandas, criarDemanda, obterDemanda, obterRelatorio } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import type { DemandaResumo } from "@/lib/api";

export default function Sidebar() {
  const { username, plano, demandaAtiva, demandas, setDemandas, setDemandaAtiva, setRelatorio, logout } = useAppStore();
  const [criando, setCriando] = useState(false);
  const [nomaNova, setNomaNova] = useState("");
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    listarDemandas()
      .then(setDemandas)
      .finally(() => setCarregando(false));
  }, []);

  async function selecionarDemanda(slug: string) {
    const detalhes = await obterDemanda(slug);
    setDemandaAtiva(detalhes);
    try {
      const rel = await obterRelatorio(slug);
      setRelatorio(rel);
    } catch {
      setRelatorio("");
    }
  }

  async function handleCriar(e: React.FormEvent) {
    e.preventDefault();
    if (!nomaNova.trim()) return;
    try {
      await criarDemanda(nomaNova);
      const lista = await listarDemandas();
      setDemandas(lista);
      setNomaNova("");
      setCriando(false);
    } catch (err: any) {
      alert(err.message);
    }
  }

  const badgePlano: Record<string, string> = {
    free: "badge-atencao",
    pro: "badge-ok",
    enterprise: "badge-critico",
  };

  return (
    <aside className="w-[260px] flex flex-col bg-gray-900 border-r border-gray-800 shrink-0">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2 mb-1">
          <Scale className="w-5 h-5 text-apex-400" />
          <span className="font-bold text-white text-sm tracking-wide">APEX-LEGAL</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">{username}</span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badgePlano[plano ?? "free"] ?? "badge-atencao"}`}>
            {plano ?? "free"}
          </span>
        </div>
      </div>

      {/* Demandas */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        <div className="flex items-center justify-between px-1 mb-2">
          <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Demandas</span>
          <button
            onClick={() => setCriando(!criando)}
            className="w-6 h-6 rounded-md bg-gray-800 hover:bg-apex-600 text-gray-400 hover:text-white
                       flex items-center justify-center transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
          </button>
        </div>

        {criando && (
          <form onSubmit={handleCriar} className="mb-2">
            <input
              autoFocus
              value={nomaNova}
              onChange={(e) => setNomaNova(e.target.value)}
              placeholder="Nome da demanda…"
              className="w-full bg-gray-800 border border-apex-600 rounded-lg px-3 py-2
                         text-white text-xs focus:outline-none"
            />
          </form>
        )}

        {carregando && (
          <p className="text-xs text-gray-600 px-1 py-2">Carregando…</p>
        )}

        {demandas.map((d) => (
          <DemandaItem
            key={d.slug}
            demanda={d}
            ativa={demandaAtiva?.slug === d.slug}
            onClick={() => selecionarDemanda(d.slug)}
          />
        ))}

        {!carregando && demandas.length === 0 && (
          <p className="text-xs text-gray-600 px-1 py-4 text-center">
            Nenhuma demanda ainda.
            <br />Crie uma com o botão +
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-800">
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                     text-gray-500 hover:text-red-400 hover:bg-red-500/10
                     text-xs transition-colors"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sair
        </button>
      </div>
    </aside>
  );
}

function DemandaItem({
  demanda,
  ativa,
  onClick,
}: {
  demanda: DemandaResumo;
  ativa: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors group ${
        ativa
          ? "bg-apex-600/20 border border-apex-600/30 text-white"
          : "hover:bg-gray-800 text-gray-400 hover:text-white"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium leading-tight line-clamp-2">{demanda.nome}</span>
        <div className="flex flex-col items-end gap-1 shrink-0 mt-0.5">
          {demanda.tem_relatorio && (
            <FileText className="w-3 h-3 text-green-400" />
          )}
          <span className="text-[10px] text-gray-600">{demanda.total_docs}d</span>
        </div>
      </div>
      {demanda.ultima_analise && (
        <div className="flex items-center gap-1 mt-1">
          <Clock className="w-2.5 h-2.5 text-gray-600" />
          <span className="text-[10px] text-gray-600">
            {new Date(demanda.ultima_analise).toLocaleDateString("pt-BR")}
          </span>
        </div>
      )}
    </button>
  );
}
