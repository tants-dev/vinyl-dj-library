#!/bin/zsh
cd "$(dirname "$0")"

# Kill any existing server on port 8000
existing=$(lsof -ti :8000)
if [[ -n "$existing" ]]; then
  echo "Stopping existing server (PID $existing)..."
  kill "$existing"
  sleep 1
fi

source .venv/bin/activate
echo "Starting server at http://localhost:8000"
uvicorn api.main:app --port 8000 &

# Wait until the server is accepting connections, then open Chrome
until curl -s http://localhost:8000 > /dev/null; do sleep 0.2; done
open -a "Google Chrome" http://localhost:8000

wait
