# 목적: 옷 한 벌의 사이즈를 치수 하나로 나란히 비교 — 바로 앞 사이즈와 몇 cm 차이인지 (LAG), 권장 신체 범위도 같은 방법
# 누가 쓰나: 공통 (3D 사이즈 간격, AI 사이즈 특징, 프론트 "한 치수 크게" 안내)
# 난이도: 고급 — 4개 표 JOIN + 창 함수 LAG() OVER (ORDER BY ...) 로 앞 행 값 가져오기 (MySQL 8)
# 출력: 크루넥T LAG 비교 — 가슴단면 2행, 소매길이 2행(앞 사이즈 값·diff_cm), 권장 신체 범위 4행(low_diff_cm)
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/02_옷_사이즈_비교.py
# LAG(값) OVER (ORDER BY 순서) = 정렬했을 때 바로 앞 행의 값 (첫 행은 NULL)
# 예시 DB 는 지역마다 치수가 있는 사이즈가 M 하나뿐이라 지역을 나누지 않고 비교함 (KR M → US M).
#   자료가 차면 같은 지역 안에서만 비교: OVER (PARTITION BY s.region ORDER BY s.size_id)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 실측(basis = garment) 치수 하나를 사이즈 순서로 나란히 + 앞 사이즈와 차이
def size_steps(source_name="uniqlo_site", item_code="E422992-000", measure_code="chest_width"):
    sql = """
        SELECT s.region, s.size_label, d.korean_name, gm.value_cm,
               LAG(s.region)     OVER (ORDER BY s.region, s.size_id) AS prev_region,
               LAG(s.size_label) OVER (ORDER BY s.region, s.size_id) AS prev_size_label,
               LAG(gm.value_cm)  OVER (ORDER BY s.region, s.size_id) AS prev_value_cm,
               gm.value_cm - LAG(gm.value_cm) OVER (ORDER BY s.region, s.size_id) AS diff_cm
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE g.source_name = %s
          AND g.item_code = %s
          AND gm.measure_code = %s
          AND gm.basis = 'garment'
        ORDER BY s.region, s.size_id
    """
    return query(sql, (source_name, item_code, measure_code))


# 목적: 권장 신체 범위(basis = body) — 치수마다 사이즈 순서로 low~high, 범위 폭, 앞 사이즈보다 low 가 몇 cm 커졌는지
def body_ranges(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT gm.measure_code, d.korean_name, s.region, s.size_label,
               gm.low_cm, gm.high_cm,
               gm.high_cm - gm.low_cm AS range_cm,
               LAG(s.region)     OVER (PARTITION BY gm.measure_code ORDER BY s.region, s.size_id) AS prev_region,
               LAG(s.size_label) OVER (PARTITION BY gm.measure_code ORDER BY s.region, s.size_id) AS prev_size_label,
               gm.low_cm - LAG(gm.low_cm) OVER (PARTITION BY gm.measure_code ORDER BY s.region, s.size_id) AS low_diff_cm
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE g.source_name = %s
          AND g.item_code = %s
          AND gm.basis = 'body'
        ORDER BY gm.measure_code, s.region, s.size_id
    """
    return query(sql, (source_name, item_code))


if __name__ == "__main__":
    show("가슴단면 사이즈 비교 (uniqlo_site / E422992-000 / chest_width)", size_steps("uniqlo_site", "E422992-000", "chest_width"))
    show("소매길이 사이즈 비교 (uniqlo_site / E422992-000 / sleeve_length)", size_steps("uniqlo_site", "E422992-000", "sleeve_length"))
    show("권장 신체 범위 (uniqlo_site / E422992-000, basis = body)", body_ranges("uniqlo_site", "E422992-000"))
