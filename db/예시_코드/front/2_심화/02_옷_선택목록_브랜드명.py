# 목적: 브랜드를 먼저 고르지 않는 "옷 검색" 드롭다운 — "브랜드 · 옷 이름 (사이즈 N개)" 라벨, 사이즈가 없는 옷은 선택 못 함
# 누가 쓰나: 프론트 (브랜드를 고른 뒤 옷 목록은 front/1_기본/09_브랜드별_옷_선택목록.py)
# 난이도: 심화 — 표 3개 LEFT JOIN (브랜드 없는 옷·사이즈 없는 옷도 나옴) + GROUP BY COUNT + COALESCE
# 출력: 브랜드명 붙은 옷 검색 드롭다운(value·label·disabled) 전체 14행, 검색어 '크루넥' 3행
# 실행: .venv/bin/python db/예시_코드/front/2_심화/02_옷_선택목록_브랜드명.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 옷마다 브랜드 이름 + 사이즈 개수. keyword 를 주면 옷 이름에 그 글자가 들어간 것만 (LIKE)
def garment_rows(keyword=None):
    sql = """
        SELECT g.garment_id,
               COALESCE(b.brand_name, '브랜드 없음') AS brand_name,
               g.garment_name, g.target_gender,
               COUNT(s.size_id) AS size_tally
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        LEFT JOIN garment.sizes  AS s ON s.garment_id = g.garment_id
        WHERE g.garment_name LIKE %s
        GROUP BY g.garment_id, b.brand_name, g.garment_name, g.target_gender
        ORDER BY size_tally DESC, brand_name, g.garment_name
    """
    pattern = "%"
    if keyword is not None:
        pattern = "%" + keyword + "%"
    return query(sql, (pattern,))


# 목적: 행 → 드롭다운 선택값 (사이즈 0개면 disabled=True)
def garment_options(keyword=None):
    options = []
    for row in garment_rows(keyword):
        disabled = False
        if row["size_tally"] == 0:
            disabled = True
        label = (row["brand_name"] + " · " + row["garment_name"] + " (" + row["target_gender"]
                 + ", 사이즈 " + str(row["size_tally"]) + "개)")
        options.append({"value": row["garment_id"], "label": label, "disabled": disabled})
    return options


if __name__ == "__main__":
    show("옷 검색 드롭다운 (전체)", garment_options())
    show("옷 검색 드롭다운 (검색어 = 크루넥)", garment_options("크루넥"))
