# 목적: 옷 한 벌 → 사이즈별 옷 실측(basis = garment) + 권장 신체 범위(basis = body) → 옷 3D 모델 입력 JSON
# 누가 쓰나: 3D (브랜드별 옷 목록은 공통/브랜드/2_심화/01_브랜드별_옷_목록.py)
# 난이도: 심화 — 2~3개 표 LEFT JOIN (치수 없는 사이즈도 보이게) + 파이썬으로 사이즈별 묶기 → JSON
# 출력: 옷 2벌(UNIQLO 12행·musinsa 4행) 사이즈별 치수 표 + 3D 입력 JSON(sizes 등); --save 면 out/3d/garment_*.json
# 실행: .venv/bin/python db/예시_코드/3d/2_심화/07_옷_사이즈별_치수_JSON.py            (JSON 은 화면에 출력)
#       .venv/bin/python db/예시_코드/3d/2_심화/07_옷_사이즈별_치수_JSON.py --save     (out/3d/garment_<source>_<item>.json 으로도 저장)
# JSON 은 옷 3D 모델(패턴·드레이핑)에 넣을 사이즈별 치수. 단위 cm. 단면(width)은 옷을 펼쳐 잰 너비
import json
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → 3d → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show, save_text


# 목적: 옷 한 벌의 정보 (브랜드가 없는 출처도 있어 LEFT JOIN)
def garment_info(source_name, item_code):
    sql = """
        SELECT g.garment_id, b.brand_name, g.source_name, g.item_code, g.garment_name,
               g.category, g.target_gender, g.fit
        FROM garment.garments AS g
        LEFT JOIN garment.brands AS b ON b.brand_id = g.brand_id
        WHERE g.source_name = %s AND g.item_code = %s
    """
    rows = query(sql, (source_name, item_code))
    if len(rows) == 0:
        return None
    return rows[0]


# 목적: 옷 한 벌의 사이즈별 치수 행 (치수 없는 사이즈도 보이도록 LEFT JOIN)
def size_measures(garment_id):
    sql = """
        SELECT s.size_id, s.size_label, s.region,
               gm.basis, gm.measure_code, d.korean_name, gm.value_cm, gm.low_cm, gm.high_cm
        FROM garment.sizes AS s
        LEFT JOIN garment.measures AS gm ON gm.size_id = s.size_id
        LEFT JOIN ref.measure_definitions AS d ON d.measure_code = gm.measure_code
        WHERE s.garment_id = %s
        ORDER BY s.region, s.size_id, gm.basis DESC, gm.measure_code
    """
    return query(sql, (garment_id,))


# 목적: DB 값(Decimal) → float (NULL 은 None)
def to_number(value):
    if value is None:
        return None
    return float(value)


# 목적: 옷 한 벌 → 3D 팀용 dict. 치수가 있는 사이즈는 sizes 에, 없는 사이즈는 이름만 sizes_without_measures 에
def garment_dims(source_name, item_code, verbose=True):
    info = garment_info(source_name, item_code)
    if info is None:
        print("  (" + source_name + " / " + item_code + " 옷 없음)")
        return None
    rows = size_measures(info["garment_id"])

    sizes = []
    by_id = {}
    order = []
    for row in rows:
        sid = row["size_id"]
        if sid not in by_id:
            by_id[sid] = {"size_label": row["size_label"], "region": row["region"],
                          "garment": {}, "body_range": {}}
            order.append(sid)
        if row["basis"] == "garment":
            by_id[sid]["garment"][row["measure_code"]] = to_number(row["value_cm"])
        if row["basis"] == "body":
            by_id[sid]["body_range"][row["measure_code"]] = [to_number(row["low_cm"]), to_number(row["high_cm"])]

    empty = []
    for sid in order:
        item = by_id[sid]
        if len(item["garment"]) == 0 and len(item["body_range"]) == 0:
            empty.append(item["size_label"] + "(" + item["region"] + ")")
        else:
            sizes.append(item)

    data = {
        "brand_name": info["brand_name"],
        "source_name": info["source_name"],
        "item_code": info["item_code"],
        "garment_name": info["garment_name"],
        "category": info["category"],
        "target_gender": info["target_gender"],
        "fit": info["fit"],
        "unit": "cm",
        "sizes": sizes,
        "sizes_without_measures": empty,
    }

    if verbose:
        table = []
        for row in rows:
            if row["basis"] is not None:
                table.append({"size_label": row["size_label"], "region": row["region"],
                              "basis": row["basis"], "measure_code": row["measure_code"],
                              "korean_name": row["korean_name"], "value_cm": row["value_cm"],
                              "low_cm": row["low_cm"], "high_cm": row["high_cm"]})
        show("사이즈별 치수 (" + source_name + " / " + item_code + ")", table)
        if len(empty) > 0:
            print("  · 치수 자료가 없는 사이즈: " + ", ".join(empty))
    return data


# 목적: 실행 예시 하나: 표 → JSON 출력 → (--save 면) 파일 저장
def demo(source_name, item_code, save):
    data = garment_dims(source_name, item_code)
    if data is None:
        return
    text = json.dumps(data, ensure_ascii=False, indent=2)
    print()
    print("■ 옷 3D 입력 JSON (" + source_name + " / " + item_code + ")")
    print(text)
    if save:
        path = save_text("3d/garment_" + source_name + "_" + item_code + ".json", text)
        print("  → 저장: " + str(path))


if __name__ == "__main__":
    save = "--save" in sys.argv
    # UNIQLO 크루넥T: KR M · US M 에 옷 실측 4개 + 권장 범위 2개
    demo("uniqlo_site", "E422992-000", save)
    # COVERNAT 티셔츠(무신사 출처): KR M 에 옷 실측 4개
    demo("musinsa_ml_project", "1848166", save)
