# 목적: AI 학습 표 읽기 함수 모음 — 1명 = 1행, 열 = 성별·나이·키·체중 + 치수 코드마다 1열 (없으면 None). 예시가 아니라 import 하는 도우미
# 누가 쓰나: AI(ai/2_심화/04_학습용_데이터표_만들기.py · ai/3_고급/03_회귀_키로_치수_예측.py)
# 난이도: 심화 — 2개 표 JOIN + 선택 조건, 세로(사람 × 치수) → 가로(1명 = 1행) 펼치기는 파이썬
# db/query/train/01_wide_by_profile.sql 과 같은 행·열 (실측 measured 만, 추정값 제외)
from _db import query

# 치수 열 (01_wide_by_profile.sql 의 MAX(CASE ...) 열과 같은 순서). 열을 늘리려면 여기에 코드 추가
MEASURE_COLUMNS = [
    "chest_girth", "waist_girth", "hip_girth", "neck_girth", "shoulder_width", "arm_length",
    "upperarm_girth", "wrist_girth", "inseam", "thigh_girth", "calf_girth", "ankle_girth",
]
BASE_COLUMNS = ["profile_id", "source_name", "gender", "age", "height_cm", "weight_kg"]


# 목적: DB 에서 실측 치수 행 읽기 (사람 × 치수 = 1행). source_name 을 주면 그 출처만
def measured_rows(source_name=None):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg,
               m.measure_code, m.value_cm
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE (%s IS NULL OR p.source_name = %s)
          AND m.measure_method = 'measured'
        ORDER BY p.profile_id, m.measure_code
    """
    return query(sql, (source_name, source_name))


# 목적: DB 값(Decimal) → float (NULL 은 None)
def to_number(value):
    if value is None:
        return None
    return float(value)


# 목적: 세로(사람 × 치수) → 가로(1명 = 1행) 로 펼치기. 없는 치수는 None
def load_rows(source_name=None):
    table = []
    by_id = {}
    for row in measured_rows(source_name):
        pid = row["profile_id"]
        if pid not in by_id:
            item = {
                "profile_id": pid,
                "source_name": row["source_name"],
                "gender": row["gender"],
                "age": row["age"],
                "height_cm": to_number(row["height_cm"]),
                "weight_kg": to_number(row["weight_kg"]),
            }
            for code in MEASURE_COLUMNS:
                item[code] = None
            by_id[pid] = item
            table.append(item)
        if row["measure_code"] in MEASURE_COLUMNS:
            by_id[pid][row["measure_code"]] = to_number(row["value_cm"])
    return table
