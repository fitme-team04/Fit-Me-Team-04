"""팀 사이즈 판정 기준(ease_check)을 불러와 웹앱 데이터에 맞춰 부른다.

판정 기준값(여유분 최소·최대)은 ease_check 한 곳에서만 관리한다. 이 파일과 화면에는 기준 숫자를 두지 않는다.
- 저장소에서 실행: 최상위 ml/ease_check/ease_check.py
- 배포 이미지: /app/ease_check.py (web/Dockerfile 에서 복사)
"""
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_CANDIDATES = (_HERE / "ease_check.py", _HERE.parent / "ml" / "ease_check" / "ease_check.py")
# 웹앱 분류 → ease_check 분류. 하의·원피스는 ease_check 가 판정하지 않는다(2026-11-16 팀 결정).
CATEGORIES = {"상의·아우터": "상의", "상의": "상의", "tops": "상의", "top": "상의"}


def _load():
    for path in _CANDIDATES:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("ease_check", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


ease_check = _load()


def rules_version():
    return getattr(ease_check, "RULES_VERSION", None)


def undetermined(reason, size_label=None):
    """check_all_sizes 와 같은 모양의 '판정할 수 없음' 결과."""
    selected = {"verdict": "UNDETERMINED", "message_ko": "판정할 수 없습니다: " + reason,
                "size_label": size_label, "parts": [], "rules_version": rules_version()}
    return {"selected": selected, "fit_sizes": [], "recommended_size": None, "all_sizes": [],
            "rules_version": rules_version()}


def judge_sizes(category, body_chest, rows, selected_size):
    """한 상품의 사이즈를 ease_check 로 판정한다.

    body_chest : 가슴둘레 cm 숫자 또는 {"value", "lo", "hi"} (판정에는 value 만 쓰인다)
    rows       : ease_check.sizes_from_db_rows 가 받는 가슴단면 행
                 [{"size_label": "M", "region": "KR", "measure_code": "chest_width", "basis": "garment", "value_cm": 53}]
    """
    if ease_check is None:
        return undetermined("판정 모듈(ease_check)을 찾지 못했습니다.", selected_size)
    kind = CATEGORIES.get(str(category).strip(), category)
    try:
        ease_check.normalize_category(kind)
    except ValueError:
        return undetermined("상의만 판정합니다. 이 옷은 아직 판정하지 않습니다.", selected_size)
    sizes = ease_check.sizes_from_db_rows(rows)
    labels = {size["size_label"] for size in sizes}
    result = ease_check.check_all_sizes(kind, {"chest_girth_cm": body_chest}, sizes,
                                        selected_size if selected_size in labels else None)
    if result["selected"] is None:
        result["selected"] = undetermined("이 사이즈는 판정할 가슴단면 실측이 없습니다.", selected_size)["selected"]
    return result
