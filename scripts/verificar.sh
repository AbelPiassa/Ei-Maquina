#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

echo '[1/4] Sintaxe Python'
python3 -m compileall -q main.py storage.py local_ai.py

echo '[2/4] Testes Python'
if ! python3 -m pytest -q; then
  echo 'Para instalar os testes: python3 -m pip install -r requirements-dev.txt' >&2
  exit 1
fi

echo '[3/4] Scripts shell'
bash -n iniciar.sh configurar_ia_local.sh scripts/verificar.sh

echo '[4/4] JavaScript'
if command -v node >/dev/null 2>&1; then
  node --check static/app.js
else
  echo 'Node.js ausente: teste JS ignorado (não necessário para executar o aplicativo).'
fi

echo 'Verificações concluídas.'
