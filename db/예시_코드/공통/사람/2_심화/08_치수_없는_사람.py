# 목적: 신체 치수가 하나도 없는 사람, 특정 치수(예: 목둘레)만 빠진 사람 찾기 (치수 입력·추정이 필요한 사람)
# 누가 쓰나: 공통 (AI 추정 대상 고르기, 프론트 "치수를 더 입력해 주세요" 안내)
# 난이도: 심화 — 2개 표 LEFT JOIN + IS NULL(짝 없는 행 찾기) / NOT IN 서브쿼리
# 출력: 표 2개 — 치수가 하나도 없는 사람(출처·성별·키·체중, 12행), 치수는 있으나 목둘레 없는 사람(치수 수, 5행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/08_치수_없는_사람.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 치수 행이 하나도 없는 사람 (LEFT JOIN 뒤 오른쪽이 NULL = 짝이 없음)
def people_without_measures():
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        LEFT JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.profile_id IS NULL
        ORDER BY p.profile_id
    """
    return query(sql)


# 목적: 치수는 있는데 measure_code 하나가 빠진 사람 (NOT IN 서브쿼리: 그 치수를 가진 사람 목록에 없음)
def people_missing_code(measure_code="neck_girth"):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender,
               (SELECT COUNT(*) FROM body.measures AS c WHERE c.profile_id = p.profile_id) AS measure_tally
        FROM body.profiles AS p
        WHERE p.profile_id IN (SELECT m.profile_id FROM body.measures AS m)
          AND p.profile_id NOT IN (SELECT m.profile_id FROM body.measures AS m WHERE m.measure_code = %s)
        ORDER BY p.profile_id
    """
    return query(sql, (measure_code,))


if __name__ == "__main__":
    show("치수가 하나도 없는 사람 (LEFT JOIN ... IS NULL)", people_without_measures())
    show("치수는 있지만 목둘레(neck_girth)가 없는 사람 (NOT IN)", people_missing_code("neck_girth"))
