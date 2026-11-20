# 역할: 옷의 전체 질량을 정점 질량으로 변환하고 Cloth 결과를 판정합니다.
"""Numerical acceptance limits; never resize a DB-sized garment to force a fit."""
import math
import os

MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_EDGE_STRETCH = 1.005  # 0.5% numerical tolerance, not a stretch allowance for fit.
FRAMES = 72
SOFT_BUDGET_SECONDS = 180


def mass_settings(kind, vertex_count, environment=None):
    """Preview defaults are not measured fabric properties. Unit: kilograms."""
    defaults={'crewneck':.2,'slacks':.5}
    if kind not in defaults:
        raise ValueError('Unsupported cloth mass kind')
    if type(vertex_count) is not int or vertex_count <= 0:
        raise ValueError('Invalid cloth vertex count')
    environment=os.environ if environment is None else environment
    key='CLOTH_'+kind.upper()+'_TOTAL_MASS_KG'
    value=environment.get(key,defaults[kind])
    if type(value) not in (str,int,float):
        raise ValueError('Invalid '+key)
    try: total=float(value)
    except (TypeError,ValueError) as exc:
        raise ValueError('Invalid '+key) from exc
    if not math.isfinite(total) or not .01 <= total <= 5.:
        raise ValueError(key+' must be between 0.01 and 5 kg')
    return {'total_mass_kg':total,'vertex_mass_kg':total/vertex_count,
            'vertex_count':vertex_count,'distribution':'uniform_per_vertex',
            'source':'configured' if key in environment else 'preview_default'}


def stop_reason(frame, stable_frames, elapsed, max_stretch, finite=True):
    if not finite:
        return 'non_finite_simulation'
    if max_stretch > 1.15:
        return 'simulation_diverged'
    if elapsed >= SOFT_BUDGET_SECONDS:
        return 'simulation_timeout'
    if frame >= 12 and stable_frames >= 5:
        return 'settled'
    return None


def validate_simulation(rest_lengths, final_lengths, movement_m, penetration_m, *, stable_frames=None, mesh_quality=None, body_intersections=None):
    if not rest_lengths or len(rest_lengths) != len(final_lengths):
        raise ValueError('Invalid cloth edge topology')
    if any(not math.isfinite(v) or v <= 0 for v in (*rest_lengths, *final_lengths)):
        raise ValueError('Non-finite or collapsed cloth edges')
    stretch = max(b/a for a, b in zip(rest_lengths, final_lengths))
    if not math.isfinite(movement_m) or not math.isfinite(penetration_m):
        raise ValueError('Non-finite cloth quality measurements')
    reasons = []
    compression = min(b/a for a,b in zip(rest_lengths,final_lengths))
    if compression < .98:
        reasons.append('compression_exceeded')
    if stable_frames is not None and stable_frames < 5:
        reasons.append('unsettled')
    if mesh_quality is not None and not mesh_quality['valid']:
        reasons.append('invalid_cloth_mesh')
    if body_intersections is not None:
        if body_intersections['crossing_pairs']:
            reasons.append('body_penetration')
        if not body_intersections['validation_complete']:
            reasons.append('validation_incomplete')
    if stretch > MAX_EDGE_STRETCH:
        reasons.append('stretch_exceeded')
    if movement_m > .002:
        reasons.append('unsettled')
    if penetration_m > .001:
        reasons.append('body_penetration')
    reasons=list(dict.fromkeys(reasons))
    return {'status':'failed' if reasons else 'passed', 'failure_reasons':reasons,
            'min_edge_length_ratio':compression,'stable_frames':stable_frames,
            'mesh_quality':mesh_quality,'body_intersections':body_intersections,
            'max_edge_stretch_ratio':stretch, 'last_frame_max_movement_m':movement_m,
            'sampled_max_penetration_m':penetration_m,
            'edge_stretch_tolerance_ratio':MAX_EDGE_STRETCH}
