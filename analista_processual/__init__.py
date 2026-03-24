from .squad import (
    executar,
    executar_demanda,
    consultar_demanda,
    abrir_squad,
    analisar_pdf_direto,
)
from .workspace import (
    criar_demanda,
    listar_demandas,
    obter_demanda,
    pasta_base,
    DemandaWorkspace,
    DocIndexado,
    classificar_tipo_peca,
)

__all__ = [
    # squad
    "executar",
    "executar_demanda",
    "consultar_demanda",
    "abrir_squad",
    "analisar_pdf_direto",
    # workspace
    "criar_demanda",
    "listar_demandas",
    "obter_demanda",
    "pasta_base",
    "DemandaWorkspace",
    "DocIndexado",
    "classificar_tipo_peca",
]
