#!/usr/bin/env bash
# CodeLens one-shot launcher (macOS first; Linux works too).
#
#   ./start.sh          install what's missing, pull the model, run everything
#   ./start.sh setup    install dependencies + pull the model only
#   ./start.sh test     run every test suite
#
# Override the auto-picked model:  OLLAMA_MODEL=qwen2.5-coder:14b ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="${ROOT}/backend"
FRONTEND="${ROOT}/frontend"
LOGS="${ROOT}/.logs"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
OLLAMA_URL="http://127.0.0.1:11434"
PIDS=""

say()  { printf '\033[1;35m▸ %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✓ %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------- checks ----
find_python() {
  for py in python3.13 python3.12 python3.11 python3; do
    if have "${py}" && "${py}" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
      echo "${py}"; return
    fi
  done
  die "Python 3.11+ required. Install it with:  brew install python@3.12"
}

check_tools() {
  PY="$(find_python)"
  have node || die "Node 18+ required. Install it with:  brew install node"
  [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ] || die "Node 18+ required (found $(node -v))."
  have ollama || die "Ollama not found. Install it from https://ollama.com/download"
  ok "python: $(${PY} --version)  node: $(node -v)  ollama: $(ollama --version 2>&1 | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | tail -1)"
}

# ----------------------------------------------------------------- model ----
# Pick the largest Qwen2.5-Coder that runs comfortably in this machine's RAM.
pick_model() {
  if [ -n "${OLLAMA_MODEL:-}" ]; then echo "${OLLAMA_MODEL}"; return; fi
  local bytes gb
  if [ "$(uname)" = "Darwin" ]; then bytes="$(sysctl -n hw.memsize)"
  else bytes="$(awk '/MemTotal/ {print $2 * 1024}' /proc/meminfo)"; fi
  gb=$((bytes / 1024 / 1024 / 1024))
  if   [ "${gb}" -ge 32 ]; then echo "qwen2.5-coder:14b"   # ~9 GB, best quality
  elif [ "${gb}" -ge 16 ]; then echo "qwen2.5-coder:7b"    # ~4.7 GB, recommended
  else                        echo "qwen2.5-coder:3b"    # ~1.9 GB, 8 GB Macs
  fi
}

ensure_ollama() {
  if ! curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
    say "Starting Ollama..."
    if [ "$(uname)" = "Darwin" ] && [ -d "/Applications/Ollama.app" ]; then
      open -ga Ollama
    else
      nohup ollama serve >"${LOGS}/ollama.log" 2>&1 &
    fi
    for _ in $(seq 1 30); do curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1 && break; sleep 1; done
    curl -fsS "${OLLAMA_URL}/api/tags" >/dev/null 2>&1 || die "Ollama did not start (see ${LOGS}/ollama.log)."
  fi
  if ollama list | awk 'NR > 1 {print $1}' | grep -qx "${MODEL}"; then
    ok "model ${MODEL} already pulled"
  else
    say "Pulling ${MODEL} (one-time download)..."
    ollama pull "${MODEL}"
  fi
}

# ------------------------------------------------------------------ deps ----
install_deps() {
  say "Backend dependencies..."
  [ -x "${BACKEND}/.venv/bin/python" ] || "${PY}" -m venv "${BACKEND}/.venv"
  local stamp="${BACKEND}/.venv/.deps-stamp"
  if [ ! -f "${stamp}" ] || [ "${BACKEND}/requirements-dev.txt" -nt "${stamp}" ] || [ "${BACKEND}/requirements.txt" -nt "${stamp}" ]; then
    "${BACKEND}/.venv/bin/pip" install -q --upgrade pip
    "${BACKEND}/.venv/bin/pip" install -q -r "${BACKEND}/requirements-dev.txt"
    touch "${stamp}"
  fi
  ok "backend ready"

  say "Frontend dependencies..."
  if [ ! -d "${FRONTEND}/node_modules" ] || [ "${FRONTEND}/package-lock.json" -nt "${FRONTEND}/node_modules" ]; then
    (cd "${FRONTEND}" && npm install --no-fund --no-audit --loglevel=error && touch node_modules)
  fi
  ok "frontend ready"
}

# ------------------------------------------------------------------- run ----
cleanup() {
  [ -n "${PIDS}" ] && kill ${PIDS} 2>/dev/null || true
  wait 2>/dev/null || true
  echo; ok "CodeLens stopped (Ollama keeps running)."
}

port_free() { ! (have lsof && lsof -ti "tcp:$1" >/dev/null 2>&1); }

run_all() {
  port_free "${API_PORT}" || die "Port ${API_PORT} is busy. Free it or run: API_PORT=8001 ./start.sh"
  port_free "${WEB_PORT}" || die "Port ${WEB_PORT} is busy. Free it or run: WEB_PORT=5174 ./start.sh"
  trap cleanup INT TERM EXIT

  say "Starting API on :${API_PORT} (model ${MODEL})..."
  (cd "${BACKEND}" && LLM_PROVIDER=ollama OLLAMA_MODEL="${MODEL}" OLLAMA_BASE_URL="${OLLAMA_URL}" \
    CORS_ORIGINS="http://localhost:${WEB_PORT},http://127.0.0.1:${WEB_PORT}" \
    exec .venv/bin/uvicorn main:app --host 127.0.0.1 --port "${API_PORT}") >"${LOGS}/api.log" 2>&1 &
  PIDS="${PIDS} $!"
  for _ in $(seq 1 30); do curl -fsS "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1 && break; sleep 1; done
  curl -fsS "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1 || die "API failed to start — see ${LOGS}/api.log"
  ok "API up: $(curl -fsS "http://127.0.0.1:${API_PORT}/api/health")"

  say "Starting web app on :${WEB_PORT}..."
  (cd "${FRONTEND}" && VITE_API_TARGET="http://127.0.0.1:${API_PORT}" exec ./node_modules/.bin/vite --port "${WEB_PORT}" --strictPort) \
    >"${LOGS}/web.log" 2>&1 &
  PIDS="${PIDS} $!"
  for _ in $(seq 1 30); do curl -fsS "http://localhost:${WEB_PORT}" >/dev/null 2>&1 && break; sleep 1; done

  local url="http://localhost:${WEB_PORT}"
  ok "CodeLens is running → ${url}   (logs in .logs/, Ctrl+C to stop)"
  if have open; then open "${url}"; elif have xdg-open; then xdg-open "${url}" >/dev/null 2>&1 || true; fi
  wait
}

run_tests() {
  say "Backend tests + lint";  (cd "${BACKEND}" && .venv/bin/pytest -q && .venv/bin/ruff check .)
  say "Frontend unit tests";   (cd "${FRONTEND}" && npm test --silent)
  say "Type-check + build";    (cd "${FRONTEND}" && npm run build --silent >/dev/null)
  ok "All tests passed."
}

# ------------------------------------------------------------------ main ----
mkdir -p "${LOGS}"
check_tools
install_deps
case "${1:-run}" in
  test)  run_tests ;;
  setup) MODEL="$(pick_model)"; ensure_ollama; ok "Setup complete. Run ./start.sh to launch." ;;
  run)   MODEL="$(pick_model)"; ensure_ollama; run_all ;;
  *)     die "Usage: ./start.sh [run|setup|test]" ;;
esac
