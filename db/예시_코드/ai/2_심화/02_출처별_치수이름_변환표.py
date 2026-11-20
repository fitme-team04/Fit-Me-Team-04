# 목적: 출처(데이터셋·쇼핑몰)마다 다른 치수 이름 → 표준 코드 변환표, 신체 ↔ 옷 치수 대응 규칙 (학습 데이터 이름 맞추기)
# 누가 쓰나: AI
# 난이도: 심화 — 2~3개 표 JOIN (같은 정의 표를 신체·옷 역할로 두 번 JOIN)
# 출력: uniqlo_site 별칭 9행·ansur2 별칭 23행(alias_name→measure_code), ansur2 변환 dict, measure_maps 8행
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/02_출처별_치수이름_변환표.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 출처 하나가 쓰는 치수 이름 → 표준 measure_code (ref.measure_aliases)
def measure_aliases(source_name="uniqlo_site"):
    sql = """
        SELECT a.alias_name, a.measure_code, d.korean_name
        FROM ref.measure_aliases AS a
        JOIN ref.measure_definitions AS d ON d.measure_code = a.measure_code
        WHERE a.source_name = %s
        ORDER BY a.alias_name
    """
    return query(sql, (source_name,))


# 목적: 출처 원래 이름 목록 → {원래 이름: 표준 코드} (원본 데이터 열 이름을 바꿀 때 씀)
def alias_dict(source_name):
    names = {}
    for row in measure_aliases(source_name):
        names[row["alias_name"]] = row["measure_code"]
    return names


# 목적: 신체 치수 ↔ 옷 치수 대응 (신체값 ≈ 옷값 × factor, ref.measure_maps)
def measure_maps():
    sql = """
        SELECT mm.body_measure_code, bd.korean_name AS body_korean_name,
               mm.garment_measure_code, gd.korean_name AS garment_korean_name,
               mm.factor
        FROM ref.measure_maps AS mm
        JOIN ref.measure_definitions AS bd ON bd.measure_code = mm.body_measure_code
        JOIN ref.measure_definitions AS gd ON gd.measure_code = mm.garment_measure_code
        ORDER BY mm.body_measure_code
    """
    return query(sql)


if __name__ == "__main__":
    show("ref.measure_aliases (source_name = uniqlo_site)", measure_aliases("uniqlo_site"))
    show("ref.measure_aliases (source_name = ansur2)", measure_aliases("ansur2"))
    print()
    print("  ansur2 열 이름 변환 dict:", alias_dict("ansur2"))
    show("ref.measure_maps", measure_maps())
