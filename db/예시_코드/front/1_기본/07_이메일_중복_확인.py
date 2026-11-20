# 목적: 회원가입 화면 "이메일 중복 확인" 버튼 (형식 검사는 03 다음 단계) — 이미 가입한 email 인지 확인 (body.users.email 은 UNIQUE)
# 누가 쓰나: 프론트
# 난이도: 기본 — 표 1개(body.users) SELECT + WHERE 한 줄, COUNT(*) 하나
# 출력: email 2개의 exists·message 표: user01 은 이미 가입(True), new_member 는 가입 가능(False)
# 실행: .venv/bin/python db/예시_코드/front/1_기본/07_이메일_중복_확인.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: email 이 이미 있으면 True (공백은 앞뒤 잘라서 비교)
def email_exists(email):
    sql = """
        SELECT COUNT(*) AS tally
        FROM body.users AS u
        WHERE u.email = %s
    """
    rows = query(sql, (email.strip(),))
    if rows[0]["tally"] > 0:
        return True
    return False


if __name__ == "__main__":
    rows = []
    for email in ["user01@example.com", "new_member@example.com"]:
        used = email_exists(email)
        message = "가입 가능"
        if used:
            message = "이미 가입한 email (다른 email 입력)"
        rows.append({"email": email, "exists": used, "message": message})
    show("이메일 중복 확인", rows)
