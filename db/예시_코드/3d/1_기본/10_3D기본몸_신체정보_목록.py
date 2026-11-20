# 목적: 3D 기본 몸(base mesh)을 키우거나 줄일 신체 정보 목록 — 키·체중·체형(body_type), 성별·체형으로 거르기 + 키 배율 계산
# 누가 쓰나: 3D
# 난이도: 기본 — 표 1개(body.profiles) SELECT + 선택 조건 2개(%s IS NULL OR ...)·ORDER BY
# 출력: body.profiles 표 3개 — 여성 전체(11행)·normal(3행)·남성 obese_2(4행); gender·height_cm·weight_kg·body_type·scale
# 실행: .venv/bin/python db/예시_코드/3d/1_기본/10_3D기본몸_신체정보_목록.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

# 3D 기본 몸의 키 (cm). 배율 = 사람 키 / 이 값
BASE_MESH_HEIGHT_CM = 170.0


# 목적: 키가 있는 신체 정보 목록. gender·body_type 이 None 이면 그 조건은 안 씀
def profiles_for_mesh(gender=None, body_type=None):
    sql = """
        SELECT p.profile_id, p.gender, p.height_cm, p.weight_kg, p.body_type, p.source_name
        FROM body.profiles AS p
        WHERE p.height_cm IS NOT NULL
          AND (%s IS NULL OR p.gender = %s)
          AND (%s IS NULL OR p.body_type = %s)
        ORDER BY p.height_cm DESC
    """
    return query(sql, (gender, gender, body_type, body_type))


# 목적: 행마다 키 배율(scale) 붙이기 — 3D 기본 몸을 이 배율로 늘리면 키가 맞음
def add_scale(rows):
    for row in rows:
        row["scale"] = round(float(row["height_cm"]) / BASE_MESH_HEIGHT_CM, 3)
    return rows


if __name__ == "__main__":
    show("여성 전체 + 키 배율 (기준 170cm)", add_scale(profiles_for_mesh("female")))
    show("체형 normal(정상)만", add_scale(profiles_for_mesh(None, "normal")))
    show("남성 · 2단계 비만(obese_2)", add_scale(profiles_for_mesh("male", "obese_2")))
