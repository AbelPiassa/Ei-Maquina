# Como publicar a Ei, Máquina! no GitHub

Este é um guia para o **primeiro upload do código**, sem enviar os dados reais de estudo. A versão atual é **v0.2**.

## 1. Revise antes de publicar

No terminal, dentro da pasta que contém `main.py`, `README.md` e `.gitignore`:

```bash
ls -la
./scripts/verificar.sh
```

Nenhum modelo GGUF, arquivo `ai_config.json`, banco SQLite, ZIP de backup, `.env` ou print particular deve ser enviado.

## 2. Inicialize o Git na pasta do código

```bash
git init -b main
git add .
git status --short
git diff --cached --stat
git commit -m "chore: organiza Ei Máquina v0.2 para GitHub"
```

**Importante:** faça isso na pasta do projeto extraído, **não** dentro de `~/.local/share/ei-maquina/`, onde ficam seus dados privados. Se o Git já estiver inicializado, pule o `git init`.

## 3. Crie o repositório vazio no GitHub

Acesse https://github.com/new e configure:

- **Repository name:** `Ei-Maquina`
- **Description:** `Assistente pessoal de estudos para Linux Mint com Python, SQLite, anotações e IA local opcional.`
- **Visibility:** `Public` somente se você quiser tornar o código visível a todos; `Private` caso prefira revisar mais antes.
- **Initialize this repository with:** **nenhum** README, `.gitignore` ou `LICENSE` — esses arquivos são gerenciados localmente.

Depois que o GitHub criar o repositório, copie a URL HTTPS que ele mostrar. O endereço costuma ter este formato: `https://github.com/SEU_USUARIO/Ei-Maquina.git`.

## 4. Envie os arquivos

Substitua a URL abaixo **pela URL real** copiada do seu GitHub:

```bash
git remote add origin https://github.com/SEU_USUARIO/Ei-Maquina.git
git push -u origin main
```

Se já existir um remoto `origin`, confira com `git remote -v` antes de alterá-lo. Se o GitHub pedir autenticação, use um método suportado (login pelo gerenciador de credenciais ou token), **não** sua senha de conta como senha Git.

## 5. Deixe o perfil do repositório organizado

Em **About** no GitHub, adicione a descrição, o link do Figma (como referência de design) e tópicos, por exemplo:

```text
python, sqlite, linux-mint, local-ai, study-planner, javascript, llama-cpp, portfolio
```

Quando o workflow `Testes e verificações` rodar com sucesso em **Actions**, você pode mencionar isso no portfólio. Não marque a IA por voz como concluída antes de implementá-la.

## 6. Próximas atualizações

```bash
git status
git add .
git commit -m "feat: descreva a melhoria feita"
git push
```

Mantenha alterações pequenas, descreva testes realizados e atualize `CHANGELOG.md` e `AI.md` conforme a evolução. Nunca envie arquivos ignorados usando `git add -f` sem revisar sua natureza.

## Licença

O projeto **ainda não possui licença de uso definida**. Antes de convidar contribuidores ou permitir que outras pessoas reutilizem o código, escolha conscientemente uma licença apropriada e adicione o arquivo `LICENSE`.
