# 목적: 치수를 하나라도 잰 사람들 중, 신체 치수 항목마다 값이 빠진(결측) 사람 수와 빠진 사람 목록
# 누가 쓰나: AI (결측 처리 방법 정하기: 열 빼기 / 사람 빼기 / 채우기)
# 난이도: 심화 — 파생 테이블(측정한 사람) CROSS JOIN 항목 정의 + LEFT JOIN 치수 + GROUP BY·HAVING, NOT EXISTS 서브쿼리
# 출력: 신체 치수 23항목 결측 표(filled·missing·missing_pct, 결측 0은 가슴·허리·엉덩이둘레), 어깨너비 빠진 3명
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/08_치수별_결측_사람수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 항목마다 채운 사람 수·빠진 사람 수 (한 명도 안 잰 항목은 HAVING 으로 뺌)
def missing_per_measure():
    sql = """
        SELECT d.measure_code, d.korean_name,
               COUNT(m.profile_id) AS filled_tally,
               COUNT(*) - COUNT(m.profile_id) AS missing_tally,
               ROUND((COUNT(*) - COUNT(m.profile_id)) * 100.0 / COUNT(*), 1) AS missing_pct
        FROM (
            SELECT DISTINCT mm.profile_id
            FROM body.measures AS mm
            WHERE mm.measure_method = 'measured'
        ) AS mp
        CROSS JOIN ref.measure_definitions AS d
        LEFT JOIN body.measures AS m
               ON m.profile_id = mp.profile_id
              AND m.measure_code = d.measure_code
              AND m.measure_method = 'measured'
        WHERE d.basis = 'body'
        GROUP BY d.measure_code, d.korean_name
        HAVING COUNT(m.profile_id) > 0
        ORDER BY missing_tally, d.measure_code
    """
    return query(sql)


# 목적: 치수 하나가 빠진 사람 목록 (다른 치수는 잰 사람 중에서)
def profiles_missing(measure_code):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender
        FROM body.profiles AS p
        WHERE p.profile_id IN (SELECT m.profile_id FROM body.measures AS m WHERE m.measure_method = 'measured')
          AND NOT EXISTS (
              SELECT 1 FROM body.measures AS m2
              WHERE m2.profile_id = p.profile_id
                AND m2.measure_code = %s
                AND m2.measure_method = 'measured'
          )
        ORDER BY p.profile_id
    """
    return query(sql, (measure_code,))


if __name__ == "__main__":
    rows = missing_per_measure()
    show("신체 치수 항목별 결측 (치수를 잰 사람 기준)", rows)
    full = []
    for row in rows:
        if row["missing_tally"] == 0:
            full.append(row["measure_code"])
    print("  → 결측 없는 항목:", ", ".join(full))
    show("shoulder_width 가 빠진 사람", profiles_missing("shoulder_width"))
