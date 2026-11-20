# 역할: 실제 브랜드별 사이즈 테이블을 공통 상품·사이즈·의류 단면 데이터로 읽기 전용 변환합니다.
from database.connection import query

BRAND_TABLES = {
    'MUSINSA STANDARD': 'garment.size_musinsa_standard',
    'TOPTEN': 'garment.size_topten',
    'ZIOZIA': 'garment.size_ziozia',
}
COLUMNS = '''category,product_id,product_name,size_label,chest_girth_cm,
    shoulder_width_cm,arm_length_cm,waist_girth_cm,hip_girth_cm,thigh_girth_cm,
    inseam_cm,notes,source_name'''
CATEGORY = {'tops':'상의', 'bottoms':'하의', '상의':'상의', '하의':'하의'}
WIDTHS = {'chest_girth_cm':'chest_width', 'waist_girth_cm':'waist_width',
          'hip_girth_cm':'hip_width', 'thigh_girth_cm':'thigh_width'}


def product(item_code, only_bottoms=False):
    matches = []
    for brand, table in BRAND_TABLES.items():
        category_filter = " AND category='bottoms'" if only_bottoms else ''
        rows = query(f'SELECT {COLUMNS} FROM {table} WHERE product_id=?{category_filter} ORDER BY size_label', (item_code,))
        if only_bottoms:
            rows = [row for row in rows if row['category']=='bottoms']
        if rows:
            matches.append((brand, rows))
    if len(matches)>1:
        raise ValueError('Product code is ambiguous across brand tables')
    return matches[0] if matches else (None, [])


def catalog():
    result = []
    for brand,table in BRAND_TABLES.items():
        rows = query(f'''SELECT category,product_id,product_name,source_name,
            COUNT(*) AS size_count FROM {table} WHERE category='bottoms'
            GROUP BY category,product_id,product_name,source_name ORDER BY product_id''')
        for row in rows:
            if row['category']!='bottoms':
                continue
            result.append({'item_code':row['product_id'],'garment_name':row['product_name'],
                           'category':CATEGORY.get(row['category'],row['category']),
                           'brand_name':brand,'source_name':row['source_name'],
                           'size_count':row['size_count'],'selection_mode':'item_code_size_label'})
            result[-1]['supports_3d'] = row['category'] in ('bottoms','하의')
    return result


def spec_from_row(row):
    spec = {target:float(row[source])/2 for source,target in WIDTHS.items() if row.get(source) is not None}
    for source,target in (('shoulder_width_cm','garment_shoulder_width'),
                          ('arm_length_cm','sleeve_length'),('inseam_cm','inseam')):
        if row.get(source) is not None:
            spec[target] = float(row[source])
    # 실제 DB에는 총장이 없습니다. notes의 추정·계산 근거를 실제 실측값으로 대체하지 않습니다.
    return spec


def measure_rows(rows):
    return [{'size_label':row['size_label'],'region':'KR','basis':'garment',
             'measure_code':code,'value_cm':value}
            for row in rows for code,value in spec_from_row(row).items()]
