#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_UVICORN="$ROOT_DIR/.venv/bin/uvicorn"

if [[ ! -x "$BACKEND_UVICORN" ]]; then
  echo "Erro: nao encontrei o uvicorn em $BACKEND_UVICORN"
  exit 1
fi

cleanup() {
  local exit_code=$?
  if [[ -n "${backend_pid:-}" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid" 2>/dev/null || true
  fi
  if [[ -n "${frontend_pid:-}" ]] && kill -0 "$frontend_pid" 2>/dev/null; then
    kill "$frontend_pid" 2>/dev/null || true
  fi
  if [[ -n "${backend_pid:-}" ]]; then
    wait "$backend_pid" 2>/dev/null || true
  fi
  if [[ -n "${frontend_pid:-}" ]]; then
    wait "$frontend_pid" 2>/dev/null || true
  fi
  exit "$exit_code"
}

trap cleanup INT TERM EXIT

echo "Iniciando backend em http://localhost:8000"
"$BACKEND_UVICORN" api.main:app --reload &
backend_pid=$!

echo "Iniciando frontend em http://localhost:5173"
(cd "$ROOT_DIR/web" && npm run dev) &
frontend_pid=$!

wait -n "$backend_pid" "$frontend_pid"
