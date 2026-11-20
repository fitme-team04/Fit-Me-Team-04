# 목적: DB 에 저장된 체형 라벨(body_type)이 키·체중으로 다시 계산한 값과 같은지 검사 = 라벨 오류(잡음) 찾기
# 누가 쓰나: AI (정답 라벨 품질 확인)
# 난이도: 기본 — 표 1개(body.profiles) SELECT + WHERE, BMI·체형 재계산과 비교는 파이썬(_body_type.py)
# 출력: 22명 BMI·저장 체형·재계산 체형 비교 표(일치 22·불일치 0), user 5명만 같은 표
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/09_체형라벨_재계산_검사.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show
from _body_type import bmi_of, body_type_of                  # 키·체중 → BMI → 체형 (예시_코드/_body_type.py)


# 목적: 키·체중·저장된 체형 읽기. source_name 을 주면 그 출처만
def labeled_profiles(source_name=None):
    sql = """
        SELECT p.profile_id, p.source_name, p.height_cm, p.weight_kg, p.body_type
        FROM body.profiles AS p
        WHERE (%s IS NULL OR p.source_name = %s)
        ORDER BY p.profile_id
    """
    return query(sql, (source_name, source_name))


# 목적: 행마다 BMI·재계산 체형·일치 여부 붙이기
def check_labels(rows):
    result = []
    for row in rows:
        bmi = bmi_of(row["height_cm"], row["weight_kg"])
        expected = body_type_of(row["height_cm"], row["weight_kg"])
        bmi_text = "-"
        if bmi is not None:
            bmi_text = round(bmi, 1)
        same = expected == row["body_type"]
        result.append({"profile_id": row["profile_id"], "source_name": row["source_name"],
                       "bmi": bmi_text, "stored": row["body_type"], "recomputed": expected, "same": same})
    return result


if __name__ == "__main__":
    result = check_labels(labeled_profiles())
    show("체형 라벨 재계산 검사 (전체)", result)
    wrong = []
    for row in result:
        if not row["same"]:
            wrong.append(row)
    print("  → 일치", len(result) - len(wrong), "명 / 불일치", len(wrong), "명")
    if len(wrong) > 0:
        show("불일치 행 (라벨 수정 필요)", wrong)
    show("출처 하나만 (source_name = user)", check_labels(labeled_profiles("user")))
