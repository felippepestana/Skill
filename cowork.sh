#!/usr/bin/env bash
# ============================================================
# APEX-LEGAL PERFORMANCE — Modo Cowork
# Expõe o sistema na rede local ou via Cloudflare Tunnel
# ============================================================
set -euo pipefail

MODE="${1:-local}"   # local | tunnel | docker
PORT_API=8000
PORT_FRONT=3000
PORT_GRADIO=7860

# ── Verifica ANTHROPIC_API_KEY ───────────────────────────────
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "❌  ANTHROPIC_API_KEY não definida."
  echo "    export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

case "$MODE" in

  # ── Modo local: inicia FastAPI + Gradio na rede LAN ─────────
  local)
    echo "═══════════════════════════════════════════════════════"
    echo "  APEX-LEGAL  ·  Modo Cowork Local"
    echo "═══════════════════════════════════════════════════════"
    MY_IP=$(hostname -I | awk '{print $1}')
    echo "  API REST : http://$MY_IP:$PORT_API"
    echo "  Gradio   : http://$MY_IP:$PORT_GRADIO"
    echo "  Frontend : http://localhost:$PORT_FRONT  (rode npm run dev)"
    echo "═══════════════════════════════════════════════════════"
    echo ""

    # Inicia API em background
    python -m apex_legal api --host 0.0.0.0 --port "$PORT_API" &
    API_PID=$!

    # Inicia Gradio em background
    python -m analista_processual ui --host 0.0.0.0 --port "$PORT_GRADIO" --no-auth &
    GRADIO_PID=$!

    trap "kill $API_PID $GRADIO_PID 2>/dev/null; echo '  Serviços encerrados.'" EXIT
    wait
    ;;

  # ── Modo tunnel: Cloudflare Tunnel (grátis, sem VPS) ─────────
  tunnel)
    if ! command -v cloudflared &>/dev/null; then
      echo "Instalando cloudflared…"
      if [[ "$(uname -s)" == "Linux" ]]; then
        curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
          -o /tmp/cloudflared && chmod +x /tmp/cloudflared && sudo mv /tmp/cloudflared /usr/local/bin/
      elif [[ "$(uname -s)" == "Darwin" ]]; then
        brew install cloudflared
      else
        echo "Instale cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/"
        exit 1
      fi
    fi

    echo "═══════════════════════════════════════════════════════"
    echo "  APEX-LEGAL  ·  Modo Tunnel (Cloudflare)"
    echo "═══════════════════════════════════════════════════════"

    # Inicia API
    python -m apex_legal api --host 0.0.0.0 --port "$PORT_API" &
    API_PID=$!

    # Inicia Gradio
    python -m analista_processual ui --host 0.0.0.0 --port "$PORT_GRADIO" --no-auth &
    GRADIO_PID=$!

    sleep 2

    # Cria túnel público temporário para API
    cloudflared tunnel --url "http://localhost:$PORT_API" &
    CF_API_PID=$!

    # Cria túnel público temporário para Gradio
    cloudflared tunnel --url "http://localhost:$PORT_GRADIO" &
    CF_GRADIO_PID=$!

    echo ""
    echo "  URLs públicas acima (geradas pelo cloudflared)."
    echo "  Pressione Ctrl+C para encerrar."
    echo "═══════════════════════════════════════════════════════"

    trap "kill $API_PID $GRADIO_PID $CF_API_PID $CF_GRADIO_PID 2>/dev/null; echo '  Encerrado.'" EXIT
    wait
    ;;

  # ── Modo docker: sobe todo o stack via docker compose ────────
  docker)
    echo "═══════════════════════════════════════════════════════"
    echo "  APEX-LEGAL  ·  Modo Docker Compose"
    echo "═══════════════════════════════════════════════════════"
    export ANTHROPIC_API_KEY
    docker compose up --build
    ;;

  *)
    echo "Uso: ./cowork.sh [local|tunnel|docker]"
    echo ""
    echo "  local   → Inicia na rede LAN (padrão)"
    echo "  tunnel  → Expõe publicamente via Cloudflare Tunnel (grátis)"
    echo "  docker  → Sobe via docker compose"
    exit 1
    ;;
esac
