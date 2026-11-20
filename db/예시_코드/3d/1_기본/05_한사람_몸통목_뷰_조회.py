# 목적: 한 사람의 몸통·목 치수를 부위별 뷰(body.torso_measures·body.neck_measures)에서 조회, 몸통은 치수 종류로 거르기 (3D 몸통 메시)
# 누가 쓰나: 3D
# 난이도: 기본 — 뷰 1개 SELECT + 선택 조건(%s IS NULL OR ...)·ORDER BY
# 출력: profile 19 몸통 전부(14행)·높이만(3행)·목(1행), profile 6 몸통(4행) 표(measure_code·korean_name·value_cm 등)
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/05_한사람_몸통목_뷰_조회.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 한 사람의 몸통 치수. measure_type 을 주면 그 종류만 (None 이면 전부)
def torso_rows(profile_id, measure_type=None):
    sql = """
        SELECT t.measure_code, t.korean_name, t.measure_type, t.value_cm
        FROM body.torso_measures AS t
        WHERE t.profile_id = %s
          AND (%s IS NULL OR t.measure_type = %s)
        ORDER BY t.measure_type, t.measure_code
    """
    return query(sql, (profile_id, measure_type, measure_type))


# 목적: 한 사람의 목 치수 (목둘레 — 3D 목 단면·옷 깃 위치)
def neck_rows(profile_id):
    sql = """
        SELECT n.measure_code, n.korean_name, n.measure_type, n.value_cm
        FROM body.neck_measures AS n
        WHERE n.profile_id = %s
    """
    return query(sql, (profile_id,))


if __name__ == "__main__":
    show("몸통 치수 전부 (body.torso_measures, profile_id = 19)", torso_rows(19))
    # 높이(height) 항목 = 가슴·허리·엉덩이 단면을 세로 어디에 둘지
    show("몸통 높이 항목만 (measure_type = height, profile_id = 19)", torso_rows(19, "height"))
    # profile 6: ANSUR II 여성 — 몸통 일부만 있음
    show("몸통 치수 (profile_id = 6, ANSUR II)", torso_rows(6))
    show("목 치수 (body.neck_measures, profile_id = 19)", neck_rows(19))
