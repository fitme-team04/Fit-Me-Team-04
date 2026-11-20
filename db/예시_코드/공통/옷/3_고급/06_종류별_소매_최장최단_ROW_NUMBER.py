# 목적: 옷 종류(category)마다 소매가 가장 긴·짧은 사이즈가 어느 옷의 어느 사이즈인지 (2_심화/09 는 값만, 여기는 그 행까지)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 고급 — 표 4개 JOIN + CTE + 창 함수 ROW_NUMBER() OVER (PARTITION BY 묶음 ORDER BY 값) 로 묶음 안 순번 → 1번만 고르기
# 출력: 종류별 소매 최장·최단 사이즈 2행, 가슴단면 최대·최소 2행, (종류, 성별)별 가슴단면 큰 순 앞 2개 3행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/06_종류별_소매_최장최단_ROW_NUMBER.py
# GROUP BY + MAX 는 "최댓값"만 주고 그 행의 다른 열(옷 이름·사이즈)은 못 줌 → 순번을 매겨 1번 행을 통째로 가져옴
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 종류마다 치수 하나가 가장 큰 사이즈(max) + 가장 작은 사이즈(min)
def extremes_by_category(measure_code="sleeve_length"):
    sql = """
        WITH ranked AS (
            SELECT g.category, g.item_code, g.garment_name, s.size_label, s.region,
                   d.korean_name, gm.value_cm,
                   ROW_NUMBER() OVER (PARTITION BY g.category ORDER BY gm.value_cm DESC, s.size_id) AS longest_no,
                   ROW_NUMBER() OVER (PARTITION BY g.category ORDER BY gm.value_cm ASC,  s.size_id) AS shortest_no
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
            JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
            WHERE gm.measure_code = %s
              AND gm.basis = 'garment'
        )
        SELECT r.category,
               CASE WHEN r.longest_no = 1 THEN 'max' ELSE 'min' END AS pick,
               r.korean_name, r.value_cm, r.item_code, r.garment_name, r.size_label, r.region
        FROM ranked AS r
        WHERE r.longest_no = 1 OR r.shortest_no = 1
        ORDER BY r.category, r.value_cm DESC
    """
    return query(sql, (measure_code,))


# 목적: (종류, 대상 성별)마다 치수 하나가 큰 순으로 앞 top_n 개 사이즈
def top_n_by_category_gender(measure_code="chest_width", top_n=2):
    sql = """
        WITH ranked AS (
            SELECT g.category, g.target_gender, g.item_code, s.size_label, s.region, d.korean_name, gm.value_cm,
                   ROW_NUMBER() OVER (PARTITION BY g.category, g.target_gender
                                      ORDER BY gm.value_cm DESC, s.size_id) AS row_no
            FROM garment.garments AS g
            JOIN garment.sizes AS s ON s.garment_id = g.garment_id
            JOIN garment.measures AS gm ON gm.size_id = s.size_id
            JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
            WHERE gm.measure_code = %s
              AND gm.basis = 'garment'
        )
        SELECT r.category, r.target_gender, r.row_no, r.item_code, r.size_label, r.region, r.korean_name, r.value_cm
        FROM ranked AS r
        WHERE r.row_no <= %s
        ORDER BY r.category, r.target_gender, r.row_no
    """
    return query(sql, (measure_code, top_n))


if __name__ == "__main__":
    show("종류별 소매 최장·최단 사이즈", extremes_by_category("sleeve_length"))
    show("종류별 가슴단면 최대·최소 사이즈", extremes_by_category("chest_width"))
    show("(종류, 성별)별 가슴단면 큰 순 앞 2개", top_n_by_category_gender("chest_width", 2))
