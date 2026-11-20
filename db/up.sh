#!/usr/bin/env bash
# PoC MySQL (Docker) — 컨테이너를 만들거나 시작하고 sql/*.sql 을 이름 순서대로 적용
# 사용: ./up.sh   (포트 바꾸기: DB_PORT=3307 ./up.sh / 여는 주소: DB_BIND, 기본 127.0.0.1 = 이 컴퓨터 안에서만)
# -p 주소·포트는 컨테이너를 처음 만들 때만 적용됨 (이미 있는 컨테이너는 그대로 시작)
set -euo pipefail
cd "$(dirname "$0")"

# ../.env 가 있으면 DB 값만 읽음 (CR 제거, 이미 환경변수로 준 값이 우선)
if [ -f ../.env ]; then
  while IFS='=' read -r k v; do
    case "$k" in DB_CONTAINER|DB_VOLUME|DB_IMAGE|DB_BIND|DB_PORT|MYSQL_ROOT_PASSWORD) [ -n "${!k:-}" ] || export "$k=$v" ;; esac
  done < <(tr -d '\r' < ../.env)
fi
NAME=${DB_CONTAINER:-poc-mysql}
VOLUME=${DB_VOLUME:-poc-mysql-data}
IMAGE=${DB_IMAGE:-mysql:8.0}
BIND=${DB_BIND:-127.0.0.1}
PORT=${DB_PORT:-3306}
ROOT_PW=${MYSQL_ROOT_PASSWORD:-poc-root}
DOCKER=${DOCKER:-docker}   # setup.sh 가 sudo 가 필요하면 "sudo docker" 로 넘김

# Docker 확인
$DOCKER ps >/dev/null 2>&1 || { echo "Docker 를 켜 주세요 (Windows 는 Docker Desktop)"; exit 1; }

# 컨테이너: 있으면 시작, 없으면 생성 (데이터는 볼륨 $VOLUME 에 보존)
# --restart unless-stopped: dockerd 가 뜰 때마다 컨테이너도 저절로 다시 뜸 (docker stop 으로 끈 것은 그대로)
if $DOCKER container inspect "$NAME" >/dev/null 2>&1; then
  $DOCKER update --restart unless-stopped "$NAME" >/dev/null   # 예전에 만든 컨테이너에도 같은 정책
  $DOCKER start "$NAME" >/dev/null
else
  $DOCKER run -d --restart unless-stopped --name "$NAME" -p "$BIND:$PORT:3306" \
    -e MYSQL_ROOT_PASSWORD="$ROOT_PW" \
    -v "$VOLUME:/var/lib/mysql" "$IMAGE" >/dev/null
fi

# 준비될 때까지 대기 (최대 3분)
echo -n "MySQL 준비 대기"
for _ in $(seq 90); do
  $DOCKER exec -e MYSQL_PWD="$ROOT_PW" "$NAME" mysql -h127.0.0.1 -uroot -e "SELECT 1" >/dev/null 2>&1 && break
  echo -n "."; sleep 2
done
echo

# SQL 적용 (00_ → 53_ 순서)
for f in sql/*.sql; do
  echo "적용: $f"
  $DOCKER exec -i -e MYSQL_PWD="$ROOT_PW" "$NAME" mysql -h127.0.0.1 -uroot --default-character-set=utf8mb4 < "$f"
done
echo "완료 — 접속: mysql -h 127.0.0.1 -P $PORT -uroot -p   (스키마 body / garment / ref)"
echo "열린 주소: $($DOCKER port "$NAME" 3306 2>/dev/null | tr '\n' ' ')"
