# 목적: DB 에 접속할 수 없을 때 화면을 끝까지 시연하기 위한 "데모 데이터"
# 주의: 여기 숫자는 시연용 가상 값이다. 실제 유니클로 사이즈표가 아님 (FigJam 시안의 "예시 데이터" 표기와 같은 원칙)
#   - 크루넥T KR M 의 실측(가슴단면 53 · 어깨 46.5 · 총장 69 · 소매 45)만 팀 예시 DB(db/sample/sample_data.sql) 값이고
#     나머지 사이즈는 한 치수씩 늘린 가상 값
#   - DB 가 연결되면 이 파일은 쓰이지 않고, 팀 DB(garment.sizes / garment.measures)의 진짜 값을 씀

# 신체 ↔ 옷 대응 규칙 (팀 db/sql/52_seed_measure_maps.sql 과 같은 값: 단면 × 2 ≈ 둘레)
MEASURE_MAPS = [
    {"body_measure_code": "chest_girth", "garment_measure_code": "chest_width", "factor": 2.00},
    {"body_measure_code": "waist_girth", "garment_measure_code": "waist_width", "factor": 2.00},
    {"body_measure_code": "hip_girth", "garment_measure_code": "hip_width", "factor": 2.00},
    {"body_measure_code": "shoulder_width", "garment_measure_code": "garment_shoulder_width", "factor": 1.00},
    {"body_measure_code": "arm_length", "garment_measure_code": "sleeve_length", "factor": 1.00},
]

# 치수 코드 → 한글 이름 (팀 db/sql/50_seed_measure_definitions.sql 의 일부)
MEASURE_NAMES = {
    "height": "키", "chest_girth": "가슴둘레", "waist_girth": "허리둘레", "hip_girth": "엉덩이둘레",
    "shoulder_width": "어깨너비", "arm_length": "팔길이",
    "body_length": "총장", "chest_width": "가슴단면", "garment_shoulder_width": "어깨너비(옷)",
    "sleeve_length": "소매길이", "waist_width": "허리단면", "hip_width": "엉덩이단면",
}


# 목적: 사이즈표 만들기 도우미 {사이즈: {치수 코드: cm}}
def _table(rows):
    sizes = []
    for label, chest, shoulder, length, sleeve in rows:
        sizes.append({"size_label": label, "garment": {
            "chest_width": chest, "garment_shoulder_width": shoulder,
            "body_length": length, "sleeve_length": sleeve}})
    return sizes


PRODUCTS = [
    {
        "item_code": "E422992-000", "garment_name": "크루넥T", "brand_name": "UNIQLO",
        "category": "상의", "target_gender": "unisex", "source_name": "uniqlo_site", "region": "KR",
        "sizes": _table([
            ("XS", 47.0, 43.5, 65.0, 41.0),
            ("S", 50.0, 45.0, 67.0, 43.0),
            ("M", 53.0, 46.5, 69.0, 45.0),
            ("L", 56.0, 48.0, 71.0, 47.0),
            ("XL", 59.0, 49.5, 73.0, 49.0),
        ]),
    },
    {
        "item_code": "E465187-000", "garment_name": "드라이컬러크루넥T", "brand_name": "UNIQLO",
        "category": "상의", "target_gender": "male", "source_name": "uniqlo_site", "region": "KR",
        "sizes": _table([
            ("S", 51.0, 44.0, 68.0, 20.0),
            ("M", 54.0, 45.5, 70.0, 21.0),
            ("L", 57.0, 47.0, 72.0, 22.0),
            ("XL", 60.0, 48.5, 74.0, 23.0),
        ]),
    },
]


# 목적: 키·체중 → 대략적인 가슴둘레·어깨너비 (데모 전용 단순 식)
# DB 모드에서는 이 식 대신 팀의 k-NN 추정(_추정.py, 실측자 데이터 기반)을 씀.
# 이 식은 정확도 검증을 하지 않은 시연용 값이다.
def estimate_body(gender, height_cm, weight_kg):
    if gender == "female":
        chest = 0.30 * height_cm + 0.55 * weight_kg + 4.0
        shoulder = 0.19 * height_cm + 0.06 * weight_kg + 2.0
    else:
        chest = 0.30 * height_cm + 0.63 * weight_kg
        shoulder = 0.20 * height_cm + 0.07 * weight_kg
    return {"chest_girth": round(chest, 1), "shoulder_width": round(shoulder, 1)}


# db/sample/sample_data.sql의 ANSUR II·BodyM 예시 중 키, 체중, 실측이 모두 있는 행.
# 순서: 키(cm), 체중(kg), 가슴·허리·엉덩이둘레·어깨너비(cm). 계정/성별은 필요하지 않다.
REFERENCE_DIMENSIONS = ("chest_girth", "waist_girth", "hip_girth", "shoulder_width")
SAMPLE_PROFILES = (
    (177.6,  81.5, 107.4,  93.3,  97.9, 40.1),
    (156.0,  65.7,  92.2,  85.0, 101.1, 37.3),
    (160.0,  92.4, 121.8, 110.7, 116.2, None),
    (175.8, 102.8, 114.3, 110.0, 123.1, None),
    (174.8, 106.9, 117.6, 107.8, 119.0, None),
    (172.2,  62.5,  94.1,  77.7,  88.4, 42.9),
    (171.2,  79.1, 100.7,  95.8, 106.3, 39.1),
    (176.9,  75.6,  98.4,  88.7, 100.9, 41.0),
    (171.3,  52.0,  76.6,  65.7,  92.3, 37.2),
    (185.3, 109.4, 114.4, 107.5, 117.5, 45.3),
)
