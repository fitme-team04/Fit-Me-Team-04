# 역할: SAM 신체와 투영 가이드에 동일 배율 키 보정을 적용합니다.
"""Uniform height normalization shared by the SAM mesh and its landmarks."""
import math


def height_transform(vertices, height_cm):
    if type(height_cm) not in (int, float) or not math.isfinite(height_cm) or height_cm <= 0:
        raise ValueError('Invalid requested height')
    if len(vertices) < 3 or any(len(point) != 3 or any(not math.isfinite(v) for v in point)
                                for point in vertices):
        raise ValueError('Invalid SAM vertices')
    floor = min(point[2] for point in vertices)
    span = max(point[2] for point in vertices)-floor
    if span <= 0:
        raise ValueError('SAM surface has no height')
    return height_cm/100/span, floor


def normalize_points(points, scale, floor):
    return [[x*scale, y*scale, (z-floor)*scale] for x,y,z in points]
