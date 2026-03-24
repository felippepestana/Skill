"""
Autenticação — Analista Processual
====================================
Gerencia usuários com SQLite + bcrypt. Suporta:
- Login via Gradio auth=
- Cadastro via CLI (adduser)
- Planos para evolução SaaS (free, pro, enterprise)

Banco: {DEMANDAS_DIR}/users.db  (ou ~/demandas/users.db)
"""

from __future__ import annotations

import os
import sqlite3
import time
import threading
from datetime import datetime
from pathlib import Path


# ─── Rate limiting em memória (brute-force protection) ────────────────────────

_JANELA_SEGUNDOS = 300   # Janela deslizante de 5 minutos
_MAX_TENTATIVAS = 10     # Máximo de falhas antes do bloqueio

_tentativas_falhas: dict[str, list[float]] = {}
_tentativas_lock = threading.Lock()


def _verificar_rate_limit(username: str) -> bool:
    """Retorna True se o login pode prosseguir, False se bloqueado."""
    agora = time.monotonic()
    with _tentativas_lock:
        historico = _tentativas_falhas.get(username, [])
        historico = [t for t in historico if agora - t < _JANELA_SEGUNDOS]
        _tentativas_falhas[username] = historico
        return len(historico) < _MAX_TENTATIVAS


def _registrar_falha(username: str) -> None:
    """Registra uma tentativa de login falha."""
    with _tentativas_lock:
        historico = _tentativas_falhas.get(username, [])
        historico.append(time.monotonic())
        _tentativas_falhas[username] = historico


def _limpar_falhas(username: str) -> None:
    """Remove o histórico de falhas após login bem-sucedido."""
    with _tentativas_lock:
        _tentativas_falhas.pop(username, None)


# ─── Localização do banco ──────────────────────────────────────────────────────

def _db_path() -> Path:
    base = os.environ.get("DEMANDAS_DIR")
    if base:
        raiz = Path(base).expanduser().resolve()
    else:
        raiz = Path.home() / "demandas"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz / "users.db"


# ─── Inicialização do schema ───────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS users (
    username            TEXT PRIMARY KEY,
    password_hash       TEXT NOT NULL,
    email               TEXT UNIQUE NOT NULL,
    plano               TEXT NOT NULL DEFAULT 'free',
    storage_usado_bytes INTEGER NOT NULL DEFAULT 0,
    stripe_customer_id  TEXT,
    stripe_subscription_id TEXT,
    criado_em           TEXT NOT NULL,
    ativo               INTEGER NOT NULL DEFAULT 1
);
"""


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(_DDL)
    conn.commit()
    return conn


# ─── bcrypt via passlib (opcional, fallback para sha256 simples) ───────────────

try:
    from passlib.context import CryptContext as _CryptContext
    _pwd_context = _CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _hash_senha(senha: str) -> str:
        return _pwd_context.hash(senha)

    def _verificar_hash(senha: str, hash_: str) -> bool:
        return _pwd_context.verify(senha, hash_)

except ImportError:
    # Fallback: sha256 — funcional mas menos seguro. Instale passlib[bcrypt].
    import hashlib as _hashlib

    def _hash_senha(senha: str) -> str:  # type: ignore[misc]
        return "sha256:" + _hashlib.sha256(senha.encode()).hexdigest()

    def _verificar_hash(senha: str, hash_: str) -> bool:  # type: ignore[misc]
        if hash_.startswith("sha256:"):
            return hash_ == "sha256:" + _hashlib.sha256(senha.encode()).hexdigest()
        return False


# ─── API pública ───────────────────────────────────────────────────────────────

def verificar_credenciais(username: str, password: str) -> bool:
    """
    Verifica usuário e senha com proteção contra brute-force.
    Após 10 tentativas falhas em 5 minutos, bloqueia o username.
    Usado diretamente como: app.launch(auth=verificar_credenciais)
    """
    if not username or not password:
        return False
    username = username.strip().lower()
    if not _verificar_rate_limit(username):
        return False  # Bloqueado por excesso de tentativas falhas
    try:
        conn = _conectar()
        row = conn.execute(
            "SELECT password_hash, ativo FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        conn.close()
        if not row or not row["ativo"]:
            _registrar_falha(username)
            return False
        sucesso = _verificar_hash(password, row["password_hash"])
        if sucesso:
            _limpar_falhas(username)
        else:
            _registrar_falha(username)
        return sucesso
    except Exception:
        return False


def registrar_usuario(
    username: str,
    password: str,
    email: str,
    plano: str = "free",
) -> None:
    """
    Cria um novo usuário.

    Raises:
        ValueError: se username ou email já existirem, ou se os dados forem inválidos.
    """
    username = username.strip().lower()
    email = email.strip().lower()

    if not username or not password or not email:
        raise ValueError("username, password e email são obrigatórios.")
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if "@" not in email:
        raise ValueError("E-mail inválido.")
    if plano not in ("free", "pro", "enterprise"):
        raise ValueError(f"Plano inválido: {plano}. Use: free, pro, enterprise.")

    hash_ = _hash_senha(password)
    conn = _conectar()
    try:
        conn.execute(
            """
            INSERT INTO users (username, password_hash, email, plano, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, hash_, email, plano, datetime.now().isoformat()),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise ValueError(f"Usuário ou e-mail já cadastrado: {e}") from e
    finally:
        conn.close()


def listar_usuarios() -> list[dict]:
    """Retorna lista de todos os usuários (sem password_hash)."""
    conn = _conectar()
    rows = conn.execute(
        "SELECT username, email, plano, storage_usado_bytes, criado_em, ativo FROM users ORDER BY criado_em"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def obter_plano(username: str) -> str:
    """Retorna o plano do usuário ('free', 'pro', 'enterprise')."""
    conn = _conectar()
    row = conn.execute(
        "SELECT plano FROM users WHERE username = ? AND ativo = 1",
        (username.strip().lower(),),
    ).fetchone()
    conn.close()
    return row["plano"] if row else "free"


def alterar_plano(username: str, plano: str) -> None:
    """Altera o plano de um usuário existente."""
    if plano not in ("free", "pro", "enterprise"):
        raise ValueError(f"Plano inválido: {plano}")
    conn = _conectar()
    conn.execute(
        "UPDATE users SET plano = ? WHERE username = ?",
        (plano, username.strip().lower()),
    )
    conn.commit()
    conn.close()


def desativar_usuario(username: str) -> None:
    """Desativa (não exclui) um usuário."""
    conn = _conectar()
    conn.execute(
        "UPDATE users SET ativo = 0 WHERE username = ?",
        (username.strip().lower(),),
    )
    conn.commit()
    conn.close()
