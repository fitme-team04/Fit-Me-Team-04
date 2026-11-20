# 목적: 학습 데이터에 어떤 출처(데이터셋)·성별 값이 들어 있는지 종류만 보기 — 출처별 이름 변환표가 있는지도 확인
# 누가 쓰나: AI (데이터 출처 파악)
# 난이도: 기본 — 표 1개씩 SELECT DISTINCT + ORDER BY, 두 목록 비교는 파이썬
# 출력: profiles 출처 3종(ansur2·bodym·user)·성별 2종, aliases 출처 6종, 출처별 변환표 유무 표(user만 False)
# 실행: .venv/bin/python db/예시_코드/ai/1_기본/02_데이터_출처_종류.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 신체 정보(body.profiles)에 들어 있는 출처 이름 종류
def profile_sources():
    sql = """
        SELECT DISTINCT p.source_name
        FROM body.profiles AS p
        ORDER BY p.source_name
    """
    return query(sql)


# 목적: 신체 정보에 들어 있는 성별 값 종류 (male / female 외 값이 섞였는지 확인)
def profile_genders():
    sql = """
        SELECT DISTINCT p.gender
        FROM body.profiles AS p
        ORDER BY p.gender
    """
    return query(sql)


# 목적: 치수 이름 변환표(ref.measure_aliases)가 있는 출처 이름 종류
def alias_sources():
    sql = """
        SELECT DISTINCT a.source_name
        FROM ref.measure_aliases AS a
        ORDER BY a.source_name
    """
    return query(sql)


# 목적: 신체 정보 출처마다 변환표가 있는지 표로 (user 는 화면에서 표준 코드로 받으므로 변환표가 없어도 됨)
def compare_sources(profile_rows, alias_rows):
    alias_names = []
    for row in alias_rows:
        alias_names.append(row["source_name"])
    result = []
    for row in profile_rows:
        name = row["source_name"]
        has_alias = name in alias_names
        note = "변환표 있음"
        if not has_alias:
            note = "변환표 없음 (표준 코드로 입력하는 출처면 정상)"
        result.append({"source_name": name, "has_alias": has_alias, "note": note})
    return result


if __name__ == "__main__":
    sources = profile_sources()
    aliases = alias_sources()
    show("body.profiles 출처 종류", sources)
    show("body.profiles 성별 종류", profile_genders())
    show("ref.measure_aliases 출처 종류", aliases)
    show("출처별 변환표 유무", compare_sources(sources, aliases))
