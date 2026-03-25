"""
Auth — APEX-LEGAL
=================
Re-exporta de analista_processual.auth (fonte de verdade durante migração).
Em Phase 2 este módulo absorverá a implementação completa com JWT.
"""
from analista_processual.auth import (  # noqa: F401
    verificar_credenciais,
    registrar_usuario,
    listar_usuarios,
    obter_plano,
    alterar_plano,
    desativar_usuario,
    _db_path,
    _conectar,
)

__all__ = [
    "verificar_credenciais",
    "registrar_usuario",
    "listar_usuarios",
    "obter_plano",
    "alterar_plano",
    "desativar_usuario",
]
