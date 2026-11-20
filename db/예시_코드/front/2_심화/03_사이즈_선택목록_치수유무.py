# 목적: 사이즈 드롭다운에 "추천 가능 여부" 표시 — 사이즈마다 옷 실측·권장 체형 범위 치수가 몇 개 있는지 세어 없으면 선택 못 함
# 누가 쓰나: 프론트 (치수 없이 사이즈만 고르는 목록은 front/1_기본/10_옷별_사이즈_선택목록.py)
# 난이도: 심화 — 표 2개 LEFT JOIN + GROUP BY 에 SUM(CASE ...) 로 basis 별 개수 나눠 세기
# 출력: 사이즈 드롭다운 + 치수 유무 note·disabled: garment 6 US 3행·KR 8행, garment 14 KR 6행
# 실행: .venv/bin/python db/예시_코드/front/2_심화/03_사이즈_선택목록_치수유무.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 옷 한 벌 + 표기 체계의 사이즈마다 옷 실측(garment) 개수·권장 범위(body) 개수
def size_measure_counts(garment_id, region):
    sql = """
        SELECT s.size_id, s.size_label,
               SUM(CASE WHEN m.basis = 'garment' THEN 1 ELSE 0 END) AS garment_tally,
               SUM(CASE WHEN m.basis = 'body'    THEN 1 ELSE 0 END) AS body_tally
        FROM garment.sizes AS s
        LEFT JOIN garment.measures AS m ON m.size_id = s.size_id
        WHERE s.garment_id = %s
          AND s.region = %s
        GROUP BY s.size_id, s.size_label
        ORDER BY s.size_id
    """
    return query(sql, (garment_id, region))


# 목적: 개수 행 → 드롭다운 선택값. 치수가 하나도 없으면 비교를 못 하니 disabled=True
def size_options(garment_id, region):
    options = []
    for row in size_measure_counts(garment_id, region):
        garment_tally = int(row["garment_tally"])
        body_tally = int(row["body_tally"])
        disabled = False
        note = "옷 실측 " + str(garment_tally) + "개 · 권장범위 " + str(body_tally) + "개"
        if garment_tally + body_tally == 0:
            disabled = True
            note = "치수 자료 없음"
        options.append({"value": row["size_id"], "label": row["size_label"], "note": note, "disabled": disabled})
    return options


if __name__ == "__main__":
    # garment_id 6 = UNIQLO 크루넥T(unisex), 14 = COVERNAT 2-PACK 티셔츠 (db/sample/sample_data.sql)
    show("사이즈 드롭다운 (garment_id = 6, region = US)", size_options(6, "US"))
    show("사이즈 드롭다운 (garment_id = 6, region = KR)", size_options(6, "KR"))
    show("사이즈 드롭다운 (garment_id = 14, region = KR)", size_options(14, "KR"))
