# 목적: 같은 성별 평균 키보다 큰 사람, 같은 성별 평균 체중보다 무거운 사람 찾기
# 누가 쓰나: 공통 (3D 큰 체형 표본 고르기, AI 이상값 살펴보기)
# 난이도: 심화 — 단순 서브쿼리(SELECT AVG(...) 를 WHERE 안에서 값 하나로 씀) + 서브쿼리 결과를 열로도 보여 주기
# 출력: 표 3개 — 평균 키보다 큰 여성(7행)·남성(5행), 평균 체중보다 무거운 남성(6행); 값과 성별 평균 열
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/07_성별_평균보다_큰_사람.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 성별 하나에서 그 성별 평균 키보다 큰 사람 (평균은 괄호 안 서브쿼리가 먼저 계산)
def taller_than_average(gender="female"):
    sql = """
        SELECT p.profile_id, p.source_name, p.height_cm,
               (SELECT ROUND(AVG(a.height_cm), 1) FROM body.profiles AS a WHERE a.gender = %s) AS gender_avg_cm
        FROM body.profiles AS p
        WHERE p.gender = %s
          AND p.height_cm > (SELECT AVG(a.height_cm) FROM body.profiles AS a WHERE a.gender = %s)
        ORDER BY p.height_cm DESC
    """
    return query(sql, (gender, gender, gender))


# 목적: 성별 하나에서 그 성별 평균 체중보다 무거운 사람
def heavier_than_average(gender="male"):
    sql = """
        SELECT p.profile_id, p.source_name, p.weight_kg,
               (SELECT ROUND(AVG(a.weight_kg), 1) FROM body.profiles AS a WHERE a.gender = %s) AS gender_avg_kg
        FROM body.profiles AS p
        WHERE p.gender = %s
          AND p.weight_kg > (SELECT AVG(a.weight_kg) FROM body.profiles AS a WHERE a.gender = %s)
        ORDER BY p.weight_kg DESC
    """
    return query(sql, (gender, gender, gender))


if __name__ == "__main__":
    show("여성 평균 키보다 큰 여성", taller_than_average("female"))
    show("남성 평균 키보다 큰 남성", taller_than_average("male"))
    show("남성 평균 체중보다 무거운 남성", heavier_than_average("male"))
