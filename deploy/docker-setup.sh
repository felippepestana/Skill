#!/usr/bin/env bash
# ============================================================
# APEX-LEGAL — Deploy Docker no Hostinger VPS
# Uso: bash deploy/docker-setup.sh SEU-DOMINIO.COM.BR
# ============================================================
set -euo pipefail

DOMINIO="${1:-}"
REPO="https://github.com/felippepestana/Skill.git"
APP_DIR="/opt/apex-legal"
ENV_FILE="/etc/apex-legal/.env"

if [[ -z "$DOMINIO" ]]; then
  echo "Uso: bash deploy/docker-setup.sh SEU-DOMINIO.COM.BR"
  exit 1
fi

echo "═══════════════════════════════════════════════════"
echo "  APEX-LEGAL · Deploy Docker — $DOMINIO"
echo "═══════════════════════════════════════════════════"

# ── 1. Dependências do sistema ────────────────────────
apt-get update -qq
apt-get install -y --no-install-recommends \
  curl git nginx certbot python3-certbot-nginx

# ── 2. Instalar Docker (se não tiver) ────────────────
if ! command -v docker &>/dev/null; then
  echo "Instalando Docker…"
  curl -fsSL https://get.docker.com | sh
  systemctl enable docker
  systemctl start docker
fi

# Docker Compose v2
if ! docker compose version &>/dev/null; then
  echo "Instalando Docker Compose plugin…"
  apt-get install -y docker-compose-plugin
fi

# ── 3. Clonar / atualizar o repositório ──────────────
if [[ -d "$APP_DIR" ]]; then
  echo "Atualizando repositório…"
  git -C "$APP_DIR" pull
else
  echo "Clonando repositório…"
  git clone "$REPO" "$APP_DIR"
fi

# ── 4. Criar arquivo de secrets ──────────────────────
mkdir -p /etc/apex-legal
if [[ ! -f "$ENV_FILE" ]]; then
  cat > "$ENV_FILE" <<ENVEOF
ANTHROPIC_API_KEY=sk-ant-COLOQUE-SUA-CHAVE-AQUI
NEXT_PUBLIC_API_URL=https://api.${DOMINIO}
NEXT_PUBLIC_WS_URL=wss://api.${DOMINIO}
ENVEOF
  echo ""
  echo "⚠️  Edite o arquivo de secrets antes de continuar:"
  echo "    nano $ENV_FILE"
  echo ""
  read -rp "Pressione ENTER após preencher a ANTHROPIC_API_KEY… "
fi

# Carrega env
set -a; source "$ENV_FILE"; set +a

# ── 5. Configurar nginx ───────────────────────────────
NGINX_CONF="/etc/nginx/sites-available/apex-legal"
cp "$APP_DIR/deploy/nginx.conf" "$NGINX_CONF"
sed -i "s/DOMINIO_AQUI/$DOMINIO/g" "$NGINX_CONF"
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/apex-legal
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# ── 6. SSL com Let's Encrypt ─────────────────────────
echo "Obtendo certificado SSL para $DOMINIO e api.$DOMINIO…"
certbot --nginx \
  -d "$DOMINIO" -d "www.$DOMINIO" -d "api.$DOMINIO" \
  --non-interactive --agree-tos \
  --email "admin@$DOMINIO" \
  --redirect

systemctl reload nginx

# ── 7. Build e start dos containers ──────────────────
cd "$APP_DIR"
cp "$ENV_FILE" .env

echo "Fazendo build das imagens Docker…"
docker compose build

echo "Subindo containers…"
docker compose up -d

# ── 8. Verificar saúde ───────────────────────────────
sleep 5
if docker compose ps | grep -q "Up"; then
  echo ""
  echo "═══════════════════════════════════════════════════"
  echo "  ✅  APEX-LEGAL rodando!"
  echo "  🌐  Frontend : https://$DOMINIO"
  echo "  🔌  API      : https://api.$DOMINIO"
  echo "  📖  Docs     : https://api.$DOMINIO/docs"
  echo "═══════════════════════════════════════════════════"
else
  echo "⚠️  Algum container não iniciou. Verifique:"
  docker compose ps
  docker compose logs --tail 30
fi

# ── 9. Criar primeiro usuário ─────────────────────────
echo ""
echo "Para criar o primeiro usuário admin, rode:"
echo "  docker compose exec backend python -m apex_legal adduser admin SENHA admin@$DOMINIO"
