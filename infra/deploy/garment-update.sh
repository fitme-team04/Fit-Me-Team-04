#!/usr/bin/env bash
# =====================================================================
# infra/deploy/garment-update.sh — 의류 VM 에서 "새 의류 서버 이미지로 바꿔 끼우기"
# GitHub Actions 가 Run Command 로 의류 VM(fitme-vm-garment-dev) 안에서 root 로 실행.
# web-update.sh 와 같은 방식: 관리 ID → ACR 로그인 → 이미지 교체 → /health 확인
# __TAG__ 는 워크플로가 커밋 번호로 바꿔 넣음.
# =====================================================================
set -euo pipefail

ACR=fitmeacrdev.azurecr.io
TAG=__TAG__
APP_DIR=/opt/fitme-garment
HEALTH=http://10.4.2.5:8002/health   # VM_BIND_IP(사설 IP)로 열려 있음

cd "$APP_DIR"

# 1) VM 관리 ID 토큰 → 2) ACR 전용 토큰으로 docker 로그인 (비밀번호 없음)
AAD_TOKEN=$(curl -s -H Metadata:true \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')
ACR_TOKEN=$(curl -s -X POST \
  -d "grant_type=access_token&service=$ACR&access_token=$AAD_TOKEN" \
  "https://$ACR/oauth2/exchange" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["refresh_token"])')
echo "$ACR_TOKEN" | docker login "$ACR" -u 00000000-0000-0000-0000-000000000000 --password-stdin >/dev/null
echo "ACR 로그인 완료"

# 3) .env 의 GARMENT_TAG 를 이번 커밋으로 바꾸고 교체 (되돌리기: GARMENT_TAG 만 예전 값으로)
sed -i "s/^GARMENT_TAG=.*/GARMENT_TAG=$TAG/" .env
docker compose pull garment
docker compose up -d garment
echo "의류 서버 컨테이너 교체 완료 (태그 $TAG)"
docker image prune -f >/dev/null || true

# 4) 최대 60초 동안 /health 확인
for i in $(seq 20); do
  if curl -fs "$HEALTH"; then echo; exit 0; fi
  sleep 3
done
echo "health check 실패 — 최근 로그:"
docker compose logs --tail 30 garment
exit 1
