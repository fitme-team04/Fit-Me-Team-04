#!/usr/bin/env bash
# =====================================================================
# infra/deploy/web-update.sh — 웹 VM 에서 "새 웹앱 이미지로 바꿔 끼우기"
# ---------------------------------------------------------------------
# 누가 실행하나?
#   GitHub Actions 가 Azure 의 "Run Command" 기능으로 웹 VM(fitme-vm-web-dev)
#   안에서 root 권한으로 실행한다. 사람이 VM 에 접속할 필요가 없다.
#
# 무엇을 하나? (4단계)
#   1) VM 관리 ID 로 Azure 토큰 받기         → 비밀번호 없이 로그인
#   2) 그 토큰을 ACR 전용 토큰으로 바꿔 docker 로그인
#   3) 새 이미지를 받아 웹앱 컨테이너만 교체 (MySQL·Redis 는 그대로 둠)
#   4) /api/health 로 잘 떴는지 확인 → 실패하면 로그를 보여 주고 실패 처리
#
# 전제 (11/11 설정 완료)
#   - 웹 VM 관리 ID(System assigned) On
#   - 웹 VM 관리 ID 에 ACR fitmeacrdev 의 AcrPull 역할 (이미지 받기만 가능)
#   - /opt/fitme-web 에 docker-compose.yml, .env, app.env 가 있음
#
# __TAG__ 는 워크플로가 실행 직전에 커밋 번호(github.sha)로 바꿔 넣는다.
# =====================================================================
set -euo pipefail   # 중간에 하나라도 실패하면 바로 멈춤

ACR=fitmeacrdev.azurecr.io   # 이미지 저장소 주소
TAG=__TAG__                  # 이번에 배포할 이미지 태그 (= 커밋 번호)
APP_DIR=/opt/fitme-web       # compose 파일과 설정 파일이 있는 폴더

cd "$APP_DIR"

# ---------------------------------------------------------------------
# 1) VM 관리 ID 토큰 받기
#    169.254.169.254 는 Azure VM 안에서만 접속되는 특별한 주소(IMDS).
#    여기에 물어보면 이 VM 의 관리 ID 로 된 Azure 토큰을 준다.
# ---------------------------------------------------------------------
AAD_TOKEN=$(curl -s -H Metadata:true \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

# ---------------------------------------------------------------------
# 2) ACR 로그인
#    Azure 토큰을 ACR 의 /oauth2/exchange 로 보내 ACR 전용 토큰으로 바꾼 뒤
#    docker login 에 비밀번호 대신 넣는다. (사용자 이름은 정해진 값 0000...)
# ---------------------------------------------------------------------
ACR_TOKEN=$(curl -s -X POST \
  -d "grant_type=access_token&service=$ACR&access_token=$AAD_TOKEN" \
  "https://$ACR/oauth2/exchange" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["refresh_token"])')
echo "$ACR_TOKEN" | docker login "$ACR" -u 00000000-0000-0000-0000-000000000000 --password-stdin >/dev/null
echo "ACR 로그인 완료"

# ---------------------------------------------------------------------
# 3) 새 이미지로 웹앱만 교체
#    .env 의 WEB_TAG 를 이번 커밋 번호로 바꾸면 compose 가 그 태그의 이미지를 씀.
#    (예전 태그로 되돌리고 싶을 땐 WEB_TAG 만 예전 값으로 바꾸고 up -d 하면 됨)
#    "app" 서비스만 지정해서 MySQL·Redis 는 재시작하지 않는다.
# ---------------------------------------------------------------------
sed -i "s/^WEB_TAG=.*/WEB_TAG=$TAG/" .env
docker compose pull app
docker compose up -d app
echo "웹앱 컨테이너 교체 완료 (태그 $TAG)"

# 안 쓰는 옛 이미지 정리 (디스크가 가득 차지 않게, 최근 것은 남음)
docker image prune -f >/dev/null || true

# ---------------------------------------------------------------------
# 4) 상태 확인: 최대 60초 동안 /api/health 가 응답하는지 확인
#    성공하면 응답(JSON)을 출력하고 끝, 실패하면 최근 로그 30줄을 보여 주고 실패
#    (워크플로는 출력에 "version":"2" 가 있는지로 성공/실패를 판단한다)
# ---------------------------------------------------------------------
for i in $(seq 20); do
  if curl -fs 127.0.0.1:8766/api/health; then
    echo
    exit 0
  fi
  sleep 3
done
echo "health check 실패 — 최근 로그:"
docker compose logs --tail 30 app
exit 1
