"""유니클로 사이즈 추천 앱 (yusuke0127/body-size-pred) + 유니클로 공식 신체 치수표 이미지 2장.
GitHub 커밋 zip 을 받아 sources/uniqlo_body_size_pred 에 풀고, 공식 치수표(남·여 jpg)를 sizechart/ 에 받는다.
입력 성별·나이·키(mm)·체중(kg) → 학습 모델(model.pkl)이 가슴·허리·엉덩이 둘레(mm) 예측 → 사이즈표로 XS~4XL 추천.
학습 데이터(data/data.csv)는 저장소에 없음 (예측 결과 csv 만 있음).
라이선스 없음 → PoC 전용 (치수표 이미지는 유니클로 저작물). API 키 불필요.
실행: python -m fetch.model.uniqlo_body_size_pred
"""
import ast
import re
import sys
from pathlib import Path

from .._common import SOURCES_DIR, get, github_zip, lock_version

NAME = "uniqlo_body_size_pred"
REPO = "yusuke0127/body-size-pred"
LICENSE = "없음 — PoC 전용"
UA = {"User-Agent": "fetch-uniqlo/1.0"}
SIZE_CHARTS = [
    "https://image.uniqlo.com/UQ/ST3/jp/imagesother/sizechart/graph_bodysize_uq_m.jpg",
    "https://image.uniqlo.com/UQ/ST3/jp/imagesother/sizechart/graph_bodysize_uq_w.jpg",
]


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": f"https://github.com/{REPO}", "license": LICENSE}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} 저장소 — 이미 파일 있음")
        info["version"] = lock_version(dest, NAME)
    else:
        sha, _ = github_zip(REPO, dest, UA)
        info["version"] = f"commit {sha}"
    # 공식 치수표 이미지: 파일별로 없을 때만 받는다
    for url in SIZE_CHARTS:
        out = dest / "sizechart" / url.rsplit("/", 1)[1]
        if out.exists():
            print(f"[건너뜀] {out.name} — 이미 있음")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(get(url, UA))
        print(f"[받음] {out.name} ({out.stat().st_size} bytes)")
    info["files"] = sum(1 for p in dest.rglob("*") if p.is_file())
    return info


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    # 1) API 입력: main.py 의 predict() 인자 (코드는 실행하지 않고 텍스트로만 읽는다)
    main_src = (dest / "api" / "main.py").read_text(encoding="utf-8")
    m = re.search(r"def predict\(([^)]*)\)", main_src)
    print(f"== {NAME}")
    print("API GET /predict 입력:", m.group(1) if m else "찾지 못함")
    for line in main_src.splitlines():
        if "/ 10" in line or "pd.DataFrame" in line or '"' in line and ": float(" in line:
            print("   main.py:", line.strip())
    st = dest / "streamlit" / "main.py"
    if st.exists():
        for line in st.read_text(encoding="utf-8").splitlines():
            if "height * 10" in line or "number_input" in line:
                print("   streamlit/main.py:", line.strip())
    print("모델 출력 (main.py 주석): bust_circumference, waist_circumference, hip_circumference (mm)")

    # 2) 사이즈표: size_recommender.py 의 리스트 상수를 ast 로 읽는다
    tree = ast.parse((dest / "api" / "utils" / "size_recommender.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.targets[0].id.endswith("_size_chart"):
            chart = ast.literal_eval(node.value)
            print(f"사이즈표 {node.targets[0].id} ({len(chart)}개, cm):")
            for row in chart:
                print("   ", row)

    # 3) 실제 예측 결과 csv (저장소에 포함된 유일한 표 데이터)
    pred = dest / "predictions" / "predicted-measurements.csv"
    if pred.exists():
        lines = pred.read_text(encoding="utf-8").splitlines()
        print(f"{pred.name}: {len(lines) - 1}행, 헤더 {lines[0]}")
        for line in lines[1:n + 1]:
            print("   ", line)

    # 4) 모델·치수표 이미지 파일 확인
    for p in [dest / "api" / "models" / "model.pkl"] + [dest / "sizechart" / u.rsplit("/", 1)[1] for u in SIZE_CHARTS]:
        if p.exists():
            head = p.read_bytes()[:4]
            if head[:3] == b"\xff\xd8\xff":
                kind = "JPEG"
            elif head == b"\x89PNG":
                kind = "PNG (확장자는 .jpg)"
            elif head[:1] == b"\x80":
                kind = "pickle"
            else:
                kind = repr(head)
            print(f"파일 {p.relative_to(dest)}: {p.stat().st_size} bytes ({kind})")
        else:
            print(f"파일 {p.relative_to(dest)}: 없음")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    print(fetch(dest))
    sample(dest)
