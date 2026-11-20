# 목적: 한 사람의 신체 치수를 한글 이름·부위와 함께 보기 — 뷰 1개(body.measure_details)만으로 (JOIN 은 뷰 안에 숨어 있음)
# 누가 쓰나: 공통 (프론트 내 치수 화면, 3D·AI 값 확인)
# 난이도: 기본 — 뷰 1개(body.measure_details) SELECT + WHERE =·IN·LIKE·ORDER BY
# 출력: 표 2개 — profile 19 팔·다리 치수(코드·한글명·부위·종류·값cm·측정방법, 7행), 둘레 치수 큰 순(9행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/10_한사람_치수_뷰.py
# 뷰 정의: db/sql/40_view_body_part.sql (body.measures + ref.measure_definitions)
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 값 개수만큼 "%s, %s, ..." 자리 만들기 (값 자체는 %s 로 넘김)
def placeholders(values):
    marks = []
    for value in values:
        marks.append("%s")
    return ", ".join(marks)


# 목적: 한 사람의 치수 중 고른 부위(IN) 만 (부위 → 코드 순)
def measures_of(profile_id, body_parts):
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part, d.measure_type, d.value_cm, d.measure_method
        FROM body.measure_details AS d
        WHERE d.profile_id = %s
          AND d.body_part IN (""" + placeholders(body_parts) + """)
        ORDER BY d.body_part, d.measure_code
    """
    params = [profile_id]
    for part in body_parts:
        params.append(part)
    return query(sql, tuple(params))


# 목적: 한 사람의 둘레(girth) 치수만 — 코드 끝이 _girth 인 것 (LIKE 뒤 일치, _ 는 \_ 로 글자 그대로)
def girths_of(profile_id):
    sql = """
        SELECT d.measure_code, d.korean_name, d.value_cm
        FROM body.measure_details AS d
        WHERE d.profile_id = %s
          AND d.measure_code LIKE %s
        ORDER BY d.value_cm DESC
    """
    return query(sql, (profile_id, "%\\_girth"))


if __name__ == "__main__":
    # profile 19: 회원 2 (여성), 치수 23개
    show("profile 19 의 팔·다리 치수 (body_part IN arm, leg)", measures_of(19, ["arm", "leg"]))
    show("profile 19 의 둘레 치수 (measure_code LIKE '%_girth', 큰 순)", girths_of(19))
