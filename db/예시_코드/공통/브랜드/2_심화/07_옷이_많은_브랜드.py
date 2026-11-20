# 목적: 옷이 min_tally 벌 이상 등록된 브랜드만 — 자료가 충분한 브랜드만 AI 학습·추천 대상에 넣을 때
# 누가 쓰나: 공통 (3D / AI / 프론트. AI 학습 대상 브랜드 고르기)
# 난이도: 심화 — 2개 표 JOIN + GROUP BY + HAVING COUNT(*) >= %s (묶은 뒤 거르기, WHERE 는 묶기 전)
# 출력: 표 2개 — 옷 2벌 이상 브랜드 1행(UNIQLO 12), 1벌 이상 2행(UNIQLO·COVERNAT, 열 이름·나라·garment_tally)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/07_옷이_많은_브랜드.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 옷 수가 min_tally 이상인 브랜드와 그 옷 수
def brands_with_many_garments(min_tally=2):
    sql = """
        SELECT b.brand_name, b.country, COUNT(*) AS garment_tally
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        GROUP BY b.brand_id, b.brand_name, b.country
        HAVING COUNT(*) >= %s
        ORDER BY garment_tally DESC
    """
    return query(sql, (min_tally,))


if __name__ == "__main__":
    show("옷이 2벌 이상인 브랜드", brands_with_many_garments(2))
    show("옷이 1벌 이상인 브랜드", brands_with_many_garments(1))
