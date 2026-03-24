#!/usr/bin/env bash
# update.sh — Atualização do Analista Processual no VPS
# Chamado pelo GitHub Actions a cada push na branch main.
# Também pode ser rodado manualmente: sudo bash /opt/analista/Skill/deploy/update.sh

set -euo pipefail

APP_DIR="/opt/analista"
SKILL_DIR="$APP_DIR/Skill"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="analista-processual"
BRANCH="${1:-main}"

echo "→ [$(date '+%Y-%m-%d %H:%M:%S')] Iniciando atualização…"

# Pull da branch correta
git -C "$SKILL_DIR" fetch origin "$BRANCH"
git -C "$SKILL_DIR" reset --hard "origin/$BRANCH"

# Atualiza dependências Python (apenas se requirements.txt mudou)
"$VENV_DIR/bin/pip" install -r "$SKILL_DIR/requirements.txt" -q
"$VENV_DIR/bin/pip" install -e "$SKILL_DIR" -q

# Reinicia o serviço
systemctl restart "$SERVICE_NAME"

# Aguarda para confirmar que subiu
sleep 3
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "✔ Serviço reiniciado com sucesso."
else
    echo "❌ Serviço falhou ao reiniciar. Verificar com: journalctl -u $SERVICE_NAME -n 50"
    exit 1
fi

echo "✔ [$(date '+%Y-%m-%d %H:%M:%S')] Atualização concluída."
