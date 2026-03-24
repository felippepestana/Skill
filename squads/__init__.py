"""
Squads especializados do ecosistema AIOX.

Cada squad é um pacote Python independente que segue o padrão:
  squads/<nome>/
  ├── __init__.py      — exporta SQUAD_AGENTS e executar()
  ├── squad.py         — definição dos agentes e orquestração
  └── __main__.py      — CLI entry point (python -m squads.<nome>)

Squads disponíveis:
- documental   — geração e revisão de documentos jurídicos
"""

from .documental import SQUAD_AGENTS as DOCUMENTAL_AGENTS
from .documental import executar as executar_documental

__all__ = [
    "DOCUMENTAL_AGENTS",
    "executar_documental",
]
