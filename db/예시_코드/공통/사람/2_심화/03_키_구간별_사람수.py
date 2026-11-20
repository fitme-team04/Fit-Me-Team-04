# 목적: 키를 5cm 구간으로 나눠 성별마다 몇 명인지 (키 분포 히스토그램 자료)
# 누가 쓰나: 공통 (AI 키 분포 확인, 3D 키 구간별 표본, 프론트 통계 그래프)
# 난이도: 심화 — 표 1개 GROUP BY 계산식(FLOOR(height_cm / 5) * 5) 2개 열 묶기 + COUNT·AVG
# 출력: 표 2개 — 성별×키 5cm 구간 사람 수·평균 체중·구간·막대(11행), 성별×키 10cm 구간(7행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/03_키_구간별_사람수.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 성별 × 키 구간(width cm 단위로 내림) 사람 수와 그 구간의 평균 체중
def people_by_height_band(width=5):
    sql = """
        SELECT p.gender,
               FLOOR(p.height_cm / %s) * %s AS height_from_cm,
               COUNT(*) AS people_tally,
               ROUND(AVG(p.weight_kg), 1) AS avg_weight_kg
        FROM body.profiles AS p
        WHERE p.height_cm IS NOT NULL
        GROUP BY p.gender, height_from_cm
        ORDER BY p.gender, height_from_cm
    """
    rows = query(sql, (width, width))
    for row in rows:
        start = int(row["height_from_cm"])
        row["구간"] = str(start) + " ~ " + str(start + width - 1) + "cm"
        row["막대"] = "#" * int(row["people_tally"])          # 글자로 그린 막대
    return rows


if __name__ == "__main__":
    show("성별 × 키 5cm 구간 사람 수", people_by_height_band(5))
    show("성별 × 키 10cm 구간 사람 수", people_by_height_band(10))
