# 목적: 브랜드 하나의 사이즈표 — (옷, 사이즈, 지역) 한 행에 옷 실측 치수를 열로 펼침 + 브랜드별 옷·사이즈·치수 개수
# 누가 쓰나: 공통 (3D / AI / 프론트. 상품 화면 사이즈표)
# 난이도: 고급 — 4개 표 JOIN + 조건부 집계 피벗 MAX(CASE ...) + 파생 테이블(FROM 안의 SELECT) + HAVING
# 출력: 표 4개 — UNIQLO 사이즈표 11행·치수 있는 것 2행, COVERNAT 1행(총장·가슴단면 등) + 열 이름 풀이, 브랜드별 개수 4행
# 실행: .venv/bin/python db/예시_코드/공통/브랜드/3_고급/06_브랜드_사이즈표.py
# 세로(사이즈 × 치수 = 1행)로 저장된 garment.measures 를 가로(사이즈 = 1행, 치수 = 열)로 바꾸는 방법:
#   GROUP BY 사이즈 → 열마다 MAX(CASE WHEN 치수 = '그 치수' THEN 값 END) (그 치수가 없으면 NULL)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 브랜드 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show

# 표 열 이름 → 한글 (ref.measure_definitions.korean_name 과 같음)
COLUMN_NAMES = {
    "body_length": "총장",
    "chest_width": "가슴단면",
    "garment_shoulder_width": "어깨너비(옷)",
    "sleeve_length": "소매길이",
    "chest_girth_range": "권장 가슴둘레(신체, low~high)",
}


# 목적: 브랜드 사이즈표. only_measured=True 면 치수가 하나라도 있는 사이즈만
def size_chart(brand_name="UNIQLO", only_measured=False):
    measured_flag = 0
    if only_measured:
        measured_flag = 1
    sql = """
        SELECT g.item_code, g.garment_name, s.size_label, s.region,
               MAX(CASE WHEN gm.basis = 'garment' AND gm.measure_code = 'body_length' THEN gm.value_cm END) AS body_length,
               MAX(CASE WHEN gm.basis = 'garment' AND gm.measure_code = 'chest_width' THEN gm.value_cm END) AS chest_width,
               MAX(CASE WHEN gm.basis = 'garment' AND gm.measure_code = 'garment_shoulder_width' THEN gm.value_cm END) AS garment_shoulder_width,
               MAX(CASE WHEN gm.basis = 'garment' AND gm.measure_code = 'sleeve_length' THEN gm.value_cm END) AS sleeve_length,
               MAX(CASE WHEN gm.basis = 'body' AND gm.measure_code = 'chest_girth' THEN CONCAT(gm.low_cm, '~', gm.high_cm) END) AS chest_girth_range,
               COUNT(gm.measure_code) AS measure_tally
        FROM garment.brands AS b
        JOIN garment.garments AS g ON g.brand_id = b.brand_id
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE b.brand_name = %s
        GROUP BY g.garment_id, g.item_code, g.garment_name, s.size_id, s.size_label, s.region
        HAVING (%s = 0 OR COUNT(gm.measure_code) > 0)
        ORDER BY g.garment_id, s.region, s.size_id
    """
    return query(sql, (brand_name, measured_flag))


# 목적: 브랜드마다 옷 수·사이즈 수·치수가 있는 사이즈 수·치수 행 수 (자료가 얼마나 찼는지)
# 파생 테이블 mc = 사이즈마다 치수 행 수를 먼저 세어 둔 작은 표 (FROM 안의 SELECT)
def brand_tally():
    sql = """
        SELECT b.brand_name,
               COUNT(DISTINCT g.garment_id) AS garment_tally,
               COUNT(DISTINCT s.size_id) AS size_tally,
               COUNT(DISTINCT mc.size_id) AS measured_size_tally,
               COALESCE(SUM(mc.measure_tally), 0) AS measure_tally
        FROM garment.brands AS b
        LEFT JOIN garment.garments AS g ON g.brand_id = b.brand_id
        LEFT JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN (
            SELECT gm.size_id, COUNT(*) AS measure_tally
            FROM garment.measures AS gm
            GROUP BY gm.size_id
        ) AS mc ON mc.size_id = s.size_id
        GROUP BY b.brand_id, b.brand_name
        ORDER BY b.brand_id
    """
    return query(sql)


# 목적: 열 이름 안내 한 줄씩
def print_columns():
    print("  열 이름:")
    for code in COLUMN_NAMES:
        print("    " + code + " = " + COLUMN_NAMES[code])


if __name__ == "__main__":
    show("UNIQLO 사이즈표 (사이즈가 등록된 옷 전부, 치수 없는 사이즈는 NULL)", size_chart("UNIQLO"))
    show("UNIQLO 사이즈표 (치수 있는 사이즈만)", size_chart("UNIQLO", only_measured=True))
    show("COVERNAT 사이즈표 (치수 있는 사이즈만)", size_chart("COVERNAT", only_measured=True))
    print_columns()
    show("브랜드별 개수 (옷·사이즈·치수 있는 사이즈·치수 행)", brand_tally())
