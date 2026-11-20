# 목적: 출처 × 성별마다 전체 인원 중 실측 치수가 있는(= 학습에 쓸 수 있는) 인원과 1명당 평균 치수 개수
# 누가 쓰나: AI (데이터셋 크기를 "쓸 수 있는 인원" 기준으로 보기)
# 난이도: 심화 — 2개 표 LEFT JOIN(치수 없는 사람도 셈) + GROUP BY + COUNT(DISTINCT), HAVING 으로 최소 인원 거르기
# 출력: 출처×성별 6행 표(사람 수·치수 있는 사람·치수 행·usable_pct·1인당 치수), HAVING 2명 이상 3행
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/01_출처성별_학습가능_인원.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 출처 × 성별 전체 인원·치수 있는 인원·치수 행 수. min_measured 명 이상인 묶음만 (HAVING)
def usable_by_source(min_measured=0):
    sql = """
        SELECT p.source_name, p.gender,
               COUNT(DISTINCT p.profile_id) AS profile_tally,
               COUNT(DISTINCT m.profile_id) AS measured_profile_tally,
               COUNT(m.measure_code) AS measure_row_tally
        FROM body.profiles AS p
        LEFT JOIN body.measures AS m
               ON m.profile_id = p.profile_id
              AND m.measure_method = 'measured'
        GROUP BY p.source_name, p.gender
        HAVING COUNT(DISTINCT m.profile_id) >= %s
        ORDER BY p.source_name, p.gender
    """
    return query(sql, (min_measured,))


# 목적: 행마다 학습가능 비율(%)·1명당 평균 치수 개수 붙이기
def add_ratios(rows):
    result = []
    for row in rows:
        pct = 0.0
        per_person = 0.0
        if row["profile_tally"] > 0:
            pct = round(row["measured_profile_tally"] * 100.0 / row["profile_tally"], 1)
        if row["measured_profile_tally"] > 0:
            per_person = round(row["measure_row_tally"] / row["measured_profile_tally"], 1)
        item = dict(row)
        item["usable_pct"] = pct
        item["measures_per_person"] = per_person
        result.append(item)
    return result


if __name__ == "__main__":
    show("출처 × 성별 학습가능 인원 (전체)", add_ratios(usable_by_source(0)))
    show("치수 있는 사람이 2명 이상인 묶음만 (HAVING)", add_ratios(usable_by_source(2)))
