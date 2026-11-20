# 목적: 성별 하나에서 키가 큰 사람 상위 N명 보기 (키 순서 확인, 큰 체형 표본 고르기)
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE·ORDER BY DESC·LIMIT
# 출력: 표 3개 — 남성 키 큰 순 5명, 여성 키 큰 순 5명, 여성 키 작은 순 5명(출처·성별·나이·키·체중, 각 5행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/1_기본/02_키_큰_순_상위.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 성별(male / female) 하나에서 키 큰 순서로 앞 limit 명 (키가 같으면 체중 큰 순)
def tallest(gender="male", limit=5):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.gender = %s
          AND p.height_cm IS NOT NULL
        ORDER BY p.height_cm DESC, p.weight_kg DESC
        LIMIT %s
    """
    return query(sql, (gender, limit))


# 목적: 성별 하나에서 키 작은 순서로 앞 limit 명 (ORDER BY 방향만 반대)
def shortest(gender="female", limit=5):
    sql = """
        SELECT p.profile_id, p.source_name, p.gender, p.age, p.height_cm, p.weight_kg
        FROM body.profiles AS p
        WHERE p.gender = %s
          AND p.height_cm IS NOT NULL
        ORDER BY p.height_cm ASC, p.weight_kg ASC
        LIMIT %s
    """
    return query(sql, (gender, limit))


if __name__ == "__main__":
    show("남성 키 큰 순 상위 5명", tallest("male", 5))
    show("여성 키 큰 순 상위 5명", tallest("female", 5))
    show("여성 키 작은 순 5명", shortest("female", 5))
