# 목적: 고른 출처(source_name) 몇 개의 신체 정보만 보기 (예: 데이터셋 ansur2 + bodym 만, 회원 user 만)
# 누가 쓰나: 공통 (AI 학습 데이터 고르기, 3D 표본 고르기)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE IN (값 여러 개)·ORDER BY
# 출력: 표 2개 — 출처 ansur2·bodym 신체 정보(출처·성별·나이·키·체중, 17행), 그 밖 출처 user(5행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/06_출처_골라_신체정보.py
# 출처별 사람 수(GROUP BY)는 2_심화/05_사용자_신체정보_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 값 개수만큼 "%s, %s, ..." 자리 만들기 (값 자체는 SQL 에 넣지 않고 %s 로 넘김)
def placeholders(values):
    marks = []
    for value in values:
        marks.append("%s")
    return ", ".join(marks)


# 목적: 출처 목록(IN) 에 드는 신체 정보 (출처 → 키 순)
def profiles_by_sources(sources):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.source_name IN (""" + placeholders(sources) + """)
        ORDER BY p.source_name, p.height_cm
    """
    return query(sql, tuple(sources))


# 목적: 출처 목록에 들지 않는 신체 정보 (NOT IN)
def profiles_not_in_sources(sources):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.source_name NOT IN (""" + placeholders(sources) + """)
        ORDER BY p.profile_id
    """
    return query(sql, tuple(sources))


if __name__ == "__main__":
    show("데이터셋 출처만 (source_name IN ansur2, bodym)", profiles_by_sources(["ansur2", "bodym"]))
    show("데이터셋이 아닌 사람 (source_name NOT IN ansur2, bodym)", profiles_not_in_sources(["ansur2", "bodym"]))
