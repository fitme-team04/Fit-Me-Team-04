# 역할: 표본 사이의 관통, 메시 퇴화, 수축과 불충분한 안정 판정을 검증합니다.
from pathlib import Path
import importlib.util
import sys
from types import ModuleType
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.mesh_quality import triangle_intersection, mesh_statistics
from core.cloth_contract import validate_simulation
from core.pose_geometry import pose_error, translate_landmarks


class MeshQualityTests(unittest.TestCase):
    def test_self_intersections_are_unknown_when_geometry_check_prevents_bvh(self):
        fake=ModuleType('mathutils.bvhtree'); fake.BVHTree=MagicMock()
        path=Path(__file__).resolve().parents[1]/'garment/src/geometry/mesh_validation.py'
        spec=importlib.util.spec_from_file_location('validation_report_test',path)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'mathutils':ModuleType('mathutils'),'mathutils.bvhtree':fake}):
            spec.loader.exec_module(module)
        invalid=module.validate_mesh([(0,0,0),(1,0,0),(.5,0,0)],[(0,1,2)])
        self.assertIsNone(invalid['self_intersections'])
        self.assertFalse(invalid['validation_complete'])
        self.assertEqual(invalid['self_intersection_check'],'skipped_invalid_geometry')
        fake.BVHTree.FromPolygons.assert_not_called()

    def test_skinny_warning_does_not_skip_self_intersection_check(self):
        fake=ModuleType('mathutils.bvhtree'); fake.BVHTree=MagicMock()
        fake.BVHTree.FromPolygons.return_value.overlap.return_value=[]
        path=Path(__file__).resolve().parents[1]/'garment/src/geometry/mesh_validation.py'
        spec=importlib.util.spec_from_file_location('validation_skinny_test',path)
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'mathutils':ModuleType('mathutils'),'mathutils.bvhtree':fake}):
            spec.loader.exec_module(module)
        report=module.validate_mesh([(0,0,0),(.1,0,0),(0,.1/8965,0)],[(0,1,2)])
        self.assertTrue(report['valid'])
        self.assertEqual(report['self_intersection_check'],'completed')
        fake.BVHTree.FromPolygons.assert_called_once()

    def test_inherited_aspect_8965_is_warning_not_degenerate(self):
        source=[(0,0,0),(.1,0,0),(0,.1/8965,0)]
        report=mesh_statistics(source,[(0,1,2)])
        self.assertTrue(report['valid'])
        self.assertEqual(report['degenerate_triangles'],0)
        self.assertEqual(report['skinny_triangles'],1)
        self.assertAlmostEqual(report['worst_triangle_aspect'],8965,delta=.001)
        improved=[(0,0,0),(.1,0,0),(0,.1/4000,0)]
        self.assertTrue(mesh_statistics(improved,[(0,1,2)],source)['valid'])

    def test_real_zero_area_and_new_severe_sliver_still_fail(self):
        source=[(0,0,0),(.1,0,0),(0,.1,0)]
        self.assertIn('degenerate_faces',mesh_statistics([(0,0,0),(.1,0,0),(.05,0,0)],[(0,1,2)])['reasons'])
        # Same area, but enormous shear: not an inherited skinny triangle.
        sheared=[(0,0,0),(10,0,0),(0,.001,0)]
        self.assertIn('triangle_shape_degraded',mesh_statistics(sheared,[(0,1,2)],source)['reasons'])

    def test_clear_but_wrong_sleeve_pose_has_worse_score(self):
        source={'fit_shoulder_L':(0,0,0),'fit_cuff_L':(1,0,0)}
        body={'fit_shoulder_L':(0,0,0),'fit_wrist_L':(0,0,-1)}
        before=pose_error(source,body)
        source['fit_cuff_L']=(0,0,-1)
        self.assertLess((0,0,*pose_error(source,body)),(0,0,*before))

    def test_rigid_placement_moves_support_anchors_and_keeps_alignment_root(self):
        anchors=[{'name':name,'translation':[1,2,3]} for name in
                 ('fit_anchor','fit_anchor_waist','fit_shoulder_L','fit_cuff_R')]
        translate_landmarks(anchors,(.01,-.02,.03))
        self.assertEqual(anchors[0]['translation'],[1,2,3])
        self.assertEqual(anchors[1]['translation'],[1,2,3])
        self.assertEqual(anchors[2]['translation'],[1.01,2.03,3.02])
        self.assertEqual(anchors[3]['translation'],anchors[2]['translation'])

    def test_triangle_interior_crossing_without_cloth_vertex_inside(self):
        cloth=[(0,0,0),(1,0,0),(0,1,0)]
        body=[(.05,.05,-.05),(.15,.05,.05),(.05,.15,.05)]
        self.assertEqual(triangle_intersection(cloth,body),'crossing')
        self.assertIsNone(triangle_intersection(cloth,[(x,y,z+1) for x,y,z in body]))

    def test_coplanar_overlap_and_allowed_shared_boundary(self):
        first=[(0,0,0),(1,0,0),(0,1,0)]
        self.assertEqual(triangle_intersection(first,[(.1,.1,0),(.4,.1,0),(.1,.4,0)]),'coplanar_overlap')
        self.assertIsNone(triangle_intersection(first,[(1,0,0),(1,1,0),(0,1,0)]))

    def test_mesh_quality_rejects_collapse_and_duplicate_faces(self):
        rest=[(0,0,0),(1,0,0),(0,1,0)]
        self.assertTrue(mesh_statistics(rest,[(0,1,2)])['valid'])
        self.assertIn('duplicate_faces',mesh_statistics(rest,[(0,1,2),(2,1,0)])['reasons'])
        self.assertIn('degenerate_faces',mesh_statistics([(0,0,0),(1,0,0),(0,.001,0)],[(0,1,2)],rest)['reasons'])
        self.assertFalse(mesh_statistics(rest,[(0,1,9)])['valid'])

    def test_shrunken_cloth_and_one_quiet_frame_cannot_pass(self):
        result=validate_simulation([1]*3,[.5]*3,0,0,stable_frames=1)
        self.assertEqual(result['status'],'failed')
        self.assertIn('compression_exceeded',result['failure_reasons'])
        self.assertIn('unsettled',result['failure_reasons'])

    def test_exact_crossings_and_incomplete_validation_fail(self):
        result=validate_simulation([1],[1],0,0,stable_frames=5,
            mesh_quality={'valid':False},body_intersections={'crossing_pairs':1,'validation_complete':False})
        self.assertEqual(set(result['failure_reasons']),{'body_penetration','invalid_cloth_mesh','validation_incomplete'})


if __name__ == '__main__': unittest.main()
