# 목적: 학습에 쓸 데이터가 얼마나 있는지 세기 — 출처별 사람 수, 치수 항목별 실측 행 수, 출처 하나의 앞 몇 명
# 누가 쓰나: AI (학습 시작 전 데이터 양 확인)
# 난이도: 기본 — 표 1개씩 SELECT + WHERE·LIMIT, COUNT(*) 하나 (GROUP BY 없이 파이썬 for 로 여러 번)
# 출력: 출처별 사람 수(ansur2 10·bodym 7·user 5), 치수 6개 실측 행 수, ansur2 앞 5명(나이·키·체중·체형) 표
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/04_학습데이터_개수_세기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

SOURCES = ["ansur2", "bodym", "user"]                                      # body.profiles.source_name 값
MEASURES = ["height", "chest_girth", "waist_girth", "hip_girth", "shoulder_width", "arm_length"]


# 목적: 출처 하나의 사람(신체 정보) 수
def count_profiles(source_name):
    sql = """
        SELECT COUNT(*) AS tally
        FROM body.profiles AS p
        WHERE p.source_name = %s
    """
    return query(sql, (source_name,))[0]["tally"]


# 목적: 치수 항목 하나의 실측(measured) 행 수 = 그 치수를 잰 사람 수
def count_measured(measure_code):
    sql = """
        SELECT COUNT(*) AS tally
        FROM body.measures AS m
        WHERE m.measure_code = %s
          AND m.measure_method = 'measured'
    """
    return query(sql, (measure_code,))[0]["tally"]


# 목적: 출처 하나의 앞 몇 명 (어떤 값이 들어 있는지 눈으로 보기)
def sample_profiles(source_name, limit=5):
    sql = """
        SELECT p.profile_id, p.gender, p.age, p.height_cm, p.weight_kg, p.body_type
        FROM body.profiles AS p
        WHERE p.source_name = %s
        ORDER BY p.profile_id
        LIMIT %s
    """
    return query(sql, (source_name, limit))


if __name__ == "__main__":
    rows = []
    for source in SOURCES:
        rows.append({"source_name": source, "profile_tally": count_profiles(source)})
    show("출처별 사람 수 (body.profiles)", rows)

    rows = []
    for code in MEASURES:
        rows.append({"measure_code": code, "measured_tally": count_measured(code)})
    show("치수 항목별 실측 행 수 (body.measures, measure_method = measured)", rows)

    show("ansur2 앞 5명", sample_profiles("ansur2", 5))
