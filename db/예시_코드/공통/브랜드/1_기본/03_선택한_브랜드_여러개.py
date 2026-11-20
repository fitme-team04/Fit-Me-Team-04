# 목적: 화면에서 여러 개 고른 브랜드(brand_id 목록)를 한 번에 불러오기 — 체크박스로 브랜드 여러 개 선택
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 브랜드 다중 선택 필터)
# 난이도: 기본 — 표 1개(garment.brands) SELECT + WHERE IN (%s, %s, ...) + ORDER BY
# 출력: 표 2개 — brand_id 1·4 고른 결과 2행, brand_id 2·3 고른 결과 2행(brand_id·이름·나라·모회사)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/1_기본/03_선택한_브랜드_여러개.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: brand_id 목록 → 그 브랜드들. 목록 길이만큼 %s 자리를 만들어 값은 따로 넘김 (SQL 에 값을 직접 붙이지 않음)
def brands_by_ids(brand_ids=(1, 4)):
    if len(brand_ids) == 0:
        return []
    marks = []
    for brand_id in brand_ids:
        marks.append("%s")
    placeholders = ", ".join(marks)       # 예: "%s, %s"
    sql = """
        SELECT b.brand_id, b.brand_name, b.country, b.group_name
        FROM garment.brands AS b
        WHERE b.brand_id IN (""" + placeholders + """)
        ORDER BY b.brand_id
    """
    return query(sql, tuple(brand_ids))


if __name__ == "__main__":
    show("brand_id 1, 4 (UNIQLO, COVERNAT)", brands_by_ids((1, 4)))
    show("brand_id 2, 3", brands_by_ids((2, 3)))
