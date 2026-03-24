#!/usr/bin/env bash
# setup.sh — Instalação completa no Hostinger KVM2 (Ubuntu 22.04 LTS)
# Rodar como root: bash setup.sh seu-dominio.com.br
#
# O que este script faz:
#   1. Instala dependências do sistema (Python 3.11, nginx, certbot, git)
#   2. Cria usuário 'analista' sem shell interativo
#   3. Clona o repositório em /opt/analista/Skill
#   4. Cria virtualenv e instala dependências Python
#   5. Cria pasta de demandas e arquivo de secrets
#   6. Instala e habilita o serviço systemd
#   7. Configura nginx + SSL via certbot
#   8. Instala Claude Code CLI

set -euo pipefail

DOMAIN="${1:-}"
REPO_URL="${2:-https://github.com/felippepestana/Skill.git}"
BRANCH="${3:-main}"
APP_DIR="/opt/analista"
SKILL_DIR="$APP_DIR/Skill"
VENV_DIR="$APP_DIR/venv"
DEMANDAS_DIR="$APP_DIR/demandas"
SERVICE_NAME="analista-processual"

# ── Verificações ───────────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    echo "❌ Rode como root: sudo bash setup.sh $DOMAIN"
    exit 1
fi

if [[ -z "$DOMAIN" ]]; then
    echo "❌ Informe o domínio: bash setup.sh seu-dominio.com.br"
    exit 1
fi

echo ""
echo "══════════════════════════════════════════════════"
echo "  ⚖️  Analista Processual — Instalação"
echo "  Domínio : $DOMAIN"
echo "  Repo    : $REPO_URL ($BRANCH)"
echo "  App dir : $APP_DIR"
echo "══════════════════════════════════════════════════"
echo ""

# ── 1. Dependências do sistema ─────────────────────────────────────────────────

echo "→ Atualizando pacotes…"
apt-get update -qq
apt-get install -y -qq \
    python3.11 python3.11-venv python3-pip \
    nginx certbot python3-certbot-nginx \
    git curl wget unzip \
    build-essential libssl-dev

# ── 2. Usuário do sistema ──────────────────────────────────────────────────────

echo "→ Criando usuário 'analista'…"
id -u analista &>/dev/null || useradd \
    --system \
    --shell /usr/sbin/nologin \
    --home-dir "$APP_DIR" \
    --create-home \
    analista

# ── 3. Clonar repositório ─────────────────────────────────────────────────────

echo "→ Clonando repositório…"
mkdir -p "$APP_DIR"
if [[ -d "$SKILL_DIR/.git" ]]; then
    echo "  (repositório já existe, fazendo git pull)"
    sudo -u analista git -C "$SKILL_DIR" pull origin "$BRANCH"
else
    sudo -u analista git clone --branch "$BRANCH" "$REPO_URL" "$SKILL_DIR"
fi

# ── 4. Python virtualenv ──────────────────────────────────────────────────────

echo "→ Criando virtualenv e instalando dependências…"
sudo -u analista python3.11 -m venv "$VENV_DIR"
sudo -u analista "$VENV_DIR/bin/pip" install --upgrade pip -q
sudo -u analista "$VENV_DIR/bin/pip" install -r "$SKILL_DIR/requirements.txt" -q
sudo -u analista "$VENV_DIR/bin/pip" install -e "$SKILL_DIR" -q

# ── 5. Pasta de demandas e secrets ────────────────────────────────────────────

echo "→ Criando pasta de demandas e arquivo de secrets…"
sudo -u analista mkdir -p "$DEMANDAS_DIR"

mkdir -p /etc/analista
if [[ ! -f /etc/analista/secrets.env ]]; then
    cat > /etc/analista/secrets.env <<EOF
# ⚠️  IMPORTANTE: Preencha sua API key da Anthropic abaixo e salve o arquivo.
# Gere em: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-SUBSTITUA-AQUI

# Pasta onde as demandas dos usuários ficam armazenadas
DEMANDAS_DIR=$DEMANDAS_DIR
EOF
    echo "  ✔ Arquivo /etc/analista/secrets.env criado."
    echo "  ⚠️  EDITE agora: nano /etc/analista/secrets.env"
else
    echo "  (secrets.env já existe, mantendo)"
fi
chmod 640 /etc/analista/secrets.env
chown root:analista /etc/analista/secrets.env

# ── 6. Serviço systemd ────────────────────────────────────────────────────────

echo "→ Instalando serviço systemd…"
cp "$SKILL_DIR/deploy/analista-processual.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# ── 7. Nginx + SSL ────────────────────────────────────────────────────────────

echo "→ Configurando nginx…"
sed "s/seu-dominio.com.br/$DOMAIN/g" \
    "$SKILL_DIR/deploy/nginx.conf" \
    > /etc/nginx/sites-available/analista-processual

ln -sf \
    /etc/nginx/sites-available/analista-processual \
    /etc/nginx/sites-enabled/analista-processual

# Desabilita o site default
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx

echo "→ Obtendo certificado SSL (Let's Encrypt)…"
certbot --nginx -d "$DOMAIN" \
    --non-interactive \
    --agree-tos \
    --email "admin@$DOMAIN" \
    --redirect

# ── 8. Claude Code CLI ────────────────────────────────────────────────────────

echo "→ Instalando Claude Code CLI…"
if ! command -v claude &>/dev/null; then
    curl -fsSL https://claude.ai/install.sh | sh || echo "  ⚠️ Instale Claude Code manualmente se falhar."
else
    echo "  (Claude Code já instalado)"
fi

# ── Finalização ───────────────────────────────────────────────────────────────

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✔  Instalação concluída!"
echo ""
echo "  Próximos passos:"
echo ""
echo "  1. Preencha a API key da Anthropic:"
echo "     nano /etc/analista/secrets.env"
echo ""
echo "  2. Cadastre o primeiro usuário admin:"
echo "     sudo -u analista $VENV_DIR/bin/python -m analista_processual \\"
echo "       adduser admin SENHA_SEGURA admin@$DOMAIN"
echo ""
echo "  3. Inicie o serviço:"
echo "     systemctl start $SERVICE_NAME"
echo "     systemctl status $SERVICE_NAME"
echo ""
echo "  4. Acesse: https://$DOMAIN"
echo ""
echo "  Logs: journalctl -u $SERVICE_NAME -f"
echo "══════════════════════════════════════════════════"
