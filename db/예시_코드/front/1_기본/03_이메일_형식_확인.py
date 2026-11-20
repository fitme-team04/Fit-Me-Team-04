# 목적: 가입 화면 email 칸 — 앞뒤 공백 정리 후 형식(길이·@·도메인)만 검사해 이유별 메시지 보여 주기 (DB 접속 없음, 중복 확인은 07)
# 누가 쓰나: 프론트
# 난이도: 기본 — SQL 없음, 정규식 한 개(_검증.EMAIL_PATTERN)와 if 검사만
# 출력: email 8개의 정리값·ok·message 표(2개 통과, 6개는 빈 값·@·공백·도메인·100자 초과 오류)
# 실행: .venv/bin/python db/예시_코드/front/1_기본/03_이메일_형식_확인.py
import re
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import show
from _검증 import EMAIL_PATTERN                        # 간단한 형식 검사 정규식

EMAIL_MAX = 100                                       # body.users.email VARCHAR(100)


# 목적: 화면에서 받은 email 정리 (앞뒤 공백 제거, None 은 빈 글자)
def clean_email(email):
    if email is None:
        return ""
    return str(email).strip()


# 목적: 형식 검사 → 틀린 이유 한 줄 (통과면 빈 글자). 이유를 나눠야 사용자가 무엇을 고칠지 앎
def email_format_error(email):
    text = clean_email(email)
    if text == "":
        return "email 을 입력하세요"
    if len(text) > EMAIL_MAX:
        return "email 은 " + str(EMAIL_MAX) + "자 이하"
    if " " in text:
        return "email 안에 공백이 있음"
    if text.count("@") != 1:
        return "@ 가 하나여야 함"
    if re.match(EMAIL_PATTERN, text) is None:
        return "도메인 형식이 아님 (예: name@example.com)"
    return ""


if __name__ == "__main__":
    rows = []
    for email in ["user01@example.com", "  user02@example.com  ", "", "hong@", "hong@@example.com",
                  "hong gil@example.com", "hong@example", "a" * 95 + "@x.com"]:
        error = email_format_error(email)
        ok = error == ""
        rows.append({"입력": repr(email)[:30], "정리값": clean_email(email)[:30], "ok": ok, "message": error})
    show("email 형식 확인", rows)
