# Deploy — Analista Processual no Hostinger KVM2

Guia completo para hospedar o Analista Processual com domínio próprio, HTTPS e múltiplos usuários.

## Pré-requisitos

- VPS Hostinger KVM2 (8 GB RAM, 100 GB NVMe) — ou superior
- Ubuntu 22.04 LTS
- Domínio com DNS apontando para o IP do VPS (registro A)
- Conta no GitHub com o repositório do projeto

---

## 1. Preparar o Hostinger

1. Acesse o **hPanel** do Hostinger
2. Vá em **VPS** → selecione seu servidor → **Gerenciar**
3. Em **Sistema Operacional**, reinstale com **Ubuntu 22.04 LTS**
4. Anote o **IP do servidor**

### Configurar DNS do domínio

No painel do seu registrador (Registro.br, Hostinger Domains, etc.):

```
Tipo: A
Nome: @  (ou seu-dominio.com.br)
Valor: <IP DO VPS>
TTL: 3600
```

Aguarde a propagação (5–30 minutos). Teste: `ping seu-dominio.com.br`

---

## 2. Instalação automática

Conecte via SSH e rode o script de setup:

```bash
ssh root@<IP-DO-VPS>

# Baixe e execute o script de instalação
curl -fsSL https://raw.githubusercontent.com/felippepestana/Skill/main/deploy/setup.sh | \
    bash -s -- seu-dominio.com.br

# OU, se já clonou o repo:
bash /opt/analista/Skill/deploy/setup.sh seu-dominio.com.br
```

O script:
- Instala Python 3.11, nginx, certbot, git
- Cria usuário `analista` (sem shell interativo)
- Clona o repositório em `/opt/analista/Skill`
- Cria virtualenv e instala dependências
- Configura nginx como reverse proxy com SSL (Let's Encrypt)
- Instala o serviço systemd com auto-restart
- Instala o Claude Code CLI

---

## 3. Configurar secrets

```bash
# Preencha com sua API key da Anthropic
nano /etc/analista/secrets.env
```

Conteúdo obrigatório:
```bash
ANTHROPIC_API_KEY=sk-ant-SUA-CHAVE-AQUI
DEMANDAS_DIR=/opt/analista/demandas
```

---

## 4. Cadastrar o primeiro usuário

```bash
sudo -u analista /opt/analista/venv/bin/python -m analista_processual \
    adduser admin SUA_SENHA_SEGURA admin@seuescritorio.com.br

# Verificar usuários cadastrados
sudo -u analista /opt/analista/venv/bin/python -m analista_processual listusers
```

---

## 5. Iniciar o serviço

```bash
systemctl start analista-processual
systemctl status analista-processual

# Ver logs em tempo real
journalctl -u analista-processual -f
```

Acesse: **https://seu-dominio.com.br**

---

## 6. Configurar CD automático (GitHub Actions)

No seu repositório GitHub, vá em **Settings → Secrets and variables → Actions** e adicione:

| Secret | Valor |
|--------|-------|
| `VPS_HOST` | IP ou domínio do VPS |
| `VPS_USER` | `root` (ou usuário com sudo) |
| `VPS_SSH_KEY` | Conteúdo da chave privada SSH (`cat ~/.ssh/id_ed25519`) |
| `VPS_PORT` | `22` (opcional, padrão) |

A partir daí, cada `git push main` faz deploy automático em ~30 segundos.

### Gerar chave SSH para o GitHub Actions

```bash
# Na sua máquina local
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""

# Copie a chave pública para o VPS
ssh-copy-id -i ~/.ssh/deploy_key.pub root@<IP-DO-VPS>

# Copie a chave PRIVADA para o GitHub Secret VPS_SSH_KEY
cat ~/.ssh/deploy_key
```

---

## Gestão de usuários

```bash
# Cadastrar usuário
python -m analista_processual adduser usuario senha123 email@dominio.com

# Listar usuários
python -m analista_processual listusers

# Alterar plano
python -m analista_processual setplan usuario pro
```

**Planos disponíveis:** `free` · `pro` · `enterprise`

Os dados de cada usuário ficam isolados em:
```
/opt/analista/demandas/<username>/
├── caso-1/
├── caso-2/
└── ...
```

---

## Comandos úteis no VPS

```bash
# Status do serviço
systemctl status analista-processual

# Reiniciar após mudanças de configuração
systemctl restart analista-processual

# Logs em tempo real
journalctl -u analista-processual -f

# Atualizar manualmente (sem GitHub Actions)
sudo bash /opt/analista/Skill/deploy/update.sh

# Testar nginx
nginx -t && systemctl reload nginx

# Renovação SSL (automática via certbot timer, mas pode forçar)
certbot renew --dry-run
```

---

## Arquitetura do stack

```
Internet
    ↓ HTTPS (443)
nginx — SSL/TLS (Let's Encrypt)
    ↓ HTTP interno (127.0.0.1:7860)
systemd: analista-processual.service
    ↓ EnvironmentFile: /etc/analista/secrets.env
Python 3.11 + Gradio 5.x
    ↓ auth= verificar_credenciais()
SQLite: /opt/analista/demandas/users.db
    ↓ workspace por usuário
/opt/analista/demandas/<username>/<demanda>/
```

---

## Custos estimados

| Item | Custo/mês |
|------|-----------|
| Hostinger KVM2 | ~$6,49 USD |
| Domínio .com.br | ~R$5 (amortizado) |
| SSL (Let's Encrypt) | Gratuito |
| Anthropic API | Conforme uso |
| **Total fixo** | **~R$45/mês** |
