# 역할: GLB에서 신체·상의·하의 정렬 앵커와 피팅 메타데이터를 읽습니다.
import json
import struct

def extract(glb, kind):
    length, chunk = struct.unpack_from("<I4s", glb, 12)
    if chunk != b"JSON":
        raise ValueError("Missing glTF JSON chunk")
    doc = json.loads(glb[20:20+length])
    nodes = doc["nodes"]
    root_id, = doc["scenes"][doc["scene"]]["nodes"]
    root = nodes[root_id]
    fitting = doc["scenes"][doc["scene"]].get("extras", {}).get("fitme_garment", {})
    if kind == "garments" and fitting.get("kind") == "slacks":
        if fitting.get("fit_anchor") != "fit_anchor_waist":
            raise ValueError("Slacks must use the waist anchor")
        expected = {"fit_anchor_waist", "fit_crotch", "fit_hem_L", "fit_hem_R"}
    else:
        if kind == "garments" and fitting.get("kind", "crewneck") != "crewneck":
            raise ValueError("Unsupported garment fitting contract")
        expected = {"fit_anchor", "fit_anchor_waist"} if kind == "avatars" else {"fit_anchor"}
        end = "wrist" if kind == "avatars" else "cuff"
        expected.update(f"fit_{tag}_{side}" for tag in ("shoulder",end) for side in ("L","R"))
    anchors = {}
    optional = {'fit_neck_L','fit_neck_R'} if kind == 'avatars' else set()
    for index in root["children"]:
        node = nodes[index]
        name = node.get("name")
        if name not in expected | optional:
            continue
        if name in anchors or "matrix" in node:
            raise ValueError("Unexpected anchor representation")
        anchors[name] = {"translation":node.get("translation",[0,0,0]),
                         "rotation":node.get("rotation",[0,0,0,1]),
                         "scale":node.get("scale",[1,1,1])}
    if not expected <= anchors.keys():
        raise ValueError("Missing required fitting anchors")
    report = doc["scenes"][doc["scene"]].get("extras", {}).get("fitme_measurements", {})
    return root["name"], anchors, report


def garment_fitting(glb):
    length = struct.unpack_from("<I", glb, 12)[0]
    doc = json.loads(glb[20:20+length])
    return doc["scenes"][doc["scene"]].get("extras", {}).get("fitme_garment", {})
