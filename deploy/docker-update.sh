#!/usr/bin/env bash
# ── Atualizar APEX-LEGAL sem downtime ──────────────
set -euo pipefail
APP_DIR="/opt/apex-legal"

echo "Atualizando APEX-LEGAL…"
git -C "$APP_DIR" pull
cd "$APP_DIR"

# Rebuild e restart com zero-downtime (serviço por serviço)
docker compose build backend frontend
docker compose up -d --no-deps backend
sleep 3
docker compose up -d --no-deps frontend

echo "✅ Atualização concluída."
docker compose ps
