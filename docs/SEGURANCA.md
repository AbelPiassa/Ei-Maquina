# Segurança, privacidade e publicação

A Ei, Máquina! é um organizador **local e de uso pessoal**. Não foi construída como servidor público, nem inclui contas de usuário ou autenticação.

## Antes de publicar o repositório

- Não envie `~/.local/share/ei-maquina/`, bancos SQLite, backups, prints particulares, capturas com dados reais, `.env`, `ai_config.json`, modelos GGUF ou binários do `llama.cpp`.
- Use apenas capturas de tela com dados fictícios em `docs/previews/`.
- Revise `git status` e `git ls-files` antes de publicar. O `.gitignore` **não remove** arquivos já adicionados ao Git.
- Não inclua tokens pessoais, senhas, chaves privadas ou arquivos de configuração da sua máquina.
- Nunca execute scripts desconhecidos enviados em issues ou pull requests sem revisão.

## Executar com segurança

- A interface escuta somente `127.0.0.1` e deve permanecer assim.
- **Não exponha a porta 8765**, nem a porta da IA 18765, por encaminhamento de portas, túnel público ou bind em `0.0.0.0`.
- O mecanismo local pode carregar dados resumidos dos estudos no processo de IA do próprio computador.
- O modelo é obtido de um repositório de terceiros e o código-fonte de `llama.cpp` vem do GitHub. Leia os termos/licenças desses componentes antes de redistribuir.
- Os backups manuais contêm seus dados de estudo. Armazene as cópias com cuidado.

## Reportar problemas

Antes de abrir um issue público, remova informações pessoais dos logs e das imagens. Para falhas de segurança, evite publicar detalhes que exponham dados reais até avaliar o impacto.

## Limitações conhecidas

A proteção de origem e os limites de tamanho das requisições reduzem riscos, mas **não substituem autenticação**. O serviço não foi auditado para exposição em redes públicas. O uso é restrito ao computador pessoal.
