#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 não encontrado. Instale python3 pelo gerenciador de pacotes.'
  exit 1
fi
exec python3 main.py "$@"
