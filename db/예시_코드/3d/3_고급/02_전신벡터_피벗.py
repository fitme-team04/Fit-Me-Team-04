# 목적: 사람마다 신체 치수 23개를 고정 순서 한 줄(전신 벡터)로 피벗 → 3D 몸 모델 형태 맞추기 입력 (없는 값은 None)
# 누가 쓰나: 3D
# 난이도: 고급 — 조건부 집계 피벗(MAX(CASE WHEN ...)) 23열을 코드 목록으로 만들기 + LEFT JOIN + GROUP BY + HAVING
# 출력: 벡터 순서(23코드) + 전신 벡터 목록(23개 모두 5명·일부만 5명, 없는 값 None) + profile 20 피벗 행 표(1행)
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/02_전신벡터_피벗.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 벡터 순서 (3D 팀과 약속한 순서: 키·높이 → 길이 → 둘레 → 너비·두께). 이 순서가 바뀌면 모델 입력도 바뀜
BODY_VECTOR = (
    "height", "chest_height", "waist_height", "hip_height", "inseam",
    "arm_length", "back_length", "shoulder_width",
    "neck_girth", "chest_girth", "waist_girth", "hip_girth",
    "upperarm_girth", "wrist_girth", "thigh_girth", "calf_girth", "ankle_girth",
    "chest_breadth", "chest_depth", "waist_breadth", "waist_depth", "hip_breadth", "hip_depth",
)


# 목적: 피벗 SQL 만들기 — 코드마다 "MAX(CASE WHEN 코드 = %s THEN 값 END) AS 코드" 한 열
# 열 이름(AS 뒤)은 위 BODY_VECTOR 고정값만 씀 (SQL 에 글자를 직접 넣는 곳이라 고정값만), 비교 값은 %s
def pivot_sql():
    columns = []
    for code in BODY_VECTOR:
        columns.append("MAX(CASE WHEN m.measure_code = %s THEN m.value_cm END) AS " + code)
    sql = """
        SELECT p.profile_id, p.gender, p.body_type,
               COUNT(m.measure_code) AS filled,
               """ + ",\n               ".join(columns) + """
        FROM body.profiles AS p
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        GROUP BY p.profile_id, p.gender, p.body_type
        HAVING COUNT(m.measure_code) >= %s
        ORDER BY filled DESC, p.profile_id
    """
    return sql


# 목적: 치수가 min_filled 개 이상인 사람의 피벗 행
def body_vectors(min_filled):
    params = list(BODY_VECTOR)
    params.append(min_filled)
    return query(pivot_sql(), tuple(params))


# 목적: 피벗 행 하나 → 숫자 리스트 (BODY_VECTOR 순서, 없는 값 None)
def vector_of(row):
    values = []
    for code in BODY_VECTOR:
        value = row[code]
        if value is None:
            values.append(None)
        else:
            values.append(float(value))
    return values


# 목적: 요약 표(사람·채운 수) + 벡터 줄 출력
def print_vectors(title, rows):
    summary = []
    for row in rows:
        summary.append({"profile_id": row["profile_id"], "gender": row["gender"],
                        "body_type": row["body_type"], "filled": row["filled"],
                        "dim": len(BODY_VECTOR)})
    show(title, summary)
    for row in rows:
        print("  profile " + str(row["profile_id"]) + ": " + str(vector_of(row)))


if __name__ == "__main__":
    print("벡터 순서:", list(BODY_VECTOR))
    # 23개 전부 = 더미 회원 18~22
    print_vectors("전신 벡터 — 23개 모두 채운 사람", body_vectors(23))
    # 3~5개만 있는 ANSUR II·BodyM 행 — None 자리는 3D 쪽에서 기본 몸 값으로 채움
    print_vectors("전신 벡터 — 일부만 있는 사람 (3개 이상)", body_vectors(3)[5:])
    # 보기 쉽게 한 사람은 피벗 행 그대로 표로
    show("피벗 행 그대로 (profile_id = 20)", [body_vectors(23)[2]])
