# /apex-frontend — Trabalhar no frontend Next.js

Auxilie no desenvolvimento do frontend APEX-LEGAL PERFORMANCE.

**Argumento:** `$ARGUMENTS` — componente ou feature a desenvolver (ex: `login`, `sidebar`, `chat`, `relatorio`)

## Contexto do frontend

- **Stack:** Next.js 14 App Router + TypeScript + Tailwind CSS
- **Estado:** Zustand (`frontend/lib/store.ts`)
- **API client:** `frontend/lib/api.ts` (REST + WebSocket)
- **Componentes existentes:** `Sidebar`, `WorkspaceMain`, `PainelIA`
- **Domínio produção:** `pestana.app`
- **Palette:** `apex` (azul jurídico) + `gold` (dourado) — ver `tailwind.config.ts`

## O que fazer

1. Leia os arquivos relevantes do frontend antes de qualquer modificação:
   - `frontend/lib/api.ts` — entenda os endpoints disponíveis
   - `frontend/lib/store.ts` — entenda o estado global
   - Componente alvo (se existir)

2. Se `$ARGUMENTS` especificar uma feature:
   - Analise se já existe implementação parcial
   - Identifique quais endpoints da API são necessários (leia `apex_legal/core/api.py`)
   - Implemente seguindo os padrões visuais existentes (dark mode, classes Tailwind do projeto)

3. **Padrões visuais obrigatórios:**
   - Fundo: `bg-gray-950` (app) / `bg-gray-900` (cards/sidebar)
   - Bordas: `border-gray-800`
   - Texto primário: `text-white`, secundário: `text-gray-400`
   - Accent: `text-apex-400` / `bg-apex-600`
   - Botões primários: `bg-apex-600 hover:bg-apex-500`
   - Textos xs: `text-xs`, labels: `text-[10px]`

4. Sempre verifique se o componente está conectado ao store Zustand corretamente

Se não houver argumento, faça um diagnóstico do frontend: componentes existentes, o que está faltando, gaps em relação à API disponível.
