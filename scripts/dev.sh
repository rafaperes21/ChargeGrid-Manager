#!/usr/bin/env bash
# Sobe o ambiente de desenvolvimento do ChargeGrid-Manager com um unico comando.
#
# Garante os .env de cada servico, sobe o Postgres via docker compose, cria/instala os venvs
# (Python 3.11) e node_modules que faltarem, roda migration+seed+gerador de historico no
# backend, e sobe cada servico em background nesta mesma janela, com log prefixado por
# servico. Ctrl+C encerra todos de uma vez.
#
# E idempotente: pode rodar de novo a qualquer momento sem duplicar dado ou reinstalar do
# zero (seed e gerador de historico ja se protegem sozinhos; o script pula venv/node_modules
# que ja existem).
#
# Uso:
#   ./scripts/dev.sh                          # sobe tudo
#   ./scripts/dev.sh --only backend,ia         # so backend + IA (sem os frontends)
#   ./scripts/dev.sh --skip-setup              # so abre os servicos, sem reinstalar/migrar
#   ./scripts/dev.sh --recreate                # apaga e recria venv/node_modules antes

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALL_SERVICES=(backend ia frontend-proprietario frontend-cliente)
ONLY=("${ALL_SERVICES[@]}")
SKIP_SETUP=0
RECREATE=0
POSTGRES_USER=chargegrid  # precisa bater com POSTGRES_USER do .env.example da raiz

usage() {
  cat <<EOF
Uso: $0 [--only svc1,svc2,...] [--skip-setup] [--recreate]

Servicos disponiveis: ${ALL_SERVICES[*]}
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --only)
      IFS=',' read -r -a ONLY <<< "$2"
      shift 2
      ;;
    --skip-setup)
      SKIP_SETUP=1
      shift
      ;;
    --recreate)
      RECREATE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Argumento desconhecido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

contains() {
  local needle="$1"
  shift
  for item in "$@"; do
    if [ "$item" = "$needle" ]; then
      return 0
    fi
  done
  return 1
}

for svc in "${ONLY[@]}"; do
  if ! contains "$svc" "${ALL_SERVICES[@]}"; then
    echo "Servico desconhecido: '$svc'. Use um de: ${ALL_SERVICES[*]}" >&2
    exit 1
  fi
done

ensure_env() {
  local dir="$1"
  if [ -f "$dir/.env.example" ] && [ ! -f "$dir/.env" ]; then
    cp "$dir/.env.example" "$dir/.env"
    echo "  .env criado em $dir"
  fi
}

# Imprime o caminho do python do venv em stdout - use com PYTHON_EXE=$(ensure_python_venv dir)
ensure_python_venv() {
  local dir="$1"
  local venv_path="$dir/.venv"
  if [ "$RECREATE" = "1" ] && [ -d "$venv_path" ]; then
    echo "  Removendo venv existente em $dir..." >&2
    rm -rf "$venv_path"
  fi
  if [ ! -d "$venv_path" ]; then
    echo "  Criando venv (Python 3.11) em $dir..." >&2
    if ! command -v python3.11 >/dev/null 2>&1; then
      echo "Nao encontrei 'python3.11' no PATH. Instale o Python 3.11 e tente de novo - versoes mais novas quebram o Prophet/cmdstanpy da IA." >&2
      exit 1
    fi
    python3.11 -m venv "$venv_path" || { echo "Falha ao criar o venv em $dir." >&2; exit 1; }
  fi
  echo "$venv_path/bin/python"
}

install_requirements() {
  local dir="$1" python_exe="$2"
  echo "  Instalando dependencias em $dir..."
  "$python_exe" -m pip install --upgrade pip -q
  "$python_exe" -m pip install -q -r "$dir/requirements-dev.txt" \
    || { echo "pip install falhou em $dir." >&2; exit 1; }
}

ensure_node_modules() {
  local dir="$1"
  local node_modules="$dir/node_modules"
  if [ "$RECREATE" = "1" ] && [ -d "$node_modules" ]; then
    echo "  Removendo node_modules existente em $dir..."
    rm -rf "$node_modules"
  fi
  if [ ! -d "$node_modules" ]; then
    echo "  Rodando npm install em $dir..."
    (cd "$dir" && npm install) || { echo "npm install falhou em $dir." >&2; exit 1; }
  fi
}

wait_postgres() {
  echo "  Aguardando Postgres ficar saudavel..."
  local max_attempts=30
  local i
  for ((i = 1; i <= max_attempts; i++)); do
    if docker compose exec -T postgres pg_isready -U "$POSTGRES_USER" >/dev/null 2>&1; then
      echo "  Postgres pronto."
      return 0
    fi
    sleep 2
  done
  echo "Postgres nao respondeu em $((max_attempts * 2))s. Confira se o Docker esta rodando ('docker ps') e tente 'docker compose up -d' manualmente." >&2
  exit 1
}

run_labeled() {
  local label="$1"
  shift
  ("$@" 2>&1 | sed -u "s/^/[$label] /") &
}

echo "=== ChargeGrid-Manager dev ==="
echo "Servicos: ${ONLY[*]}"

echo
echo "[1/4] Conferindo .env..."
ensure_env "$ROOT"
for svc in "${ALL_SERVICES[@]}"; do
  ensure_env "$ROOT/$svc"
done

NEEDS_POSTGRES=0
if contains backend "${ONLY[@]}"; then
  NEEDS_POSTGRES=1
fi
if contains ia "${ONLY[@]}"; then
  NEEDS_POSTGRES=1
fi

if [ "$NEEDS_POSTGRES" = "1" ]; then
  echo
  echo "[2/4] Subindo Postgres..."
  (cd "$ROOT" && docker compose up -d) \
    || { echo "Falha ao rodar 'docker compose up -d'. O Docker esta rodando?" >&2; exit 1; }
  wait_postgres
else
  echo
  echo "[2/4] Postgres nao necessario para os servicos escolhidos - pulando."
fi

if [ "$SKIP_SETUP" = "0" ]; then
  echo
  echo "[3/4] Setup dos servicos..."

  if contains backend "${ONLY[@]}"; then
    echo "backend:"
    BACKEND_PY=$(ensure_python_venv "$ROOT/backend")
    install_requirements "$ROOT/backend" "$BACKEND_PY"
    (
      cd "$ROOT/backend" || exit 1
      echo "  Rodando migrations..."
      "$BACKEND_PY" -m alembic upgrade head || { echo "alembic upgrade head falhou." >&2; exit 1; }
      echo "  Rodando seed..."
      "$BACKEND_PY" -m app.db.seed
      echo "  Rodando gerador de historico (pode levar alguns segundos)..."
      "$BACKEND_PY" -m simulador.historical_generator --seed 42
    ) || exit 1
  fi

  if contains ia "${ONLY[@]}"; then
    echo "ia:"
    IA_PY=$(ensure_python_venv "$ROOT/ia")
    install_requirements "$ROOT/ia" "$IA_PY"
  fi

  for frontend in frontend-proprietario frontend-cliente; do
    if contains "$frontend" "${ONLY[@]}"; then
      echo "${frontend}:"
      ensure_node_modules "$ROOT/$frontend"
    fi
  done
else
  echo
  echo "[3/4] --skip-setup: pulando instalacao/migrations/seed/gerador."
fi

echo
echo "[4/4] Subindo servicos (Ctrl+C encerra todos)..."

trap 'kill 0' EXIT INT TERM

if contains backend "${ONLY[@]}"; then
  run_labeled backend bash -c "cd '$ROOT/backend' && exec '$ROOT/backend/.venv/bin/python' -m uvicorn app.main:app --reload --port 8000"
fi
if contains ia "${ONLY[@]}"; then
  run_labeled ia bash -c "cd '$ROOT/ia' && exec '$ROOT/ia/.venv/bin/python' -m uvicorn app.main:app --reload --port 8001"
fi
if contains frontend-proprietario "${ONLY[@]}"; then
  run_labeled proprietario bash -c "cd '$ROOT/frontend-proprietario' && exec npm run dev"
fi
if contains frontend-cliente "${ONLY[@]}"; then
  run_labeled cliente bash -c "cd '$ROOT/frontend-cliente' && exec npm run dev"
fi

echo
echo "URLs:"
if contains backend "${ONLY[@]}"; then
  echo "  backend:      http://localhost:8000/docs"
fi
if contains ia "${ONLY[@]}"; then
  echo "  ia:           http://localhost:8001/docs"
fi
if contains frontend-proprietario "${ONLY[@]}"; then
  echo "  proprietario: veja a porta no log [proprietario] acima (Vite, geralmente 5173)"
fi
if contains frontend-cliente "${ONLY[@]}"; then
  echo "  cliente:      veja a porta no log [cliente] acima (Vite, geralmente 5174)"
fi

wait
