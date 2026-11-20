# 목적: 출처 × 치수 항목마다 잰 인원·평균·범위 → 출처마다 어떤 치수 열을 학습에 쓸 수 있는지 (query/train/02 + 한글 이름·부위)
# 누가 쓰나: AI (출처별 학습 열 고르기)
# 난이도: 심화 — 3개 표 JOIN + GROUP BY 집계(COUNT·AVG·MIN·MAX) + HAVING 최소 인원
# 출력: 출처×치수 채움 31행(profile_tally·avg/min/max_cm), 출처별 쓸 수 있는 열 수(ansur2 5·bodym 3·user 23)
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/03_출처별_치수_채움현황.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 출처 × 치수 항목 집계 (실측만). min_tally 명 이상 잰 항목만 (HAVING). source_name 을 주면 그 출처만
def coverage(min_tally=1, source_name=None):
    sql = """
        SELECT p.source_name, m.measure_code, d.korean_name, d.body_part,
               COUNT(*) AS profile_tally,
               ROUND(AVG(m.value_cm), 1) AS avg_cm,
               MIN(m.value_cm) AS min_cm,
               MAX(m.value_cm) AS max_cm
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE m.measure_method = 'measured'
          AND (%s IS NULL OR p.source_name = %s)
        GROUP BY p.source_name, m.measure_code, d.korean_name, d.body_part
        HAVING COUNT(*) >= %s
        ORDER BY p.source_name, profile_tally DESC, m.measure_code
    """
    return query(sql, (source_name, source_name, min_tally))


# 목적: 출처마다 쓸 수 있는 치수 열 개수 요약 (파이썬으로 묶기)
def columns_per_source(rows):
    tally = {}
    for row in rows:
        name = row["source_name"]
        if name not in tally:
            tally[name] = 0
        tally[name] += 1
    result = []
    for name in sorted(tally):
        result.append({"source_name": name, "usable_column_tally": tally[name]})
    return result


if __name__ == "__main__":
    rows = coverage(2)
    show("출처 × 치수 채움 현황 (2명 이상 잰 항목)", rows)
    show("출처별 쓸 수 있는 치수 열 수", columns_per_source(rows))
    show("bodym 만 (1명 이상)", coverage(1, "bodym"))
