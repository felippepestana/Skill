"""
APEX-LEGAL PERFORMANCE
======================
Workspace jurídico multi-agente construído sobre o Claude Agent SDK.

Pacotes:
- apex_legal.core       — infraestrutura: auth, workspace, API FastAPI
- apex_legal.squads     — squads especializados (analise, documental, inteligencia)
"""

from .core.workspace import (
    criar_demanda,
    listar_demandas,
    obter_demanda,
    pasta_base,
    DemandaWorkspace,
    DocIndexado,
    classificar_tipo_peca,
)
from .core.auth import (
    verificar_credenciais,
    registrar_usuario,
    listar_usuarios,
    obter_plano,
    alterar_plano,
)
from .squads.analise.squad import (
    executar,
    executar_demanda,
    consultar_demanda,
    SQUAD_AGENTS,
)

__version__ = "2.0.0"
__all__ = [
    # workspace
    "criar_demanda",
    "listar_demandas",
    "obter_demanda",
    "pasta_base",
    "DemandaWorkspace",
    "DocIndexado",
    "classificar_tipo_peca",
    # auth
    "verificar_credenciais",
    "registrar_usuario",
    "listar_usuarios",
    "obter_plano",
    "alterar_plano",
    # squad
    "executar",
    "executar_demanda",
    "consultar_demanda",
    "SQUAD_AGENTS",
]
