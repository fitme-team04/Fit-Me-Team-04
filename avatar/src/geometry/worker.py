# 역할: Blob의 Blender 기본 신체를 입력 키·ML 치수 28개로 변형하고 GLB로 내보냅니다.
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import numpy as np
from core.contract import FIXED_POSE, SLEEVE_TOLERANCE_DEG
from geometry.deform import solve, points
from geometry.glb import to_gltf
from geometry.measure import analyze
from geometry.glb import export, unpack, pack, body_positions

def generate(job,body):
    fitted, tri, rings, ids, arc, applied = solve("male", job,body=body)
    floor = fitted[:,2].min()
    fitted[:,2] -= floor
    actual, anchors = analyze(fitted,rings,ids,arc)
    for side,label in [(-1,"R"),(1,"L")]:
        wrist = next(loop for tag,s,loop in rings if tag == "wrist" and s == side)
        for tag,position in [("shoulder",fitted[ids["tip",side]]),
                             ("wrist",points(fitted,wrist).mean(0))]:
            anchors.append({"name":f"fit_{tag}_{label}",
                            "translation":to_gltf(position[None,:])[0].tolist()})
    blob = export([("FitMe_Body",fitted,tri)],anchors)
    actual["height_cm"] = float(np.ptp(body_positions(blob)[:,2])*100)
    report = {}
    for key,target in job["male"].items():
        if key == "reference_pose":
            continue
        measured = float(actual[key])
        report[key] = dict(target=target, measured=measured,
                           surface="template",
                           abs_error=None if target is None else abs(measured-target))
    adjustments = {}
    for key,target in job['male'].items():
        if key == 'reference_pose' or target is None or key not in applied:
            continue
        if abs(float(applied[key])-target) > 1e-4:
            report[key]['applied_target'] = float(applied[key])
            adjustments[key] = {'requested':target, 'applied':float(applied[key])}
            print('FITME_ADJUSTMENT '+json.dumps({key:adjustments[key]}), flush=True)
    doc, binary = unpack(blob)
    doc["scenes"][0]["extras"] = {"fitme_measurements":report,"reference_pose":FIXED_POSE["reference_pose"],
        "fitme_pose":dict(FIXED_POSE,sleeve_tolerance_deg=SLEEVE_TOLERANCE_DEG)}
    doc['scenes'][0]['extras']['fitme_adjustments'] = adjustments
    if job.get('prediction_source') == 'example':
        doc['scenes'][0]['extras']['fitme_prediction_source'] = 'example'
    return pack(doc,binary)


def main():
    from geometry.template_copy import request_body
    job=json.load(sys.stdin)
    with request_body() as body:
        blob=generate(job,body)
    with os.fdopen(int(os.environ['FITME_FD']),'wb') as out:
        out.write(blob)

if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print("FITME_INPUT_ERROR "+str(exc), flush=True)
        raise
