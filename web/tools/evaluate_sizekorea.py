"""V2와 같은 추정식으로 학습용 표본과 분리된 사람의 인체 치수를 평가한다."""
import argparse
import math
import random
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sizekorea_reference import DIMENSIONS, load_profiles
from team_bridge import estimate_parts


def evaluate(people, seed):
    if len(people) < 4:
        raise ValueError("평가자와 최소 3명의 참고 표본을 분리할 수 있는 자료가 필요합니다.")
    keys = list(people)
    random.Random(seed).shuffle(keys)
    held_out = max(1, math.floor(len(keys) * 0.2))
    training = {key: people[key] for key in keys[held_out:]}
    observed = {code: 0 for code in DIMENSIONS.values()}
    errors = {code: [] for code in DIMENSIONS.values()}
    for key in keys[:held_out]:
        person = people[key]
        predicted, _, _ = estimate_parts(training, person["height"], person["weight"])
        for code, actual in person["measures"].items():
            observed[code] += 1
            if code in predicted:
                errors[code].append(abs(actual - predicted[code]))
    return held_out, observed, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path, help="준비된 인체 참고 CSV")
    parser.add_argument("--seed", type=int, default=2021)
    args = parser.parse_args()
    try:
        people = load_profiles(args.reference)
        count, observed, errors = evaluate(people, args.seed)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    print(f"참고 표본 {len(people)-count}명 / 분리한 평가 표본 {count}명 / seed {args.seed}")
    print("부위 | 평가 실측 수 | 추정 수 | 보류 수 | 평균절대오차(cm)")
    for label, code in DIMENSIONS.items():
        diffs = errors[code]
        mae = f"{mean(diffs):.2f}" if diffs else "—"
        print(f"{label} | {observed[code]} | {len(diffs)} | {observed[code]-len(diffs)} | {mae}")
