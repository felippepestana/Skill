# /apex-novo-agente — Criar um novo agente especializado

Crie um novo agente para o squad APEX-LEGAL com base no argumento fornecido.

**Argumento:** `$ARGUMENTS` — descrição do agente a criar (ex: `imobiliário`, `previdenciário`, `ambiental`)

## O que fazer

1. Leia `apex_legal/squads/analise/squad.py` para entender o padrão dos agentes existentes
2. Identifique o nome do agente a partir de `$ARGUMENTS`
3. Crie a definição do novo agente seguindo exatamente o padrão `AgentDefinition`:
   - `description`: 2-3 linhas, papel no squad, especialidade
   - `prompt`: estruturado em seções numeradas (como tributarista e trabalhista)
     - Inclua fontes jurídicas específicas (sites de tribunais, legislação)
     - Inclua prazos, súmulas e precedentes relevantes da área
   - `tools`: use `["Read", "Grep", "Glob", "WebSearch", "WebFetch"]` para agentes com pesquisa online

4. Adicione o agente ao dicionário `_AGENTES_NOVOS` em `apex_legal/squads/analise/squad.py`
5. Atualize o `_SYSTEM_PROMPT_APEX` para incluir o novo agente na ordem de orquestração
6. Atualize `apex_legal/squads/analise/__init__.py` se necessário

## Regras

- IDs em kebab-case: `especialista-previdenciario`, `ambientalista`, `imobiliario`
- Prompt sempre em pt-BR com linguagem técnico-jurídica
- Inclua fontes autoritativas brasileiras (CNJ, tribunais superiores, legislação federal)
- Agentes de nicho só são acionados quando o caso envolve aquela área (instrução no system prompt)

Após criar o agente, mostre um resumo das mudanças e confirme se quer fazer commit.
