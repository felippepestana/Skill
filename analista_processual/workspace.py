"""
Workspace — Gerenciamento de Demandas Jurídicas
================================================
Mantém uma pasta base (~/.demandas/ ou DEMANDAS_DIR) com subpastas
para cada demanda. Cada demanda contém:

  nome-da-demanda/
  ├── .contexto.json        ← metadados (criação, última análise, índice de docs…)
  ├── processo/             ← peças processuais principais (PDFs, TXTs…)
  ├── documentos/           ← outros documentos da demanda
  ├── instrucoes.md         ← instruções/notas do usuário
  └── relatorio/
      └── relatorio_estrategico_YYYY-MM-DD_HHMM.md

Funcionalidades:
- Índice de documentos com metadados (tipo, data, status de análise)
- Classificação automática de tipo de peça pelo nome do arquivo
- Rastreamento delta: quais docs foram analisados, quais são novos
- Versionamento de instruções com timestamp
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path


# ─── Pasta base ───────────────────────────────────────────────────────────────

def _pasta_base() -> Path:
    """Retorna a pasta raiz das demandas (DEMANDAS_DIR ou ~/demandas)."""
    base = os.environ.get("DEMANDAS_DIR")
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / "demandas"


# ─── Classificação automática de tipo de peça ─────────────────────────────────

_TIPOS_PECA: list[tuple[re.Pattern, str]] = [
    (re.compile(r"peti[cç][aã]o.?inicial|inicial", re.I), "Petição Inicial"),
    (re.compile(r"contesta[cç][aã]o", re.I), "Contestação"),
    (re.compile(r"r[eé]plica", re.I), "Réplica"),
    (re.compile(r"senten[cç]a", re.I), "Sentença"),
    (re.compile(r"ac[oó]rd[aã]o", re.I), "Acórdão"),
    (re.compile(r"despacho", re.I), "Despacho"),
    (re.compile(r"decis[aã]o", re.I), "Decisão Interlocutória"),
    (re.compile(r"recurso.?apelaç[aã]o|apela[cç][aã]o", re.I), "Apelação"),
    (re.compile(r"agravo", re.I), "Agravo"),
    (re.compile(r"embargo", re.I), "Embargos"),
    (re.compile(r"mandado|manda[nm]us", re.I), "Mandado"),
    (re.compile(r"intima[cç][aã]o", re.I), "Intimação"),
    (re.compile(r"cita[cç][aã]o", re.I), "Citação"),
    (re.compile(r"contrato", re.I), "Contrato"),
    (re.compile(r"procura[cç][aã]o", re.I), "Procuração"),
    (re.compile(r"nota.?fiscal|nf[e]?", re.I), "Nota Fiscal"),
    (re.compile(r"laudo|per[ií]cia", re.I), "Laudo Pericial"),
    (re.compile(r"ata|audiencia|audi[eê]ncia", re.I), "Ata de Audiência"),
    (re.compile(r"oficio|ofício", re.I), "Ofício"),
]


def classificar_tipo_peca(nome_arquivo: str) -> str:
    """Infere o tipo de peça processual pelo nome do arquivo."""
    nome = Path(nome_arquivo).stem
    for padrao, tipo in _TIPOS_PECA:
        if padrao.search(nome):
            return tipo
    return "Documento"


# ─── Helpers internos ─────────────────────────────────────────────────────────

def _slug(nome: str) -> str:
    """'Fulano vs. Ciclano (2024)' → 'fulano_vs_ciclano_2024'"""
    s = nome.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s[:80]


def _extensoes_documento() -> set[str]:
    return {".pdf", ".txt", ".md", ".docx", ".odt", ".rtf", ".html"}


def _listar_docs(pasta: Path) -> list[Path]:
    if not pasta.exists():
        return []
    return sorted(
        p for p in pasta.iterdir()
        if p.is_file() and p.suffix.lower() in _extensoes_documento()
    )


def _tamanho_humano(bytes_: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.0f} {unit}"
        bytes_ /= 1024
    return f"{bytes_:.1f} GB"


# ─── Modelo de documento indexado ─────────────────────────────────────────────

@dataclass
class DocIndexado:
    """Metadados de um documento dentro de uma demanda."""
    nome: str
    pasta: str                    # "processo" | "documentos"
    caminho: str
    tipo: str                     # classificado automaticamente
    extensao: str
    tamanho: str
    adicionado_em: str
    analisado: bool = False
    analisado_em: str | None = None
    hash_modificacao: str | None = None

    @staticmethod
    def _sha256(path: Path) -> str:
        """
        SHA-256 completo do arquivo.
        Estratégia híbrida: verifica mtime+size antes de ler o arquivo inteiro,
        usando um prefixo com esses valores para evitar hashing desnecessário
        quando o arquivo não mudou.
        """
        stat = path.stat()
        # Chave rápida: se mtime e size são idênticos, arquivo provavelmente não mudou.
        # O hash inclui mtime+size+conteúdo para ser completamente confiável.
        h = hashlib.sha256()
        h.update(f"{stat.st_mtime}:{stat.st_size}:".encode())
        with open(path, "rb") as f:
            for bloco in iter(lambda: f.read(65536), b""):
                h.update(bloco)
        return h.hexdigest()

    @staticmethod
    def de_arquivo(path: Path, pasta: str) -> "DocIndexado":
        stat = path.stat()
        return DocIndexado(
            nome=path.name,
            pasta=pasta,
            caminho=str(path),
            tipo=classificar_tipo_peca(path.name),
            extensao=path.suffix.lower(),
            tamanho=_tamanho_humano(stat.st_size),
            adicionado_em=datetime.fromtimestamp(stat.st_ctime).isoformat(),
            hash_modificacao=DocIndexado._sha256(path),
        )

    def foi_modificado(self, path: Path) -> bool:
        """True se o conteúdo do arquivo mudou desde a última indexação."""
        return DocIndexado._sha256(path) != self.hash_modificacao

    def marcar_analisado(self) -> None:
        self.analisado = True
        self.analisado_em = datetime.now().isoformat()
        path = Path(self.caminho)
        if path.exists():
            self.hash_modificacao = DocIndexado._sha256(path)


# ─── DemandaWorkspace ─────────────────────────────────────────────────────────

class DemandaWorkspace:
    """Representa o workspace completo de uma demanda jurídica."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = caminho
        self.nome = caminho.name

    # ── Subpastas ─────────────────────────────────────────────────────────────

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

    # ── Metadados / contexto ──────────────────────────────────────────────────

    def _ler_contexto(self) -> dict:
        if self.arquivo_contexto.exists():
            try:
                return json.loads(self.arquivo_contexto.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {}

    def _salvar_contexto(self, dados: dict) -> None:
        """Escrita atômica via arquivo temporário + os.replace() para evitar corrupção."""
        conteudo = json.dumps(dados, ensure_ascii=False, indent=2)
        tmp = self.arquivo_contexto.with_suffix(".tmp")
        tmp.write_text(conteudo, encoding="utf-8")
        os.replace(str(tmp), str(self.arquivo_contexto))

    def data_criacao(self) -> str:
        return self._ler_contexto().get("criado_em", "desconhecida")

    def ultima_analise(self) -> str | None:
        return self._ler_contexto().get("ultima_analise")

    def nome_original(self) -> str:
        return self._ler_contexto().get("nome_original", self.nome)

    def registrar_analise(self, caminho_relatorio: str) -> None:
        ctx = self._ler_contexto()
        ctx["ultima_analise"] = datetime.now().isoformat()
        ctx["ultimo_relatorio"] = caminho_relatorio
        self._salvar_contexto(ctx)

    # ── Índice de documentos ──────────────────────────────────────────────────

    def _ler_indice(self) -> dict[str, dict]:
        """Retorna o índice salvo em .contexto.json → 'indice'."""
        return self._ler_contexto().get("indice", {})

    def _salvar_indice(self, indice: dict[str, dict]) -> None:
        ctx = self._ler_contexto()
        ctx["indice"] = indice
        self._salvar_contexto(ctx)

    @classmethod
    def _doc_de_dict_seguro(cls, dados: dict, raiz_workspace: Path) -> "DocIndexado | None":
        """
        Constrói DocIndexado a partir de dict validado.
        Valida que o caminho está dentro do workspace (evita path traversal).
        Retorna None se os dados forem inválidos.
        """
        campos_obrigatorios = {"nome", "pasta", "caminho", "tipo", "extensao", "tamanho", "adicionado_em"}
        if not campos_obrigatorios.issubset(dados.keys()):
            return None
        # Valida caminho dentro do workspace
        caminho = Path(dados["caminho"])
        try:
            caminho.resolve().relative_to(raiz_workspace.resolve())
        except ValueError:
            return None  # Path traversal detectado
        # Filtra apenas campos conhecidos
        campos_validos = set(DocIndexado.__dataclass_fields__.keys())
        dados_filtrados = {k: v for k, v in dados.items() if k in campos_validos}
        try:
            return DocIndexado(**dados_filtrados)
        except (TypeError, ValueError):
            return None

    def sincronizar_indice(self) -> list[DocIndexado]:
        """
        Varre processo/ e documentos/, sincroniza o índice e retorna
        todos os documentos atuais.
        """
        indice_salvo = self._ler_indice()
        indice_novo: dict[str, dict] = {}
        docs: list[DocIndexado] = []

        for pasta_nome, pasta_path in [
            ("processo", self.pasta_processo),
            ("documentos", self.pasta_documentos),
        ]:
            for path in _listar_docs(pasta_path):
                chave = f"{pasta_nome}/{path.name}"
                entrada_salva = indice_salvo.get(chave)

                if entrada_salva:
                    doc = DemandaWorkspace._doc_de_dict_seguro(entrada_salva, self.caminho)
                    if doc is None:
                        doc = DocIndexado.de_arquivo(path, pasta_nome)
                    elif doc.foi_modificado(path):
                        doc.analisado = False
                        doc.analisado_em = None
                        doc.hash_modificacao = DocIndexado._sha256(path)
                        doc.tamanho = _tamanho_humano(path.stat().st_size)
                else:
                    doc = DocIndexado.de_arquivo(path, pasta_nome)

                indice_novo[chave] = asdict(doc)
                docs.append(doc)

        self._salvar_indice(indice_novo)
        return docs

    def documentos_indexados(self) -> list[DocIndexado]:
        """Retorna documentos com base no índice atual (sem varrer disco)."""
        return [DocIndexado(**v) for v in self._ler_indice().values()]

    def documentos_novos(self) -> list[DocIndexado]:
        """Documentos ainda não analisados."""
        return [d for d in self.sincronizar_indice() if not d.analisado]

    def marcar_todos_analisados(self) -> None:
        """Marca todos os documentos atuais como analisados."""
        indice = self._ler_indice()
        for chave, dados in indice.items():
            doc = DocIndexado(**dados)
            path = Path(doc.caminho)
            if path.exists():
                doc.marcar_analisado()
                indice[chave] = asdict(doc)
        self._salvar_indice(indice)

    # ── Acesso a documentos por tipo ──────────────────────────────────────────

    def todos_pdfs(self) -> list[str]:
        pdfs: list[str] = []
        for pasta in (self.pasta_processo, self.pasta_documentos):
            pdfs.extend(
                str(p) for p in _listar_docs(pasta) if p.suffix.lower() == ".pdf"
            )
        return pdfs

    def todos_textos(self) -> list[str]:
        exts = {".txt", ".md", ".docx", ".odt", ".rtf", ".html"}
        textos: list[str] = []
        for pasta in (self.pasta_processo, self.pasta_documentos):
            textos.extend(
                str(p) for p in _listar_docs(pasta) if p.suffix.lower() in exts
            )
        return textos

    def documentos_processo(self) -> list[Path]:
        return _listar_docs(self.pasta_processo)

    def outros_documentos(self) -> list[Path]:
        return _listar_docs(self.pasta_documentos)

    # ── Adicionar documento ───────────────────────────────────────────────────

    def adicionar_documento(
        self, origem: str | Path, pasta: str = "documentos"
    ) -> DocIndexado:
        """
        Copia um arquivo para processo/ ou documentos/ e atualiza o índice.

        Args:
            origem: Caminho do arquivo a adicionar.
            pasta:  "processo" ou "documentos".

        Returns:
            DocIndexado com os metadados do arquivo adicionado.
        """
        import shutil

        origem = Path(origem)
        destino_dir = self.pasta_processo if pasta == "processo" else self.pasta_documentos
        destino_dir.mkdir(parents=True, exist_ok=True)
        destino = destino_dir / origem.name

        shutil.copy2(str(origem), str(destino))
        doc = DocIndexado.de_arquivo(destino, pasta)

        indice = self._ler_indice()
        indice[f"{pasta}/{destino.name}"] = asdict(doc)
        self._salvar_indice(indice)

        return doc

    # ── Instruções ────────────────────────────────────────────────────────────

    def ler_instrucoes(self) -> str:
        """Retorna instruções ativas como texto Markdown (backward compat)."""
        ativas = self.listar_instrucoes_estruturadas()
        if not ativas:
            # Fallback para instrucoes.md simples
            if self.arquivo_instrucoes.exists():
                return self.arquivo_instrucoes.read_text(encoding="utf-8").strip()
            return ""
        linhas = [f"# Instruções e Notas — {self.nome_original()}\n"]
        for inst in ativas:
            ts = inst.get("criado_em", "")[:16].replace("T", " ")
            linhas.append(f"\n---\n*{ts}*\n\n{inst['texto']}\n")
        return "".join(linhas)

    def adicionar_instrucao(self, texto: str) -> None:
        """Acrescenta instrução ao arquivo com timestamp (backward compat)."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        bloco = f"\n\n---\n*{ts}*\n\n{texto.strip()}\n"
        if self.arquivo_instrucoes.exists():
            conteudo = self.arquivo_instrucoes.read_text(encoding="utf-8")
        else:
            conteudo = f"# Instruções e Notas — {self.nome_original()}\n"
        self.arquivo_instrucoes.write_text(conteudo + bloco, encoding="utf-8")

    def listar_instrucoes_estruturadas(self) -> list[dict]:
        """
        Retorna instruções ativas como lista estruturada.
        Migra automaticamente de instrucoes.md se necessário (lazy migration).
        """
        ctx = self._ler_contexto()

        if "instrucoes" not in ctx:
            instrucoes: list[dict] = []
            if self.arquivo_instrucoes.exists():
                conteudo = self.arquivo_instrucoes.read_text(encoding="utf-8").strip()
                # Só migra se tiver conteúdo real além do cabeçalho padrão
                linhas_reais = [
                    l for l in conteudo.splitlines()
                    if l.strip() and not l.startswith("#") and l.strip() != "---"
                ]
                if linhas_reais:
                    instrucoes.append({
                        "id": 1,
                        "texto": conteudo,
                        "criado_em": ctx.get("criado_em", datetime.now().isoformat()),
                        "ativo": True,
                        "migrado_de_arquivo": True,
                    })
            ctx["instrucoes"] = instrucoes
            self._salvar_contexto(ctx)

        return [i for i in ctx.get("instrucoes", []) if i.get("ativo", True)]

    def adicionar_instrucao_estruturada(self, texto: str) -> int:
        """Adiciona instrução estruturada. Retorna o ID gerado."""
        ctx = self._ler_contexto()
        instrucoes = ctx.get("instrucoes", [])
        novo_id = max((i.get("id", 0) for i in instrucoes), default=0) + 1
        instrucoes.append({
            "id": novo_id,
            "texto": texto.strip(),
            "criado_em": datetime.now().isoformat(),
            "ativo": True,
        })
        ctx["instrucoes"] = instrucoes
        self._salvar_contexto(ctx)
        # Sync instrucoes.md para ferramentas externas
        self.adicionar_instrucao(texto)
        return novo_id

    def remover_instrucao(self, id_instrucao: int) -> bool:
        """Remove instrução por ID (soft delete). Retorna True se encontrou."""
        ctx = self._ler_contexto()
        instrucoes = ctx.get("instrucoes", [])
        for inst in instrucoes:
            if inst.get("id") == id_instrucao:
                inst["ativo"] = False
                ctx["instrucoes"] = instrucoes
                self._salvar_contexto(ctx)
                return True
        return False

    # ── Relatório ─────────────────────────────────────────────────────────────

    def novo_caminho_relatorio(self) -> Path:
        self.pasta_relatorio.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        return self.pasta_relatorio / f"relatorio_estrategico_{ts}.md"

    def listar_relatorios(self) -> list[Path]:
        """Retorna todos os relatórios em ordem cronológica (mais recente primeiro)."""
        if not self.pasta_relatorio.exists():
            return []
        return sorted(
            (p for p in self.pasta_relatorio.iterdir() if p.is_file() and p.suffix == ".md"),
            reverse=True,
        )

    def ultimo_relatorio(self) -> Path | None:
        rels = self.listar_relatorios()
        return rels[0] if rels else None

    def ler_ultimo_relatorio(self) -> str:
        rel = self.ultimo_relatorio()
        if rel and rel.exists():
            return rel.read_text(encoding="utf-8")
        return ""

    def ler_relatorio(self, caminho: str | Path) -> str:
        """Lê relatório específico pelo caminho."""
        p = Path(caminho)
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    # ── Citações ──────────────────────────────────────────────────────────────

    def registrar_citacoes(
        self,
        caminho_relatorio: str | Path,
        citacoes: list[dict],
    ) -> None:
        """
        Registra citações extraídas de um relatório.
        Cada citação: {"documento": str, "pagina": int|None, "trecho": str, "tipo": str}
        """
        ctx = self._ler_contexto()
        historico = ctx.get("historico_citacoes", {})
        nome_rel = Path(caminho_relatorio).name
        historico[nome_rel] = {
            "caminho": str(caminho_relatorio),
            "registrado_em": datetime.now().isoformat(),
            "citacoes": citacoes,
        }
        ctx["historico_citacoes"] = historico
        self._salvar_contexto(ctx)

    def ler_citacoes(self, caminho_relatorio: str | Path | None = None) -> list[dict]:
        """
        Retorna citações do último relatório (ou do especificado).
        Retorna lista vazia se não houver citações registradas.
        """
        ctx = self._ler_contexto()
        historico = ctx.get("historico_citacoes", {})
        if not historico:
            return []
        if caminho_relatorio:
            nome = Path(caminho_relatorio).name
        else:
            # Mais recente pelo timestamp de registro
            entradas = sorted(
                historico.items(),
                key=lambda x: x[1].get("registrado_em", ""),
                reverse=True,
            )
            nome = entradas[0][0] if entradas else None
        if nome and nome in historico:
            return historico[nome].get("citacoes", [])
        return []

    # ── Linha do tempo ────────────────────────────────────────────────────────

    def timeline(self) -> list[dict]:
        """
        Retorna linha do tempo da demanda com eventos registrados em ordem cronológica.
        Cada evento: {"data": str, "tipo": str, "descricao": str, "caminho": str|None}
        """
        ctx = self._ler_contexto()
        eventos: list[dict] = []

        # Criação
        if "criado_em" in ctx:
            eventos.append({
                "data": ctx["criado_em"],
                "tipo": "criacao",
                "icone": "🗂️",
                "descricao": f"Demanda criada: {self.nome_original()}",
                "caminho": None,
            })

        # Documentos adicionados
        indice = ctx.get("indice", {})
        for chave, dados in sorted(
            indice.items(), key=lambda x: x[1].get("adicionado_em", "")
        ):
            if dados.get("adicionado_em"):
                eventos.append({
                    "data": dados["adicionado_em"],
                    "tipo": "documento",
                    "icone": "📎",
                    "descricao": (
                        f"[{dados['pasta']}] **{dados['nome']}** — {dados.get('tipo', 'Documento')}"
                    ),
                    "caminho": dados.get("caminho"),
                })

        # Relatórios gerados
        for rel_path in self.listar_relatorios():
            m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4})", rel_path.name)
            if m:
                hh, mm_ = m.group(2)[:2], m.group(2)[2:]
                data_str = f"{m.group(1)}T{hh}:{mm_}:00"
                ctx_citacoes = ctx.get("historico_citacoes", {})
                n_citacoes = len(ctx_citacoes.get(rel_path.name, {}).get("citacoes", []))
                desc = f"Relatório gerado: **{rel_path.name}**"
                if n_citacoes:
                    desc += f" ({n_citacoes} citações)"
                eventos.append({
                    "data": data_str,
                    "tipo": "relatorio",
                    "icone": "📊",
                    "descricao": desc,
                    "caminho": str(rel_path),
                })

        return sorted(eventos, key=lambda e: e["data"])

    # ── Resumo ────────────────────────────────────────────────────────────────

    def resumo(self) -> str:
        docs = self.sincronizar_indice()
        analisados = sum(1 for d in docs if d.analisado)
        pendentes = len(docs) - analisados
        ultima = self.ultima_analise()
        ultimo_rel = self.ultimo_relatorio()

        linhas = [
            f"Demanda : {self.nome_original()}",
            f"Pasta   : {self.caminho}",
            f"Criado  : {self.data_criacao()}",
        ]
        if ultima:
            linhas.append(f"Última análise: {ultima}")

        if docs:
            linhas.append(f"Documentos: {len(docs)} total  |  {analisados} analisados  |  {pendentes} pendentes")
            for d in docs:
                status = "✔" if d.analisado else "○"
                linhas.append(f"  {status} [{d.pasta:10s}] {d.nome:40s}  {d.tipo}")
        else:
            linhas.append("Documentos: nenhum")

        tem_instrucoes = self.arquivo_instrucoes.exists()
        linhas.append(f"Instruções: {'sim' if tem_instrucoes else 'não'}")
        if ultimo_rel:
            linhas.append(f"Último relatório: {ultimo_rel.name}")

        return "\n".join(linhas)

    def arvore(self) -> dict:
        """
        Retorna estrutura de dados para renderização em UI.

        Returns:
            {
              "nome": ...,
              "processo": [DocIndexado, ...],
              "documentos": [DocIndexado, ...],
              "relatorios": [Path, ...],
              "tem_instrucoes": bool,
              "ultima_analise": str | None,
            }
        """
        docs = self.sincronizar_indice()
        return {
            "nome": self.nome_original(),
            "slug": self.nome,
            "caminho": str(self.caminho),
            "processo": [d for d in docs if d.pasta == "processo"],
            "documentos": [d for d in docs if d.pasta == "documentos"],
            "relatorios": sorted(
                (p for p in self.pasta_relatorio.iterdir() if p.is_file() and p.suffix == ".md"),
                reverse=True,
            ) if self.pasta_relatorio.exists() else [],
            "tem_instrucoes": self.arquivo_instrucoes.exists(),
            "ultima_analise": self.ultima_analise(),
        }


# ─── API pública ──────────────────────────────────────────────────────────────

def criar_demanda(nome: str) -> DemandaWorkspace:
    """
    Cria nova demanda com estrutura de pastas padrão.

    Raises:
        FileExistsError: se já existir.
    """
    base = _pasta_base()
    slug = _slug(nome)
    caminho = base / slug

    if caminho.exists():
        raise FileExistsError(f"Demanda já existe: {caminho}")

    for sub in ("processo", "documentos", "relatorio"):
        (caminho / sub).mkdir(parents=True)

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

    ws = DemandaWorkspace(caminho)
    ws._salvar_contexto({
        "nome_original": nome,
        "criado_em": datetime.now().isoformat(),
        "slug": slug,
        "indice": {},
    })
    return ws


def listar_demandas() -> list[DemandaWorkspace]:
    """Retorna todas as demandas ordenadas por nome."""
    base = _pasta_base()
    if not base.exists():
        return []
    return sorted(
        (DemandaWorkspace(p) for p in base.iterdir() if p.is_dir()),
        key=lambda w: w.nome,
    )


def obter_demanda(nome_ou_slug: str) -> DemandaWorkspace:
    """
    Encontra demanda pelo nome ou slug.

    Raises:
        FileNotFoundError: se não existir.
    """
    base = _pasta_base()
    slug = _slug(nome_ou_slug)

    direto = base / slug
    if direto.exists():
        return DemandaWorkspace(direto)

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
