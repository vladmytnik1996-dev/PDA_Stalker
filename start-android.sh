#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8080}"
if ! command -v python >/dev/null 2>&1; then
  echo "Python не установлен. Выполните: pkg install python -y"
  exit 1
fi
exec python server.py --port "$PORT"
