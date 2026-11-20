# 목적: 치수 하나가 범위 안인 사람 찾기 (예: 가슴둘레 90~110cm 인 몸으로 3D 옷 입혀 보기)
# 누가 쓰나: 3D
# 난이도: 기본 — 뷰 1개(body.measure_details) SELECT + WHERE BETWEEN·ORDER BY
# 출력: 범위별 사람 표 3개 — 가슴둘레 90~110(5행)·다리안쪽길이 75~85(2행)·엉덩이둘레 95~125cm(8행); profile_id·value_cm
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/09_치수범위로_사람찾기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: measure_code 의 값이 low_cm ~ high_cm 인 사람 (작은 값부터)
def profiles_in_range(measure_code, low_cm, high_cm):
    sql = """
        SELECT md.profile_id, md.measure_code, md.korean_name, md.value_cm
        FROM body.measure_details AS md
        WHERE md.measure_code = %s
          AND md.value_cm BETWEEN %s AND %s
        ORDER BY md.value_cm
    """
    return query(sql, (measure_code, low_cm, high_cm))


if __name__ == "__main__":
    show("가슴둘레 90~110cm", profiles_in_range("chest_girth", 90, 110))
    show("다리안쪽길이 75~85cm", profiles_in_range("inseam", 75, 85))
    show("엉덩이둘레 95~125cm", profiles_in_range("hip_girth", 95, 125))
