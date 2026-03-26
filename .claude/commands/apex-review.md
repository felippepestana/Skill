# /apex-review — Revisão de código APEX-LEGAL

Faça uma revisão de código completa do APEX-LEGAL PERFORMANCE.

**Argumento:** `$ARGUMENTS` — módulo ou arquivo específico (opcional). Se vazio, revisa tudo.

## O que fazer

Se `$ARGUMENTS` estiver vazio, revise os módulos principais:
- `apex_legal/core/api.py`
- `apex_legal/squads/analise/squad.py`
- `apex_legal/squads/inteligencia/squad.py`
- `analista_processual/squad.py`
- `analista_processual/workspace.py`
- `analista_processual/auth.py`

Se `$ARGUMENTS` for um arquivo ou módulo específico, revise apenas esse.

## Critérios de revisão

1. **Segurança**
   - Injeção de path (path traversal)
   - Exposição de dados sensíveis em logs
   - Rate limiting adequado
   - Validação de inputs nas APIs

2. **Qualidade do código**
   - Tratamento de exceções (não swallow exceptions silenciosamente)
   - Thread safety (especialmente no state compartilhado)
   - Memory leaks (sessions dict sem TTL cleanup, jobs sem expiração)
   - Imports circulares

3. **Arquitetura**
   - Consistência com os padrões do projeto (async/sync bridge, lock por demanda)
   - TODOs e FIXMEs não resolvidos
   - Código duplicado entre `analista_processual` e `apex_legal`

4. **Performance**
   - Queries SQLite sem índice em tabelas grandes
   - Operações síncronas bloqueando event loop
   - Cache desnecessariamente ausente

## Saída esperada

Para cada problema encontrado:
- Arquivo e linha
- Severidade: 🔴 crítico / 🟡 importante / 🟢 sugestão
- Descrição do problema
- Correção sugerida (com código)

Ao final, pergunte se quer aplicar as correções.
