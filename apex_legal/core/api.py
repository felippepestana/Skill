"""
API REST + WebSocket — APEX-LEGAL PERFORMANCE
=============================================
FastAPI app que expõe todas as funcionalidades do workspace jurídico
para consumo pelo frontend Next.js.

Endpoints:
  POST   /auth/login                     → token de sessão
  POST   /auth/register                  → cadastro de usuário
  GET    /demandas                        → listar demandas do usuário
  POST   /demandas                        → criar demanda
  GET    /demandas/{slug}                 → detalhes da demanda
  POST   /demandas/{slug}/upload          → upload de documento
  PUT    /demandas/{slug}/instrucoes      → salvar instruções
  GET    /demandas/{slug}/relatorio       → último relatório
  PUT    /demandas/{slug}/relatorio       → salvar edição do relatório
  GET    /demandas/{slug}/citacoes        → citações rastreadas
  GET    /demandas/{slug}/timeline        → linha do tempo
  WS     /ws/{slug}                       → streaming de análise em tempo real
  POST   /demandas/{slug}/analisar        → iniciar análise completa (via WS)
  POST   /demandas/{slug}/delta           → iniciar análise delta (via WS)
  POST   /demandas/{slug}/consultar       → consulta pontual ao squad
  POST   /demandas/{slug}/inteligencia    → análise de inteligência
  GET    /usuarios                        → listar usuários (admin)
  PUT    /usuarios/{username}/plano       → alterar plano (admin)
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated

import anyio
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from .auth import verificar_credenciais, registrar_usuario, listar_usuarios, obter_plano, alterar_plano
from .workspace import criar_demanda, listar_demandas, obter_demanda, pasta_base, DemandaWorkspace


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="APEX-LEGAL PERFORMANCE",
    description="API do workspace jurídico multi-agente",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_security = HTTPBasic()


# ─── Autenticação simples via HTTP Basic → token de sessão ────────────────────

_sessions: dict[str, dict] = {}  # token → {username, expira_em}
_SESSION_HOURS = 24


def _gerar_token() -> str:
    return secrets.token_urlsafe(32)


def _criar_sessao(username: str) -> str:
    token = _gerar_token()
    _sessions[token] = {
        "username": username,
        "expira_em": datetime.now() + timedelta(hours=_SESSION_HOURS),
    }
    return token


def _resolver_usuario(authorization: str | None) -> str:
    """Extrai username de um token Bearer. Lança 401 se inválido."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    token = authorization[7:]
    sessao = _sessions.get(token)
    if not sessao:
        raise HTTPException(status_code=401, detail="Token inválido")
    if datetime.now() > sessao["expira_em"]:
        _sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Sessão expirada")
    return sessao["username"]


def _usuario_atual(
    credentials: Annotated[HTTPBasicCredentials, Depends(_security)],
) -> str:
    """Dependency que autentica via HTTP Basic (login direto)."""
    if not verificar_credenciais(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ─── Schemas Pydantic ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    plano: str


class RegistroRequest(BaseModel):
    username: str
    password: str
    email: str
    plano: str = "free"


class CriarDemandaRequest(BaseModel):
    nome: str


class InstrucoesRequest(BaseModel):
    texto: str


class ConsultaRequest(BaseModel):
    pergunta: str


class AnalisarRequest(BaseModel):
    instrucao: str | None = None


class AlterarPlanoRequest(BaseModel):
    plano: str


class RelatorioPatchRequest(BaseModel):
    conteudo: str


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(req: LoginRequest):
    if not verificar_credenciais(req.username, req.password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = _criar_sessao(req.username.strip().lower())
    return LoginResponse(
        token=token,
        username=req.username.strip().lower(),
        plano=obter_plano(req.username),
    )


@app.post("/auth/register", status_code=201, tags=["auth"])
def register(req: RegistroRequest):
    try:
        registrar_usuario(req.username, req.password, req.email, req.plano)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "username": req.username.strip().lower()}


# ─── Demandas ─────────────────────────────────────────────────────────────────

def _auth_header(request) -> str:
    """Extrai username do header Authorization da request."""
    auth = request.headers.get("Authorization")
    return _resolver_usuario(auth)


@app.get("/demandas", tags=["demandas"])
async def listar(request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    demandas = listar_demandas(username)
    return {"demandas": [
        {
            "slug": ws.slug(),
            "nome": ws.nome_original(),
            "criado_em": ws.criado_em(),
            "ultima_analise": ws.ultima_analise(),
            "total_docs": ws.total_documentos(),
            "tem_relatorio": bool(ws.ler_ultimo_relatorio()),
        }
        for ws in demandas
    ]}


@app.post("/demandas", status_code=201, tags=["demandas"])
async def criar(req: CriarDemandaRequest, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    try:
        ws = criar_demanda(req.nome, username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"slug": ws.slug(), "nome": ws.nome_original()}


@app.get("/demandas/{slug}", tags=["demandas"])
async def detalhes(slug: str, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    ws.sincronizar_indice()
    return {
        "slug": ws.slug(),
        "nome": ws.nome_original(),
        "criado_em": ws.criado_em(),
        "ultima_analise": ws.ultima_analise(),
        "instrucoes": ws.ler_instrucoes(),
        "arvore": ws.resumo(),          # string formatada para exibição no frontend
        "citacoes": ws.citacoes_recentes(),
        "timeline": ws.timeline(),
    }


@app.post("/demandas/{slug}/upload", tags=["demandas"])
async def upload(
    slug: str,
    request: Request,
    arquivo: UploadFile = File(...),
    pasta: str = Query("processo", pattern="^(processo|documentos)$"),
):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)

    destino = ws.caminho / pasta / arquivo.filename
    destino.parent.mkdir(parents=True, exist_ok=True)

    conteudo = await arquivo.read()
    destino.write_bytes(conteudo)
    ws.sincronizar_indice()

    return {"ok": True, "arquivo": arquivo.filename, "pasta": pasta}


@app.put("/demandas/{slug}/instrucoes", tags=["demandas"])
async def salvar_instrucoes(slug: str, req: InstrucoesRequest, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    ws.adicionar_instrucao_estruturada(req.texto)
    return {"ok": True}


@app.get("/demandas/{slug}/relatorio", tags=["demandas"])
async def obter_relatorio(slug: str, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    conteudo = ws.ler_ultimo_relatorio()
    if not conteudo:
        raise HTTPException(status_code=404, detail="Nenhum relatório disponível")
    return {"conteudo": conteudo}


@app.put("/demandas/{slug}/relatorio", tags=["demandas"])
async def salvar_relatorio(slug: str, req: RelatorioPatchRequest, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    caminho = ws.caminho_ultimo_relatorio()
    if caminho is None:
        raise HTTPException(status_code=404, detail="Nenhum relatório para editar")
    caminho.write_text(req.conteudo, encoding="utf-8")
    return {"ok": True}


@app.get("/demandas/{slug}/citacoes", tags=["demandas"])
async def obter_citacoes(slug: str, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    return {"citacoes": ws.citacoes_recentes()}


@app.get("/demandas/{slug}/timeline", tags=["demandas"])
async def obter_timeline(slug: str, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    return {"timeline": ws.timeline()}


# ─── Análise via REST (dispara em thread, retorna job_id) ─────────────────────

_jobs: dict[str, dict] = {}  # job_id → {status, resultado, progresso[]}


@app.post("/demandas/{slug}/analisar", tags=["analise"])
async def analisar(slug: str, req: AnalisarRequest, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    job_id = _iniciar_job(ws, req.instrucao, modo_delta=False)
    return {"job_id": job_id}


@app.post("/demandas/{slug}/delta", tags=["analise"])
async def delta(slug: str, req: AnalisarRequest, request: Request):
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    job_id = _iniciar_job(ws, req.instrucao, modo_delta=True)
    return {"job_id": job_id}


@app.post("/demandas/{slug}/consultar", tags=["analise"])
async def consultar(slug: str, req: ConsultaRequest, request: Request):
    from analista_processual.squad import consultar_demanda as _consultar
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    resultado = await asyncio.to_thread(_consultar, ws, req.pergunta)
    return {"resposta": resultado}


@app.post("/demandas/{slug}/inteligencia", tags=["analise"])
async def inteligencia(slug: str, request: Request):
    from apex_legal.squads.inteligencia.squad import executar as _intel
    username = _resolver_usuario(request.headers.get("Authorization"))
    ws = _obter_ws(slug, username)
    resultado = await asyncio.to_thread(_intel, ws)
    return {"resultado": resultado}


# ─── WebSocket — streaming de progresso ───────────────────────────────────────

@app.websocket("/ws/{slug}")
async def websocket_analise(ws_conn: WebSocket, slug: str, token: str = Query(...)):
    """
    WebSocket para acompanhar análise em tempo real.
    Fluxo:
      1. Cliente conecta: ws://host/ws/{slug}?token=<bearer_token>
      2. Servidor valida token
      3. Cliente envia JSON: {"acao": "analisar"|"delta", "instrucao": "..."}
      4. Servidor streama mensagens de progresso: {"tipo": "progresso", "msg": "..."}
      5. Quando concluído: {"tipo": "concluido", "resultado": "..."}
    """
    try:
        username = _resolver_usuario(f"Bearer {token}")
    except HTTPException:
        await ws_conn.close(code=4001, reason="Token inválido")
        return

    ws = _obter_ws_ou_none(slug, username)
    if ws is None:
        await ws_conn.close(code=4004, reason="Demanda não encontrada")
        return

    await ws_conn.accept()

    try:
        dados = await ws_conn.receive_json()
        acao = dados.get("acao", "analisar")
        instrucao = dados.get("instrucao")
        modo_delta = acao == "delta"

        progresso_q: queue.Queue = queue.Queue()
        resultado_container: list[str] = []
        erro_container: list[str] = []

        def _callback(msg: str) -> None:
            progresso_q.put({"tipo": "progresso", "msg": msg})

        def _executar_em_thread() -> None:
            from apex_legal.squads.analise.squad import executar_demanda_apex
            try:
                resultado = executar_demanda_apex(ws, instrucao, modo_delta, _callback)
                resultado_container.append(resultado)
            except Exception as e:
                erro_container.append(str(e))
            finally:
                progresso_q.put(None)  # Sentinel

        t = threading.Thread(target=_executar_em_thread, daemon=True)
        t.start()

        while True:
            try:
                item = await asyncio.to_thread(progresso_q.get, timeout=120)
            except Exception:
                break
            if item is None:
                break
            await ws_conn.send_json(item)

        if erro_container:
            await ws_conn.send_json({"tipo": "erro", "msg": erro_container[0]})
        else:
            await ws_conn.send_json({
                "tipo": "concluido",
                "resultado": resultado_container[0] if resultado_container else "",
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws_conn.send_json({"tipo": "erro", "msg": str(e)})
        except Exception:
            pass


# ─── Admin ────────────────────────────────────────────────────────────────────

@app.get("/usuarios", tags=["admin"])
async def listar_users(request: Request):
    _resolver_usuario(request.headers.get("Authorization"))
    return {"usuarios": listar_usuarios()}


@app.put("/usuarios/{username}/plano", tags=["admin"])
async def alterar_plano_usuario(username: str, req: AlterarPlanoRequest, request: Request):
    _resolver_usuario(request.headers.get("Authorization"))
    try:
        alterar_plano(username, req.plano)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _obter_ws(slug: str, username: str) -> DemandaWorkspace:
    ws = obter_demanda(slug, username)
    if ws is None:
        raise HTTPException(status_code=404, detail=f"Demanda '{slug}' não encontrada")
    return ws


def _obter_ws_ou_none(slug: str, username: str) -> DemandaWorkspace | None:
    return obter_demanda(slug, username)


def _iniciar_job(
    ws: DemandaWorkspace,
    instrucao: str | None,
    modo_delta: bool,
) -> str:
    """Dispara análise em thread e retorna job_id."""
    from apex_legal.squads.analise.squad import executar_demanda_apex
    job_id = secrets.token_urlsafe(12)
    _jobs[job_id] = {"status": "em_andamento", "progresso": [], "resultado": None}

    def _callback(msg: str) -> None:
        if job_id in _jobs:
            _jobs[job_id]["progresso"].append(msg)

    def _run() -> None:
        try:
            resultado = executar_demanda_apex(ws, instrucao, modo_delta, _callback)
            _jobs[job_id].update({"status": "concluido", "resultado": resultado})
        except Exception as e:
            _jobs[job_id].update({"status": "erro", "erro": str(e)})

    threading.Thread(target=_run, daemon=True).start()
    return job_id


@app.get("/jobs/{job_id}", tags=["analise"])
async def status_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job


# ─── Entry point ──────────────────────────────────────────────────────────────

def iniciar(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
    import uvicorn
    uvicorn.run("apex_legal.core.api:app", host=host, port=port, reload=reload)
