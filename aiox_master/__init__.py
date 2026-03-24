"""
AIOX Master — Orion, orquestrador mestre de agentes e squads.
"""

from .squad import executar, chamar_aiox_master, AIOX_MASTER_AGENTS, AIOS_CORE_AGENTS

__all__ = [
    "executar",
    "chamar_aiox_master",
    "AIOX_MASTER_AGENTS",
    "AIOS_CORE_AGENTS",
]
