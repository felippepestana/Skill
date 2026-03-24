# CLAUDE.md — Contexto de Desenvolvimento

## Visão geral do projeto

**Analista Processual** é um workspace jurídico multi-agente construído sobre o Claude Agent SDK. Permite análise de processos jurídicos com 5 agentes especializados, gestão de demandas por pasta, interface web Gradio de 3 colunas e extração automática de citações.

## Estrutura de pacotes

```
Skill/
├── analista_processual/     # Squad jurídico (5 agentes) + workspace + UI
├── aiox_master/             # Orquestrador mestre (11 aios-core + squads)
└── squads/
    └── documental/          # Squad de geração de documentos (3 agentes)
```

## Comandos principais

```bash
# Interface web (default)
python -m analista_processual

# CLI do analista
python -m analista_processual nova "Fulano vs Ciclano 2024"
python -m analista_processual analisar "Fulano vs Ciclano"
python -m analista_processual delta "Fulano vs Ciclano"
python -m analista_processual consultar "Fulano vs Ciclano" "qual o risco?"

# Squad documental
python -m squads.documental gerar "Recurso de Apelação" ~/demandas/fulano

# AIOX Master
python -m aiox_master "analise a arquitetura e sugira melhorias"
python -m aiox_master ux "interface do analista processual"
python -m aiox_master codigo "revise o analista_processual/"
```

## Agentes do squad analista-processual (5)

| Agente                       | Função                                        |
|------------------------------|-----------------------------------------------|
| `leitor-de-pecas`            | Extrai informações estruturadas dos docs      |
| `pesquisador-juridico`       | Busca jurisprudência e legislação (WebSearch) |
| `estrategista-processual`    | Avalia riscos, cenários, probabilidades       |
| `advogado-orientador`        | Plano de ação prático com prazos              |
| `relator-processual`         | Relatório final + bloco `citacoes` rastreado  |

## Workspace por demanda

Cada demanda em `~/.demandas/<slug>/`:
- `.contexto.json` — metadados, índice SHA-256, citações, instruções versionadas
- `processo/` — peças processuais (PDFs, TXTs)
- `documentos/` — outros documentos
- `relatorio/` — relatórios gerados (`relatorio_estrategico_YYYY-MM-DD_HHMM.md`)
- `instrucoes.md` — instruções (backup; fonte de verdade é `.contexto.json["instrucoes"]`)

## Padrões críticos

### Streaming de progresso
O `_analisar_demanda` processa `TaskProgressMessage` da SDK e envia para
`callback_progresso(msg)`. A UI usa uma `queue.Queue` + thread para bridge síncrono/assíncrono.
**NÃO chamar `anyio.run()` dentro de handler async do Gradio** — usar sempre thread dedicada.

### Lock por demanda
`_Estado.lock_demanda(slug)` retorna `threading.Lock` por slug. Impede análises concorrentes
na mesma demanda. O lock é adquirido `with lock_demanda:` dentro da thread.

### SHA-256 delta
`DocIndexado._sha256(path)` — primeiros 256 KB do arquivo. Hash armazenado em
`.contexto.json["indice"][chave]["hash_modificacao"]`. Mudança de hash → `analisado=False`.

### Citações
`relator-processual` gera bloco `\`\`\`citacoes\`\`\`` no relatório. A função
`_extrair_e_registrar_citacoes()` parseia e salva em `.contexto.json["historico_citacoes"]`.

### Variáveis de ambiente
- `DEMANDAS_DIR` — sobrescreve pasta base das demandas (padrão: `~/demandas`)
- `ANTHROPIC_API_KEY` — obrigatório para todas as operações de IA

## Aios-core (aiox_master)

O `aiox_master/squad.py` importa `ANALISTA_PROCESSUAL_AGENTS` e prefixia com
`analista-processual__`. Importa `DOCUMENTAL_AGENTS` de `squads.documental` com
prefixo `documental__`. O import do documental é opcional (try/except).

**Autoridades exclusivas (não modificar):**
- git push → @devops
- código → @dev
- stories → @sm
- schema/DB → @data-engineer

## UI (Gradio 5.x)

Layout 3 colunas: esq(2) | centro(4) | dir(3)

Coluna direita tem 4 abas:
1. **Relatório** — Preview Markdown + Editor com save
2. **Citações** — citações rastreadas do último relatório
3. **Linha do Tempo** — cronologia de eventos da demanda
4. **Gerar Documento** — squad documental via `squads.documental`

## Branch de desenvolvimento

Branch ativo: `claude/open-analyst-squad-5ujs8`
