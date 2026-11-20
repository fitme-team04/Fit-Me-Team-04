#!/usr/bin/env bash
# Rocky8/Linux에서 V2를 이 체크아웃의 코드로 실행한다. 인자 db 또는 media는 독립 워커를 실행한다.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
APP_ROOT=$(pwd -P)
TEAM_DIR=${FITME_TEAM_DIR:-"$HOME/poc-size-ai"}
VENV_DIR=${FITME_V2_VENV:-"${XDG_DATA_HOME:-$HOME/.local/share}/fitme-v2/venv"}
ROLE=${1:-web}
case "$ROLE" in web|db|media) ;; *) echo "사용: bash web/run.sh [web|db|media]"; exit 2 ;; esac

# 설정은 shell 코드로 실행하지 않는다. web/.env가 우선이고 팀 .env에서는 DB 설정만 재사용한다.
read_config() {
  local file=$1 scope=$2 key value
  [ -r "$file" ] || return 0
  while IFS='=' read -r key value || [ -n "${key:-}" ]; do
    value=${value%$'\r'}
    case "$key" in
      DB_HOST|DB_PORT|DB_USER|DB_PASSWORD|DB_SSL|DB_CONTAINER|MYSQL_ROOT_PASSWORD) ;;
      APP_PORT|APP_BIND|REDIS_URL|V2_EMBEDDED_WORKERS|V2_RELOAD) [ "$scope" = app ] || continue ;;
      *) continue ;;
    esac
    if [ -n "$value" ] && [ -z "${!key:-}" ]; then export "$key=$value"; fi
  done < "$file"
}
read_config "$APP_ROOT/.env" app
read_config "$APP_ROOT/../.env" app
read_config "$TEAM_DIR/.env" team
export REDIS_URL=${REDIS_URL:-redis://127.0.0.1:6380/0}
export PYTHONDONTWRITEBYTECODE=1

shared="$TEAM_DIR/.venv/bin/python"
has_dependencies() {
  [ -x "$1" ] && "$1" -c 'import fastapi, uvicorn, pymysql, redis, openai' >/dev/null 2>&1
}
if has_dependencies "$VENV_DIR/bin/python"; then
  PY="$VENV_DIR/bin/python"
elif has_dependencies "$shared"; then
  PY="$shared"
else
  PY="$VENV_DIR/bin/python"
  if [ ! -x "$PY" ]; then
    base="$shared"
    if [ ! -x "$base" ]; then
      base=$(command -v python3.12 || true)
      [ -n "$base" ] || { echo "팀 Python 3.12 환경 또는 python3.12가 필요합니다."; exit 1; }
    fi
    "$base" -m venv "$VENV_DIR"
  fi
  "$PY" -m pip install --disable-pip-version-check -r requirements.txt
fi

docker_cmd=(docker)
if command -v sudo >/dev/null && ! docker info >/dev/null 2>&1 && sudo -n docker info >/dev/null 2>&1; then
  docker_cmd=(sudo -n docker)
fi
redis_ok() { "$PY" -c 'from v2_bus import connection; connection().ping()' >/dev/null 2>&1; }
if ! redis_ok; then
  if [ "$REDIS_URL" != redis://127.0.0.1:6380/0 ]; then
    echo "설정된 REDIS_URL에 접속할 수 없습니다."; exit 1
  fi
  if "${docker_cmd[@]}" container inspect fitme-v2-redis >/dev/null 2>&1; then
    "${docker_cmd[@]}" start fitme-v2-redis >/dev/null
  else
    "${docker_cmd[@]}" run -d --name fitme-v2-redis -p 127.0.0.1:6380:6379 redis:7.4-alpine >/dev/null
  fi
  for ((i=0; i<20; i++)); do redis_ok && break; sleep 1; done
  redis_ok || { echo "V2 Redis가 응답하지 않습니다."; exit 1; }
fi

# 독립 웹 프로세스는 Redis로만 요청을 전달한다. DB 준비는 워커가 있는 호스트에서 수행한다.
embedded=${V2_EMBEDDED_WORKERS:-true}
if [[ "$ROLE" != web || "${embedded,,}" =~ ^(1|true|yes)$ ]]; then
  name=${DB_CONTAINER:-poc-mysql}
  if [ "${DB_HOST:-127.0.0.1}" = 127.0.0.1 ] &&
     [ "$("${docker_cmd[@]}" inspect --format '{{.State.Status}}' "$name" 2>/dev/null || true)" = exited ]; then
    "${docker_cmd[@]}" start "$name" >/dev/null
  fi
  db_ok() { "$PY" -c 'from team_bridge import _db; _db.query("SELECT 1")' >/dev/null 2>&1; }
  for ((i=0; i<15; i++)); do db_ok && break; sleep 1; done
  db_ok || { echo "MySQL에 연결할 수 없습니다. 팀 DB 실행 상태와 web/.env의 DB 설정을 확인해 주세요."; exit 1; }
  if ! "$PY" -c 'from team_bridge import _db; _db.query("SELECT id FROM fitme_v2.listings LIMIT 0"); _db.query("SELECT id FROM fitme_v2.captures LIMIT 0")' >/dev/null 2>&1; then
    "$PY" v2_store.py
  fi
fi

if [ "$ROLE" = web ]; then
  reload=()
  default_reload=false
  [[ "$APP_ROOT" = /mnt/* ]] && default_reload=true
  if [[ "${V2_RELOAD:-$default_reload}" = true ]]; then reload=(--reload --reload-dir "$APP_ROOT"); fi
  echo "입어봄 V2  http://localhost:${APP_PORT:-8766}/"
  exec "$PY" -m uvicorn main:app --host "${APP_BIND:-127.0.0.1}" --port "${APP_PORT:-8766}" "${reload[@]}"
fi
exec "$PY" v2_worker.py "$ROLE"
