# 역할: 미세한 장식·목둘레 영역의 거짓 자기 충돌 제외와 나머지 천의 충돌 유지를 검증합니다.
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.cloth_resolution import self_collision_exclusions


class ClothResolutionTests(unittest.TestCase):
    def test_server_micro_edge_excludes_only_its_patch(self):
        points=[(0,0,0),(.000022872,0,0),(0,.01,0),(1,0,0),(1.01,0,0),(1,.01,0)]
        report=self_collision_exclusions(points,[(0,1),(1,2),(2,0),(3,4),(4,5),(5,3)],[(0,1,2),(3,4,5)])
        self.assertEqual(report['vertices'],[0,1,2])
        self.assertEqual(report['excluded_faces'],1)
        self.assertEqual(report['self_distance_m'],.001)

    def test_uniform_proxy_does_not_lose_self_collision(self):
        report=self_collision_exclusions([(0,0,0),(.004824,0,0),(0,.01,0)],[(0,1),(1,2),(2,0)],[(0,1,2)])
        self.assertEqual(report['vertices'],[])
        self.assertEqual(report['excluded_faces'],0)
        self.assertEqual(report['altitude_seed_faces'],0)

    def test_long_thin_face_seeds_one_ring_without_a_short_edge(self):
        points=[(0,0,0),(.01,0,0),(.005,.0005,0),(.01,.01,0),(0,.01,0),
                (1,0,0),(1.01,0,0),(1,.01,0)]
        faces=[(0,1,2),(2,3,4),(5,6,7)]
        edges=[edge for a,b,c in faces for edge in ((a,b),(b,c),(c,a))]
        report=self_collision_exclusions(points,edges,faces)
        self.assertEqual(report['short_edge_seed_vertices'],0)
        self.assertEqual(report['altitude_seed_faces'],1)
        self.assertEqual(report['vertices'],[0,1,2,3,4])
        self.assertEqual(report['excluded_faces'],2)

    def test_altitude_uses_three_dimensional_geometry(self):
        points=[(0,0,0),(.01,0,0),(.005,0,.0005)]
        report=self_collision_exclusions(points,[(0,1),(1,2),(2,0)],[(0,1,2)])
        self.assertEqual(report['short_edge_seed_vertices'],0)
        self.assertEqual(report['altitude_seed_faces'],1)
        self.assertEqual(report['vertices'],[0,1,2])

    def test_polygon_fan_thin_triangle_seeds_entire_polygon(self):
        points=[(0,0,0),(.01,0,0),(.005,.0005,0),(0,.01,0)]
        report=self_collision_exclusions(points,[(0,1),(1,2),(2,3),(3,0)],[(0,1,2,3)])
        self.assertEqual(report['short_edge_seed_vertices'],0)
        self.assertEqual(report['altitude_seed_faces'],1)
        self.assertEqual(report['vertices'],[0,1,2,3])

    def test_altitude_threshold_scales_with_self_contact_distance(self):
        points=[(0,0,0),(.01,0,0),(.005,.0015,0)]
        edges=[(0,1),(1,2),(2,0)]
        self.assertEqual(self_collision_exclusions(points,edges,[(0,1,2)],.001)['altitude_seed_faces'],1)
        self.assertEqual(self_collision_exclusions(points,edges,[(0,1,2)],.0005)['altitude_seed_faces'],0)

    def test_invalid_physical_input_is_rejected(self):
        with self.assertRaises(ValueError): self_collision_exclusions([(0,0,0)]*3,[(0,1)],[(0,1,2)])
        with self.assertRaises(ValueError): self_collision_exclusions([],[],[],float('nan'))

    def test_near_faces_exclude_close_triangles_without_short_edges(self):
        points=[(0,0,0),(.01,0,0),(0,.01,0),(.006,.006,0),(.016,.006,0),(.006,.016,0),
                (.1,0,0),(.11,0,0),(.1,.01,0)]
        faces=[(0,1,2),(3,4,5),(6,7,8)]
        edges=[edge for a,b,c in faces for edge in ((a,b),(b,c),(c,a))]
        report=self_collision_exclusions(points,edges,faces,near_faces={0,1})
        self.assertEqual(report['vertices'],list(range(6)))
        self.assertEqual(report['near_rest_faces'],2)
        self.assertEqual(report['short_edge_seed_vertices'],0)
        self.assertEqual(report['excluded_faces'],2)

    def test_near_face_does_not_expand_to_unaffected_neighbor(self):
        points=[(0,0,0),(.01,0,0),(0,.01,0),(.01,.01,0),(0,.02,0)]
        faces=[(0,1,2),(2,3,4)]
        report=self_collision_exclusions(points,[(0,1),(1,2),(2,0),(2,3),(3,4),(4,2)],faces,near_faces=[0,0])
        self.assertEqual(report['vertices'],[0,1,2])
        self.assertEqual(report['near_rest_faces'],1)
        self.assertEqual(report['excluded_faces'],1)

    def test_near_faces_combine_with_short_edge_patch(self):
        points=[(0,0,0),(.00002,0,0),(0,.01,0),(1,0,0),(1.01,0,0),(1,.01,0)]
        report=self_collision_exclusions(points,[(0,1),(1,2),(2,0),(3,4),(4,5),(5,3)],
                                         [(0,1,2),(3,4,5)],near_faces=[1])
        self.assertEqual(report['vertices'],list(range(6)))
        self.assertEqual(report['excluded_faces'],2)
        self.assertEqual(report['short_edge_seed_vertices'],2)

    def test_invalid_near_face_ids_are_rejected(self):
        for invalid in ([-1],[1],[0.0],[True],['0'],None,[[0]]):
            with self.subTest(near_faces=invalid),self.assertRaises(ValueError):
                self_collision_exclusions([(0,0,0),(.01,0,0),(0,.01,0)],
                    [(0,1),(1,2),(2,0)],[(0,1,2)],near_faces=invalid)

    def test_invalid_vertices_edges_and_faces_are_rejected(self):
        cases=[([(float('nan'),0,0),(1,0,0),(0,1,0)],[(0,1)],[(0,1,2)]),
               ([(0,0,0),(1,0,0),(0,1,0)],[(0,3)],[(0,1,2)]),
               ([(0,0,0),(1,0,0),(0,1,0)],[(0,1)],[(0,1)]),
               ([(0,0,0),(1,0,0),(0,1,0)],[(0,1)],[(0,1,1)]),
               ([(0,0,0),(1,0,0),(0,1,0)],[(False,1)],[(0,1,2)])]
        for points,edges,faces in cases:
            with self.subTest(points=points,edges=edges,faces=faces),self.assertRaises(ValueError):
                self_collision_exclusions(points,edges,faces)


if __name__=='__main__': unittest.main()
