# 목적: 같은 브랜드·같은 사이즈 표기인데 지역(KR·US)마다 옷 치수가 얼마나 다른지 — "유니클로 KR M 과 US M 은 같은 옷인가?"
# 누가 쓰나: 공통 (3D / AI / 프론트. 해외 직구 사이즈 안내)
# 난이도: 고급 — 5개 표 JOIN(브랜드 + 옷 + 사이즈 + 치수 + 항목 정의) + 지역을 열로 펼치는 피벗 MAX(CASE ...) + 차이 계산식 + HAVING
# 출력: 표 1개 — UNIQLO M 사이즈 KR↔US 옷 실측 4행(measure_code·korean_name·kr_cm·us_cm·us_minus_kr_cm)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/07_브랜드_지역별_사이즈_비교.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 브랜드 + 사이즈 표기 → (옷, 치수 항목) 한 행에 KR 값·US 값·차이(US − KR). 두 지역 모두 값이 있는 것만
def region_compare(brand_name="UNIQLO", size_label="M"):
    sql = """
        SELECT g.item_code, gm.measure_code, d.korean_name,
               MAX(CASE WHEN s.region = 'KR' THEN gm.value_cm END) AS kr_cm,
               MAX(CASE WHEN s.region = 'US' THEN gm.value_cm END) AS us_cm,
               MAX(CASE WHEN s.region = 'US' THEN gm.value_cm END)
                 - MAX(CASE WHEN s.region = 'KR' THEN gm.value_cm END) AS us_minus_kr_cm
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE b.brand_name = %s
          AND s.size_label = %s
          AND gm.basis = 'garment'
        GROUP BY g.garment_id, g.item_code, gm.measure_code, d.korean_name
        HAVING kr_cm IS NOT NULL AND us_cm IS NOT NULL
        ORDER BY g.garment_id, gm.measure_code
    """
    return query(sql, (brand_name, size_label))


if __name__ == "__main__":
    show("UNIQLO M 사이즈 KR ↔ US 옷 실측 비교", region_compare("UNIQLO", "M"))
