# 목적: 나이(age)가 비어 있는 신체 정보 찾기와 개수 — 나이 조건을 걸면 빠지는 사람 미리 확인 (BodyM 은 나이 없음)
# 누가 쓰나: 공통 (AI 학습 데이터 정리, 3D 나이대별 표본 고르기)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE IS NULL·COUNT(*)·COUNT(열)
# 출력: 표 2개 — 나이 빈값 신체 정보(출처·성별·키·체중, bodym 7행), 나이 채움 개수(전체 22·있음 15·없음 7, 1행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/04_나이_빈값_신체정보.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 나이가 NULL 인 신체 정보 목록 (= 나이 조건 검색에서 빠지는 사람)
def profiles_without_age():
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.age IS NULL
        ORDER BY p.profile_id
    """
    return query(sql)


# 목적: 전체 사람 수, 나이 있는 사람 수, 나이 없는 사람 수 (COUNT(age) 는 NULL 을 세지 않음)
def age_fill_tally():
    sql = """
        SELECT COUNT(*) AS people_tally,
               COUNT(p.age) AS with_age_tally,
               COUNT(*) - COUNT(p.age) AS without_age_tally
        FROM body.profiles AS p
    """
    return query(sql)


if __name__ == "__main__":
    show("나이가 없는 신체 정보 (age IS NULL)", profiles_without_age())
    show("나이 채움 개수", age_fill_tally())
