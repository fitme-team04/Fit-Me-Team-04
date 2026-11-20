# 목적: "치수 수정" 화면을 열 때 — 신체 치수 항목 전부를 칸으로 깔고, 이미 저장된 값은 채우고 빈 칸은 "미입력" 으로 표시 + 채운 비율
# 누가 쓰나: 프론트
# 난이도: 심화 — LEFT JOIN 조건을 ON 에 두기 (WHERE 에 두면 빈 칸이 사라짐) + GROUP BY 로 채운 개수
# 출력: profile 20 치수 수정 폼 25행(state 저장됨/미입력), 빈 칸만 2행, 부위별 채운 비율 5행(percent)
# 실행: .venv/bin/python db/예시_코드/front/2_심화/08_내_치수_입력현황.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 신체 치수 항목마다 이 profile 의 저장값 (없으면 NULL) — 폼 미리 채우기
def prefill_rows(profile_id):
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part, m.value_cm, m.measure_method
        FROM ref.measure_definitions AS d
        LEFT JOIN body.measures AS m
               ON m.measure_code = d.measure_code
              AND m.profile_id = %s
        WHERE d.basis = 'body'
        ORDER BY FIELD(d.body_part, 'full', 'neck', 'torso', 'arm', 'leg'), d.measure_code
    """
    rows = query(sql, (profile_id,))
    for row in rows:
        if row["value_cm"] is None:
            row["state"] = "미입력"
        else:
            row["state"] = "저장됨"
    return rows


# 목적: 부위별 채운 칸 수 / 전체 칸 수 (진행 막대용)
def fill_summary(profile_id):
    sql = """
        SELECT d.body_part,
               COUNT(m.measure_code) AS filled,
               COUNT(*) AS total
        FROM ref.measure_definitions AS d
        LEFT JOIN body.measures AS m
               ON m.measure_code = d.measure_code
              AND m.profile_id = %s
        WHERE d.basis = 'body'
        GROUP BY d.body_part
        ORDER BY FIELD(d.body_part, 'full', 'neck', 'torso', 'arm', 'leg')
    """
    rows = query(sql, (profile_id,))
    for row in rows:
        row["percent"] = round(100.0 * row["filled"] / row["total"], 1)
    return rows


if __name__ == "__main__":
    # profile_id 20 = user03@example.com 의 신체 정보 (db/sample/sample_data.sql)
    rows = prefill_rows(20)
    empty = []
    for row in rows:
        if row["state"] == "미입력":
            empty.append(row)
    show("치수 수정 폼 미리 채우기 (profile_id = 20)", rows)
    show("빈 칸만 (profile_id = 20)", empty)
    show("부위별 채운 비율 (profile_id = 20)", fill_summary(20))
