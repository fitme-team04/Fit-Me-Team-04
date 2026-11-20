# 목적: 화면에서 받은 사용자 신체 정보가 올바른지 검사하는 실행 예시 → 틀린 곳 목록 (함수는 예시_코드/_검증.py, DB 접속 없음)
# 누가 쓰나: 프론트
# 난이도: 기본 — SQL 없음, 파이썬 if 검사만
# 출력: 올바른 입력 → 통과(오류 없음), 틀린 입력 → 오류 9개 목록(gender·height_cm·email·measures 등)
# 실행: .venv/bin/python db/예시_코드/front/1_기본/06_입력값_검증.py
# 허용값(성별·키·체중 범위·email·생년월일·body_type)은 _검증.py 맨 위 숫자·목록
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _검증 import validate                            # 입력 검사 (예시_코드/_검증.py)


# 목적: 결과 출력
def print_result(title, form, errors):
    print()
    print("■ " + title)
    print("  입력:", form)
    if len(errors) == 0:
        print("  → 통과 (오류 없음)")
    else:
        print("  → 오류 " + str(len(errors)) + "개")
        for e in errors:
            print("    - " + e)


if __name__ == "__main__":
    good = {"user_name": "홍길동", "email": "hong@example.com", "gender": "male",
            "birth_date": "1995-03-01", "height_cm": "175.0", "weight_kg": 70,
            "measures": {"chest_girth": 96.0, "waist_girth": 82.0}}
    print_result("올바른 입력", good, validate(good))

    bad = {"user_name": "", "email": "hong@", "gender": "man", "body_type": "fat",
           "birth_date": "1995/03/01", "height_cm": "abc", "weight_kg": 320,
           "measures": {"Chest": 96.0, "waist_girth": 82.25}}
    print_result("틀린 입력", bad, validate(bad))
