# Código de Acesso do GitHub para o Computador

Este guia explica como gerar e configurar um **Personal Access Token (PAT)** do GitHub para usar o Git no seu computador local.

---

## O que é um Personal Access Token?

Um **Personal Access Token (PAT)** é uma alternativa segura à senha para autenticar operações do Git via HTTPS. O GitHub exige o uso de tokens em vez de senhas para acesso via linha de comando desde agosto de 2021.

---

## 1. Gerar um Personal Access Token no GitHub

1. Acesse [github.com](https://github.com) e faça login na sua conta.
2. Clique na sua foto de perfil (canto superior direito) → **Settings**.
3. No menu lateral esquerdo, clique em **Developer settings**.
4. Clique em **Personal access tokens** → **Tokens (classic)**.
5. Clique em **Generate new token** → **Generate new token (classic)**.
6. Preencha os campos:
   - **Note**: dê um nome descritivo (ex: `Meu Computador`).
   - **Expiration**: escolha o prazo de validade desejado.
   - **Scopes**: marque pelo menos `repo` para acesso completo aos repositórios.
7. Clique em **Generate token**.
8. **Copie o token gerado** — ele só será exibido uma vez!

---

## 2. Configurar o Git no Computador

### Instalar o Git

- **Windows**: baixe em [git-scm.com](https://git-scm.com/download/win)
- **macOS**: execute `brew install git` ou baixe em [git-scm.com](https://git-scm.com/download/mac)
- **Linux (Ubuntu/Debian)**: execute `sudo apt install git`

### Configurar nome e e-mail

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

---

## 3. Usar o Token para Clonar ou Fazer Push

Ao executar um comando `git clone`, `git push` ou `git pull` em um repositório privado, o Git solicitará suas credenciais:

- **Username**: seu nome de usuário do GitHub
- **Password**: cole o **Personal Access Token** (não sua senha)

### Exemplo

```bash
git clone https://github.com/felippepestana/Skill.git
# Username: felippepestana
# Password: <cole o token aqui>
```

---

## 4. Salvar o Token (opcional, mas recomendado)

Para não precisar digitar o token toda vez, salve-o no gerenciador de credenciais do sistema:

### Windows

```bash
git config --global credential.helper manager
```

### macOS

```bash
git config --global credential.helper osxkeychain
```

### Linux

```bash
git config --global credential.helper store
```

> **Atenção**: o `credential.helper store` salva o token em texto simples em `~/.git-credentials`. Use em ambientes seguros.

---

## 5. Alternativa: Autenticação via SSH

Se preferir usar SSH (sem precisar de token), siga os passos:

1. Gere uma chave SSH no terminal:
   ```bash
   ssh-keygen -t ed25519 -C "seu@email.com"
   ```
2. Copie a chave pública:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
3. No GitHub: **Settings → SSH and GPG keys → New SSH key** → cole a chave pública.
4. Clone repositórios usando o endereço SSH:
   ```bash
   git clone git@github.com:felippepestana/Skill.git
   ```

---

## Recursos Adicionais

- [Documentação oficial: Creating a personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Documentação oficial: Connecting to GitHub with SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [GitHub CLI (`gh`)](https://cli.github.com/) — ferramenta de linha de comando oficial do GitHub
