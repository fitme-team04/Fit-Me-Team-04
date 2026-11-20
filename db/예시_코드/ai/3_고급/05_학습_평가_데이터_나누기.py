# 목적: 학습(train) / 평가(test) 나누기 + k 겹 교차검증 번호(fold) 붙이기 — 성별마다 같은 비율이 되도록(층화) SQL 창 함수로 정해진 규칙
# 누가 쓰나: AI (모델 평가 전에 같은 사람이 학습·평가에 함께 들어가지 않게)
# 난이도: 고급 — CTE 2단(치수 개수 GROUP BY HAVING → ROW_NUMBER·COUNT OVER PARTITION BY) + 계산식(MOD 로 split·fold), 균형 검사는 파이썬
# 출력: 10명 train/test·fold 배정 표(test 12·18번), split×성별·split×출처·fold×성별 인원 표, 누락·중복 검사
# 규칙: 성별 안에서 profile_id 순 번호 rn → rn 이 test_every 의 배수면 test, 나머지 train / fold = (rn − 1) MOD k
#       난수를 쓰지 않아 몇 번 돌려도 같은 결과 (3_고급/07 회귀 평가도 같은 규칙)
# 실행: .venv/bin/python db/예시_코드/ai/3_고급/05_학습_평가_데이터_나누기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 치수 min_measures 개 이상 잰 사람 → 성별 층화 번호·split·fold
def split_rows(min_measures=3, test_every=3, k_folds=2):
    sql = """
        WITH labeled AS (
            SELECT p.profile_id, p.gender, p.source_name, p.body_type, COUNT(*) AS measure_tally
            FROM body.profiles AS p
            JOIN body.measures AS m ON m.profile_id = p.profile_id
            WHERE m.measure_method = 'measured'
            GROUP BY p.profile_id
            HAVING COUNT(*) >= %s
        ),
        numbered AS (
            SELECT l.*,
                   ROW_NUMBER() OVER (PARTITION BY l.gender ORDER BY l.profile_id) AS rn,
                   COUNT(*) OVER (PARTITION BY l.gender) AS gender_tally
            FROM labeled AS l
        )
        SELECT n.profile_id, n.gender, n.source_name, n.body_type, n.measure_tally,
               n.rn, n.gender_tally,
               CASE WHEN MOD(n.rn, %s) = 0 THEN 'test' ELSE 'train' END AS split,
               MOD(n.rn - 1, %s) AS fold
        FROM numbered AS n
        ORDER BY n.gender, n.rn
    """
    return query(sql, (min_measures, test_every, k_folds))


# 목적: 두 열 값 짝마다 사람 수 세기 → 표 행 목록 (예: split × gender)
def cross_tally(rows, col_a, col_b):
    tally = {}
    for row in rows:
        key = (str(row[col_a]), str(row[col_b]))
        if key not in tally:
            tally[key] = 0
        tally[key] += 1
    result = []
    for key in sorted(tally):
        result.append({col_a: key[0], col_b: key[1], "tally": tally[key]})
    return result


# 목적: 검사: test 에 모든 성별이 들어갔는지, 같은 사람이 두 번 나오지 않는지
def check_split(rows):
    genders_all = []
    genders_test = []
    ids = []
    for row in rows:
        if row["gender"] not in genders_all:
            genders_all.append(row["gender"])
        if row["split"] == "test" and row["gender"] not in genders_test:
            genders_test.append(row["gender"])
        ids.append(row["profile_id"])
    missing = []
    for g in genders_all:
        if g not in genders_test:
            missing.append(g)
    return {"test_missing_gender": missing, "duplicate_ids": len(ids) - len(set(ids))}


if __name__ == "__main__":
    rows = split_rows(3, 3, 2)
    show("학습 / 평가 나누기 (치수 3개 이상, 성별마다 3번째마다 test, 2겹 fold)", rows)
    show("split × gender 인원", cross_tally(rows, "split", "gender"))
    show("split × source_name 인원", cross_tally(rows, "split", "source_name"))
    show("fold × gender 인원", cross_tally(rows, "fold", "gender"))
    print("  검사:", check_split(rows))
