# /apex-deploy — Guia de deploy no pestana.app

Oriente o usuário no deploy do APEX-LEGAL PERFORMANCE no Hostinger VPS com domínio `pestana.app`.

## Contexto do projeto

- **Domínio:** `pestana.app` (frontend) e `api.pestana.app` (backend FastAPI)
- **VPS:** Hostinger KVM2 com Docker instalado
- **Branch de produção:** `main` (após merge do `claude/open-analyst-squad-5ujs8`)
- **Script de setup:** `deploy/docker-setup.sh`
- **Script de update:** `deploy/docker-update.sh`

## O que fazer

1. Leia `deploy/docker-setup.sh` e `deploy/nginx.conf` para entender o stack atual
2. Leia `docker-compose.yml` para verificar os serviços configurados
3. Se o argumento for `$ARGUMENTS`:
   - `status` → oriente como verificar se o deploy está saudável (docker ps, logs, curl)
   - `update` → mostre os comandos para atualizar sem downtime
   - `ssl` → oriente sobre renovação de certificado Let's Encrypt
   - `logs` → mostre como ver logs dos containers
   - (vazio) → mostre o fluxo completo do zero

## Checklist DNS (sempre mostrar)

```
hPanel Hostinger → pestana.app → DNS Zone Editor:
  @    A  →  IP_DA_VPS
  www  A  →  IP_DA_VPS
  api  A  →  IP_DA_VPS
```

## Comando principal

```bash
ssh root@IP_DA_VPS
curl -fsSL https://raw.githubusercontent.com/felippepestana/Skill/main/deploy/docker-setup.sh \
  | bash -s -- pestana.app
```

Seja objetivo e mostre os comandos exatos para executar no terminal.
