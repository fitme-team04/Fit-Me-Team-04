# 역할: SAM 신체에 맞춘 의류 프로파일 보간과 방사 윤곽의 제한 변형을 계산합니다.
import math
from bisect import bisect_right


def _finite_number(value, label):
    if isinstance(value,(bool,str,bytes)):
        raise ValueError('Invalid '+label)
    try:
        result=float(value)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid '+label) from exc
    if not math.isfinite(result):
        raise ValueError('Non-finite '+label)
    return result


def bounded_radial_ratio(ratio, amplitude=.02):
    """Retain small source radial folds within a positive target-radius band.

    The input is dimensionless source radius / source reference radius. This
    does not size from DB measurements or change the target SAM radius itself.
    """
    ratio=_finite_number(ratio,'radial ratio')
    amplitude=_finite_number(amplitude,'radial amplitude')
    if ratio < 0 or not 0 < amplitude < 1:
        raise ValueError('Invalid radial ratio or amplitude')
    return 1+amplitude*math.tanh((ratio-1)/amplitude)


def interpolate_profile(level, levels, samples):
    """Interpolate equal-dimensional samples; keep endpoint values outside range.

    Levels must increase strictly. A single sample provides a constant profile.
    Sample components can hold centers, radii or other scalar profile values.
    """
    level=_finite_number(level,'profile level')
    try:
        levels=tuple(_finite_number(v,'profile knot') for v in levels)
        samples=tuple(tuple(_finite_number(v,'profile sample') for v in sample) for sample in samples)
    except TypeError as exc:
        raise ValueError('Invalid profile arrays') from exc
    if not levels or len(levels) != len(samples):
        raise ValueError('Mismatched or empty profile arrays')
    if not samples[0] or any(len(sample) != len(samples[0]) for sample in samples):
        raise ValueError('Mismatched profile sample dimensions')
    if any(a >= b for a,b in zip(levels,levels[1:])):
        raise ValueError('Profile levels must increase strictly')
    if level <= levels[0]: return samples[0]
    if level >= levels[-1]: return samples[-1]
    right=bisect_right(levels,level); left=right-1
    # Normalization avoids overflow for finite knots on opposite large scales.
    scale=max(1.,abs(level),abs(levels[left]),abs(levels[right]))
    amount=(level/scale-levels[left]/scale)/(levels[right]/scale-levels[left]/scale)
    return tuple(a*(1-amount)+b*amount for a,b in zip(samples[left],samples[right]))
