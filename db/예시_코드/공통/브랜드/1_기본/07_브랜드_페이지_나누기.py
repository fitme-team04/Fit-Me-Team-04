# 목적: 브랜드 목록을 페이지로 나눠 보기 — 브랜드가 많아졌을 때 한 화면에 page_size 개씩 (1쪽, 2쪽 ...)
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 목록 화면 페이지 넘김)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + ORDER BY + LIMIT %s OFFSET %s
# 출력: 표 2개 — 이름순 2개씩 1쪽 2행(COVERNAT·GU), 2쪽 2행(MUSINSA STANDARD·UNIQLO), 열 brand_id·이름·나라
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/07_브랜드_페이지_나누기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: page 쪽(1부터)의 브랜드. OFFSET = 앞 쪽들에서 건너뛸 개수 = (page - 1) × page_size
def brand_page(page=1, page_size=2):
    offset = (page - 1) * page_size
    sql = """
        SELECT b.brand_id, b.brand_name, b.country
        FROM garment.brands AS b
        ORDER BY b.brand_name
        LIMIT %s OFFSET %s
    """
    return query(sql, (page_size, offset))


if __name__ == "__main__":
    show("브랜드 1쪽 (2개씩, 이름순)", brand_page(1, 2))
    show("브랜드 2쪽 (2개씩, 이름순)", brand_page(2, 2))
