#!/usr/bin/env bash
# Instalação OPCIONAL da IA local. Não requer API nem envia dados a servidores.
# Requer internet APENAS para baixar código-fonte do llama.cpp e modelo GGUF.
set -euo pipefail

DATA_DIR="${EI_MAQUINA_DATA_DIR:-$HOME/.local/share/ei-maquina}"
ENGINE_DIR="${EI_MAQUINA_IA_DIR:-$DATA_DIR/ia-local}"
SRC="$ENGINE_DIR/llama.cpp"
BIN="$SRC/build/bin/llama-server"
MODEL_DIR="$ENGINE_DIR/modelos"
MODEL="$MODEL_DIR/Qwen3-1.7B-Q4_K_M.gguf"
MODEL_URL='https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/main/Qwen3-1.7B-Q4_K_M.gguf?download=true'

printf '\nEi, Máquina! — Instalação opcional da IA local\n'
printf 'Modelo: Qwen3 1.7B Q4_K_M (cerca de 1,28 GB)\n'
printf 'Destino do modelo: %s\n' "$MODEL"
printf 'O código será compilado na sua máquina sem AVX2/FMA/F16C/BMI2.\n'
printf 'O modelo pode demorar para responder no i5-2500K.\n'
printf 'Se o download ou build falhar, o organizador continuará funcionando.\n\n'
read -r -p 'Deseja baixar e compilar agora? [s/N] ' answer
[[ "$answer" =~ ^[sS]$ ]] || { echo 'Nenhuma alteração realizada.'; exit 0; }

for dep in git cmake c++ curl python3; do
  if ! command -v "$dep" >/dev/null 2>&1; then
    printf 'Falta o programa %s. Instale-o antes de continuar.\n' "$dep" >&2
    echo 'No Linux Mint: sudo apt install git cmake build-essential curl python3' >&2
    exit 1
  fi
done

mkdir -p "$SRC" "$MODEL_DIR" "$DATA_DIR"
if [[ ! -d "$SRC/.git" ]]; then
  # Se a pasta está vazia, clone nela; em uma reinstalação, preserve a versão local.
  if [[ -n "$(ls -A "$SRC")" ]]; then
    echo "A pasta $SRC existe e não é um repositório Git; escolha outro EI_MAQUINA_IA_DIR." >&2
    exit 1
  fi
  git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$SRC"
fi

if [[ ! -x "$BIN" ]]; then
  echo 'Compilando o llama-server para CPU antiga...'
  cmake -S "$SRC" -B "$SRC/build" -DCMAKE_BUILD_TYPE=Release \
    -DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=OFF \
    -DGGML_FMA=OFF -DGGML_F16C=OFF -DGGML_BMI2=OFF \
    -DGGML_AVX_VNNI=OFF -DGGML_CPU_ALL_VARIANTS=OFF -DLLAMA_CURL=OFF
  cmake --build "$SRC/build" --config Release --target llama-server -j 2
fi

if [[ ! -f "$MODEL" ]]; then
  printf 'Baixando o modelo de %s ...\n' "$MODEL_URL"
  curl --fail --location --retry 3 --continue-at - --output "$MODEL.part" "$MODEL_URL"
  bytes=$(stat -c %s "$MODEL.part")
  if (( bytes < 800000000 )); then
    echo 'O download está incompleto (menos de 800 MB). Arquivo parcial preservado.' >&2
    exit 1
  fi
  mv "$MODEL.part" "$MODEL"
fi

export EI_MAQUINA_MODEL="$MODEL" EI_MAQUINA_BINARY="$BIN" EI_MAQUINA_CONFIG="$DATA_DIR/ai_config.json"
python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ['EI_MAQUINA_CONFIG'])
config = {'llama_server': os.environ['EI_MAQUINA_BINARY'],
          'model': os.environ['EI_MAQUINA_MODEL'], 'port': 18765}
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
p.chmod(0o600)
print('\nConfiguração salva em:', p)
PY
cat <<'EOF'

Instalação preparada. Agora execute:
    ./iniciar.sh
No dashboard, digite uma pergunta sobre seus estudos.
A primeira resposta pode demorar porque a IA inicia sob demanda.
O processo da IA será encerrado após cerca de 3 minutos de inatividade.
EOF
