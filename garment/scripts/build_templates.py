# 역할: 기본 상의와 슬랙스 템플릿 자산을 재생성합니다.
"""Generate FitMe's original, unbranded starter garment assets (no external downloads)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from geometry.garment_cages import cage
from core.garment_specs import DEFAULTS
from prepare_template import register

root=Path(__file__).resolve().parents[1]/'models'/'garments'
for kind,color in [('crewneck',(.18,.29,.44,1)),('slacks',(.12,.14,.18,1))]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec=DEFAULTS[kind];basis='shoulder' if kind=='crewneck' else 'none'
    vertices,faces,_,_=cage(kind,spec,basis)
    mesh=bpy.data.meshes.new('GarmentMesh');mesh.from_pydata(vertices.tolist(),[],faces.tolist());mesh.update()
    obj=bpy.data.objects.new('GarmentMesh',mesh);bpy.context.collection.objects.link(obj)
    for polygon in mesh.polygons:polygon.use_smooth=True
    material=bpy.data.materials.new('FitMe Fabric');material.diffuse_color=color;material.use_nodes=True
    bsdf=material.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=color;bsdf.inputs['Roughness'].default_value=.85
    material.use_backface_culling=False;obj.data.materials.append(material)
    # Basic UV map is retained by the loader/exporter, ready for team texture edits.
    uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:
        x,y,z=vertices[loop.vertex_index]
        uv.data[loop.index].uv=((x+1)/2,(z+1.5)/2)
    print(kind,register(obj,kind,spec,basis,kind+'_v1',root))
