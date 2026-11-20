# 목적: 저장된 체형(body_type)마다 실제 BMI 가 어디서 어디까지인지 (최소·평균·최대), 2명 이상인 체형만
# 누가 쓰나: 공통 (체형 값이 BMI 단계와 맞게 들어갔는지 눈으로 확인, AI 체형 라벨 살펴보기)
# 난이도: 심화 — 표 1개 GROUP BY + 계산식(BMI = 체중 / 키²) 안의 집계 MIN·AVG·MAX + HAVING
# 출력: 표 2개 — 체형별 사람 수·BMI 최소/평균/최대·한글 체형(6행), 2명 이상 체형만 HAVING(4행)
# 실행: .venv/bin/python db/예시_코드/공통/사람/2_심화/04_체형별_BMI_범위.py
# 체형 기준: 대한비만학회 BMI 단계 (_body_type.py). 체형별 사람 수만 보려면 05_사용자_신체정보_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 사람 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show
from _body_type import BODY_TYPES, body_type_name               # 체형 순서·한글 이름


# 목적: 체형마다 BMI 최소·평균·최대 (min_people 명 이상인 체형만, HAVING)
def bmi_range_by_body_type(min_people=1):
    sql = """
        SELECT p.body_type,
               COUNT(*) AS people_tally,
               ROUND(MIN(p.weight_kg / POW(p.height_cm / 100, 2)), 1) AS min_bmi,
               ROUND(AVG(p.weight_kg / POW(p.height_cm / 100, 2)), 1) AS avg_bmi,
               ROUND(MAX(p.weight_kg / POW(p.height_cm / 100, 2)), 1) AS max_bmi
        FROM body.profiles AS p
        WHERE p.height_cm IS NOT NULL
          AND p.weight_kg IS NOT NULL
        GROUP BY p.body_type
        HAVING COUNT(*) >= %s
    """
    found = {}
    for row in query(sql, (min_people,)):
        found[row["body_type"]] = row
    result = []
    for body_type in BODY_TYPES:                 # BMI 작은 단계부터 다시 줄 세우기
        if body_type in found:
            row = found[body_type]
            row["체형"] = body_type_name(body_type)
            result.append(row)
    return result


if __name__ == "__main__":
    show("체형별 BMI 범위 (전체)", bmi_range_by_body_type(1))
    show("체형별 BMI 범위 (2명 이상인 체형만, HAVING)", bmi_range_by_body_type(2))
