# AGENTS.md

Workspace multi-repo: este projeto vive em `/agent/repos/Skill`. Outros repos relacionados ficam em `/agent/repos/` (ex.: `legal-ai-flow-hub`, `juridic-ai-nexus`, `JurisBotIA`). Ver também `CLAUDE.md` neste diretório.

## Cursor Cloud specific instructions

### Skill — Analista Processual (este repo)

- **Venv:** `.venv` na raiz (`python3 -m venv .venv` na primeira vez).
- **Instalar:** `.venv/bin/pip install -r requirements.txt`
- **Se venv falhar:** instalar pacote de sistema `python3.12-venv` (uma vez por VM).
- **Dev UI local sem login:**  
  `.venv/bin/python -m analista_processual --no-auth --host 0.0.0.0 --port 7860`  
  → http://127.0.0.1:7860/
- **Secrets:** `ANTHROPIC_API_KEY` obrigatória para `analisar` / chat com agentes; `DEMANDAS_DIR` opcional (padrão `~/demandas`).
- **CLI:** `nova`, `listar`, `info`, `analisar`, `consultar` — `python -m analista_processual --help`.
- **Smoke de sintaxe:** `python -m py_compile analista_processual/*.py` (não há pytest no repo).
- **Deploy prod:** `deploy/setup.sh` — só em servidor; não faz parte do refresh automático da VM.

### legal-ai-flow-hub (AdvLabIA) — repo irmão

- Caminho: `/agent/repos/legal-ai-flow-hub`
- `npm install` → `npm run dev -- --host 0.0.0.0 --port 5173` → http://127.0.0.1:5173/
- `npm run build` valida o frontend; `npm run lint` pode falhar por regras ESLint já existentes no repo.
- Supabase na nuvem via `.env` (`VITE_SUPABASE_*`); landing funciona sem `.env`.

### tmux

Servidores de dev convém rodar em sessões tmux (`skill-gradio`, `advlabia-vite`) com `tmux -f /exec-daemon/tmux.portal.conf`.

### JurisBotIA (opcional)

Fork Supabase pesado: Docker em `JurisBotIA/docker` + `pnpm dev:studio`. Não iniciar no script de update da VM.
