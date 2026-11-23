# Roadmap — Ei, Máquina!

As marcações indicam o estado do **código**, não testes em todos os ambientes.

## v0.1 — Base local

- [x] Dashboard com menu superior e temas claro/escuro.
- [x] Cadastro de cursos e aulas, com progresso e status.
- [x] Anotações com textos, códigos e prints.
- [x] Pastas e vínculo de anotações aos estudos.
- [x] Histórico do conteúdo estudado sem gráficos de horas.
- [x] Agenda, prioridades e cronômetro separado do histórico.
- [x] Backup manual e armazenamento SQLite.

## v0.2 — IA local opcional (versão atual)

- [x] Comandos escritos para navegar e consultar dados.
- [x] Integração opcional com `llama.cpp` e GGUF.
- [x] Motor sob demanda e encerramento após inatividade.
- [x] Contexto mínimo de estudos, sem análise de imagens.
- [x] Testes de integração com servidor de IA **simulado**.
- [ ] Testar desempenho e compatibilidade da inferência real no Linux Mint com i5-2500K/12 GB de RAM.

## v0.3 — Voz e experiência desktop (planejado)

- [ ] Detectar offline a frase de ativação "Ei, Máquina!" em português.
- [ ] Reconhecer comandos falados e responder por voz ou texto, conforme configuração.
- [ ] Janela flutuante completa e compacta.
- [ ] Conversa temporária com tempo de silêncio configurável.
- [ ] Iniciar serviço leve de escuta depois de entrar no Linux Mint.
- [ ] Controles de privacidade do microfone e confirmação de mudanças importantes.

## Fora de escopo da v1

- IA que interpreta prints ou imagens.
- Arduino e outros dispositivos eletrônicos.
- APIs de IA pagas.
- Estatísticas e gráficos de horas estudadas.
- Armazenamento integral do histórico de conversas.
- Backups automáticos.

Documentar cada marco no `CHANGELOG.md` após teste.
