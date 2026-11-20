# 목적: 체형(body_type) 클래스 × 성별마다, 치수를 N 개 이상 잰(= 정답·특징이 다 있는) 학습 가능 인원이 몇 명인지
# 누가 쓰나: AI (클래스마다 학습 샘플이 있는지, 비어 있는 클래스 찾기)
# 난이도: 심화 — 파생 테이블(서브쿼리 GROUP BY + HAVING) 을 LEFT JOIN + 바깥 GROUP BY, 클래스 순서 정렬은 파이썬
# 출력: 체형×성별 10행(profile_tally·labeled_tally)을 치수 3개·20개 이상 기준으로 각각, 샘플 0명 클래스 목록
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/05_학습가능_체형별_인원.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _body_type import BODY_TYPES, body_type_name            # 체형 허용값·한글 이름 (예시_코드/_body_type.py)


# 목적: 체형 × 성별 전체 인원과 치수 min_measures 개 이상 잰 인원
def labeled_by_class(min_measures):
    sql = """
        SELECT p.body_type, p.gender,
               COUNT(*) AS profile_tally,
               COUNT(mc.profile_id) AS labeled_tally
        FROM body.profiles AS p
        LEFT JOIN (
            SELECT m.profile_id, COUNT(*) AS measure_tally
            FROM body.measures AS m
            WHERE m.measure_method = 'measured'
            GROUP BY m.profile_id
            HAVING COUNT(*) >= %s
        ) AS mc ON mc.profile_id = p.profile_id
        WHERE p.body_type IS NOT NULL
        GROUP BY p.body_type, p.gender
    """
    return query(sql, (min_measures,))


# 목적: 정렬 기준: 체형 순서(BMI 작은 순) → 성별 (lambda 대신)
def class_order(row):
    return (BODY_TYPES.index(row["body_type"]), row["gender"])


# 목적: 클래스 순서로 정렬하고 한글 이름 붙이기
def arrange(rows):
    rows.sort(key=class_order)
    result = []
    for row in rows:
        result.append({"body_type": row["body_type"], "korean_name": body_type_name(row["body_type"]),
                       "gender": row["gender"], "profile_tally": row["profile_tally"],
                       "labeled_tally": row["labeled_tally"]})
    return result


if __name__ == "__main__":
    for n in [3, 20]:
        rows = arrange(labeled_by_class(n))
        show("체형 × 성별 학습 가능 인원 (치수 " + str(n) + "개 이상)", rows)
        empty = []
        for row in rows:
            if row["labeled_tally"] == 0:
                empty.append(row["body_type"] + "/" + row["gender"])
        print("  · 사람은 있지만 학습 샘플 0명인 클래스:", ", ".join(empty))
