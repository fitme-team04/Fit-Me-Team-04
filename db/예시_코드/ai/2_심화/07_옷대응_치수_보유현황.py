# 목적: 신체 ↔ 옷 대응 규칙(ref.measure_maps)마다 그 신체 치수를 잰 사람 수와 그 옷 치수가 있는 사이즈 수 → 추천에 실제로 쓸 수 있는 특징
# 누가 쓰나: AI (사이즈 추천·분류에 쓸 특징 고르기)
# 난이도: 심화 — 3개 표 JOIN + LEFT JOIN(사람·사이즈가 0 이어도 규칙은 나옴) + GROUP BY COUNT(DISTINCT)
# 출력: 대응 치수 8쌍의 신체 쪽 잰 사람 수·옷 쪽 사이즈 수 표, 추천 특징 가능 여부(팔길이·가슴둘레·어깨너비만 예)
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/07_옷대응_치수_보유현황.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 대응 규칙마다 신체 쪽: 그 치수를 잰 사람 수
def body_side():
    sql = """
        SELECT mm.body_measure_code, d.korean_name, mm.garment_measure_code, mm.factor,
               COUNT(DISTINCT m.profile_id) AS profile_tally
        FROM ref.measure_maps AS mm
        JOIN ref.measure_definitions AS d ON d.measure_code = mm.body_measure_code
        LEFT JOIN body.measures AS m
               ON m.measure_code = mm.body_measure_code
              AND m.measure_method = 'measured'
        GROUP BY mm.body_measure_code, d.korean_name, mm.garment_measure_code, mm.factor
        ORDER BY mm.body_measure_code
    """
    return query(sql)


# 목적: 대응 규칙마다 옷 쪽: 그 옷 실측 치수가 있는 사이즈 수
def garment_side():
    sql = """
        SELECT mm.garment_measure_code, d.korean_name,
               COUNT(DISTINCT gm.size_id) AS size_tally
        FROM ref.measure_maps AS mm
        JOIN ref.measure_definitions AS d ON d.measure_code = mm.garment_measure_code
        LEFT JOIN garment.measures AS gm
               ON gm.measure_code = mm.garment_measure_code
              AND gm.basis = 'garment'
        GROUP BY mm.garment_measure_code, d.korean_name
        ORDER BY mm.garment_measure_code
    """
    return query(sql)


# 목적: 두 결과 합치기 → 양쪽 다 있으면 "쓸 수 있음"
def combine(body_rows, garment_rows):
    sizes = {}
    for row in garment_rows:
        sizes[row["garment_measure_code"]] = row["size_tally"]
    result = []
    for row in body_rows:
        size_tally = sizes.get(row["garment_measure_code"], 0)
        usable = "아니오"
        if row["profile_tally"] > 0 and size_tally > 0:
            usable = "예"
        result.append({"body_measure_code": row["body_measure_code"], "korean_name": row["korean_name"],
                       "garment_measure_code": row["garment_measure_code"], "factor": row["factor"],
                       "profile_tally": row["profile_tally"], "size_tally": size_tally, "usable": usable})
    return result


if __name__ == "__main__":
    body_rows = body_side()
    garment_rows = garment_side()
    show("신체 쪽: 대응 치수를 잰 사람 수", body_rows)
    show("옷 쪽: 대응 치수가 있는 사이즈 수", garment_rows)
    show("추천 특징으로 쓸 수 있는지", combine(body_rows, garment_rows))
