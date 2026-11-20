# 목적: 서로 다른 두 사이즈(같은 옷의 KR M ↔ US M, 또는 다른 옷끼리)를 치수 항목마다 나란히 놓고 차이(cm·비율) 계산
# 누가 쓰나: 공통 (3D 옷 모델 차이, AI 사이즈 대응 특징, 프론트 "다른 옷과 비교" 안내)
# 난이도: 고급 — 같은 표를 두 번 쓰는 셀프 조인 포함 7개 JOIN(옷·사이즈·치수 A쪽 + B쪽 + 정의) + 계산식(차이, 비율)
# 출력: 크루넥T KR M 과 비교(a_cm·b_cm·diff_cm·diff_pct) — US M 4행, COVERNAT KR M 4행, kobo US M 2행
# 실행: .venv/bin/python db/예시_코드/공통/옷/3_고급/03_두_사이즈_치수_비교.py
# 같은 표를 두 번 쓰려면 별칭을 다르게(ga/gb, sa/sb, ma/mb) 붙여서 서로 다른 표처럼 다룸
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: A 사이즈와 B 사이즈의 옷 실측(basis = garment)을 치수 항목마다 비교 (두 쪽 다 있는 항목만)
def compare_two_sizes(a_source="uniqlo_site", a_item="E422992-000", a_label="M", a_region="KR",
                      b_source="uniqlo_site", b_item="E422992-000", b_label="M", b_region="US"):
    sql = """
        SELECT ma.measure_code, d.korean_name,
               ma.value_cm AS a_cm,
               mb.value_cm AS b_cm,
               mb.value_cm - ma.value_cm AS diff_cm,
               ROUND((mb.value_cm - ma.value_cm) / ma.value_cm * 100, 1) AS diff_pct
        FROM garment.garments AS ga
        JOIN garment.sizes AS sa ON sa.garment_id = ga.garment_id
        JOIN garment.measures AS ma ON ma.size_id = sa.size_id AND ma.basis = 'garment'
        JOIN garment.measures AS mb ON mb.measure_code = ma.measure_code AND mb.basis = 'garment'
        JOIN garment.sizes AS sb ON sb.size_id = mb.size_id
        JOIN garment.garments AS gb ON gb.garment_id = sb.garment_id
        JOIN ref.measure_definitions AS d ON d.measure_code = ma.measure_code
        WHERE ga.source_name = %s AND ga.item_code = %s AND sa.size_label = %s AND sa.region = %s
          AND gb.source_name = %s AND gb.item_code = %s AND sb.size_label = %s AND sb.region = %s
        ORDER BY ma.measure_code
    """
    params = (a_source, a_item, a_label, a_region, b_source, b_item, b_label, b_region)
    return query(sql, params)


if __name__ == "__main__":
    show("크루넥T KR M ↔ 크루넥T US M",
         compare_two_sizes("uniqlo_site", "E422992-000", "M", "KR", "uniqlo_site", "E422992-000", "M", "US"))
    show("크루넥T KR M ↔ COVERNAT 1848166 KR M",
         compare_two_sizes("uniqlo_site", "E422992-000", "M", "KR", "musinsa_ml_project", "1848166", "M", "KR"))
    show("크루넥T KR M ↔ kobo mens-tops US M",
         compare_two_sizes("uniqlo_site", "E422992-000", "M", "KR", "kobo_garment_measurements", "mens-tops", "M", "US"))
