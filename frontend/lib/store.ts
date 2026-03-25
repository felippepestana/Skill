/**
 * Store global com Zustand — estado da sessão APEX-LEGAL.
 */
import { create } from "zustand";
import { DemandaResumo, DemandaDetalhes } from "./api";

interface AppState {
  // Auth
  token: string | null;
  username: string | null;
  plano: string | null;
  setAuth: (token: string, username: string, plano: string) => void;
  logout: () => void;

  // Demandas
  demandas: DemandaResumo[];
  setDemandas: (d: DemandaResumo[]) => void;

  // Demanda ativa
  demandaAtiva: DemandaDetalhes | null;
  setDemandaAtiva: (d: DemandaDetalhes | null) => void;

  // Relatório
  relatorio: string;
  setRelatorio: (r: string) => void;

  // Progresso do squad
  progressoMsgs: string[];
  addProgresso: (msg: string) => void;
  clearProgresso: () => void;
  analisando: boolean;
  setAnalisando: (v: boolean) => void;

  // Chat
  chatHistory: { role: "user" | "assistant"; content: string }[];
  addChatMsg: (role: "user" | "assistant", content: string) => void;
  clearChat: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  token: null,
  username: null,
  plano: null,
  setAuth: (token, username, plano) => set({ token, username, plano }),
  logout: () => set({ token: null, username: null, plano: null, demandaAtiva: null }),

  demandas: [],
  setDemandas: (demandas) => set({ demandas }),

  demandaAtiva: null,
  setDemandaAtiva: (demandaAtiva) => set({ demandaAtiva, relatorio: "", chatHistory: [], progressoMsgs: [] }),

  relatorio: "",
  setRelatorio: (relatorio) => set({ relatorio }),

  progressoMsgs: [],
  addProgresso: (msg) => set((s) => ({ progressoMsgs: [...s.progressoMsgs, msg] })),
  clearProgresso: () => set({ progressoMsgs: [] }),
  analisando: false,
  setAnalisando: (analisando) => set({ analisando }),

  chatHistory: [],
  addChatMsg: (role, content) => set((s) => ({
    chatHistory: [...s.chatHistory, { role, content }],
  })),
  clearChat: () => set({ chatHistory: [] }),
}));
