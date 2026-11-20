# 역할: 실상품 category와 출처별 측정 별칭을 3D 종류·템플릿·소매 기준으로 변환합니다.
CATEGORY_TEMPLATES = {
    '상의': ('crewneck', 'body_center_back_v19'),
    '하의': ('slacks', 'black_midrise_straight_v1'),
}

# These are garment sleeve aliases, never body arm-length measurements.
SLEEVE_ALIASES = {
    'sleeve-length-cb': 'center_back',
    'sleeve-length': 'shoulder',
    '소매길이': 'shoulder',
    'そで丈': 'shoulder',
}


def category_template(category):
    mapping = CATEGORY_TEMPLATES.get(category.strip() if isinstance(category, str) else '')
    if mapping is None:
        raise ValueError('Only category 상의 or 하의 supports 3D generation')
    return mapping


def generation_settings(category, aliases):
    kind, template_id = category_template(category)
    if kind == 'slacks':
        return {'kind': kind, 'template_id': template_id, 'sleeve_basis': 'none'}
    bases = {SLEEVE_ALIASES[name.strip().casefold()] for name in aliases
             if isinstance(name, str) and name.strip().casefold() in SLEEVE_ALIASES}
    if len(bases) != 1:
        raise ValueError('Sleeve measurement basis is missing or ambiguous in ref.measure_aliases')
    return {'kind': kind, 'template_id': template_id, 'sleeve_basis': bases.pop()}
