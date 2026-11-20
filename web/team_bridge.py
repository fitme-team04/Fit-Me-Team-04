# 목적: 팀이 만든 파이썬 코드(db/예시_코드)를 이 웹앱에서 그대로 불러 쓰기 위한 "다리" 파일
# 왜 필요한가:
#   팀 코드(_추천.py · _추정.py · _검증.py)는 원래 터미널에서 실행하는 예시라서
#   ① 폴더 위치를 알려 줘야 import 할 수 있고
#   ② DB 접속 주소가 127.0.0.1(내 PC)로 고정돼 있어 Azure 의 DB 로 바꿔 끼울 방법이 필요함
# 팀 파일은 한 글자도 고치지 않고, 여기서 접속 함수만 바꿔 끼운다 (기본값은 팀 코드와 똑같음)
import math
import os
import ssl
import sys
import time
from pathlib import Path

import pymysql

import demo_data
import settings
import sizekorea_reference

# 팀 코드 위치 후보: ① 저장소 안(내 PC: web/ 옆의 db/예시_코드) ② 배포용 복사본(Azure: web/team_code)
APP_DIR = Path(__file__).resolve().parent
CANDIDATES = [APP_DIR.parent / "db" / "예시_코드", APP_DIR / "team_code"]

TEAM_DIR = None
for folder in CANDIDATES:
    if (folder / "_추천.py").exists():
        TEAM_DIR = folder
        break
if TEAM_DIR is None:
    raise RuntimeError("팀 코드(_추천.py)를 찾지 못함: " + ", ".join(str(p) for p in CANDIDATES))

sys.path.insert(0, str(TEAM_DIR))

import _db                    # noqa: E402  팀: 접속·조회 도우미
import _추천 as team_rec       # noqa: E402  팀: 규칙 사이즈 추천 (여유분 계산·순위)
import _추정 as team_est       # noqa: E402  팀: k-NN 치수 추정 (키·체중 → 가슴둘레 등)
import _검증 as team_check     # noqa: E402  팀: 입력값 검사


# 목적: DB 접속 — 팀 _db.connect 와 같지만 주소·계정·암호화(SSL)를 환경 변수로 바꿀 수 있음
#   DB_HOST     기본 127.0.0.1 (내 PC). Azure VM 이면 VM 사설 IP, Azure Database for MySQL 이면 <이름>.mysql.database.azure.com
#   DB_PORT     기본 3306
#   DB_USER     기본 root
#   DB_PASSWORD 없으면 팀 .env 의 MYSQL_ROOT_PASSWORD → poc-root
#   DB_SSL      true 면 TLS 암호화 접속 (Azure Database for MySQL 은 기본으로 필수)
def azure_ready_connect():
    values = _db.read_env_file()                       # 팀 루트 .env (DB_PORT, MYSQL_ROOT_PASSWORD)
    host = _db.setting(values, "DB_HOST", "127.0.0.1")
    port = int(_db.setting(values, "DB_PORT", "3306"))
    user = _db.setting(values, "DB_USER", "root")
    password = os.environ.get("DB_PASSWORD") or _db.setting(values, "MYSQL_ROOT_PASSWORD", "poc-root")
    options = {
        "host": host, "port": port, "user": user, "password": password,
        "database": None, "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "connect_timeout": 3,
    }
    if _db.setting(values, "DB_SSL", "false").lower() in ("1", "true", "yes"):
        options["ssl"] = ssl.create_default_context()   # 서버 인증서 확인 + 암호화
    return pymysql.connect(**options)


# 팀 코드의 모든 조회(query)가 이 접속 함수를 쓰도록 바꿔 끼움
_db.connect = azure_ready_connect

# DB 상태를 30초 동안 기억 (요청마다 접속 시험을 하지 않으려고)
_status = {"checked_at": 0.0, "ok": False, "error": ""}


# 목적: 지금 DB 에 접속되는지 확인 → (True/False, 실패 이유)
def db_available():
    if settings.DATA_MODE == "demo":
        return False, "DATA_MODE=demo"
    now = time.time()
    if now - _status["checked_at"] < 30:
        return _status["ok"], _status["error"]
    try:
        _db.query("SELECT 1 AS ok")
        _status.update({"checked_at": now, "ok": True, "error": ""})
    except Exception as exc:                            # 접속 실패 이유를 그대로 보관 (화면 /api/health 에서 확인)
        _status.update({"checked_at": now, "ok": False, "error": type(exc).__name__ + ": " + str(exc)[:200]})
    return _status["ok"], _status["error"]


# 목적: 이번 요청을 DB 로 처리할지 데모로 처리할지 → "db" 또는 "demo"
def current_mode():
    ok, error = db_available()
    if ok:
        return "db"
    if settings.DATA_MODE == "db":
        raise RuntimeError("DATA_MODE=db 인데 DB 에 접속할 수 없음 — " + error)
    return "demo"


def _body_references():
    profiles = sizekorea_reference.configured_profiles()
    if profiles is not None:
        return profiles, demo_data.MEASURE_MAPS, "사이즈코리아 실측 표본"
    if current_mode() == "db":
        rows = _db.query(
            """SELECT p.profile_id, p.height_cm, p.weight_kg, m.measure_code, m.value_cm
               FROM body.profiles p JOIN body.measures m ON p.profile_id = m.profile_id
               WHERE p.height_cm > 0 AND p.weight_kg > 0 AND m.measure_method = 'measured'
                 AND m.measure_code IN (%s, %s, %s, %s) AND m.value_cm > 0
               ORDER BY p.profile_id, m.measure_code""", demo_data.REFERENCE_DIMENSIONS)
        return team_est.group_by_profile(rows), team_rec.measure_maps(), "팀 DB 실측 표본"

    people = {}
    for idx, (height, weight, *dimensions) in enumerate(demo_data.SAMPLE_PROFILES):
        measures = {code: cm for code, cm in zip(demo_data.REFERENCE_DIMENSIONS, dimensions) if cm is not None}
        people[idx] = {"height": height, "weight": weight, "measures": measures}
    return people, demo_data.MEASURE_MAPS, "예시 실측 표본"


# 국소 가중평균의 대역폭. 검증 전 시연 설정이며, 경계로 갈수록 가중치는 0으로 수렴한다.
HEIGHT_BANDWIDTH_CM = 14.0
WEIGHT_BANDWIDTH_KG = 25.0


def estimate_from_height_weight(height_cm, weight_kg):
    """부위별 평균·표준편차와 참고인 수를 반환한다. 표준편차는 현 표본의 산포다."""
    people, maps, source = _body_references()
    values, spreads, counts = estimate_parts(people, height_cm, weight_kg)
    return values, spreads, counts, maps, source


def estimate_parts(people, height_cm, weight_kg):
    """지정한 훈련 표본만 사용한다. 운영 경로와 분리 검증에서 같은 계산을 쓴다."""
    neighborhoods = {}
    for person in people.values():
        height_gap = (person["height"] - height_cm) / HEIGHT_BANDWIDTH_CM
        weight_gap = (person["weight"] - weight_kg) / WEIGHT_BANDWIDTH_KG
        distance_squared = height_gap ** 2 + weight_gap ** 2
        if distance_squared >= 1:
            continue
        weight = (1 - distance_squared) ** 2
        for code, value in person["measures"].items():
            if code in demo_data.REFERENCE_DIMENSIONS and team_check.MEASURE_MIN <= value <= team_check.MEASURE_MAX:
                neighborhoods.setdefault(code, []).append((weight, float(value)))

    values, spreads, counts = {}, {}, {}
    for code, observations in neighborhoods.items():
        total = sum(weight for weight, _ in observations)
        squared_weights = sum(weight ** 2 for weight, _ in observations)
        effective_count = total ** 2 / squared_weights
        # 가중치가 아주 낮은 먼 표본이나, 한 사람에게 거의 전부 의존하는 추정을 보류한다.
        if len(observations) < 3 or total < 1.0 or effective_count < 2.0:
            continue
        mean = sum(weight * value for weight, value in observations) / total
        variance = sum(weight * (value - mean) ** 2 for weight, value in observations)
        values[code] = mean
        spreads[code] = math.sqrt(variance / (total - squared_weights / total))
        counts[code] = len(observations)
    return values, spreads, counts
