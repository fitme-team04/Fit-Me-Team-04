# 목적: 브랜드마다 자료가 어느 단계까지 있는지 — 옷 있음? 사이즈 있음? 치수 실측 있음? (추천에 쓸 수 있는 브랜드 가리기)
# 누가 쓰나: 공통 (3D / AI / 프론트. 추천 가능 브랜드만 화면에 띄우기)
# 난이도: 고급 — 상관 하위 질의 EXISTS / NOT EXISTS (바깥 브랜드 행마다 안쪽 3개 표 JOIN 을 검사) + CASE
# 출력: 표 2개 — 브랜드별 자료 단계 4행(has_garment·has_size·has_garment_measure Y/N), 추천에 못 쓰는 브랜드 2행
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/02_브랜드_자료단계_점검.py
# EXISTS (SELECT 1 ...) = 안쪽 질의가 한 행이라도 나오면 참. 개수를 다 세지 않고 하나 찾으면 멈춤
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드별 단계 표시 (Y/N 3개 + 지금 단계 이름)
def brand_data_stage():
    sql = """
        SELECT b.brand_name,
               CASE WHEN EXISTS (SELECT 1 FROM garment.garments AS g
                                 WHERE g.brand_id = b.brand_id) THEN 'Y' ELSE 'N' END AS has_garment,
               CASE WHEN EXISTS (SELECT 1 FROM garment.garments AS g
                                 JOIN garment.sizes AS s ON s.garment_id = g.garment_id
                                 WHERE g.brand_id = b.brand_id) THEN 'Y' ELSE 'N' END AS has_size,
               CASE WHEN EXISTS (SELECT 1 FROM garment.garments AS g
                                 JOIN garment.sizes AS s ON s.garment_id = g.garment_id
                                 JOIN garment.measures AS gm ON gm.size_id = s.size_id
                                 WHERE g.brand_id = b.brand_id
                                   AND gm.basis = 'garment') THEN 'Y' ELSE 'N' END AS has_garment_measure
        FROM garment.brands AS b
        ORDER BY b.brand_id
    """
    return query(sql)


# 목적: 추천에 못 쓰는 브랜드 = 옷 실측 치수가 하나도 없는 브랜드 (NOT EXISTS)
def brands_not_recommendable():
    sql = """
        SELECT b.brand_id, b.brand_name
        FROM garment.brands AS b
        WHERE NOT EXISTS (
            SELECT 1
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
            WHERE g.brand_id = b.brand_id
              AND gm.basis = 'garment'
        )
        ORDER BY b.brand_id
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드별 자료 단계 (옷 → 사이즈 → 옷 실측)", brand_data_stage())
    show("추천에 못 쓰는 브랜드 (옷 실측 없음, NOT EXISTS)", brands_not_recommendable())
