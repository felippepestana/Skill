# /apex-adduser — Adicionar usuário ao APEX-LEGAL

Crie ou gerencie um usuário no sistema APEX-LEGAL.

**Argumento:** `$ARGUMENTS` — pode ser `nome senha email [plano]` ou apenas um nome

## O que fazer

1. Parse o argumento `$ARGUMENTS`:
   - Se tiver 3+ partes: `username password email [plano]`
   - Se tiver 1 parte: só o username — pergunte senha, email e plano
   - Se vazio: pergunte todos os campos

2. Planos disponíveis: `free` (padrão), `pro`, `enterprise`

3. Mostre o comando correto para cada contexto:

**Ambiente local (desenvolvimento):**
```bash
python -m apex_legal adduser USERNAME SENHA EMAIL PLANO
```

**Via Docker (VPS em produção):**
```bash
docker compose -f /opt/apex-legal/docker-compose.yml exec backend \
  python -m apex_legal adduser USERNAME SENHA EMAIL PLANO
```

**Listar usuários:**
```bash
# Local
python -m apex_legal listusers

# Docker
docker compose -f /opt/apex-legal/docker-compose.yml exec backend \
  python -m apex_legal listusers
```

**Alterar plano:**
```bash
# Local
python -m apex_legal setplan USERNAME PLANO

# Docker
docker compose -f /opt/apex-legal/docker-compose.yml exec backend \
  python -m apex_legal setplan USERNAME PLANO
```

4. Lembre que usuários são armazenados em SQLite: `~/demandas/users.db` (local) ou `/data/demandas/users.db` (Docker).

Mostre os comandos prontos para executar.
