# 목적: 앱 설정 읽기 — web/.env 파일(내 PC) 또는 Azure App Service 의 "환경 변수"(클라우드)에서 값을 가져옴
# 핵심: 코드는 그대로 두고, 어디서 실행하느냐에 따라 "값"만 바뀐다 (팀 setup.sh 의 .env 방식과 같은 생각)
#   - 내 PC:  web/.env 에 적어 둔 값
#   - Azure:  포털 > App Service > 설정 > 환경 변수 에 넣은 값 (os.environ 으로 들어옴)
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent


# 목적: web/.env 를 읽어 os.environ 에 넣기 (이미 있는 값은 덮어쓰지 않음 → Azure 설정이 항상 우선)
def load_env_file():
    path = APP_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line == "" or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        # 빈 설정은 팀 루트 .env의 DB_PORT 등 기존 기본값을 사용한다.
        if value.strip() and key not in os.environ:
            os.environ[key] = value.strip()


load_env_file()


# 목적: 값 하나 읽기 (없으면 기본값)
def get(key, default=""):
    value = os.environ.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


# 데이터 모드: auto = DB 접속되면 DB, 안 되면 데모 / db = DB 만 / demo = 데모만
DATA_MODE = get("DATA_MODE", "auto").lower()

# Azure OpenAI (추천 이유 설명). 비워 두면 템플릿 문장으로 설명
AZURE_OPENAI_ENDPOINT = get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = get("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = get("AZURE_OPENAI_API_VERSION", "2024-10-21")


# 목적: Azure OpenAI 를 쓸 준비가 됐는지 (세 값이 모두 있어야 함)
def ai_configured():
    return AZURE_OPENAI_ENDPOINT != "" and AZURE_OPENAI_API_KEY != "" and AZURE_OPENAI_DEPLOYMENT != ""
