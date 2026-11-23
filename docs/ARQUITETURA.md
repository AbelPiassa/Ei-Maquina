# Arquitetura — Ei, Máquina! v0.2

## Visão geral

```text
 Navegador local (HTML/CSS/JavaScript)
                 |
          HTTP 127.0.0.1
                 |
            main.py
          /     |      \
   storage.py   |     local_ai.py (opcional)
       |        |          |
     SQLite  comandos   llama-server → GGUF
       |
   dados e imagens locais
```

- `main.py`: inicializa o servidor local, expõe endpoints e interpreta comandos básicos.
- `storage.py`: gerencia SQLite, cursos, aulas, anotações, histórico, prioridades, agenda, imagens e backup.
- `local_ai.py`: controla o processo `llama-server`, envia um **contexto resumido dos estudos** e encerra o processo por inatividade.
- `static/index.html`, `static/styles.css`, `static/app.js`: interface do navegador.
- `tests/`: valida as regras do armazenamento, APIs e integração simulada da IA.

## Persistência e privacidade

O programa utiliza `~/.local/share/ei-maquina/` por padrão. O banco `estudos.sqlite3`, imagens e arquivo `ai_config.json` não devem ir para o GitHub. O backup ZIP é manual e pode conter informações pessoais.

A IA recebe metadados limitados: cursos, aulas recentes, datas, prioridades, agenda e **títulos** de notas. Prints e conteúdo HTML integral das anotações não são transmitidos ao modelo.

## Decisões técnicas

- Python puro na execução da aplicação; `pytest` é apenas dependência de desenvolvimento.
- Interface no navegador local, **não exposta** à rede Wi-Fi ou à internet.
- `llama.cpp` e GGUF opcionais, sem API de terceiros para inferência.
- Modelo carregado sob demanda e encerrado após inatividade.
- Cronômetro separado do histórico de conteúdos; sem estatísticas de horas.

## Limitações atuais

Voz, detecção da expressão "Ei, Máquina!", janela flutuante nativa e início automático com o Linux ainda não foram implementados. O modelo não foi validado em execução real no i5-2500K. A aplicação não inclui contas, autenticação ou acesso multiusuário.
