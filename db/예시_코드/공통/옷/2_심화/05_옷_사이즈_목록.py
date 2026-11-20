# 목적: 옷 한 벌의 사이즈 목록 + 사이즈마다 등록된 치수 개수 (프론트 세 번째 선택 상자, 어떤 사이즈에 자료가 있는지)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 3개 표 JOIN·LEFT JOIN(옷 + 사이즈 + 치수) + GROUP BY COUNT
# 출력: 크루넥T 사이즈 11행·COVERNAT 사이즈 6행(표기·지역·치수 수 measure_tally), 옷마다 사이즈 수 14행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/05_옷_사이즈_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷(출처 + 상품번호)의 사이즈마다 치수 개수. 치수가 없는 사이즈도 0 으로 나오도록 LEFT JOIN
def garment_sizes(source_name="uniqlo_site", item_code="E422992-000"):
    sql = """
        SELECT s.size_id, s.size_label, s.region,
               COUNT(gm.measure_code) AS measure_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE g.source_name = %s
          AND g.item_code = %s
        GROUP BY s.size_id, s.size_label, s.region
        ORDER BY s.region, s.size_id
    """
    return query(sql, (source_name, item_code))


# 목적: 옷마다 사이즈 수 (사이즈가 하나도 없는 옷도 0 으로)
def size_tally_by_garment():
    sql = """
        SELECT g.garment_id, g.source_name, g.item_code, g.garment_name,
               COUNT(s.size_id) AS size_tally
        FROM garment.garments AS g
        LEFT JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        GROUP BY g.garment_id, g.source_name, g.item_code, g.garment_name
        ORDER BY size_tally DESC, g.garment_id
    """
    return query(sql)


if __name__ == "__main__":
    show("UNIQLO 크루넥T 사이즈 (uniqlo_site / E422992-000)", garment_sizes("uniqlo_site", "E422992-000"))
    show("COVERNAT 티셔츠 사이즈 (musinsa_ml_project / 1848166)", garment_sizes("musinsa_ml_project", "1848166"))
    show("옷마다 사이즈 수", size_tally_by_garment())
