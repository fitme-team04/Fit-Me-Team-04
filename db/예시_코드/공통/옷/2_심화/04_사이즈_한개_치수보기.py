# 목적: 사이즈 하나(옷 번호 + 표기 + 지역)의 치수를 한글 이름과 함께 보기 (예: 크루넥T KR M 의 총장·가슴단면 ...)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 3개 JOIN(sizes + measures + measure_definitions) + 조건 3개
# 출력: 사이즈 1개 치수 표 3개 — 크루넥T KR M 6행, US M 6행, COVERNAT KR M 4행 (basis·항목·value·low·high)
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/04_사이즈_한개_치수보기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (garment_id, size_label, region) 사이즈 하나의 치수 전부 (옷 실측 먼저, 권장 신체 범위 다음)
def measures_of_size(garment_id=6, size_label="M", region="KR"):
    sql = """
        SELECT gm.basis, gm.measure_code, d.korean_name, d.body_part,
               gm.value_cm, gm.low_cm, gm.high_cm
        FROM garment.sizes AS s
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE s.garment_id = %s
          AND s.size_label = %s
          AND s.region = %s
        ORDER BY gm.basis DESC, gm.measure_code
    """
    return query(sql, (garment_id, size_label, region))


if __name__ == "__main__":
    show("크루넥T(garment_id 6) KR M 치수", measures_of_size(6, "M", "KR"))
    show("크루넥T(garment_id 6) US M 치수", measures_of_size(6, "M", "US"))
    show("COVERNAT(garment_id 14) KR M 치수", measures_of_size(14, "M", "KR"))
