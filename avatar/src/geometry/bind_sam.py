# 역할: SAM 바인딩 호환성 확인에 쓰는 메시 해시를 계산합니다.
"""Stable control mesh hash used by the version-2 binding and Blender worker."""
import hashlib

def digest(vertices, faces):
    return hashlib.sha256(vertices.astype('<f4').tobytes()+faces.astype('<i4').tobytes()).hexdigest()

if __name__=='__main__':
    raise SystemExit('Use scripts/build_binding.py with the bundled A pose; legacy bindings are incompatible.')
