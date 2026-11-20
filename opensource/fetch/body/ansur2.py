"""ANSUR II (2012 미군 인체측정 조사) 공개본을 받는다.
출처: Penn State OpenLab https://tools.openlab.psu.edu/publicData/
파일: 남성 CSV(4,082명), 여성 CSV(1,986명), 측정 정의서 ANSURII-TR15-007.pdf
라이선스: 명시 없음 ("approved for public release" 공개 승인 자료)
단위: 치수 mm, weightkg 는 이름과 달리 0.1kg(헥토그램) 단위 → 10 으로 나눠야 kg
실행: python -m fetch.body.ansur2
"""
import csv
import hashlib
import sys
from pathlib import Path

from .._common import SOURCES_DIR, get

NAME = "ansur2"
BASE_URL = "https://tools.openlab.psu.edu/publicData/"
FILES = ["ANSUR_II_MALE_Public.csv", "ANSUR_II_FEMALE_Public.csv", "ANSURII-TR15-007.pdf"]

# 3D 몸 모델에 쓸 치수 (모두 mm)
MEASURES = [
    "chestcircumference", "waistcircumference", "buttockcircumference",
    "biacromialbreadth", "waistbacklength", "sleeveoutseam", "crotchheight",
    "thighcircumference", "calfcircumference", "anklecircumference",
    "chestheight", "waistheightomphalion", "buttockheight",
    "chestbreadth", "chestdepth", "waistbreadth", "waistdepth", "hipbreadth", "buttockdepth",
]


def fetch(dest: Path) -> dict:
    dest = Path(dest)
    info = {"name": NAME, "source": BASE_URL, "version": "공개 파일 (버전 표기 없음, sha256 으로 고정)",
            "license": "명시 없음 (approved for public release)", "files": []}
    if dest.exists() and any(dest.iterdir()):
        print(f"[건너뜀] {NAME} — 이미 파일 있음: {dest}")
        for p in sorted(dest.iterdir()):
            if p.is_file():
                info["files"].append({"path": p.name, "bytes": p.stat().st_size})
        return info
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        data = get(BASE_URL + name, {"User-Agent": "fetch-ansur2/1.0"}, timeout=120)
        (dest / name).write_bytes(data)
        info["files"].append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        print(f"[받음] {name} ({len(data):,} bytes)")
    return info


def read_rows(path: Path) -> list:
    # 원본은 latin-1 문자가 섞여 있어 utf-8 로 읽으면 실패할 수 있음
    with open(path, encoding="latin-1", newline="") as f:
        return list(csv.DictReader(f))


def sample(dest: Path, n: int = 3) -> None:
    dest = Path(dest)
    male = read_rows(dest / "ANSUR_II_MALE_Public.csv")
    female = read_rows(dest / "ANSUR_II_FEMALE_Public.csv")
    print(f"행 수: 남성 {len(male):,}명, 여성 {len(female):,}명, 열 {len(male[0])}개")

    # weightkg 단위 검증: weightkg/10 과 Weightlbs*0.4536 비교 (Weightlbs 는 본인 신고값)
    diffs = []
    for row in male + female:
        try:
            diffs.append(int(row["weightkg"]) / 10 - float(row["Weightlbs"]) * 0.45359237)
        except (ValueError, KeyError):
            pass
    diffs.sort()
    median = diffs[len(diffs) // 2]
    print(f"weightkg 단위 검증 ({len(diffs):,}명): (weightkg/10) - (Weightlbs x 0.4536) 중앙값 {median:+.2f} kg"
          f" → weightkg 는 0.1kg 단위 (Weightlbs 는 자기 신고값이라 약간 차이 있음)")

    people = male[:2] + female[:1]
    for row in people[:n]:
        wkg = int(row["weightkg"]) / 10
        lbs_kg = float(row["Weightlbs"]) * 0.45359237
        print(f"\n--- {row['Gender']} {row['Age']}세 (subjectid {row.get('subjectid') or row.get('SubjectId')}) ---")
        print(f"  stature {int(row['stature']) / 10:.1f} cm (신고 키 {row['Heightin']} in = {float(row['Heightin']) * 2.54:.1f} cm)")
        print(f"  weightkg 원값 {row['weightkg']} → {wkg:.1f} kg (신고 Weightlbs {row['Weightlbs']} lb = {lbs_kg:.1f} kg)")
        for col in MEASURES:
            print(f"  {col:24s} {int(row[col]) / 10:6.1f} cm")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    dest = SOURCES_DIR / NAME
    fetch(dest)
    sample(dest)
