# 역할: 초기 어깨 등록·3D 각도·DB 치수 보존·충돌 면 방향을 검사합니다.
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import unittest

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'garment/src'))
from core.pose_geometry import neck_registration, pose_strain, angle_degrees, orient_closed_surface, sleeve_target_on_arm


class InitialPoseTests(unittest.TestCase):
    def test_sleeve_reaches_arm_without_changing_its_length(self):
        shoulder=(.23,0.,0.); cuff=(.38,0.,-.15)
        body_shoulder=(.18,-.03,0.); wrist=(.58,-.07,-.4)
        target=sleeve_target_on_arm(shoulder,cuff,body_shoulder,wrist)
        self.assertAlmostEqual(math.dist(shoulder,target),math.dist(shoulder,cuff),places=12)
        amount=(target[0]-body_shoulder[0])/(wrist[0]-body_shoulder[0])
        self.assertGreater(amount,0.); self.assertLess(amount,1.)
        for i in range(3):
            self.assertAlmostEqual(target[i],body_shoulder[i]+amount*(wrist[i]-body_shoulder[i]),places=12)

    def test_sleeve_target_mirrors_across_the_body(self):
        landmarks=((.23,0.,0.),(.38,0.,-.15),(.18,-.03,0.),(.58,-.07,-.4))
        left=sleeve_target_on_arm(*landmarks)
        right=sleeve_target_on_arm(*[(-x,y,z) for x,y,z in landmarks])
        for actual,expected in zip(right,(-left[0],left[1],left[2])):
            self.assertAlmostEqual(actual,expected,places=12)

    def test_aligned_sleeve_keeps_its_existing_cuff(self):
        cuff=(.3,0.,-.4)
        target=sleeve_target_on_arm((0.,0.,0.),cuff,(0.,0.,0.),(.6,0.,-.8))
        for actual,expected in zip(target,cuff): self.assertAlmostEqual(actual,expected,places=12)

    def test_sleeve_uses_the_wristward_sphere_intersection(self):
        target=sleeve_target_on_arm((.5,.1,0.),(.7,.1,0.),(0.,0.,0.),(1.,0.,0.))
        self.assertAlmostEqual(target[0],.5+math.sqrt(.2**2-.1**2),places=12)
        self.assertEqual(target[1:],(0.,0.))

    def test_sleeve_rejects_an_arm_line_it_cannot_reach(self):
        with self.assertRaisesRegex(ValueError,'does not reach'):
            sleeve_target_on_arm((0.,2.,0.),(1.,2.,0.),(0.,0.,0.),(3.,0.,0.))

    def test_sleeve_rejects_intersections_outside_the_arm_segment(self):
        for shoulder,cuff in [((0.,0.,0.),(2.,0.,0.)),((-2.,0.,0.),(-1.5,0.,0.))]:
            with self.subTest(shoulder=shoulder), self.assertRaisesRegex(ValueError,'outside'):
                sleeve_target_on_arm(shoulder,cuff,(0.,0.,0.),(1.,0.,0.))

    def test_sleeve_rejects_invalid_non_finite_and_degenerate_landmarks(self):
        valid=[(0.,0.,0.),(.2,0.,0.),(0.,0.,0.),(.5,0.,0.)]
        for index,invalid in [(0,(float('nan'),0.,0.)),(1,(float('inf'),0.,0.)),
                              (2,(0.,0.)),(3,None),(0,('0',0.,0.)),(0,(True,0.,0.)),
                              (1,valid[0]),(3,valid[2])]:
            points=valid.copy(); points[index]=invalid
            with self.subTest(index=index,invalid=invalid), self.assertRaises(ValueError):
                sleeve_target_on_arm(*points)

    def test_neck_registers_to_shoulder_line_without_shrinking_width(self):
        garment={'L':(.116,0.,.015),'R':(-.116,0.,.015)}
        neck={'L':(.067,0.,.05),'R':(-.067,0.,.05)}
        shoulder={'L':(.20,0.,0.),'R':(-.20,0.,0.)}
        shift=neck_registration(garment,neck,shoulder)
        self.assertAlmostEqual(shift[0],0.)
        self.assertAlmostEqual(shift[2],.05-(.116-.067)/(.20-.067)*.05-.015)
        self.assertAlmostEqual((garment['L'][0]+shift[0])-(garment['R'][0]+shift[0]),.232)
        with self.assertRaises(ValueError):
            neck_registration(garment,{s:(p[0],0.,.5) for s,p in neck.items()},shoulder)

    def test_axis_comparison_includes_forward_reach(self):
        self.assertAlmostEqual(angle_degrees((1,0,-1),(1,0,-1)),0.,places=5)
        angle=angle_degrees((.707,-.11,-.707),(.707,-.16,-.707))
        self.assertGreater(angle,2.); self.assertLess(angle,4.)

    def test_only_size_preserving_poses_are_accepted(self):
        points=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.)]
        edges=[(0,1),(1,2),(2,0)]; polygons=[(0,1,2)]
        translated=[(x,y+.02,z+.03) for x,y,z in points]
        self.assertTrue(pose_strain(points,translated,edges,polygons)['accepted'])
        expanded=[(x*1.01,y*1.01,z) for x,y,z in points]
        self.assertFalse(pose_strain(points,expanded,edges,polygons)['accepted'])
        flipped=[points[0],points[2],points[1]]
        self.assertTrue(pose_strain(points,flipped,edges,polygons)['face_flip'])

    def test_inward_closed_body_is_fixed_for_collision_only(self):
        vertices=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
        outward=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        inverted=[tuple(reversed(face)) for face in outward]
        fixed,report=orient_closed_surface(vertices,inverted)
        self.assertTrue(report['closed_surface'])
        self.assertTrue(report['reversed_for_collision'])
        self.assertEqual(fixed,outward)
        self.assertEqual(inverted,[tuple(reversed(face)) for face in outward])
        _,report=orient_closed_surface(vertices,inverted[:-1])
        self.assertFalse(report['closed_surface'])
        self.assertFalse(report['reversed_for_collision'])

    def test_body_metadata_accepts_optional_neck_and_legacy_six_anchors(self):
        for service in ('avatar','garment'):
            spec=importlib.util.spec_from_file_location('anchor_'+service,BASE/service/'src/geometry/mesh_anchors.py')
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            for extra in ([],['fit_neck_L','fit_neck_R']):
                names=['fit_anchor','fit_anchor_waist','fit_shoulder_L','fit_shoulder_R','fit_wrist_L','fit_wrist_R',*extra]
                doc={'scene':0,'scenes':[{'nodes':[0]}],
                     'nodes':[{'name':'FitMeAvatar','children':list(range(1,len(names)+1))},*[{'name':name} for name in names]]}
                header=json.dumps(doc).encode(); header+=b' '*(-len(header)%4)
                data=struct.pack('<4sII',b'glTF',2,20+len(header))+struct.pack('<I4s',len(header),b'JSON')+header
                _,anchors,_=module.extract(data,'avatars')
                self.assertEqual(set(anchors),set(names))


if __name__ == '__main__': unittest.main()
