# 역할: 시간 초과 시 저장된 옷 GLB에 실패 상태를 기록합니다.
"""Preserve a complete last-frame GLB; never publish partially written bytes."""
import json
import struct


def interrupted_preview(data, reason, details=None):
    if len(data) < 28 or data[:4] != b'glTF' or struct.unpack_from('<I', data, 8)[0] != len(data):
        raise ValueError('Invalid checkpoint GLB')
    size, tag = struct.unpack_from('<I4s', data, 12)
    if tag != b'JSON' or 20+size+8 > len(data):
        raise ValueError('Invalid checkpoint JSON')
    doc = json.loads(data[20:20+size])
    extras = doc['scenes'][doc.get('scene',0)]['extras']
    fitting = extras['fitme_garment']
    if fitting.get('fitting_mode') not in ('db_cloth_collision','sam_body_cloth_collision'):
        raise ValueError('Checkpoint is not a cloth preview')
    report = extras['cloth_simulation']
    reasons = list(dict.fromkeys([*report.get('failure_reasons', []),reason]))
    report.update(status='failed',failure_reasons=reasons)
    if details is not None: report['interruption']=details
    fitting.update(simulation_status='failed',failure_reasons=reasons)
    header = json.dumps(doc,allow_nan=False,separators=(',',':')).encode()
    header += b' '*(-len(header)%4)
    chunks = data[20+size:]
    return (struct.pack('<4sII',b'glTF',2,20+len(header)+len(chunks))+
            struct.pack('<I4s',len(header),b'JSON')+header+chunks)
