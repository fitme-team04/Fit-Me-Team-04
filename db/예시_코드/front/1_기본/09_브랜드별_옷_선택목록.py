# 목적: 브랜드를 고른 뒤 두 번째 드롭다운 "옷 고르기" 선택값 — 그 브랜드의 옷, 성별을 주면 그 성별 + unisex 만
# 누가 쓰나: 프론트 (브랜드별 옷 개수·종류 통계는 공통/브랜드)
# 난이도: 기본 — 표 1개(garment.garments) SELECT + WHERE(brand_id, target_gender IN) + ORDER BY
# 출력: 옷 드롭다운(value·label): UNIQLO 전체 12행, UNIQLO 남성(male+unisex) 3행, COVERNAT 1행
# 실행: .venv/bin/python db/예시_코드/front/1_기본/09_브랜드별_옷_선택목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 브랜드 이름 → brand_id (데모에서 번호를 외우지 않으려고 씀, 없으면 None)
def brand_id_of(brand_name):
    rows = query("SELECT b.brand_id FROM garment.brands AS b WHERE b.brand_name = %s", (brand_name,))
    if len(rows) == 0:
        return None
    return rows[0]["brand_id"]


# 목적: 브랜드의 옷 드롭다운 선택값. gender 를 주면 (gender, 'unisex') 대상 옷만
def garment_options(brand_id, gender=None):
    if gender is None:
        sql = """
            SELECT g.garment_id, g.garment_name, g.item_code, g.target_gender
            FROM garment.garments AS g
            WHERE g.brand_id = %s
            ORDER BY g.garment_name, g.garment_id
        """
        rows = query(sql, (brand_id,))
    else:
        sql = """
            SELECT g.garment_id, g.garment_name, g.item_code, g.target_gender
            FROM garment.garments AS g
            WHERE g.brand_id = %s
              AND g.target_gender IN (%s, 'unisex')
            ORDER BY g.garment_name, g.garment_id
        """
        rows = query(sql, (brand_id, gender))

    options = []
    for row in rows:
        # 같은 이름의 옷이 있을 수 있어 상품번호를 붙여 구분
        label = row["garment_name"] + " [" + row["item_code"] + ", " + row["target_gender"] + "]"
        options.append({"value": row["garment_id"], "label": label})
    return options


if __name__ == "__main__":
    uniqlo = brand_id_of("UNIQLO")
    show("UNIQLO 옷 드롭다운 (brand_id = " + str(uniqlo) + ")", garment_options(uniqlo))
    show("UNIQLO 옷 드롭다운 (남성 회원: male + unisex)", garment_options(uniqlo, "male"))
    covernat = brand_id_of("COVERNAT")
    show("COVERNAT 옷 드롭다운 (brand_id = " + str(covernat) + ")", garment_options(covernat))
