# 목적: 고른 체형(body_type) 몇 개에 드는 사람 목록 (예: 2·3단계 비만만, 저체중·정상만), 체형이 비어 있는 사람
# 누가 쓰나: 공통 (3D 체형별 대표 몸 고르기, AI 체형별 데이터 살펴보기)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE IN·IS NULL·ORDER BY
# 출력: 표 3개 — 2·3단계 비만(키·체중·body_type·한글 체형, 10행), 저체중·정상·비만 전단계(5행), 체형 빈값(0행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/07_체형_골라_신체정보.py
# 체형 값: underweight / normal / pre_obese / obese_1 / obese_2 / obese_3 (대한비만학회 BMI 단계, _body_type.py)
# 체형별 사람 수(GROUP BY)는 2_심화/05_사용자_신체정보_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show
from _body_type import body_type_name                          # body_type → 한글 이름


# 목적: 값 개수만큼 "%s, %s, ..." 자리 만들기 (값 자체는 %s 로 넘김)
def placeholders(values):
    marks = []
    for value in values:
        marks.append("%s")
    return ", ".join(marks)


# 목적: 체형 목록(IN) 에 드는 사람 (체형 → 체중 순) + 한글 체형 이름
def profiles_by_body_types(body_types):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.height_cm, p.weight_kg, p.body_type
        FROM body.profiles AS p
        WHERE p.body_type IN (""" + placeholders(body_types) + """)
        ORDER BY p.body_type, p.weight_kg
    """
    rows = query(sql, tuple(body_types))
    for row in rows:
        row["체형"] = body_type_name(row["body_type"])
    return rows


# 목적: 체형이 비어 있는 사람 (키·체중이 없어 계산 못 한 행. 예시 DB 는 0명이 정상)
def profiles_without_body_type():
    sql = """
        SELECT p.profile_id, p.source_name, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.body_type IS NULL
        ORDER BY p.profile_id
    """
    return query(sql)


if __name__ == "__main__":
    show("2·3단계 비만 (body_type IN obese_2, obese_3)", profiles_by_body_types(["obese_2", "obese_3"]))
    show("저체중·정상·비만 전단계", profiles_by_body_types(["underweight", "normal", "pre_obese"]))
    show("체형이 비어 있는 사람 (body_type IS NULL)", profiles_without_body_type())
