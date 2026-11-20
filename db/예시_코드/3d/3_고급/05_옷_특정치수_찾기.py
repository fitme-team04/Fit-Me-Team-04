# 목적: 특정 브랜드·옷·사이즈의 특정 치수 하나 알아내기 (예: 유니클로 크루넥T M 사이즈 소매길이는?)
# 누가 쓰나: 3D
# 난이도: 고급 — 5개 표 JOIN + OR·LIKE 조건 (상품번호·상품명 일부, 코드·한글 이름 모두 받기)
# 출력: UNIQLO 크루넥T M 검색 3건(소매길이·chest_width·가슴둘레) 각 1행 표(size_label·value_cm·low/high_cm 등) + → 요약 줄
# 실행: .venv/bin/python db/예시_코드/3d/3_고급/05_옷_특정치수_찾기.py
# 옷은 상품번호(item_code) 또는 상품명 일부, 치수는 measure_code(sleeve_length) 또는 한글 이름(소매길이) 둘 다 됨
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 출처별 치수 재는 법 주의 (db/sql/51_seed_measure_aliases.sql 주석과 같은 말)
CAVEATS = {
    ("uniqlo_site", "sleeve_length"): "유니클로 소매길이(sleeve-length-cb)는 목 뒤 중심 기준 (화장), 어깨 끝 기준과 다름",
}


# 목적: 브랜드 + 옷(상품번호 또는 이름 일부) + 사이즈 + 지역 + 치수(코드 또는 한글 이름) → 맞는 행
def garment_measure(brand_name, name_keyword_or_item_code, size_label, region, measure):
    sql = """
        SELECT b.brand_name, g.garment_name, g.item_code, g.source_name,
               s.size_label, s.region, gm.basis, gm.measure_code, d.korean_name,
               gm.value_cm, gm.low_cm, gm.high_cm
        FROM garment.measures AS gm
        JOIN garment.sizes AS s ON s.size_id = gm.size_id
        JOIN garment.garments AS g ON g.garment_id = s.garment_id
        JOIN garment.brands AS b ON b.brand_id = g.brand_id
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE b.brand_name = %s
          AND (g.item_code = %s OR g.garment_name LIKE %s)
          AND s.size_label = %s
          AND s.region = %s
          AND (gm.measure_code = %s OR d.korean_name = %s)
        ORDER BY g.item_code, gm.basis DESC
    """
    keyword = "%" + name_keyword_or_item_code + "%"
    params = (brand_name, name_keyword_or_item_code, keyword, size_label, region, measure, measure)
    return query(sql, params)


# 목적: 결과 표 + 한 줄 답 + 재는 법 주의 출력
def print_answer(title, rows):
    show(title, rows)
    if len(rows) == 0:
        print("  → 해당 치수 자료 없음 (브랜드·옷·사이즈·지역·치수 이름 확인)")
        return
    for row in rows:
        if row["basis"] == "garment":
            print("  → " + row["garment_name"] + " " + row["size_label"] + "(" + row["region"] + ") "
                  + row["korean_name"] + " = " + str(row["value_cm"]) + " cm (옷 실측)")
        else:
            print("  → " + row["garment_name"] + " " + row["size_label"] + "(" + row["region"] + ") "
                  + row["korean_name"] + " 권장 범위 = " + str(row["low_cm"]) + " ~ " + str(row["high_cm"]) + " cm")
        key = (row["source_name"], row["measure_code"])
        if key in CAVEATS:
            print("    ※ " + CAVEATS[key])


if __name__ == "__main__":
    # 유니클로 크루넥T(E422992-000) M · KR 의 소매길이 (한글 이름으로)
    print_answer("UNIQLO / E422992-000 / M / KR / 소매길이",
                 garment_measure("UNIQLO", "E422992-000", "M", "KR", "소매길이"))
    # 상품명 일부(크루넥) + measure_code 로: 가슴단면
    print_answer("UNIQLO / '크루넥' / M / US / chest_width",
                 garment_measure("UNIQLO", "크루넥", "M", "US", "chest_width"))
    # 권장 신체 범위(basis = body)도 같은 방법: 가슴둘레
    print_answer("UNIQLO / E422992-000 / M / KR / 가슴둘레",
                 garment_measure("UNIQLO", "E422992-000", "M", "KR", "가슴둘레"))
