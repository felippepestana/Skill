# /apex-status — Estado atual do projeto APEX-LEGAL

Mostre um relatório completo do estado atual do projeto APEX-LEGAL PERFORMANCE.

Faça as seguintes verificações em paralelo:

1. **Estrutura de pacotes** — liste os arquivos principais de cada pacote:
   - `apex_legal/` (core, squads)
   - `analista_processual/`
   - `squads/documental/`
   - `aiox_master/`
   - `frontend/`

2. **Agentes ativos** — liste todos os agentes definidos em:
   - `apex_legal/squads/analise/squad.py` (SQUAD_AGENTS)
   - `apex_legal/squads/inteligencia/squad.py` (INTEL_AGENTS)
   - `squads/documental/squad.py` (DOCUMENTAL_AGENTS)
   - `aiox_master/squad.py`

3. **Git status** — branch atual, último commit, arquivos pendentes

4. **Dependências** — conteúdo de `requirements.txt` e `frontend/package.json` (só dependencies)

5. **Deploy** — verifique se `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend` e `deploy/nginx.conf` existem e estão consistentes com o domínio `pestana.app`

Apresente um resumo executivo com:
- Total de agentes por squad
- Linhas de código por módulo (`wc -l`)
- Status do git
- Próximas features sugeridas com base no código atual
