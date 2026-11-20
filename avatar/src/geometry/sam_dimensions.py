# 역할: 대응된 기준 영역을 안내로 삼아 실제 SAM 삼각형 단면에서 11개 치수를 측정합니다.
import numpy as np
from geometry.deform import sections, points, perimeter, arc_points


def measure_dimensions(vertices, faces, guides, rings, arc):
    height = float(np.ptp(vertices[:, 2]))
    floor = float(vertices[:, 2].min())
    if not np.isfinite(vertices).all() or height <= 0:
        raise ValueError('Invalid SAM surface')
    centers = {(name, side): points(guides, loop).mean(0) for name, side, loop in rings}
    hip = centers['hip', 0]
    middle = hip[0]

    def contour(origin, normal, side=None):
        normal = np.asarray(normal, dtype=float)
        length = np.linalg.norm(normal)
        if not np.isfinite(length) or length <= 0:
            raise ValueError('Invalid SAM section axis')
        normal /= length
        candidates = []
        for loop in sections(vertices, faces, origin, normal):
            q = points(vertices, loop)
            if not np.isfinite(q).all() or perimeter(q) <= 0:
                continue
            if side == 0 and not q[:, 0].min() < middle < q[:, 0].max():
                continue
            if side in (-1, 1) and np.min(side * (q[:, 0]-middle)) < -height*.003:
                continue
            candidates.append(q)
        if not candidates:
            raise ValueError('No isolated SAM section in the requested body region')
        return min(candidates, key=lambda q: np.linalg.norm(q.mean(0)-origin))

    def scan(start, stop, normal, side, largest):
        candidates = []
        for amount in np.linspace(0, 1, 21):
            origin = np.asarray(start)*(1-amount) + np.asarray(stop)*amount
            try:
                q = contour(origin, normal, side)
                candidates.append((float(perimeter(q)), q))
            except ValueError:
                continue
        if len(candidates) < 3:
            raise ValueError('Insufficient valid SAM sections; no template fallback is allowed')
        return (max if largest else min)(candidates, key=lambda item: item[0])

    def optional(measure):
        try:
            return measure()
        except (ValueError, FloatingPointError, np.linalg.LinAlgError):
            return None

    def find_crotch():
        crotch_guide = float(arc_points(guides, arc)[:, 2].min())
        central = []
        origin = hip.copy(); origin[0] += height*.0002
        for loop in sections(vertices, faces, origin, np.array([1., 0., 0.])):
            q = points(vertices, loop)
            bottom = float(q[:, 2].min())
            if abs(bottom-crotch_guide) < height*.12 and q[:, 2].max() > hip[2]:
                central.append(bottom)
        if not central:
            raise ValueError('Cannot identify SAM crotch section')
        return min(central, key=lambda z: abs(z-crotch_guide))

    crotch = optional(find_crotch)
    result = {key: None for key in (
        'inseam_cm', 'hip_girth_cm', 'hip_width_cm', 'hip_depth_cm', 'hip_line_height_cm')}
    result['height_cm'] = height*100
    result['inseam_cm'] = None if crotch is None else (crotch-floor)*100

    def measure_hip():
        low = hip.copy(); low[2] = (hip[2]+crotch)/2
        high = hip.copy(); high[2] = (hip[2]+centers['belly', 0][2])/2
        girth, q = scan(low, high, np.array([0., 0., 1.]), 0, True)
        return {
            'hip_girth_cm': girth*100,
            'hip_width_cm': float(np.ptp(q[:, 0]))*100,
            'hip_depth_cm': float(np.ptp(q[:, 1]))*100,
            'hip_line_height_cm': (float(q[:, 2].mean())-floor)*100,
        }

    if crotch is not None:
        hip_values = optional(measure_hip)
        if hip_values is not None:
            result.update(hip_values)
    bilateral = {name: [] for name in ('ankle', 'calf', 'knee', 'thigh', 'upper_arm', 'wrist')}
    for side in (-1, 1):
        ankle, calf, knee, thigh = [centers[name, side] for name in ('ankle', 'calf', 'knee', 'thigh')]
        leg_axis = knee-ankle
        bilateral['ankle'].append(optional(lambda: scan(ankle-(calf-ankle)*.08, ankle+(calf-ankle)*.08, leg_axis, side, False)[0]))
        bilateral['calf'].append(optional(lambda: scan(ankle+leg_axis*.1, knee-leg_axis*.1, leg_axis, side, True)[0]))
        bilateral['knee'].append(optional(lambda: float(perimeter(contour(knee, leg_axis, side)))))
        thigh_top = thigh.copy()
        if crotch is None:
            bilateral['thigh'].append(None)
        else:
            thigh_top[2] = max(thigh[2]+height*.005, crotch-height*.01)
            bilateral['thigh'].append(optional(lambda: scan(thigh, thigh_top, thigh-knee, side, True)[0]))
        upper, wrist = centers['upper_arm', side], centers['wrist', side]
        # 고정 A 포즈의 팔 축을 기준으로 어깨·손을 제외한 영역만 탐색합니다.
        arm_axis = wrist-upper
        bilateral['upper_arm'].append(optional(lambda: scan(upper-arm_axis*.15, upper+arm_axis*.15, arm_axis, side, True)[0]))
        bilateral['wrist'].append(optional(lambda: scan(wrist-arm_axis*.04, wrist+arm_axis*.04, arm_axis, side, False)[0]))
    result.update({name+'_girth_cm': None if any(v is None for v in values) else float(np.mean(values))*100
                   for name, values in bilateral.items()})
    return result
