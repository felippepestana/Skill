"""
Workspace — Gerenciamento de Demandas Jurídicas
================================================
Mantém uma pasta base (~/.demandas/ ou DEMANDAS_DIR) com subpastas
para cada demanda. Cada demanda contém:

  nome-da-demanda/
  ├── .contexto.json        ← metadados (data de criação, última análise…)
  ├── processo/             ← peças processuais principais (PDFs, TXTs…)
  ├── documentos/           ← outros documentos da demanda
  ├── instrucoes.md         ← instruções/notas do usuário
  └── relatorio/
      └── relatorio_estrategico_YYYY-MM-DD_HHMM.md
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path


# ─── Pasta base ───────────────────────────────────────────────────────────────

def _pasta_base() -> Path:
    """
    Retorna a pasta raiz das demandas.
    Pode ser sobrescrita pela variável de ambiente DEMANDAS_DIR.
    """
    base = os.environ.get("DEMANDAS_DIR")
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / "demandas"


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _slug(nome: str) -> str:
    """Converte 'Fulano vs. Ciclano (2024)' → 'fulano_vs_ciclano_2024'."""
    s = nome.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s[:80]  # limite razoável de tamanho


def _extensoes_documento() -> set[str]:
    return {".pdf", ".txt", ".md", ".docx", ".odt", ".rtf", ".html"}


def _listar_docs(pasta: Path) -> list[Path]:
    """Retorna todos os documentos suportados em *pasta* (não recursivo)."""
    if not pasta.exists():
        return []
    return sorted(
        p for p in pasta.iterdir()
        if p.is_file() and p.suffix.lower() in _extensoes_documento()
    )


# ─── DemandaWorkspace ─────────────────────────────────────────────────────────

class DemandaWorkspace:
    """Representa o workspace de uma demanda jurídica."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self.nome = caminho.name

    # Subpastas ----------------------------------------------------------------

    @property
    def pasta_processo(self) -> Path:
        return self.caminho / "processo"

    @property
    def pasta_documentos(self) -> Path:
        return self.caminho / "documentos"

    @property
    def pasta_relatorio(self) -> Path:
        return self.caminho / "relatorio"

    @property
    def arquivo_instrucoes(self) -> Path:
        return self.caminho / "instrucoes.md"

    @property
    def arquivo_contexto(self) -> Path:
        return self.caminho / ".contexto.json"

    # Metadados ----------------------------------------------------------------

    def _ler_contexto(self) -> dict:
        if self.arquivo_contexto.exists():
            try:
                return json.loads(self.arquivo_contexto.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {}

    def _salvar_contexto(self, dados: dict) -> None:
        self.arquivo_contexto.write_text(
            json.dumps(dados, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def registrar_analise(self, caminho_relatorio: str) -> None:
        ctx = self._ler_contexto()
        ctx["ultima_analise"] = datetime.now().isoformat()
        ctx["ultimo_relatorio"] = caminho_relatorio
        self._salvar_contexto(ctx)

    def data_criacao(self) -> str:
        return self._ler_contexto().get("criado_em", "desconhecida")

    def ultima_analise(self) -> str | None:
        return self._ler_contexto().get("ultima_analise")

    # Documentos ---------------------------------------------------------------

    def documentos_processo(self) -> list[Path]:
        return _listar_docs(self.pasta_processo)

    def outros_documentos(self) -> list[Path]:
        return _listar_docs(self.pasta_documentos)

    def todos_pdfs(self) -> list[str]:
        """Retorna caminhos absolutos de todos os PDFs da demanda."""
        pdfs: list[str] = []
        for pasta in (self.pasta_processo, self.pasta_documentos):
            pdfs.extend(
                str(p) for p in _listar_docs(pasta) if p.suffix.lower() == ".pdf"
            )
        return pdfs

    def todos_textos(self) -> list[str]:
        """Retorna caminhos de documentos de texto (não PDF)."""
        exts = {".txt", ".md", ".docx", ".odt", ".rtf", ".html"}
        textos: list[str] = []
        for pasta in (self.pasta_processo, self.pasta_documentos):
            textos.extend(
                str(p) for p in _listar_docs(pasta)
                if p.suffix.lower() in exts
            )
        return textos

    # Instruções ---------------------------------------------------------------

    def ler_instrucoes(self) -> str:
        if self.arquivo_instrucoes.exists():
            return self.arquivo_instrucoes.read_text(encoding="utf-8").strip()
        return ""

    def adicionar_instrucao(self, texto: str) -> None:
        """Acrescenta uma instrução ao arquivo de instruções com timestamp."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        bloco = f"\n\n---\n*{ts}*\n\n{texto.strip()}\n"
        if self.arquivo_instrucoes.exists():
            conteudo = self.arquivo_instrucoes.read_text(encoding="utf-8")
        else:
            conteudo = "# Instruções e Notas do Usuário\n"
        self.arquivo_instrucoes.write_text(conteudo + bloco, encoding="utf-8")

    # Relatório ----------------------------------------------------------------

    def novo_caminho_relatorio(self) -> Path:
        self.pasta_relatorio.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        return self.pasta_relatorio / f"relatorio_estrategico_{ts}.md"

    def ultimo_relatorio(self) -> Path | None:
        if not self.pasta_relatorio.exists():
            return None
        relatorios = sorted(
            p for p in self.pasta_relatorio.iterdir()
            if p.is_file() and p.suffix == ".md"
        )
        return relatorios[-1] if relatorios else None

    # Resumo -------------------------------------------------------------------

    def resumo(self) -> str:
        docs_proc = self.documentos_processo()
        docs_out = self.outros_documentos()
        tem_instrucoes = self.arquivo_instrucoes.exists()
        ultimo_rel = self.ultimo_relatorio()
        ultima = self.ultima_analise()

        linhas = [
            f"Demanda : {self.nome}",
            f"Caminho : {self.caminho}",
            f"Criado  : {self.data_criacao()}",
        ]
        if ultima:
            linhas.append(f"Última análise: {ultima}")
        linhas.append(
            f"Processo: {len(docs_proc)} doc(s) — "
            + (", ".join(p.name for p in docs_proc) if docs_proc else "nenhum")
        )
        linhas.append(
            f"Outros  : {len(docs_out)} doc(s) — "
            + (", ".join(p.name for p in docs_out) if docs_out else "nenhum")
        )
        linhas.append(f"Instruções: {'sim' if tem_instrucoes else 'não'}")
        if ultimo_rel:
            linhas.append(f"Último relatório: {ultimo_rel.name}")
        return "\n".join(linhas)


# ─── API pública ──────────────────────────────────────────────────────────────

def criar_demanda(nome: str) -> DemandaWorkspace:
    """
    Cria uma nova demanda com a estrutura de pastas padrão.

    Args:
        nome: Nome da demanda (ex: "Fulano vs Ciclano 2024").

    Returns:
        DemandaWorkspace pronto para uso.

    Raises:
        FileExistsError: Se a demanda já existir.
    """
    base = _pasta_base()
    slug = _slug(nome)
    caminho = base / slug

    if caminho.exists():
        raise FileExistsError(f"Demanda já existe: {caminho}")

    # Estrutura de pastas
    for sub in ("processo", "documentos", "relatorio"):
        (caminho / sub).mkdir(parents=True)

    # Arquivo de instruções inicial
    instrucoes = caminho / "instrucoes.md"
    instrucoes.write_text(
        f"# Instruções e Notas — {nome}\n\n"
        "Adicione aqui instruções para direcionar a análise.\n"
        "Exemplos:\n"
        "- Foque na questão da prescrição\n"
        "- Verifique a competência do juízo\n"
        "- Compare com o precedente XYZ do STJ\n",
        encoding="utf-8",
    )

    # Metadados iniciais
    ws = DemandaWorkspace(caminho)
    ws._salvar_contexto({
        "nome_original": nome,
        "criado_em": datetime.now().isoformat(),
        "slug": slug,
    })

    return ws


def listar_demandas() -> list[DemandaWorkspace]:
    """Retorna todas as demandas existentes, ordenadas por nome."""
    base = _pasta_base()
    if not base.exists():
        return []
    return sorted(
        (DemandaWorkspace(p) for p in base.iterdir() if p.is_dir()),
        key=lambda w: w.nome,
    )


def obter_demanda(nome_ou_slug: str) -> DemandaWorkspace:
    """
    Encontra uma demanda pelo nome ou slug.

    Raises:
        FileNotFoundError: Se a demanda não existir.
    """
    base = _pasta_base()
    slug = _slug(nome_ou_slug)

    # Tentativa direta pelo slug
    direto = base / slug
    if direto.exists():
        return DemandaWorkspace(direto)

    # Tentativa pelo nome original nos metadados
    for ws in listar_demandas():
        ctx = ws._ler_contexto()
        if ctx.get("nome_original", "").lower() == nome_ou_slug.lower():
            return ws

    raise FileNotFoundError(
        f"Demanda não encontrada: '{nome_ou_slug}'\n"
        f"Pasta base: {base}\n"
        "Use 'listar' para ver as demandas disponíveis."
    )


def pasta_base() -> Path:
    """Retorna (e cria se necessário) a pasta base das demandas."""
    base = _pasta_base()
    base.mkdir(parents=True, exist_ok=True)
    return base
