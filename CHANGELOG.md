# Histórico de versões

As versões refletem o código preparado até aqui; testes no hardware real poderão revelar limitações.

## [0.2.0] — IA local opcional

### Adicionado

- Integração opcional com `llama.cpp` e modelos GGUF.
- Download e compilação guiados para CPU sem AVX2.
- Inicialização do modelo apenas quando necessário e desligamento após inatividade.
- Respostas baseadas em contexto resumido dos estudos.
- Comandos locais escritos e testes com servidor de IA simulado.

### Mantido

- Dashboard, temas claro e escuro, cursos, aulas, anotações, histórico de conteúdos, agenda, prioridades, cronômetro e backup manual.

### Pendente

- Validação do modelo real no computador do autor.
- Voz, palavra de ativação, janela flutuante nativa e inicialização automática no Linux.

## [0.1.0] — Primeira versão funcional

- Aplicativo local com interface HTML/CSS/JavaScript servida por Python.
- Persistência SQLite, imagens em anotações e histórico do que foi estudado.
- Interface de organização de cursos, agenda e prioridades.
- Backups manuais.
