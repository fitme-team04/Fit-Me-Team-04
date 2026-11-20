# 목적: 브랜드가 쓰는 사이즈 표기(XS·S·M ... / 지역별)와 각 표기를 쓰는 옷 수 — 프론트 사이즈 선택 버튼 만들기
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 사이즈 버튼, AI 라벨 목록)
# 난이도: 심화 — 3개 표 JOIN(브랜드 + 옷 + 사이즈) + GROUP BY (지역, 표기) + COUNT(DISTINCT) + MIN 으로 등록 순서 정렬
# 출력: 표 2개 — UNIQLO 지역별 사이즈 표기 11행(KR 8·US 3), COVERNAT 6행(region·size_label·garment_tally)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/2_심화/09_브랜드_사이즈_표기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드의 (지역, 사이즈 표기) 목록. 글자순이면 3XL·L·M ... 로 섞이므로 처음 등록된 size_id 순으로 정렬
def brand_size_labels(brand_name="UNIQLO"):
    sql = """
        SELECT s.region, s.size_label,
               COUNT(DISTINCT s.garment_id) AS garment_tally
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        WHERE b.brand_name = %s
        GROUP BY s.region, s.size_label
        ORDER BY s.region, MIN(s.size_id)
    """
    return query(sql, (brand_name,))


if __name__ == "__main__":
    show("UNIQLO 사이즈 표기 (지역별)", brand_size_labels("UNIQLO"))
    show("COVERNAT 사이즈 표기 (지역별)", brand_size_labels("COVERNAT"))
