# 목적: 한 사람의 신체 치수 전부를 body.measure_details 뷰 하나로 (부위 순서 = 3D 모델 만드는 순서: 전신 → 몸통 → 팔 → 다리 → 목)
# 누가 쓰나: 3D
# 난이도: 기본 — 뷰 1개 SELECT + WHERE·ORDER BY FIELD (뷰가 항목 정의 JOIN 을 대신해 줌)
# 출력: profile 22(23행)·1(5행) 치수 전부 표(body_part·measure_code·korean_name·measure_type·value_cm·measure_method)
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/08_한사람_치수전체_뷰_조회.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 한 사람의 치수 전부 (부위 순서는 FIELD 로 고정)
def all_details(profile_id):
    sql = """
        SELECT md.body_part, md.measure_code, md.korean_name, md.measure_type, md.value_cm, md.measure_method
        FROM body.measure_details AS md
        WHERE md.profile_id = %s
        ORDER BY FIELD(md.body_part, 'full', 'torso', 'arm', 'leg', 'neck'), md.measure_type, md.measure_code
    """
    return query(sql, (profile_id,))


if __name__ == "__main__":
    # profile 22: 더미 회원 5 (남성, 23항목)
    show("치수 전부 (body.measure_details, profile_id = 22)", all_details(22))
    # profile 1: ANSUR II 남성 — 5항목뿐
    show("치수 전부 (body.measure_details, profile_id = 1)", all_details(1))
