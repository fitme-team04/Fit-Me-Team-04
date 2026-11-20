# 목적: 예시 코드 공통 도우미 — 접속·조회·표 출력·쓰기·파일 저장 (예시가 아니라 모든 예시가 import 하는 파일)
# 누가 쓰나: 공통 / 3D / AI / 프론트 (모든 예시)
# 난이도: 기본 — 접속·SQL 실행·표 출력 도우미 (모든 예시는 이 폴더 예시_코드 하나만 sys.path 에 넣고 import)
# 전제: MySQL 컨테이너가 실행 중이고 db/sample/sample_data.sql 이 적재되어 있음
import os
import unicodedata
from pathlib import Path

import pymysql

# 저장소 루트 (이 파일 기준 두 단계 위: 예시_코드 → db → 루트)
ROOT = Path(__file__).resolve().parents[2]


# 목적: 루트의 .env 를 읽고, 없으면 .env.example 을 읽어 {키: 값} 으로 돌려줌
def read_env_file():
    path = ROOT / ".env"
    if not path.exists():
        path = ROOT / ".env.example"
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").split("\n"):
        line = line.replace("\r", "").strip()   # Windows 줄끝(CR) 제거
        if line == "" or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


# 목적: 값 하나 고르기: 환경변수 → .env 파일 → 기본값 순서
def setting(values, key, default):
    if key in os.environ:
        return os.environ[key]
    if key in values:
        return values[key]
    return default


# 목적: MySQL 접속. 쿼리에서 schema.table 로 쓰므로 database 는 지정하지 않음(None)
def connect():
    values = read_env_file()
    port = int(setting(values, "DB_PORT", "3306"))
    password = setting(values, "MYSQL_ROOT_PASSWORD", "poc-root")
    return pymysql.connect(
        host="127.0.0.1",
        port=port,
        user="root",
        password=password,
        database=None,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


# 목적: SQL 한 개 실행 → 행 목록(dict 의 list). params 는 %s 자리에 순서대로 들어감
def query(sql, params=()):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    finally:
        conn.close()
    return list(rows)


# --- 쓰기용 (front/3_고급/01~05·07~09, 예: front/3_고급/05_사용자_신체정보_저장.py) ---------------------
# 쓰기는 conn = connect() 로 접속 하나를 열고 아래 함수들을 여러 번 부른 뒤
# 끝에 conn.commit()(저장) 또는 conn.rollback()(취소) → conn.close() 순서로 씀.
# PyMySQL 은 기본이 autocommit 꺼짐이라 commit 전까지는 DB 에 반영되지 않음

# 목적: 열린 접속에서 SQL 한 개 실행 → 새로 생긴 AUTO_INCREMENT id (없으면 0)
def execute(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        new_id = cur.lastrowid
    return new_id


# 목적: 열린 접속에서 같은 SQL 을 여러 값 묶음으로 실행 → 영향받은 행 수
def execute_many(conn, sql, rows):
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
        tally = cur.rowcount
    return tally


# 목적: 열린 접속에서 조회 (commit 전에 방금 넣은 행을 확인할 때)
def query_in(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return list(rows)


# --- 파일 저장 (JSON·CSV 를 파일로도 남길 때) -----------------------------
# 저장 위치는 루트 out/ 아래로만 (out/ 은 .gitignore 로 커밋 제외)
OUT_DIR = ROOT / "out"


# 목적: 글자를 out/<rel_path> 에 저장하고 저장한 경로를 돌려줌 (폴더가 없으면 만듦)
def save_text(rel_path, text):
    path = OUT_DIR / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# 목적: 값 → 출력용 글자 (NULL 은 NULL 로 표시)
def to_text(value):
    if value is None:
        return "NULL"
    return str(value)


# 목적: 화면 폭 계산 (한글·일본어 같은 넓은 글자는 2칸)
def text_width(text):
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


# 목적: 오른쪽에 공백을 채워 폭 맞추기
def pad(text, width):
    return text + " " * (width - text_width(text))


# 목적: 결과를 열 맞춘 표로 출력
def show(title, rows):
    print()
    print("■ " + title + "  (" + str(len(rows)) + "행)")
    if len(rows) == 0:
        print("  (결과 없음)")
        return

    columns = list(rows[0].keys())

    # 열마다 가장 긴 글자 폭
    widths = []
    for col in columns:
        width = text_width(col)
        for row in rows:
            w = text_width(to_text(row[col]))
            if w > width:
                width = w
        widths.append(width)

    # 머리줄 + 구분선
    header = []
    line = []
    for i in range(len(columns)):
        header.append(pad(columns[i], widths[i]))
        line.append("-" * widths[i])
    print("  " + " | ".join(header))
    print("  " + "-+-".join(line))

    # 데이터 줄
    for row in rows:
        cells = []
        for i in range(len(columns)):
            cells.append(pad(to_text(row[columns[i]]), widths[i]))
        print("  " + " | ".join(cells))
