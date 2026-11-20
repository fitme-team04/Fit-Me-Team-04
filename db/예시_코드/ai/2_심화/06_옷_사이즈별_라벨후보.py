# 목적: 사이즈 분류의 정답 후보(클래스) 확인 — 옷 한 벌의 사이즈마다 옷 실측·권장 범위 치수가 몇 개 있는지, 치수 있는 사이즈가 있는 옷 목록
# 누가 쓰나: AI (사이즈 분류 모델이 고를 수 있는 클래스 = 치수가 있는 사이즈)
# 난이도: 심화 — 3개 표 JOIN·LEFT JOIN + GROUP BY + 조건부 합계(SUM CASE) + HAVING
# 출력: UNIQLO E422992-000 KR·US 사이즈 11행별 치수 수(M만 4개), 정답 후보 {KR:[M], US:[M]}, 치수 있는 옷 3개
# 실행: .venv/bin/python db/예시_코드/ai/2_심화/06_옷_사이즈별_라벨후보.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → ai → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 옷 한 벌(출처 + 상품번호)의 사이즈마다 옷 실측 치수 수·권장 범위 수 (치수 없는 사이즈도 0 으로 나옴)
def size_measure_tally(source_name, item_code):
    sql = """
        SELECT s.region, s.size_label,
               SUM(CASE WHEN gm.basis = 'garment' THEN 1 ELSE 0 END) AS garment_tally,
               SUM(CASE WHEN gm.basis = 'body' THEN 1 ELSE 0 END) AS body_range_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        WHERE g.source_name = %s
          AND g.item_code = %s
        GROUP BY s.size_id, s.region, s.size_label
        ORDER BY s.region, s.size_id
    """
    return query(sql, (source_name, item_code))


# 목적: 치수가 있는 사이즈가 하나 이상인 옷 목록 (사이즈 수 · 치수 있는 사이즈 수)
def garments_with_labels():
    sql = """
        SELECT g.source_name, g.item_code, g.target_gender,
               COUNT(DISTINCT s.size_id) AS size_tally,
               COUNT(DISTINCT gm.size_id) AS measured_size_tally
        FROM garment.garments AS g
        JOIN garment.sizes AS s ON s.garment_id = g.garment_id
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        GROUP BY g.garment_id, g.source_name, g.item_code, g.target_gender
        HAVING COUNT(DISTINCT gm.size_id) >= 1
        ORDER BY g.garment_id
    """
    return query(sql)


# 목적: 지역마다 정답 클래스로 쓸 수 있는 사이즈 이름 (옷 실측이 있는 사이즈)
def label_classes(rows):
    classes = {}
    for row in rows:
        if row["region"] not in classes:
            classes[row["region"]] = []
        if row["garment_tally"] > 0:
            classes[row["region"]].append(row["size_label"])
    return classes


if __name__ == "__main__":
    rows = size_measure_tally("uniqlo_site", "E422992-000")
    show("UNIQLO E422992-000 사이즈별 치수 수", rows)
    print("  지역별 정답 클래스 후보:", label_classes(rows))
    show("치수 있는 사이즈가 있는 옷 (HAVING)", garments_with_labels())
