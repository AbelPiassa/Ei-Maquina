# Comece aqui — Ei, Máquina!

Este guia utiliza a versão 0.2, cujo dashboard funciona no navegador **apenas no seu computador**.

## 1. Rodar o organizador

```bash
cd Ei-Maquina
chmod +x iniciar.sh configurar_ia_local.sh
./iniciar.sh
```

A interface abre em `http://127.0.0.1:8765`. Pressione `Ctrl+C` no terminal para encerrar.

Se a porta 8765 estiver ocupada, use `./iniciar.sh --port 8766` e acesse `http://127.0.0.1:8766`.

## 2. Testar os recursos

1. Acesse **Cursos** e cadastre um curso fictício.
2. Adicione aulas e marque o progresso.
3. Crie uma anotação, cole um print com `Ctrl+V` e salve.
4. Cadastre um registro no **Histórico de Estudos**, vinculado à aula.
5. Teste prioridades e agenda; experimente o tema escuro.
6. Faça um **backup manual** e guarde a cópia fora do computador quando possível.

## 3. IA local — instalação opcional

```bash
sudo apt update
sudo apt install git cmake build-essential curl python3
./configurar_ia_local.sh
```

O script exige internet para baixar o código-fonte de `llama.cpp` e o modelo GGUF, mas o uso posterior é local. Ele pede confirmação antes de iniciar o download.

Para manter os arquivos da IA em outro HD montado no Linux Mint, informe o caminho real, por exemplo:

```bash
EI_MAQUINA_IA_DIR="/caminho/do/HD/ei-maquina-ia" ./configurar_ia_local.sh
```

Não copie caminhos de montagem fictícios literalmente. O banco de estudos permanece em `~/.local/share/ei-maquina`.

**O microfone ainda não funciona nesta versão.** Voz e janela flutuante são etapas futuras.

## 4. Testar o código

```bash
python3 -m pip install -r requirements-dev.txt
./scripts/verificar.sh
```

## 5. Atualizar sem perder os dados

Encerre o aplicativo, faça um backup manual e atualize o código. Os dados são guardados fora da pasta do projeto.
