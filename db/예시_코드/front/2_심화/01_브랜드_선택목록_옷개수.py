# 목적: 브랜드 드롭다운에 옷 개수를 붙이고, 옷이 0벌인 브랜드는 회색(선택 못 함)으로 내려 주기
# 누가 쓰나: 프론트 (브랜드만 있는 단순 목록은 front/1_기본/08_브랜드_선택목록.py)
# 난이도: 심화 — 표 2개 LEFT JOIN (옷이 없는 브랜드도 나옴) + GROUP BY COUNT
# 출력: 브랜드 드롭다운 + 옷 개수(value·label·disabled) 전체 4행·남성 4행, 옷 0벌 브랜드는 disabled True
# 실행: .venv/bin/python db/예시_코드/front/2_심화/01_브랜드_선택목록_옷개수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 브랜드마다 옷 개수. gender 를 주면 그 성별 + unisex 옷만 셈 (조건을 ON 에 둬야 0벌 브랜드가 사라지지 않음)
def brand_counts(gender=None):
    if gender is None:
        sql = """
            SELECT b.brand_id, b.brand_name, COUNT(g.garment_id) AS garment_tally
            FROM garment.brands AS b
            LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
            GROUP BY b.brand_id, b.brand_name
            ORDER BY garment_tally DESC, b.brand_name
        """
        return query(sql)
    sql = """
        SELECT b.brand_id, b.brand_name, COUNT(g.garment_id) AS garment_tally
        FROM garment.brands AS b
        LEFT JOIN garment.garments AS g
               ON g.brand_id = b.brand_id
              AND g.target_gender IN (%s, 'unisex')
        GROUP BY b.brand_id, b.brand_name
        ORDER BY garment_tally DESC, b.brand_name
    """
    return query(sql, (gender,))


# 목적: 개수 행 → 드롭다운 선택값 (0벌이면 disabled=True)
def brand_options(gender=None):
    options = []
    for row in brand_counts(gender):
        disabled = False
        if row["garment_tally"] == 0:
            disabled = True
        options.append({"value": row["brand_id"],
                        "label": row["brand_name"] + " (" + str(row["garment_tally"]) + "벌)",
                        "disabled": disabled})
    return options


if __name__ == "__main__":
    show("브랜드 드롭다운 + 옷 개수 (전체)", brand_options())
    show("브랜드 드롭다운 + 옷 개수 (남성 회원: male + unisex)", brand_options("male"))
