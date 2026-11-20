# 목적: 옷의 대상 성별(target_gender)로 옷 거르기 — 한 성별만, 여러 성별 묶음(IN), 성별 하나의 옷 개수
# 누가 쓰나: 공통 (3D / AI / 프론트)
# 난이도: 기본 — 표 1개(garment.garments) + WHERE = / IN (...) / COUNT(*)
# 출력: 여성용 옷 9행, 남성에게 보일 옷(male+unisex) 5행 (id·상품번호·이름), 여성용 개수 표(garment_tally=9)
# 실행: .venv/bin/python db/예시_코드/공통/옷/1_기본/03_옷_대상성별별_목록.py
# 남성 사용자에게는 male + unisex 옷을 함께 보여 주는 식으로 IN 을 씀
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 1_기본 → 옷 → 공통 → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _db import query, show


# 목적: 대상 성별 하나(male / female / unisex)의 옷 목록
def garments_by_gender(target_gender="female"):
    sql = """
        SELECT g.garment_id, g.item_code, g.garment_name, g.category
        FROM garment.garments AS g
        WHERE g.target_gender = %s
        ORDER BY g.garment_id
    """
    return query(sql, (target_gender,))


# 목적: 대상 성별 두 개(예: male + unisex)의 옷 목록 — IN (%s, %s)
def garments_by_two_genders(gender_a="male", gender_b="unisex"):
    sql = """
        SELECT g.garment_id, g.target_gender, g.item_code, g.garment_name
        FROM garment.garments AS g
        WHERE g.target_gender IN (%s, %s)
        ORDER BY g.target_gender, g.garment_id
    """
    return query(sql, (gender_a, gender_b))


# 목적: 대상 성별 하나의 옷 개수 (1행)
def gender_tally(target_gender="female"):
    sql = """
        SELECT COUNT(*) AS garment_tally
        FROM garment.garments AS g
        WHERE g.target_gender = %s
    """
    return query(sql, (target_gender,))


if __name__ == "__main__":
    show("여성용 옷 (target_gender = female)", garments_by_gender("female"))
    show("남성 사용자에게 보일 옷 (male + unisex)", garments_by_two_genders("male", "unisex"))
    show("여성용 옷 개수", gender_tally("female"))
