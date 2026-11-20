# 목적: 한 사람이 부위마다 정의된 신체 치수 중 몇 개를 가지고 있는지 (3D 부위별로 실측값을 쓸지 기본값을 쓸지 판단)
# 누가 쓰나: 3D
# 난이도: 심화 — 2개 표 LEFT JOIN(조건을 ON 에 둠: 없는 항목도 세기) + GROUP BY + COUNT·GROUP_CONCAT
# 출력: profile 18·6 부위별 보유 치수 표 각 5행(body_part·defined_tally·have_tally·fill_ratio·have_codes)
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/02_한사람_부위별_보유치수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 부위마다 정의 수(defined) · 보유 수(have) · 채움 비율 · 보유 코드
# profile_id 조건을 WHERE 가 아니라 ON 에 둬야 치수가 없는 항목도 행으로 남아 정의 수가 맞음
def part_coverage(profile_id):
    sql = """
        SELECT d.body_part,
               COUNT(*) AS defined_tally,
               COUNT(m.measure_code) AS have_tally,
               ROUND(COUNT(m.measure_code) / COUNT(*), 2) AS fill_ratio,
               GROUP_CONCAT(m.measure_code ORDER BY m.measure_code SEPARATOR ', ') AS have_codes
        FROM ref.measure_definitions AS d
        LEFT JOIN body.measures AS m
               ON m.measure_code = d.measure_code AND m.profile_id = %s
        WHERE d.basis = 'body'
        GROUP BY d.body_part
        ORDER BY FIELD(d.body_part, 'full', 'torso', 'arm', 'leg', 'neck')
    """
    return query(sql, (profile_id,))


if __name__ == "__main__":
    # profile 18: 23항목 → 정의된 신체 25항목 중 knee_girth·stomach_girth 만 없음
    show("부위별 보유 치수 (profile_id = 18)", part_coverage(18))
    # profile 6: ANSUR II 여성 — 팔·다리·목 0개 → 3D 는 기본 몸 값으로 채워야 함
    show("부위별 보유 치수 (profile_id = 6)", part_coverage(6))
