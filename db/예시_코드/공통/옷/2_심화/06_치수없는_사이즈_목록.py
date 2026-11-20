# 목적: 치수가 하나도 등록되지 않은 사이즈 찾기 — 수집을 더 해야 할 사이즈 목록 (추천·3D 에 못 쓰는 사이즈)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 3개 JOIN·LEFT JOIN(garments + sizes + measures) + "LEFT JOIN 후 IS NULL" 로 짝 없는 행 고르기
# 출력: 치수 없는 사이즈 — 크루넥T 9행, COVERNAT 5행(size_id·표기·지역), 옷마다 치수 없는 사이즈 수 3행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/06_치수없는_사이즈_목록.py
# LEFT JOIN 은 짝이 없으면 오른쪽 열을 NULL 로 채움 → gm.size_id IS NULL = 치수가 없는 사이즈
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 하나(출처 + 상품번호)에서 치수가 없는 사이즈
def sizes_without_measures(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT s.size_id, s.size_label, s.region
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE g.source_name = %s
          AND g.item_code = %s
          AND gm.size_id IS NULL
        ORDER BY s.region, s.size_id
    """
    return query(sql, (source_name, item_code))


# 목적: 옷마다 치수 없는 사이즈 수 / 전체 사이즈 수
def missing_tally_by_garment():
    sql = """
        SELECT g.garment_id, g.item_code,
               COUNT(DISTINCT s.size_id) AS size_tally,
               COUNT(DISTINCT s.size_id) - COUNT(DISTINCT gm.size_id) AS no_measure_sizes
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        GROUP BY g.garment_id, g.item_code
        ORDER BY no_measure_sizes DESC, g.garment_id
    """
    return query(sql)


if __name__ == "__main__":
    show("크루넥T(E422992-000) 치수 없는 사이즈", sizes_without_measures("uniqlo_site", "E422992-000"))
    show("COVERNAT(1848166) 치수 없는 사이즈", sizes_without_measures("musinsa_ml_project", "1848166"))
    show("옷마다 치수 없는 사이즈 수", missing_tally_by_garment())
