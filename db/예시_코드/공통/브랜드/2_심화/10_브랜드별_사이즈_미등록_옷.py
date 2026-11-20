# 목적: 브랜드마다 사이즈가 하나도 등록되지 않은 옷이 몇 벌인지 + 그 옷 목록 — 사이즈표 수집이 덜 된 브랜드 찾기
# 누가 쓰나: 공통 (3D / AI / 프론트. 자료 수집 진행 점검)
# 난이도: 심화 — 3개 표 JOIN·LEFT JOIN(브랜드 + 옷 + 사이즈) + GROUP BY + COUNT(DISTINCT) 차이 + HAVING
# 출력: 표 2개 — 브랜드별 사이즈 미등록 옷 수 1행(UNIQLO 12벌 중 11벌), UNIQLO 미등록 옷 11행(garment_id·item_code·이름)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/10_브랜드별_사이즈_미등록_옷.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드별 (옷 수, 사이즈 있는 옷 수, 사이즈 없는 옷 수). 사이즈 없는 옷이 1벌 이상인 브랜드만
# COUNT(DISTINCT s.garment_id) 는 LEFT JOIN 으로 NULL 이 된 옷(사이즈 없음)을 세지 않음
def unsized_tally_by_brand():
    sql = """
        SELECT b.brand_name,
               COUNT(DISTINCT g.garment_id)                                AS garment_tally,
               COUNT(DISTINCT s.garment_id)                                AS sized_garment_tally,
               COUNT(DISTINCT g.garment_id) - COUNT(DISTINCT s.garment_id) AS unsized_garment_tally
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        LEFT JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        GROUP BY b.brand_id, b.brand_name
        HAVING COUNT(DISTINCT g.garment_id) - COUNT(DISTINCT s.garment_id) > 0
        ORDER BY unsized_garment_tally DESC
    """
    return query(sql)


# 목적: 브랜드 하나의 사이즈 미등록 옷 목록
def unsized_garments(brand_name="UNIQLO"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        LEFT JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        WHERE b.brand_name = %s
          AND s.size_id IS NULL
        ORDER BY g.garment_id
    """
    return query(sql, (brand_name,))


if __name__ == "__main__":
    show("브랜드별 사이즈 미등록 옷 수", unsized_tally_by_brand())
    show("UNIQLO 사이즈 미등록 옷", unsized_garments("UNIQLO"))
