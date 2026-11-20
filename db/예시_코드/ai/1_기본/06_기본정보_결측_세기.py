# 목적: 기본 특징(나이·키·체중·근육량·체지방률·체형) 열마다 빈 값(NULL)이 몇 개인지 출처별로 세기
# 누가 쓰나: AI (어떤 기본 정보를 특징으로 쓸 수 있는지)
# 난이도: 기본 — 표 1개(body.profiles) COUNT(*)·COUNT(열) + WHERE, 빈 값 = 전체 − 채운 수 는 파이썬
# 출력: 출처 3개별 total과 기본정보 6열 NULL 수 표, 출처별 전부 비어 못 쓰는 열 목록(muscle_kg·body_fat_pct 등)
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/06_기본정보_결측_세기.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

COLUMNS = ["age", "height_cm", "weight_kg", "muscle_kg", "body_fat_pct", "body_type"]


# 목적: 출처 하나의 전체 행 수와 열마다 채운 수 (COUNT(열) 은 NULL 을 세지 않음)
def filled_counts(source_name):
    sql = """
        SELECT COUNT(*) AS total,
               COUNT(p.age) AS age,
               COUNT(p.height_cm) AS height_cm,
               COUNT(p.weight_kg) AS weight_kg,
               COUNT(p.muscle_kg) AS muscle_kg,
               COUNT(p.body_fat_pct) AS body_fat_pct,
               COUNT(p.body_type) AS body_type
        FROM body.profiles AS p
        WHERE p.source_name = %s
    """
    return query(sql, (source_name,))[0]


# 목적: 출처 이름 목록
def source_names():
    sql = """
        SELECT DISTINCT p.source_name
        FROM body.profiles AS p
        ORDER BY p.source_name
    """
    names = []
    for row in query(sql):
        names.append(row["source_name"])
    return names


# 목적: 출처별 열마다 빈 값 수 표 (출처 1행, 열마다 빈 값 수)
def missing_table():
    result = []
    for name in source_names():
        counts = filled_counts(name)
        row = {"source_name": name, "total": counts["total"]}
        for col in COLUMNS:
            row["빈:" + col] = counts["total"] - counts[col]
        result.append(row)
    return result


if __name__ == "__main__":
    table = missing_table()
    show("출처별 기본 정보 빈 값(NULL) 수", table)
    print()
    for row in table:
        unusable = []
        for col in COLUMNS:
            if row["빈:" + col] == row["total"]:
                unusable.append(col)
        if len(unusable) > 0:
            print("  · " + row["source_name"] + ": 전부 비어 특징으로 못 씀 → " + ", ".join(unusable))
