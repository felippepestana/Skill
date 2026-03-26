# /apex-workspace — Gerenciar workspace de demandas

Auxilie na gestão de demandas jurídicas no APEX-LEGAL.

**Argumento:** `$ARGUMENTS` — comando específico ou nome de demanda

## Comandos disponíveis

Se `$ARGUMENTS` começar com:

- `nova [nome]` → crie uma nova demanda
- `listar` → liste todas as demandas do usuário atual
- `info [nome]` → detalhes de uma demanda específica
- `analisar [nome]` → inicie análise completa
- `delta [nome]` → análise incremental (apenas docs novos)
- `consultar [nome] [pergunta]` → consulta pontual ao squad
- `instrucao [nome] [texto]` → adicione instrução à demanda

## Como executar

Determine o ambiente:
- **Desenvolvimento local:** `python -m apex_legal [comando]`
- **Docker/VPS:** `docker compose exec backend python -m apex_legal [comando]`

## Estrutura de workspace

Leia `analista_processual/workspace.py` para entender `DemandaWorkspace`.

Cada demanda em `~/demandas/<username>/<slug>/`:
```
├── .contexto.json     ← metadados, índice SHA-256, citações
├── processo/          ← peças processuais (PDFs, TXTs)
├── documentos/        ← outros documentos
└── relatorio/         ← relatórios gerados
```

## Verificações automáticas

Sempre verifique:
1. Se `ANTHROPIC_API_KEY` está configurada
2. Se a pasta `DEMANDAS_DIR` existe e tem permissão de escrita
3. Se há documentos na demanda antes de iniciar análise

Mostre os comandos prontos para executar no terminal.
