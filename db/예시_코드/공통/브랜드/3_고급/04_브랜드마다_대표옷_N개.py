# 목적: 브랜드마다 대표 옷 N벌씩만 미리보기 — 첫 화면에 브랜드별 카드 N장 (사이즈가 많은 옷 먼저)
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 첫 화면 브랜드별 미리보기)
# 난이도: 고급 — 파생 테이블(사이즈 수) + 3개 표 JOIN + 창 함수 ROW_NUMBER() OVER (PARTITION BY 브랜드 ...) 로 그룹별 상위 N
# 출력: 표 1개 — 브랜드마다 사이즈 많은 순 대표 옷 4행(UNIQLO 3·COVERNAT 1, row_no·item_code·이름·size_tally)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/04_브랜드마다_대표옷_N개.py
# PARTITION BY = 브랜드마다 번호를 1부터 다시 매김. 바깥 질의에서 번호 ≤ N 만 남기면 "그룹별 상위 N"
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드마다 사이즈 수가 많은 순(같으면 garment_id 순)으로 앞 top_n 벌 + 그 브랜드 전체 옷 수
def top_garments_per_brand(top_n=3):
    sql = """
        SELECT ranked.brand_name, ranked.row_no, ranked.brand_garment_tally,
               ranked.item_code, ranked.garment_name, ranked.size_tally
        FROM (
            SELECT b.brand_id, b.brand_name, g.garment_id, g.item_code, g.garment_name,
                   COALESCE(sc.size_tally, 0) AS size_tally,
                   ROW_NUMBER() OVER (PARTITION BY b.brand_id
                                      ORDER BY COALESCE(sc.size_tally, 0) DESC, g.garment_id) AS row_no,
                   COUNT(*) OVER (PARTITION BY b.brand_id) AS brand_garment_tally
            FROM garment.brands AS b
            JOIN garment.garments AS g ON g.brand_id = b.brand_id
            LEFT JOIN (
                SELECT s.garment_id, COUNT(*) AS size_tally
                FROM garment.sizes AS s
                GROUP BY s.garment_id
            ) AS sc ON sc.garment_id = g.garment_id
        ) AS ranked
        WHERE ranked.row_no <= %s
        ORDER BY ranked.brand_id, ranked.row_no
    """
    return query(sql, (top_n,))


if __name__ == "__main__":
    show("브랜드마다 대표 옷 3벌 (사이즈 많은 순)", top_garments_per_brand(3))
