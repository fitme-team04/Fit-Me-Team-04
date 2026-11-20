# 목적: 옷 치수 항목(measure_code)마다 몇 행이 등록됐고 값이 어디서 어디까지인지 — 어떤 치수가 자료가 많은지
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 심화 — 표 2개 JOIN(measures + measure_definitions) + GROUP BY + COUNT·MIN·MAX·AVG
# 출력: 치수 항목별 등록 수·최소·최대·평균 cm 6행(코드·한글명·basis), 부위별 옷 치수 행 수 2행
# 실행: .venv/bin/python db/예시_코드/공통/옷/2_심화/03_치수항목별_등록수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: (치수 항목, 기준)마다 행 수 + 옷 실측값 최소·최대·평균 (basis = body 는 값이 NULL 이라 NULL)
def measure_stats():
    sql = """
        SELECT gm.measure_code, d.korean_name, gm.basis,
               COUNT(*) AS row_tally,
               MIN(gm.value_cm) AS min_cm,
               MAX(gm.value_cm) AS max_cm,
               ROUND(AVG(gm.value_cm), 1) AS avg_cm
        FROM garment.measures AS gm
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        GROUP BY gm.measure_code, d.korean_name, gm.basis
        ORDER BY row_tally DESC, gm.measure_code
    """
    return query(sql)


# 목적: 신체 부위(body_part)마다 옷 치수 행 수
def tally_by_body_part():
    sql = """
        SELECT d.body_part, COUNT(*) AS row_tally
        FROM garment.measures AS gm
        JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        GROUP BY d.body_part
        ORDER BY row_tally DESC
    """
    return query(sql)


if __name__ == "__main__":
    show("치수 항목별 등록 수·범위", measure_stats())
    show("부위별 옷 치수 행 수", tally_by_body_part())
