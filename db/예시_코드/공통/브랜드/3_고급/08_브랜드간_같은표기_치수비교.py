# 목적: 같은 사이즈 표기(예: M)라도 브랜드마다 치수가 얼마나 다른지 — "COVERNAT M 은 UNIQLO M 보다 큰가?"
# 누가 쓰나: 공통 (3D / AI / 프론트. 프론트 "다른 브랜드에서는 한 치수 작게" 안내, AI 브랜드 보정값)
# 난이도: 고급 — 5개 표 JOIN·LEFT JOIN + 창 함수 RANK()·MIN() OVER ()·AVG() OVER () + 가장 작은 값과의 차이 계산식
# 출력: 표 2개 — M 사이즈 가슴단면·어깨너비(옷) 브랜드 비교 각 4행(value_cm·small_rank·over_min_cm·vs_avg_cm)
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/08_브랜드간_같은표기_치수비교.py
# 브랜드가 없는 옷(kobo 공개 자료)도 비교 기준으로 쓰도록 브랜드는 LEFT JOIN, 이름은 '(브랜드 없음)'
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 사이즈 표기 + 옷 실측 항목 하나 → 브랜드·옷·지역별 값, 작은 순 순위, 최솟값과 차이, 전체 평균과 차이
def compare_across_brands(size_label="M", measure_code="chest_width"):
    sql = """
        SELECT COALESCE(b.brand_name, '(브랜드 없음)') AS brand_name,
               g.item_code, s.region, d.korean_name, gm.value_cm,
               RANK() OVER (ORDER BY gm.value_cm)                  AS small_rank,
               gm.value_cm - MIN(gm.value_cm) OVER ()              AS over_min_cm,
               ROUND(gm.value_cm - AVG(gm.value_cm) OVER (), 1)    AS vs_avg_cm
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        JOIN garment.measures AS gm ON gm.size_id = s.size_id
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE s.size_label = %s
          AND gm.measure_code = %s
          AND gm.basis = 'garment'
        ORDER BY small_rank, brand_name
    """
    return query(sql, (size_label, measure_code))


if __name__ == "__main__":
    show("M 사이즈 가슴단면 브랜드 비교 (chest_width)", compare_across_brands("M", "chest_width"))
    show("M 사이즈 어깨너비(옷) 브랜드 비교 (garment_shoulder_width)", compare_across_brands("M", "garment_shoulder_width"))
