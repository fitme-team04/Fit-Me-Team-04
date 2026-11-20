# 목적: 한 사람의 팔·다리 치수를 부위별 뷰(body.arm_measures·body.leg_measures)에서 조회 (3D 팔다리 메시 맞추기)
# 누가 쓰나: 3D
# 난이도: 기본 — 뷰 1개 SELECT + WHERE·ORDER BY (뷰 정의는 db/sql/40_view_body_part.sql)
# 출력: profile 18·21 각각 팔(3행)·다리(4행) 치수 표(measure_code·korean_name·measure_type·value_cm·measure_method)
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/04_한사람_팔다리_뷰_조회.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 한 사람의 팔 치수 (팔길이·위팔둘레·손목둘레)
def arm_rows(profile_id):
    sql = """
        SELECT a.measure_code, a.korean_name, a.measure_type, a.value_cm, a.measure_method
        FROM body.arm_measures AS a
        WHERE a.profile_id = %s
        ORDER BY a.measure_type, a.measure_code
    """
    return query(sql, (profile_id,))


# 목적: 한 사람의 다리 치수 (다리안쪽길이·허벅지·종아리·발목 둘레)
def leg_rows(profile_id):
    sql = """
        SELECT l.measure_code, l.korean_name, l.measure_type, l.value_cm, l.measure_method
        FROM body.leg_measures AS l
        WHERE l.profile_id = %s
        ORDER BY l.measure_type, l.measure_code
    """
    return query(sql, (profile_id,))


if __name__ == "__main__":
    # profile 18: 더미 회원 1 (남성), 23항목 전부 있음
    show("팔 치수 (body.arm_measures, profile_id = 18)", arm_rows(18))
    show("다리 치수 (body.leg_measures, profile_id = 18)", leg_rows(18))
    # profile 21: 더미 회원 4 (여성)
    show("팔 치수 (body.arm_measures, profile_id = 21)", arm_rows(21))
    show("다리 치수 (body.leg_measures, profile_id = 21)", leg_rows(21))
