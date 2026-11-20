# 목적: 옷 한 벌의 사이즈별 실측(단면·길이)을 대응 규칙으로 몸 기준 값으로 환산 (가슴단면 53 × 2 = 옷 가슴둘레 106 → 3D 옷 메시 둘레)
# 누가 쓰나: 3D
# 난이도: 심화 — 3개 표 JOIN(garment.sizes + garment.measures + ref.measure_maps) + 계산식(value × factor)
# 출력: garment 6(UNIQLO 크루넥T, 6행)·14(COVERNAT 티셔츠, 3행) 몸 기준 환산 표(garment_cm·factor·body_code·body_equiv_cm)
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/10_옷실측_몸둘레_환산.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show


# 목적: 옷(garment_id)의 사이즈별 옷 실측 → 몸 기준 값 (규칙이 없는 실측은 빠짐: 총장 등)
def body_equivalents(garment_id):
    sql = """
        SELECT s.size_label, s.region,
               gm.measure_code AS garment_code, gm.value_cm AS garment_cm,
               mm.factor, mm.body_measure_code AS body_code,
               ROUND(gm.value_cm * mm.factor, 1) AS body_equiv_cm
        FROM garment.sizes AS s
        JOIN garment.measures AS gm ON gm.size_id = s.size_id AND gm.basis = 'garment'
        JOIN ref.measure_maps AS mm ON mm.garment_measure_code = gm.measure_code
        WHERE s.garment_id = %s
        ORDER BY s.region, s.size_id, mm.body_measure_code
    """
    return query(sql, (garment_id,))


if __name__ == "__main__":
    # garment 6: UNIQLO 크루넥T (E422992-000) — KR M · US M 에 실측
    show("몸 기준 환산 (garment_id = 6, UNIQLO 크루넥T)", body_equivalents(6))
    # garment 14: COVERNAT 티셔츠 (무신사 1848166) — KR M 에 실측
    show("몸 기준 환산 (garment_id = 14, COVERNAT 티셔츠)", body_equivalents(14))
