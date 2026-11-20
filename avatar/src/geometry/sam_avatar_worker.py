# 역할: SAM 실제 메시를 표시·충돌용 GLB와 앵커·측정 보고서로 내보냅니다.
"""Export the actual canonical SAM surface as the displayed/collision avatar."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from core.contract import FIXED_POSE, SLEEVE_TOLERANCE_DEG
from core.sam_surface import height_transform, normalize_points
from geometry.sam_measure_worker import load_surface
from geometry.measure import analyze
from geometry.deform import sections, points, perimeter
from geometry.glb import export, pack, unpack, to_gltf


def build_avatar(surface_path, height_cm, prediction=None):
    prediction = prediction or {}
    with np.load(surface_path,allow_pickle=False) as surface:
        photo_validation=(json.loads(str(surface['photo_validation_json']))
                          if 'photo_validation_json' in surface else None)
    actual, faces, projected, rings, ids, arc = load_surface(surface_path)
    scale, floor = height_transform(actual, height_cm)
    actual = np.asarray(normalize_points(actual, scale, floor))
    projected = np.asarray(normalize_points(projected, scale, floor))
    # Projected guides provide measurements/anchors only. The exported vertices
    # and faces below belong to SAM, not to the control template.
    measured, anchors = analyze(projected, rings, ids, arc, floor_override=0.)
    sources = {key:'sam_projected_landmarks' for key in measured}
    measured['height_cm'] = float(np.ptp(actual[:,2])*100)
    sources['height_cm'] = 'sam_surface'
    diagnostics = []; section_diagnostics={}
    for region in ('chest', 'waist', 'hip'):
        loop = next(loop for name, side, loop in rings if name == region and side == 0)
        origin = points(projected, loop).mean(0)
        contours = [points(actual, loop) for loop in
                    sections(actual, faces, origin, np.array([0.,0.,1.]))]
        contours = [q for q in contours if q[:,0].min() < origin[0] < q[:,0].max()]
        if not contours:
            diagnostics.append(region+'_section_unavailable')
            section_diagnostics[region]={'status':'unavailable','guide_origin_m':origin.tolist()}
            continue
        q = min(contours, key=lambda q: np.linalg.norm(q.mean(0)-origin))
        section_diagnostics[region]={
            'status':'measured','guide_origin_m':origin.tolist(),
            'guide_girth_cm':float(perimeter(points(projected,loop))*100),
            'selected_center_m':q.mean(0).tolist(),
            'candidates':[{'girth_cm':float(perimeter(c)*100),'center_m':c.mean(0).tolist(),
                           'width_cm':float(np.ptp(c[:,0])*100),'depth_cm':float(np.ptp(c[:,1])*100)}
                          for c in contours]}
        values = {region+'_girth_cm':perimeter(q)*100,
                  region+'_width_cm':np.ptp(q[:,0])*100,
                  region+'_depth_cm':np.ptp(q[:,1])*100,
                  region+'_line_height_cm':q[:,2].mean()*100}
        measured.update(values)
        sources.update({key:'sam_surface_at_projected_height' for key in values})
    for side,label in [(-1,'R'),(1,'L')]:
        wrist = next(loop for name,s,loop in rings if name == 'wrist' and s == side)
        for tag,position in [('shoulder',projected[ids['tip',side]]),
                             ('neck',projected[ids['neck',side]]),
                             ('wrist',points(projected,wrist).mean(0))]:
            anchors.append({'name':f'fit_{tag}_{label}',
                            'translation':to_gltf(position[None,:])[0].tolist()})
    # target = ML 예측값(FITME_ML_MEASUREMENTS=on 일 때만), measured = SAM 메시에서 잰 값.
    report = {key:{'target':height_cm if key == 'height_cm' else prediction.get(key),
                   'measured':float(value), 'surface':sources[key],
                   'abs_error':abs(float(value)-height_cm) if key == 'height_cm' else None}
              for key,value in measured.items()}
    doc, binary = unpack(export([('FitMe_Body',actual,faces)],anchors))
    doc['scenes'][0]['extras'] = {
        'fitme_measurements':report, 'body_geometry_source':'sam_surface',
        'measurement_target_source':'azure_ml' if prediction else None,
        **({'photo_validation':photo_validation} if photo_validation is not None else {}),
        'reference_pose':FIXED_POSE['reference_pose'],
        'fitme_pose':dict(FIXED_POSE,sleeve_tolerance_deg=SLEEVE_TOLERANCE_DEG),
        'sam_geometry':{'uniform_scale':scale, 'vertices':len(actual), 'triangles':len(faces),
                        'measurement_diagnostics':diagnostics,
                        'section_diagnostics':section_diagnostics,
                        'control_template_use':'measurement_landmarks_only'}}
    return pack(doc,binary)


if __name__ == '__main__':
    try:
        job = json.load(sys.stdin)
        data = build_avatar(job['surface_path'],job['height_cm'],job.get('male'))
        with os.fdopen(int(os.environ['FITME_FD']),'wb') as output:
            output.write(data)
    except (ValueError, KeyError) as exc:
        print('FITME_INPUT_ERROR '+str(exc),flush=True)
        raise
