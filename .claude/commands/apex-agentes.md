# /apex-agentes — Listar e descrever todos os agentes

Liste todos os agentes do APEX-LEGAL PERFORMANCE com descrições detalhadas.

## O que fazer

Leia os seguintes arquivos e extraia todos os agentes definidos:

1. `apex_legal/squads/analise/squad.py` — squad principal (8 agentes)
2. `apex_legal/squads/inteligencia/squad.py` — squad de inteligência (3 agentes)
3. `squads/documental/squad.py` — squad documental (3 agentes)
4. `aiox_master/squad.py` — orquestrador mestre (11 agentes aios-core)

## Formato de saída

Para cada squad, mostre uma tabela:

```
## Squad: [nome] — [N] agentes

| # | ID | Persona | Função | Tools |
|---|-----|---------|--------|-------|
| 1 | leitor-de-pecas | ... | ... | Read, Grep, Glob |
```

Se o argumento `$ARGUMENTS` for um nome de agente específico (ex: `tributarista`),
mostre os detalhes completos desse agente: description, prompt completo, tools.

Ao final, mostre:
- Total de agentes no sistema
- Mapa de responsabilidades (qual agente usa quais ferramentas de rede/web)
- Sugestão de próximos agentes a implementar baseado nos gaps identificados
