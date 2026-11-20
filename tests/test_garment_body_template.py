# 역할: SAM 피팅 원형의 정점·기준점 보존과 DB 치수 없는 결과 메타데이터를 검사합니다.
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

SRC=Path(__file__).resolve().parents[1]/'garment/src'
sys.path.insert(0,str(SRC))
from geometry.glb import pack, unpack


def load(name,path,replacements):
    with patch.dict(sys.modules,replacements):
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class BodyTemplateTests(unittest.TestCase):
    def setUp(self):
        mathutils=ModuleType('mathutils'); mathutils.Vector=lambda value:value
        bvh=ModuleType('mathutils.bvhtree'); bvh.BVHTree=object
        self.binding=load('body_template_under_test',SRC/'geometry/template_binding.py',{
            'bpy':ModuleType('bpy'),'mathutils':mathutils,'mathutils.bvhtree':bvh})
        self.vertices=np.array([[0.,0.,0.],[.3,0.,-.2],[-.3,0.,-.2]])
        self.faces=np.array([[0,1,2]])
        self.baseline={'registered':'baseline'}
        self.stored={'schema_version':1,'cage_version':self.binding.CAGE_VERSION,'kind':'crewneck',
                     'geometry_hash':self.binding.digest(self.vertices,self.faces),
                     'base_spec_json':json.dumps(self.baseline),'sleeve_basis':'center_back'}
        self.entry={'kind':'crewneck','binding_path':'unused.npz',
                    'deformation_policy':'shape_preserving_center_back_v1',
                    'anchor_bindings':{'fit_shoulder_L':{'reference':[.21,-.02,.01]},
                                       'fit_cuff_L':{'reference':[.38,-.03,-.19]}}}
        self.base_anchors=[{'name':name,'translation':[0.,0.,0.]} for name in
                           ('fit_anchor','fit_shoulder_L','fit_shoulder_R','fit_cuff_L','fit_cuff_R')]
        self.validation=ModuleType('geometry.mesh_validation')
        self.validation.validate_mesh=lambda *args:{'valid':True,'reasons':[]}

    def prepare(self):
        with patch.dict(sys.modules,{'geometry.mesh_validation':self.validation}), \
             patch.object(self.binding,'geometry',return_value=(self.vertices,self.faces)), \
             patch.object(self.binding,'cached_binding',return_value=self.stored), \
             patch.object(self.binding,'cage',return_value=(None,None,self.base_anchors,{})) as cage:
            result=self.binding.body_template(SimpleNamespace(),self.entry)
        cage.assert_called_once_with(self.entry['kind'],self.baseline,self.stored['sleeve_basis'])
        return result

    def test_original_shirt_uses_registered_shape_anchors_without_db_deformation(self):
        original=self.vertices.copy()
        anchors,metrics,info=self.prepare()
        np.testing.assert_array_equal(self.vertices,original)
        self.assertEqual(metrics,{})
        self.assertFalse(info['deformation_applied'])
        self.assertEqual(info['geometry_mode'],'sam_body')
        self.assertEqual(info['source_geometry_sha256'],self.stored['geometry_hash'])
        by_name={anchor['name']:anchor['translation'] for anchor in anchors}
        self.assertEqual(by_name['fit_shoulder_L'],[.21,.01,.02])
        self.assertEqual(by_name['fit_cuff_L'],[.38,-.19,.03])
        self.assertEqual(by_name['fit_anchor'],[0.,0.,0.])
        self.assertNotIn('db_mesh_quality',info)

    def test_invalid_source_quality_is_preserved_for_failed_preview(self):
        self.validation.validate_mesh=lambda *args:{'valid':False,'reasons':['degenerate_face']}
        _,_,info=self.prepare()
        self.assertFalse(info['source_mesh_quality']['valid'])
        self.assertEqual(info['reference_mesh_quality'],info['source_mesh_quality'])

    def test_body_pants_keep_registered_waist_and_original_geometry(self):
        self.entry={'kind':'slacks','binding_path':'unused.npz'}
        self.stored={**self.stored,'kind':'slacks','sleeve_basis':'none'}
        self.base_anchors=[{'name':'fit_anchor_waist','translation':[0.,0.,0.]},
                           {'name':'fit_crotch','translation':[0.,-.3,0.]}]
        anchors,metrics,info=self.prepare()
        self.assertEqual(metrics,{})
        self.assertEqual(anchors,self.base_anchors)
        self.assertFalse(info['deformation_applied'])

    def test_changed_source_or_invalid_anchor_is_rejected(self):
        for change in ('hash','anchor'):
            with self.subTest(change=change):
                if change=='hash':self.stored['geometry_hash']='invalid'
                else:
                    self.stored['geometry_hash']=self.binding.digest(self.vertices,self.faces)
                    self.entry['anchor_bindings']['fit_cuff_L']['reference']=[float('nan'),0.,0.]
                with self.assertRaises(ValueError):self.prepare()


class BodyExportTests(unittest.TestCase):
    def test_sam_fit_has_no_db_targets_and_preserves_body_sizing_report(self):
        bpy=ModuleType('bpy')
        def export(**kwargs):Path(kwargs['filepath']).write_bytes(pack({'scenes':[{}]},b''))
        bpy.ops=SimpleNamespace(export_scene=SimpleNamespace(gltf=export))
        binding=ModuleType('geometry.template_binding'); binding.deform=lambda *args:None; binding.body_template=lambda *args:None
        cloth=ModuleType('geometry.cloth_fit'); cloth.simulate=lambda *args:None; cloth.stage=lambda *args,**kwargs:None
        worker=load('body_worker_export_under_test',SRC/'geometry/garment_worker.py',{
            'bpy':bpy,'geometry.template_binding':binding,'geometry.cloth_fit':cloth})
        sizing={'method':'sam_surface','measurements':{'chest_width_cm':44.}}
        simulation={'status':'failed','failure_reasons':['body_penetration'],'body_sizing':sizing}
        job={'body_model_id':'a'*64,'body_glb_b64':'private asset','spec':{},'recipe':{'kind':'crewneck'}}
        data=worker.export_result(job,{'template_id':'shirt'}, {'legacy_metric':100.},{},simulation)
        document,_=unpack(data); extras=document['scenes'][0]['extras']
        self.assertEqual(extras['fitme_garment']['fitting_mode'],'sam_body_cloth_collision')
        self.assertEqual(extras['fitme_garment_measurements'],{})
        self.assertEqual(extras['cloth_simulation']['body_sizing'],sizing)
        self.assertNotIn('body_glb_b64',extras)


if __name__=='__main__':unittest.main()
