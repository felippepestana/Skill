"""
Workspace — APEX-LEGAL
======================
Re-exporta de analista_processual.workspace (fonte de verdade durante migração).
"""
from analista_processual.workspace import (  # noqa: F401
    criar_demanda,
    listar_demandas,
    obter_demanda,
    pasta_base,
    DemandaWorkspace,
    DocIndexado,
    classificar_tipo_peca,
)

__all__ = [
    "criar_demanda",
    "listar_demandas",
    "obter_demanda",
    "pasta_base",
    "DemandaWorkspace",
    "DocIndexado",
    "classificar_tipo_peca",
]
