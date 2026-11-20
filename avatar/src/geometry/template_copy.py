# 역할: 읽기 전용 신체 원본에서 요청별 객체·메시·셰이프키 사본을 만들고 실패 시에도 제거합니다.
from contextlib import contextmanager
import bpy


@contextmanager
def request_body():
    source=bpy.data.objects['GEO-body_male_realistic']
    body=source.copy()
    mesh=source.data.copy()
    body.data=mesh
    body.name='FitMeRequestBody'
    body.animation_data_clear()
    bpy.context.scene.collection.objects.link(body)
    try:
        if source.data.shape_keys is not None:
            if mesh.shape_keys is source.data.shape_keys:
                raise RuntimeError('Request shape keys must be independent of the template')
            mesh.shape_keys.animation_data_clear()
            for key in mesh.shape_keys.key_blocks:key.value=0.
        yield body
    finally:
        bpy.data.objects.remove(body,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)
