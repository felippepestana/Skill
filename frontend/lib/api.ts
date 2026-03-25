/**
 * APEX-LEGAL — Cliente API
 * Centraliza todas as chamadas REST e WebSocket ao backend FastAPI.
 */

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS  = process.env.NEXT_PUBLIC_WS_URL  ?? "ws://localhost:8000";

// ─── Token de sessão ────────────────────────────────────────────────────────

let _token: string | null = null;

export function setToken(t: string) { _token = t; }
export function getToken() { return _token; }
export function clearToken() { _token = null; }

function headers(extra?: Record<string, string>) {
  return {
    "Content-Type": "application/json",
    ...((_token) ? { Authorization: `Bearer ${_token}` } : {}),
    ...extra,
  };
}

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method,
    headers: headers(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro na requisição");
  }
  return res.json();
}

// ─── Auth ───────────────────────────────────────────────────────────────────

export interface LoginResponse {
  token: string;
  username: string;
  plano: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const data = await req<LoginResponse>("POST", "/auth/login", { username, password });
  setToken(data.token);
  return data;
}

export async function register(
  username: string,
  password: string,
  email: string,
  plano = "free",
) {
  return req("POST", "/auth/register", { username, password, email, plano });
}

// ─── Demandas ───────────────────────────────────────────────────────────────

export interface DemandaResumo {
  slug: string;
  nome: string;
  criado_em: string;
  ultima_analise: string | null;
  total_docs: number;
  tem_relatorio: boolean;
}

export async function listarDemandas(): Promise<DemandaResumo[]> {
  const data = await req<{ demandas: DemandaResumo[] }>("GET", "/demandas");
  return data.demandas;
}

export async function criarDemanda(nome: string): Promise<{ slug: string; nome: string }> {
  return req("POST", "/demandas", { nome });
}

export interface DemandaDetalhes {
  slug: string;
  nome: string;
  criado_em: string;
  ultima_analise: string | null;
  instrucoes: string;
  arvore: string;
  citacoes: unknown[];
  timeline: unknown[];
}

export async function obterDemanda(slug: string): Promise<DemandaDetalhes> {
  return req("GET", `/demandas/${slug}`);
}

export async function obterRelatorio(slug: string): Promise<string> {
  const data = await req<{ conteudo: string }>("GET", `/demandas/${slug}/relatorio`);
  return data.conteudo;
}

export async function salvarRelatorio(slug: string, conteudo: string) {
  return req("PUT", `/demandas/${slug}/relatorio`, { conteudo });
}

export async function salvarInstrucoes(slug: string, texto: string) {
  return req("PUT", `/demandas/${slug}/instrucoes`, { texto });
}

export async function obterCitacoes(slug: string) {
  const data = await req<{ citacoes: unknown[] }>("GET", `/demandas/${slug}/citacoes`);
  return data.citacoes;
}

export async function obterTimeline(slug: string) {
  const data = await req<{ timeline: unknown[] }>("GET", `/demandas/${slug}/timeline`);
  return data.timeline;
}

export async function uploadArquivo(slug: string, file: File, pasta: "processo" | "documentos") {
  const formData = new FormData();
  formData.append("arquivo", file);
  const res = await fetch(`${API}/demandas/${slug}/upload?pasta=${pasta}`, {
    method: "POST",
    headers: _token ? { Authorization: `Bearer ${_token}` } : {},
    body: formData,
  });
  if (!res.ok) throw new Error("Erro no upload");
  return res.json();
}

export async function consultar(slug: string, pergunta: string): Promise<string> {
  const data = await req<{ resposta: string }>("POST", `/demandas/${slug}/consultar`, { pergunta });
  return data.resposta;
}

// ─── WebSocket — streaming de análise ───────────────────────────────────────

export interface MensagemWS {
  tipo: "progresso" | "concluido" | "erro";
  msg?: string;
  resultado?: string;
}

export function criarWsAnalise(
  slug: string,
  acao: "analisar" | "delta",
  instrucao: string | undefined,
  onMensagem: (m: MensagemWS) => void,
  onConcluido: (resultado: string) => void,
  onErro: (msg: string) => void,
): () => void {
  if (!_token) {
    onErro("Não autenticado");
    return () => {};
  }

  const ws = new WebSocket(`${WS}/ws/${slug}?token=${_token}`);

  ws.onopen = () => {
    ws.send(JSON.stringify({ acao, instrucao }));
  };

  ws.onmessage = (ev) => {
    const msg: MensagemWS = JSON.parse(ev.data);
    onMensagem(msg);
    if (msg.tipo === "concluido") {
      onConcluido(msg.resultado ?? "");
      ws.close();
    } else if (msg.tipo === "erro") {
      onErro(msg.msg ?? "Erro desconhecido");
      ws.close();
    }
  };

  ws.onerror = () => onErro("Erro na conexão WebSocket");

  return () => ws.close();
}
