"""NAVER Anny 3D 인체 파라메트릭 모델의 코드를 받는다 (GitHub naver/anny, 커밋 zip).
입력은 성별·나이·근육·체중·키·비율 등 phenotype 값 (모두 0~1 사이 정규화 값, 기본 0.5).
라이선스: LICENSE 파일 Apache-2.0. 단 README 경고 — 실행 중 내려받는 일부 자산(smplx 토폴로지 등)은 비상업 전용.
torch 는 설치하지 않는다. sample() 은 소스 파일을 파싱해 phenotype 라벨만 보여 준다.
실행: python -m fetch.model.anny
"""
import ast
import sys
from pathlib import Path

from .._common import SOURCES_DIR, github_zip

NAME = "anny"
REPO = "naver/anny"
UA = {"User-Agent": "fetch-anny/1.0"}


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": f"https://github.com/{REPO}", "version": "",
            "license": "Apache-2.0 (README: 일부 자산은 비상업 전용)", "files": 0}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} — 이미 파일 있음: {dest}")
        info["version"] = "로컬 사본 (커밋은 sources.lock.json 참고)"
        info["files"] = sum(1 for p in dest.rglob("*") if p.is_file())
        return info
    sha, files = github_zip(REPO, dest, UA, timeout=120)
    count = len(files)
    info["version"] = f"commit {sha}"
    info["files"] = count
    print(f"[받음] {NAME} — {info['version']} ({count}개 파일)")
    return info


def find_variations(dest: Path):
    # 예전에는 phenotype.py 에, 지금(v0.6.x)은 model_data.py 에 PHENOTYPE_VARIATIONS 가 있다
    for rel in ["src/anny/models/phenotype.py", "src/anny/models/model_data.py"]:
        path = dest / rel
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "PHENOTYPE_VARIATIONS" for t in node.targets):
                call = node.value  # dict(race=[...], gender=[...], ...)
                if isinstance(call, ast.Call):
                    return rel, {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
                return rel, ast.literal_eval(call)
    return None, {}


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    rel, variations = find_variations(dest)
    if not variations:
        print("PHENOTYPE_VARIATIONS 를 찾지 못함")
        return
    print(f"phenotype 정의 위치: {rel}")
    # model_data.py 의 PHENOTYPE_LABELS = race 를 뺀 키 + race 세 값
    labels = [k for k in variations if k != "race"] + variations["race"]
    print(f"PHENOTYPE_LABELS ({len(labels)}개): {labels}")
    print("값 범위: 모두 0~1 (기본 0.5). 각 라벨은 아래 앵커 사이를 선형 보간한다:")
    for key, anchors in variations.items():
        print(f"  {key:12s} {anchors}")
    print("age 앵커만 -1/3~1 (phenotype.py make_phenotype_anchors): newborn=-1/3, baby=0, child=1/3, young=2/3, old=1")
    print("기본(phenotypes='default')에서는 cupsize·firmness·race 3개가 빠짐 → 실제 입력은"
          " gender, age, muscle, weight, height, proportions")
    print("주의: 키(cm)·체중(kg)·나이(세)를 직접 받지 않음 → 실제 값을 0~1 로 바꾸는 변환이 따로 필요")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    fetch(dest)
    sample(dest)
