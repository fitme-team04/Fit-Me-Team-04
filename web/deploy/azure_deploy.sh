#!/usr/bin/env bash
# 목적: 입어봄 앱을 Azure App Service(Linux, Python)에 올리기 — WordPress 를 App Service 에 올린 것과 같은 방식
# 사용 (Rocky8 / VM 터미널, cd ~/poc-size-ai 에서 — Azure CLI 설치는 web/README.md 5-1):
#   az login --use-device-code                       # 처음 한 번
#   bash web/deploy/azure_deploy.sh <앱이름> [리소스그룹=rg-poc] [지역=koreacentral]
#   bash web/deploy/azure_deploy.sh --package-only   # Azure 연결 없이 배포 ZIP만 생성
#   → 배포한 웹앱의 기본 주소를 출력
# 하는 일:
#   1) 임시 폴더에 web/ 파일 + 팀 코드(db/예시_코드 도우미 5개)를 team_code/ 로 복사
#   2) az webapp up: App Service 플랜(B1) + 웹앱을 만들고(있으면 재사용) 코드를 zip 으로 올림 → Azure 가 requirements.txt 설치
#   3) 시작 명령을 uvicorn 으로 지정
# 비밀값(DB 암호·OpenAI 키)은 이 스크립트에 넣지 않는다 → 마지막에 안내하는 appsettings 명령으로 따로 넣기
set -euo pipefail

APP_NAME=${1:?"앱 이름을 넣어 주세요. 예: bash web/deploy/azure_deploy.sh ipeobom-dev"}
RG=${2:-rg-poc}
LOCATION=${3:-koreacentral}

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
TEAM="$ROOT/db/예시_코드"
mkdir -p "$ROOT/out"
BUILD=$(mktemp -d "$ROOT/out/.deploy.XXXXXXXX")
trap 'rm -rf -- "$BUILD"' EXIT

echo "1) 배포 폴더 만들기: $BUILD"
mkdir -p "$BUILD/team_code"
cp "$ROOT"/web/*.py "$ROOT/web/requirements.txt" "$BUILD/"
cp -r "$ROOT/web/static" "$BUILD/static"
for f in _db.py _추천.py _추정.py _검증.py _body_type.py; do
  cp "$TEAM/$f" "$BUILD/team_code/$f"
done

cd "$BUILD"
if [[ "$APP_NAME" == "--package-only" ]]; then
  archive="$ROOT/out/ipeobom-appservice.zip"
  python3 -m zipfile -c "$BUILD/package.zip" ./*.py requirements.txt team_code static
  mv -- "$BUILD/package.zip" "$archive"
  echo "배포 ZIP: $archive"
  exit 0
fi

echo "2) App Service 에 올리기 (몇 분 걸림)"
az webapp up --name "$APP_NAME" --resource-group "$RG" --location "$LOCATION" \
  --runtime "PYTHON:3.12" --sku B1

echo "3) 시작 명령 지정"
az webapp config set --name "$APP_NAME" --resource-group "$RG" \
  --startup-file "python -m uvicorn main:app --host 0.0.0.0 --port 8000" >/dev/null
HOSTNAME_APP=$(az webapp show --name "$APP_NAME" --resource-group "$RG" --query defaultHostName -o tsv)

cat <<EOF

완료: https://$HOSTNAME_APP   (상태 확인: /api/health)

다음: DB·Azure OpenAI 값을 환경 변수로 넣기 (값은 직접 채우기, 채팅·커밋에 남기지 않기)
  az webapp config appsettings set --name $APP_NAME --resource-group $RG --settings \\
    DATA_MODE=auto DB_HOST=<주소> DB_USER=<계정> DB_PASSWORD=<암호> DB_SSL=true \\
    AZURE_OPENAI_ENDPOINT=<엔드포인트> AZURE_OPENAI_API_KEY=<키> AZURE_OPENAI_DEPLOYMENT=<배포이름>
  (Key Vault 를 쓰면 값 자리에 @Microsoft.KeyVault(SecretUri=...) 를 넣음 — web/README.md 5-4)
EOF
