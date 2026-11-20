# 목적: 브랜드·지역마다 가장 작은 사이즈 ~ 가장 큰 사이즈 (예: UNIQLO KR XS~4XL) — "이 브랜드는 큰 사이즈가 나오나?"
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 브랜드 소개 "XS~4XL")
# 난이도: 고급 — CTE + 계산식으로 표기 순서 만들기(FIELD) + 창 함수 ROW_NUMBER() 오름·내림 두 번 + 조건부 집계로 한 행에 모으기
# 출력: 표 1개 — 브랜드·지역별 사이즈 범위 3행(brand_name·region·smallest_size·largest_size·label_tally)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/05_브랜드_사이즈_범위.py
# 글자 표기(S·M·L)는 글자순 정렬이 크기순이 아니라서 FIELD(표기, 'XS','S',...) 로 순서 번호를 만듦 (목록에 없으면 0 → 맨 뒤 99)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (브랜드, 지역)마다 최소·최대 사이즈 표기와 표기 개수
def brand_size_range():
    sql = """
        WITH labels AS (
            SELECT DISTINCT b.brand_id, b.brand_name, s.region, s.size_label,
                   CASE WHEN FIELD(s.size_label, 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL') = 0 THEN 99
                        ELSE FIELD(s.size_label, 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL') END AS size_order
            FROM garment.brands AS b
            JOIN garment.garments AS g ON g.brand_id = b.brand_id
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        ),
        ordered AS (
            SELECT l.brand_id, l.brand_name, l.region, l.size_label,
                   ROW_NUMBER() OVER (PARTITION BY l.brand_id, l.region ORDER BY l.size_order ASC)  AS small_no,
                   ROW_NUMBER() OVER (PARTITION BY l.brand_id, l.region ORDER BY l.size_order DESC) AS large_no
            FROM labels AS l
        )
        SELECT o.brand_name, o.region,
               MAX(CASE WHEN o.small_no = 1 THEN o.size_label END) AS smallest_size,
               MAX(CASE WHEN o.large_no = 1 THEN o.size_label END) AS largest_size,
               COUNT(*) AS label_tally
        FROM ordered AS o
        GROUP BY o.brand_id, o.brand_name, o.region
        ORDER BY o.brand_id, o.region
    """
    return query(sql)


if __name__ == "__main__":
    show("브랜드·지역별 사이즈 범위", brand_size_range())
