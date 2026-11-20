# 목적: 고른 필수 치수(예: 키·가슴·허리·엉덩이·어깨)를 하나도 빠짐없이 가진 사람, 사람마다 신체 치수 채움률과 빠진 항목
# 누가 쓰나: 공통 (AI 학습에 쓸 수 있는 사람 고르기, 3D 모델 만들 수 있는 사람 고르기, 프론트 입력 안내)
# 난이도: 고급 — 이중 NOT EXISTS(관계 나눗셈: "빠진 필수 항목이 없는 사람") + EXISTS + CROSS JOIN·LEFT JOIN 3개 표 + GROUP_CONCAT
# 출력: 필수 치수 목록 + 표 3개 — 필수 5개 완비(7행), 가슴·허리·엉덩이 완비(10행), 채움률%·빠진 항목(10행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/3_고급/09_필수치수_완비_사람.py
# 치수가 하나도 없는 사람·코드 하나 빠진 사람은 2_심화/08_치수_없는_사람.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show

REQUIRED = ["height", "chest_girth", "waist_girth", "hip_girth", "shoulder_width"]


# 목적: 값 개수만큼 "%s, %s, ..." 자리 만들기 (값 자체는 %s 로 넘김)
def placeholders(values):
    marks = []
    for value in values:
        marks.append("%s")
    return ", ".join(marks)


# 목적: 필수 치수를 모두 가진 사람 — "필수 항목 중 이 사람에게 없는 것이 존재하지 않는다" (NOT EXISTS 두 번)
def complete_people(required):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE NOT EXISTS (
            SELECT 1
            FROM ref.measure_definitions AS d
            WHERE d.measure_code IN (""" + placeholders(required) + """)
              AND NOT EXISTS (
                  SELECT 1
                  FROM body.measures AS m
                  WHERE m.profile_id = p.profile_id
                    AND m.measure_code = d.measure_code
              )
        )
        ORDER BY p.profile_id
    """
    return query(sql, tuple(required))


# 목적: 치수가 1개 이상 있는 사람마다 신체(basis = body) 항목 채움률 % + 빠진 항목 코드 (사람 × 항목 CROSS JOIN 뒤 LEFT JOIN)
def coverage_by_person():
    sql = """
        SELECT p.profile_id, p.source_name, p.gender,
               COUNT(m.measure_code) AS have_tally,
               COUNT(*) AS defined_tally,
               ROUND(100 * COUNT(m.measure_code) / COUNT(*), 1) AS fill_pct,
               GROUP_CONCAT(CASE WHEN m.measure_code IS NULL THEN d.measure_code END
                            ORDER BY d.measure_code SEPARATOR ', ') AS missing_codes
        FROM body.profiles AS p
        CROSS JOIN ref.measure_definitions AS d
        LEFT JOIN body.measures AS m
               ON m.profile_id = p.profile_id AND m.measure_code = d.measure_code
        WHERE d.basis = 'body'
          AND EXISTS (SELECT 1 FROM body.measures AS x WHERE x.profile_id = p.profile_id)
        GROUP BY p.profile_id, p.source_name, p.gender
        ORDER BY fill_pct DESC, p.profile_id
    """
    rows = query(sql)
    for row in rows:
        text = row["missing_codes"]
        if text is not None and len(text) > 60:          # 표가 너무 넓어지지 않게 줄임
            row["missing_codes"] = text[:60] + " …"
    return rows


if __name__ == "__main__":
    print("필수 치수:", REQUIRED)
    show("필수 치수 5개를 모두 가진 사람 (이중 NOT EXISTS)", complete_people(REQUIRED))
    show("가슴·허리·엉덩이 3개를 모두 가진 사람", complete_people(["chest_girth", "waist_girth", "hip_girth"]))
    show("사람별 신체 치수 채움률과 빠진 항목", coverage_by_person())
