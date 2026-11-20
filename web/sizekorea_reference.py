"""사이즈코리아 인체 실측을 V2 구매자 추천에서 읽는 단위로 준비한다."""
import argparse
import csv
import math
import os
from functools import lru_cache
from pathlib import Path
from tempfile import NamedTemporaryFile


DIMENSIONS = {
    "가슴둘레": "chest_girth", "허리둘레": "waist_girth",
    "엉덩이둘레": "hip_girth", "어깨사이너비": "shoulder_width",
}
WEIGHT_NAMES = ("weight_kg", "체중(kg)", "몸무게(kg)", "체중(몸무게)", "체중", "몸무게")
OUTPUT_FIELDS = ("height_cm", "weight_kg", *(code + "_cm" for code in DIMENSIONS.values()))
# 단위 착오와 손상된 행을 발견하기 위한 넓은 성인 범위. 핏 판단 기준과 별개다.
BOUNDS = {
    "height_cm": (70, 260), "weight_kg": (15, 450),
    "chest_girth": (30, 260), "waist_girth": (25, 280),
    "hip_girth": (35, 280), "shoulder_width": (10, 90),
}


def number(raw, code, line, divisor=1):
    if raw is None or not raw.strip():
        return None
    try:
        value = float(raw)
    except ValueError as error:
        raise ValueError(f"{line}행 {code}의 숫자 형식을 확인하세요.") from error
    if value == 9999:
        return None
    value /= divisor
    lower, upper = BOUNDS[code]
    if not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{line}행 {code}의 값과 단위를 확인하세요.")
    return value


def headers(reader, required):
    names = reader.fieldnames or []
    if len(set(names)) != len(names):
        raise ValueError("중복된 CSV 열 이름이 있습니다.")
    missing = set(required) - set(names)
    if missing:
        raise ValueError("CSV 필수 열 누락: " + ", ".join(sorted(missing)))
    return names


def weight_column(names, explicit):
    options = [explicit] if explicit else WEIGHT_NAMES
    for key in options:
        if key in names:
            return key
    raise ValueError("체중(kg) 열이 필요합니다. 같은 조사자의 HUMAN_ID와 weight_kg가 있는 --weights 파일을 지정하세요.")


def identified_rows(reader):
    seen = set()
    for row in reader:
        key = (row["HUMAN_ID"] or "").strip()
        if not key or key in seen or None in row:
            raise ValueError(f"{reader.line_num}행의 HUMAN_ID가 비었거나 중복되었거나 열 개수가 잘못되었습니다.")
        seen.add(key)
        yield key, row


def prepare(source, destination, weights=None, weight_name=None):
    inputs = [source, weights] if weights else [source]
    if destination.resolve() in [path.resolve() for path in inputs]:
        raise ValueError("출력은 입력 CSV와 다른 경로여야 합니다.")
    external = {}
    if weights:
        with weights.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            key = weight_column(headers(reader, ["HUMAN_ID"]), weight_name)
            for person, row in identified_rows(reader):
                external[person] = number(row[key], "weight_kg", reader.line_num)

    output = []
    no_match = incomplete = 0
    with source.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        names = headers(reader, ["HUMAN_ID", "키"])
        columns = {label: code for label, code in DIMENSIONS.items() if label in names}
        if not columns:
            raise ValueError("지원하는 신체 부위 열이 없습니다.")
        key = None if weights else weight_column(names, weight_name)
        for person, row in identified_rows(reader):
            if weights and person not in external:
                no_match += 1
                continue
            weight = external.pop(person) if weights else number(row[key], "weight_kg", reader.line_num)
            height = number(row["키"], "height_cm", reader.line_num, divisor=10)
            values = {code + "_cm": number(row[label], code, reader.line_num, divisor=10)
                      for label, code in columns.items()}
            if height is None or weight is None or all(x is None for x in values.values()):
                incomplete += 1
                continue
            output.append({"height_cm": height, "weight_kg": weight, **values})
    if not output:
        raise ValueError("키·체중·부위 실측을 함께 사용할 수 있는 사람이 없습니다.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, mode="w", encoding="utf-8", newline="", delete=False) as file:
        temp = Path(file.name)
    try:
        with temp.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(output)
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)
    return len(output), no_match, len(external), incomplete


@lru_cache(maxsize=1)
def _load_profiles(path, modified_ns, size):
    people = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        names = headers(reader, OUTPUT_FIELDS)
        if set(names) != set(OUTPUT_FIELDS):
            raise ValueError("준비된 CSV에는 키·체중·부위 치수 열만 허용합니다.")
        for row in reader:
            height = number(row["height_cm"], "height_cm", reader.line_num)
            weight = number(row["weight_kg"], "weight_kg", reader.line_num)
            measures = {}
            for code in DIMENSIONS.values():
                value = number(row[code + "_cm"], code, reader.line_num)
                if value is not None:
                    measures[code] = value
            if None in row or height is None or weight is None or not measures:
                raise ValueError(f"{reader.line_num}행에 필요한 키·체중·부위 실측을 확인하세요.")
            people[len(people)] = {"height": height, "weight": weight, "measures": measures}
    if not people:
        raise ValueError("준비된 CSV에 유효한 행이 없습니다.")
    return people


def load_profiles(path):
    try:
        path = Path(path).expanduser().resolve()
        stat = path.stat()
        return _load_profiles(path, stat.st_mtime_ns, stat.st_size)
    except (OSError, ValueError, csv.Error) as error:
        raise RuntimeError(f"사이즈코리아 참고 CSV를 읽을 수 없습니다. {error}") from error


def configured_profiles():
    value = os.environ.get("SIZEKOREA_REFERENCE_CSV", "").strip()
    return load_profiles(value) if value else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="HUMAN_ID, 키, 부위 실측(mm)이 있는 CSV")
    parser.add_argument("destination", type=Path, help="키·부위 cm와 체중 kg만 담는 CSV")
    parser.add_argument("--weights", type=Path, help="같은 조사·같은 HUMAN_ID의 체중(kg) CSV")
    parser.add_argument("--weight-column", help="체중(kg) 열 이름")
    args = parser.parse_args()
    try:
        saved, missing, extras, incomplete = prepare(args.source, args.destination, args.weights, args.weight_column)
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(1, f"{error}\n")
    print(f"준비 {saved}명 / 체중 파일 미매칭 {missing}명 / 체중 파일에만 있는 ID {extras}개 / 필수값 결측 {incomplete}명")
