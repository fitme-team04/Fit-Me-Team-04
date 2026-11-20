"""소스 모듈 목록. 각 모듈: NAME, fetch(dest) -> dict, sample(dest, n=3).
사용: from fetch import SOURCES   (받은 결과는 sources/sources.lock.json 에 자동 기록, 표 보기: python -m fetch.manifest)
"""


def __getattr__(name):
    # SOURCES 를 쓸 때만 모듈을 불러온다.
    # (맨 위에서 import 하면 python -m fetch.<그룹>.<모듈> 실행 때마다 RuntimeWarning 이 뜬다)
    if name != "SOURCES":
        raise AttributeError(name)
    from .body import ansur2, bodym, nhanes
    from .fit import musinsa_ml_project, uniqlo_size_predictor, uniqlo_size_recommendation
    from .garment import kobo_garment_measurements, oh_my_measure, uniqlo_garment_json, uniqlo_site, zozotown_page
    from .model import anny, clad_body, uniqlo_body_size_pred
    from .manifest import wrap
    sources = [
        # garment: 옷 치수
        kobo_garment_measurements, oh_my_measure, uniqlo_garment_json, uniqlo_site, zozotown_page,
        # fit: 신체 ↔ 구매 사이즈 짝
        uniqlo_size_predictor, uniqlo_size_recommendation, musinsa_ml_project,
        # body: 신체 치수
        ansur2, bodym, nhanes,
        # model: 코드·모델
        clad_body, uniqlo_body_size_pred, anny,
    ]
    for module in sources:
        wrap(module)  # fetch() 가 끝나면 sources/sources.lock.json 을 갱신 (manifest.py)
    return sources
