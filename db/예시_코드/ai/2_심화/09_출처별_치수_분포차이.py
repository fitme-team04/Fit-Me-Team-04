# 목적: 두 개 이상 출처가 함께 잰 치수만 골라, 출처 × 성별 평균·표준편차와 전체 평균과의 차이 = 데이터셋 간 분포 차이 확인
# 누가 쓰나: AI (출처를 섞어 학습해도 되는지 판단)
# 난이도: 심화 — 3개 표 JOIN + IN 서브쿼리(GROUP BY HAVING COUNT DISTINCT) + GROUP BY 집계(AVG·STDDEV_SAMP)
# 출력: 치수 5개×출처×성별 26행(n·avg_cm·sd_cm·전체평균·gap_cm), 최대 차이 chest_girth bodym female +17.0cm
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/09_출처별_치수_분포차이.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: min_sources 개 이상 출처가 잰 치수의 출처 × 성별 통계
def by_source(min_sources=2):
    sql = """
        SELECT m.measure_code, d.korean_name, p.source_name, p.gender,
               COUNT(*) AS n,
               ROUND(AVG(m.value_cm), 1) AS avg_cm,
               ROUND(STDDEV_SAMP(m.value_cm), 1) AS sd_cm
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        JOIN ref.measure_definitions AS d ON d.measure_code = m.measure_code
        WHERE m.measure_method = 'measured'
          AND m.measure_code IN (
              SELECT m2.measure_code
              FROM body.measures AS m2
              JOIN body.profiles AS p2 ON p2.profile_id = m2.profile_id
              WHERE m2.measure_method = 'measured'
              GROUP BY m2.measure_code
              HAVING COUNT(DISTINCT p2.source_name) >= %s
          )
        GROUP BY m.measure_code, d.korean_name, p.source_name, p.gender
        ORDER BY m.measure_code, p.gender, p.source_name
    """
    return query(sql, (min_sources,))


# 목적: 치수 × 성별 전체 평균 (출처 상관없이)
def overall_means():
    sql = """
        SELECT m.measure_code, p.gender, AVG(m.value_cm) AS avg_cm
        FROM body.profiles AS p
        JOIN body.measures AS m ON m.profile_id = p.profile_id
        WHERE m.measure_method = 'measured'
        GROUP BY m.measure_code, p.gender
    """
    means = {}
    for row in query(sql):
        means[(row["measure_code"], row["gender"])] = float(row["avg_cm"])
    return means


# 목적: 출처 평균 − 전체 평균 열 붙이기
def add_gap(rows, means):
    result = []
    for row in rows:
        item = dict(row)
        overall = means[(row["measure_code"], row["gender"])]
        item["overall_cm"] = round(overall, 1)
        item["gap_cm"] = round(float(row["avg_cm"]) - overall, 1)
        result.append(item)
    return result


if __name__ == "__main__":
    rows = add_gap(by_source(2), overall_means())
    show("출처 × 성별 치수 분포 (2개 이상 출처가 잰 치수)", rows)
    biggest = None
    for row in rows:
        if biggest is None or abs(row["gap_cm"]) > abs(biggest["gap_cm"]):
            biggest = row
    if biggest is not None:
        print("  → 전체 평균과 가장 다른 묶음:", biggest["measure_code"], biggest["source_name"],
              biggest["gender"], biggest["gap_cm"], "cm")
