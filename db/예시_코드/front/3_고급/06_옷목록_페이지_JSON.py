# 목적: 옷 목록 API — 요청(page·page_size·brand_id·gender) → LIMIT/OFFSET 한 쪽 + 전체 개수·전체 쪽수 → 응답(JSON)
# 누가 쓰나: 프론트
# 난이도: 고급 — 같은 조건으로 COUNT 와 목록 두 쿼리, 조건을 목록으로 모아 WHERE 조립(%s 만), 쪽 번호 검사·계산, JSON 응답
# 출력: 옷 목록 JSON(ok·page·total 14·total_pages·has_next·items): 1쪽 5개, 3쪽 4개, 필터 2개, 틀린 page 오류
# 실행: .venv/bin/python db/예시_코드/front/3_고급/06_옷목록_페이지_JSON.py   (조회만, DB 에 쓰지 않음)
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 3_고급 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query

PAGE_SIZE_DEFAULT = 5
PAGE_SIZE_MAX = 50


# 목적: 요청 값 → 1 이상 정수 (없으면 기본값, 틀리면 None)
def positive_int(request, key, default):
    value = request.get(key)
    if value is None or str(value).strip() == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number < 1:
        return None
    return number


# 목적: 요청의 거르기 조건 → (WHERE 글자, 값 묶음). 값은 언제나 %s 자리로만 넣음
def build_where(request):
    conditions = []
    params = []
    if request.get("brand_id") is not None:
        conditions.append("g.brand_id = %s")
        params.append(request["brand_id"])
    if request.get("gender") is not None:
        conditions.append("g.target_gender IN (%s, 'unisex')")
        params.append(request["gender"])
    if len(conditions) == 0:
        return "", ()
    return "WHERE " + " AND ".join(conditions), tuple(params)


# 목적: API 본체: 요청 dict → 응답 dict (ok=False 면 errors)
def handle_garment_list(request):
    errors = []
    page = positive_int(request, "page", 1)
    page_size = positive_int(request, "page_size", PAGE_SIZE_DEFAULT)
    if page is None:
        errors.append("page: 1 이상 정수")
    if page_size is None or page_size > PAGE_SIZE_MAX:
        errors.append("page_size: 1 ~ " + str(PAGE_SIZE_MAX) + " 정수")
    gender = request.get("gender")
    if gender is not None and gender not in ("male", "female"):
        errors.append("gender: male / female")
    if len(errors) > 0:
        return {"ok": False, "errors": errors}

    where, params = build_where(request)
    total = query("SELECT COUNT(*) AS tally FROM garment.garments AS g " + where, params)[0]["tally"]
    total_pages = (total + page_size - 1) // page_size
    offset = (page - 1) * page_size

    sql = """
        SELECT g.garment_id, COALESCE(b.brand_name, '브랜드 없음') AS brand_name, g.garment_name,
               g.category, g.target_gender, g.item_code
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        """ + where + """
        ORDER BY g.garment_id
        LIMIT %s OFFSET %s
    """
    items = query(sql, params + (page_size, offset))

    has_next = False
    if page < total_pages:
        has_next = True
    return {"ok": True, "page": page, "page_size": page_size, "total": total, "total_pages": total_pages,
            "has_next": has_next, "items": items}


# 목적: 응답을 JSON 글자로 출력 (한글 그대로)
def print_json(title, data):
    print()
    print("■ " + title)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    print_json("요청 {page: 1} → 응답", handle_garment_list({"page": 1}))
    print_json("요청 {page: 3} (마지막 쪽) → 응답", handle_garment_list({"page": 3}))
    print_json("요청 {brand_id: 1, gender: male, page_size: 2} → 응답",
               handle_garment_list({"brand_id": 1, "gender": "male", "page_size": 2}))
    print_json("요청 {page: 0, page_size: 100} (틀림) → 응답", handle_garment_list({"page": 0, "page_size": 100}))
