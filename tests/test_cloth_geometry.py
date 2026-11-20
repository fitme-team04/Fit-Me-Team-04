# 역할: SAM 충돌 영역 선택과 DB 치수를 보존하는 국소 보정을 검사합니다.
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.cloth_geometry import region_bounds, inside_region, select_region, push_out, relax_contacts


class CollisionGeometryTests(unittest.TestCase):
    def test_deep_contact_can_translate_without_changing_db_lengths(self):
        points=[(0.,0.,-.02),(.04,0.,-.02),(0.,.04,-.02)]
        before=list(points)
        moved,report=relax_contacts(points,[(0,1),(1,2),(2,0)],points,
            lambda p:((p[0],p[1],0.),(0.,0.,1.)))
        self.assertTrue(report['accepted'])
        self.assertTrue(all(p[2] >= .0039 for p in moved))
        self.assertAlmostEqual(report['min_edge_ratio'],1.)
        self.assertAlmostEqual(report['max_edge_ratio'],1.)
        self.assertEqual(points,before)

    def test_relaxation_spreads_isolated_contact_to_neighbors(self):
        points=[(-.02,0.,-.004),(.02,0.,.004),(0.,.04,.004)]
        moved,report=relax_contacts(points,[(0,1),(1,2),(2,0)],points,
            lambda p:((p[0],p[1],0.),(0.,0.,1.)))
        self.assertTrue(report['accepted'])
        self.assertGreater(moved[0][2],0.)
        self.assertNotEqual(moved[1],points[1])
        self.assertLessEqual(report['max_edge_ratio'],1.005)
        self.assertGreaterEqual(report['min_edge_ratio'],.98)

    def test_select_crossing_faces_without_modifying_display(self):
        vertices=[(-2.,0.,0.),(2.,0.,0.),(0.,2.,0.),(10.,0.,0.),(11.,0.,0.),(10.,1.,0.)]
        faces=[(0,1,2),(3,4,5)]
        before=list(vertices)
        selected,triangles=select_region(vertices,faces,([-.1]*3,[.1]*3))
        self.assertEqual(selected,vertices[:3])
        self.assertEqual(triangles,[(0,1,2)])
        self.assertEqual(vertices,before)
        self.assertEqual(len(faces),2)

    def test_region_has_motion_margin_and_detects_escape(self):
        bounds=region_bounds([(0.,0.,0.),(1.,1.,1.)])
        self.assertTrue(inside_region([(-.1,0.,0.),(1.1,1.,1.)],bounds))
        self.assertFalse(inside_region([(1.3,0.,0.)],bounds))
        with self.assertRaises(ValueError): select_region([(10.,10.,10.)]*3,[(0,1,2)],bounds)

    def test_push_only_shallow_inside_vertex_and_preserve_db_input(self):
        points=[(-1.,0.,-.001),(1.,0.,.001),(0.,1.,.001)]
        before=list(points)
        def nearest(p): return ((p[0],p[1],0.),(0.,0.,1.))
        corrected,report=push_out(points,[(0,1),(1,2),(2,0)],[(0,1,2)],nearest)
        self.assertTrue(report['accepted'])
        self.assertEqual(report['moved_vertices'],1)
        self.assertEqual(points,before)
        self.assertEqual(corrected[1:],points[1:])
        self.assertAlmostEqual(corrected[0][2],.002)
        self.assertLessEqual(report['attempted_max_edge_ratio'],1.005)

    def test_reject_size_change_and_leave_deep_contacts_untouched(self):
        def nearest(p): return ((p[0],p[1],0.),(0.,0.,1.))
        points=[(0.,0.,-.004),(.001,0.,.001),(0.,.001,.001)]
        corrected,report=push_out(points,[(0,1),(1,2),(2,0)],[(0,1,2)],nearest)
        self.assertFalse(report['accepted'])
        self.assertEqual(corrected,points)
        self.assertEqual(report['moved_vertices'],0)
        deep=[(-1.,0.,-.02),(1.,0.,.01),(0.,1.,.01)]
        corrected,report=push_out(deep,[(0,1),(1,2),(2,0)],[(0,1,2)],nearest)
        self.assertEqual(corrected,deep)
        self.assertEqual(report['moved_vertices'],0)


if __name__ == '__main__': unittest.main()
