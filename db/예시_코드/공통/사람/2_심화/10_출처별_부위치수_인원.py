# 목적: 출처(ansur2·bodym·user)마다 부위(torso·arm·leg …)별 치수를 가진 사람이 몇 명이고 평균 몇 개씩인지
# 누가 쓰나: 공통 (AI 출처별 학습 가능 범위, 3D 어느 출처로 팔·다리를 맞출 수 있는지)
# 난이도: 심화 — 3개 표 JOIN(신체 정보 + 치수 + 항목 정의) + 두 열 GROUP BY + COUNT(DISTINCT)·COUNT
# 출력: 표 2개 — 출처×부위별 치수 보유 인원·치수 수·1인당 수(8행), 다리 치수 있는 사람 수 출처×성별(2행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/10_출처별_부위치수_인원.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 출처 × 부위마다 그 부위 치수가 있는 사람 수, 치수 행 수, 1명당 평균 개수
def part_people_by_source():
    sql = """
        SELECT p.source_name, d.body_part,
               COUNT(DISTINCT p.profile_id) AS people_tally,
               COUNT(*) AS measure_tally,
               ROUND(COUNT(*) / COUNT(DISTINCT p.profile_id), 1) AS per_person
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        GROUP BY p.source_name, d.body_part
        ORDER BY p.source_name, d.body_part
    """
    return query(sql)


# 목적: 부위 하나(body_part)의 치수가 있는 사람 수를 출처마다 (WHERE 로 부위 먼저 거름)
def people_with_part(body_part="leg"):
    sql = """
        SELECT p.source_name, p.gender, COUNT(DISTINCT p.profile_id) AS people_tally
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE d.body_part = %s
        GROUP BY p.source_name, p.gender
        ORDER BY p.source_name, p.gender
    """
    return query(sql, (body_part,))


if __name__ == "__main__":
    show("출처 × 부위별 치수 보유 인원", part_people_by_source())
    show("다리(leg) 치수가 있는 사람 수 (출처 × 성별)", people_with_part("leg"))
