# 역할: 팔·손 단면이 몸통 윤곽과 합쳐지지 않고 닫힌 SAM 몸통 단면만 선택되는지 검증합니다.
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.body_sections import horizontal_contours, torso_contour, plane_contours, arm_contour


def cube(x_range,y_range,z_range=(-1.,1.)):
    points=np.array([(x,y,z) for z in z_range for y in y_range for x in x_range],dtype=float)
    faces=np.array([(0,2,3),(0,3,1),(4,5,7),(4,7,6),
                    (0,1,5),(0,5,4),(2,6,7),(2,7,3),
                    (0,4,6),(0,6,2),(1,3,7),(1,7,5)])
    return points,faces


def combine(*meshes):
    vertices=[];faces=[];offset=0
    for points,triangles in meshes:
        vertices.append(points);faces.append(triangles+offset);offset+=len(points)
    return np.vstack(vertices),np.vstack(faces)


def cylinder(center,axis,radius=.035,length=.6,count=20):
    center=np.asarray(center,dtype=float);axis=np.asarray(axis,dtype=float);axis/=np.linalg.norm(axis)
    first=np.cross(axis,(0.,1.,0.));first/=np.linalg.norm(first);second=np.cross(axis,first)
    points=[]
    for t in (-length/2,length/2):
        for angle in np.linspace(0,2*np.pi,count,endpoint=False):
            points.append(center+t*axis+radius*(np.cos(angle)*first+np.sin(angle)*second))
    points.extend((center-axis*length/2,center+axis*length/2));faces=[]
    for i in range(count):
        j=(i+1)%count
        faces.extend(((i,j,count+j),(i,count+j,count+i),(2*count,j,i),(2*count+1,count+i,count+j)))
    return np.asarray(points),np.asarray(faces)


class BodySectionsTests(unittest.TestCase):
    def test_three_separate_torso_and_arm_loops_remain_separate(self):
        points,faces=combine(cube((-.15,.15),(-.08,.08)),
                             cube((.35,.45),(-.05,.05)),cube((-.45,-.35),(-.05,.05)))
        loops=horizontal_contours(points,faces,0)
        self.assertEqual(len(loops),3)
        torso=torso_contour(points,faces,0)
        np.testing.assert_allclose(np.ptp(torso,axis=0),(.30,.16,0))
        self.assertAlmostEqual(float(np.ptp(points[:,0])),.90)
        self.assertLess(float(np.ptp(torso[:,0])),float(np.ptp(points[:,0])))
        for loop in loops:
            self.assertTrue(np.allclose(loop[:,2],0))
            self.assertFalse(np.allclose(loop[0],loop[-1]))

    def test_small_central_hand_in_front_does_not_expand_torso_depth(self):
        points,faces=combine(cube((-.15,.15),(-.08,.08)),cube((-.04,.04),(-.26,-.18)))
        self.assertEqual(len(horizontal_contours(points,faces,.25)),2)
        for guide in (None,0.):
            torso=torso_contour(points,faces,.25,center_y=guide)
            np.testing.assert_allclose(torso[:,:2].min(0),(-.15,-.08))
            np.testing.assert_allclose(torso[:,:2].max(0),(.15,.08))
        self.assertAlmostEqual(float(np.ptp(points[:,1])),.34)

    def test_y_guide_and_shifted_center_are_explicit(self):
        points,faces=combine(cube((.85,1.15),(-.08,.08)),cube((.96,1.04),(-.26,-.18)))
        torso=torso_contour(points,faces,0,center_x=1.,center_y=0.)
        self.assertAlmostEqual(float(np.ptp(torso[:,0])),.3)
        hand=torso_contour(points,faces,0,center_x=1.,center_y=-.22)
        self.assertAlmostEqual(float(np.ptp(hand[:,0])),.08)

    def test_outside_or_open_sections_have_no_torso_fallback(self):
        points,faces=cube((-.15,.15),(-.08,.08))
        self.assertEqual(horizontal_contours(points,faces,2),[])
        with self.assertRaises(ValueError):torso_contour(points,faces,2)
        # Removing a side opens the section; all remaining spans must not be joined.
        self.assertEqual(horizontal_contours(points,faces[:8],0),[])
        with self.assertRaises(ValueError):torso_contour(points,faces[:8],0)

    def test_invalid_indices_coordinates_and_guides_are_rejected(self):
        points,faces=cube((-.15,.15),(-.08,.08))
        for bad_faces in (faces.astype(float),np.array([[0,1,99]]),np.array([[0,0,1]])):
            with self.subTest(faces=bad_faces),self.assertRaises(ValueError):
                horizontal_contours(points,bad_faces,0)
        invalid=points.copy();invalid[0,0]=np.nan
        with self.assertRaises(ValueError):horizontal_contours(invalid,faces,0)
        with self.assertRaises(ValueError):torso_contour(points,faces,0,center_y=float('nan'))

    def test_tilted_arm_plane_separates_cylinder_from_torso(self):
        axis=np.array((1.,0.,-1.));axis/=np.linalg.norm(axis)
        origin=np.array((.35,0.,0.))+axis*.05
        points,faces=combine(cube((-.15,.15),(-.08,.08)),cylinder((.35,0.,0.),axis))
        self.assertEqual(len(plane_contours(points,faces,origin,axis)),2)
        for normal in (axis,axis*7,-axis):
            arm=arm_contour(points,faces,origin,normal,max_radius=.1)
            np.testing.assert_allclose((arm-origin)@axis,0,atol=1e-12)
            self.assertAlmostEqual(float(np.max(np.linalg.norm(arm-origin,axis=1))),.035)
            self.assertLess(float(np.linalg.norm(arm.mean(0)-origin)),1e-10)

    def test_origin_containment_precedes_centroid_distance(self):
        points,faces=combine(cube((-.05,.95),(-.1,.1)),cube((-.02,.02),(.04,.06)))
        arm=arm_contour(points,faces,(0.,0.,0.),(0.,0.,1.))
        self.assertAlmostEqual(float(np.ptp(arm[:,0])),1.)

    def test_oversized_shoulder_join_is_rejected_without_fallback(self):
        points,faces=cube((-.3,.3),(-.2,.2))
        with self.assertRaises(ValueError):
            arm_contour(points,faces,(0.,0.,0.),(0.,0.,1.),max_radius=.1)

    def test_invalid_plane_and_arm_limits_are_rejected(self):
        points,faces=cube((-.15,.15),(-.08,.08))
        for axis in ((0,0,0),(0,float('nan'),1),(1,2),None):
            with self.subTest(axis=axis),self.assertRaises(ValueError):
                plane_contours(points,faces,(0,0,0),axis)
        with self.assertRaises(ValueError):plane_contours(points,faces,(0,0,float('inf')),(0,0,1))
        for limit in (0,-1,float('nan'),float('inf'),'bad'):
            with self.subTest(limit=limit),self.assertRaises(ValueError):
                arm_contour(points,faces,(0,0,0),(0,0,1),max_radius=limit)


if __name__=='__main__':unittest.main()
