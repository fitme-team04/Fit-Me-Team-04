# 역할: 팔 중심축의 위치 오차가 소매 두께로 합산되지 않는지 단면 프로파일을 검증합니다.
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.arm_profiles import radial_basis,ellipse_section,offset_radial_profile,sample_radial_profiles


def rectangle(offset=(.09,-.03),half_width=.04,half_depth=.025,dense=False):
    if dense:
        lower=np.column_stack((np.linspace(-half_width,half_width,50),np.full(50,-half_depth)))
        polygon=np.vstack((lower,(half_width,half_depth),(-half_width,half_depth)))
    else:polygon=np.array(((-half_width,-half_depth),(half_width,-half_depth),
                           (half_width,half_depth),(-half_width,half_depth)))
    return polygon+offset


class ArmProfilesTests(unittest.TestCase):
    def setUp(self):
        self.axis=np.array((1.,.2,-.7));self.axis/=np.linalg.norm(self.axis)
        self.origin=np.array((.35,-.04,-.2));self.basis=radial_basis(self.axis)

    def world(self,polygon):
        return self.origin+polygon@self.basis.T

    def test_basis_is_orthonormal_perpendicular_and_front_stable(self):
        np.testing.assert_allclose(self.basis.T@self.basis,np.eye(2),atol=1e-14)
        np.testing.assert_allclose(self.axis@self.basis,0,atol=1e-14)
        np.testing.assert_allclose(radial_basis(self.axis*10),self.basis,atol=1e-14)
        self.assertGreater(float(self.basis[:,0]@np.array((0.,1.,0.))),0)
        for axis in ((0.,1.,0.),(0.,-1.,0.)):
            basis=radial_basis(axis)
            np.testing.assert_allclose(basis.T@basis,np.eye(2),atol=1e-14)
            np.testing.assert_allclose(np.asarray(axis)@basis,0,atol=1e-14)

    def test_off_axis_center_is_not_added_to_radius(self):
        result=ellipse_section(self.world(rectangle()),self.origin,self.axis,self.basis)
        np.testing.assert_allclose(result['offset'],(.09,-.03),atol=1e-14)
        np.testing.assert_allclose(result['center'],self.origin+self.basis@np.array((.09,-.03)),atol=1e-14)
        np.testing.assert_allclose(result['radii'],np.sqrt(2)*np.array((.04,.025)),atol=1e-14)
        self.assertLess(float(result['radii'][0]),.09)
        self.assertAlmostEqual(result['area_m2'],.004)
        self.assertAlmostEqual(result['perimeter_m'],.26)

    def test_nonuniform_edge_sampling_and_winding_do_not_bias_center(self):
        reference=ellipse_section(self.world(rectangle()),self.origin,self.axis,self.basis)
        for polygon in (rectangle(dense=True),rectangle(dense=True)[::-1]):
            result=ellipse_section(self.world(polygon),self.origin,self.axis,self.basis)
            for field in ('center','offset','radii'):
                np.testing.assert_allclose(result[field],reference[field],atol=1e-14)
            self.assertAlmostEqual(result['area_m2'],reference['area_m2'])
            self.assertAlmostEqual(result['perimeter_m'],reference['perimeter_m'])

    def test_corners_are_enclosed_before_additive_clearance(self):
        polygon=rectangle()
        base=ellipse_section(self.world(polygon),self.origin,self.axis,self.basis)
        padded=ellipse_section(self.world(polygon),self.origin,self.axis,self.basis,clearance_m=.005)
        radii=np.linalg.norm((polygon-base['offset'])/base['radii'],axis=1)
        self.assertTrue(np.all(radii<=1+1e-14))
        self.assertAlmostEqual(base['enclosure_scale'],np.sqrt(2))
        np.testing.assert_allclose(padded['radii']-base['radii'],.005,atol=1e-14)
        self.assertAlmostEqual(padded['perimeter_m'],base['perimeter_m'])

    def test_nonuniform_ellipse_and_mirror_have_matching_profiles(self):
        angles=np.unique(np.r_[np.linspace(0,2*np.pi,160,endpoint=False),np.linspace(0,.6,120)])
        polygon=np.column_stack((.05*np.cos(angles),.03*np.sin(angles)))+(.045,-.018)
        loop=self.world(polygon)
        result=ellipse_section(loop,self.origin,self.axis)
        np.testing.assert_allclose(result['offset'],(.045,-.018),atol=2e-6)
        np.testing.assert_allclose(result['radii'],(.05,.03),atol=3e-6)
        mirror=np.diag((-1.,1.,1.))
        reflected=ellipse_section(loop@mirror.T,self.origin@mirror.T,self.axis@mirror.T)
        np.testing.assert_allclose(reflected['center'],result['center']@mirror.T,atol=1e-14)
        np.testing.assert_allclose(reflected['radii'],result['radii'],atol=1e-14)
        np.testing.assert_allclose(reflected['offset'],result['offset']*(1.,-1.),atol=1e-14)
        self.assertAlmostEqual(reflected['area_m2'],result['area_m2'])
        self.assertAlmostEqual(reflected['perimeter_m'],result['perimeter_m'])

    def test_small_sections_keep_positive_minimum_radii(self):
        polygon=rectangle(offset=(0.,0.),half_width=.0002,half_depth=.0001)
        result=ellipse_section(self.world(polygon),self.origin,self.axis,self.basis)
        np.testing.assert_allclose(result['radii'],.001,atol=1e-14)

    def test_nonplanar_zero_area_and_invalid_parameters_are_rejected(self):
        loop=self.world(rectangle())
        bad=loop.copy();bad[0]+=self.axis*.0001
        invalid=[bad,np.zeros((3,3)),loop[:2],np.full((4,3),np.nan)]
        for points in invalid:
            with self.subTest(points=points),self.assertRaises(ValueError):
                ellipse_section(points,self.origin,self.axis)
        for clearance in (-1,float('nan'),float('inf'),True,'0.01'):
            with self.subTest(clearance=clearance),self.assertRaises(ValueError):
                ellipse_section(loop,self.origin,self.axis,clearance_m=clearance)
        for basis in (self.basis*2,np.zeros((3,2)),self.basis.T,np.full((3,2),np.nan)):
            with self.subTest(basis=basis),self.assertRaises(ValueError):
                ellipse_section(loop,self.origin,self.axis,basis=basis)
        with self.assertRaises(ValueError):radial_basis((0,0,0))
        with self.assertRaises(ValueError):radial_basis(self.axis,(0,0,0))

    def test_zero_clearance_keeps_actual_convex_support_without_ellipse_expansion(self):
        polygon=rectangle(offset=(.09,-.03),half_width=.04,half_depth=.02)
        result=offset_radial_profile(self.world(polygon),self.origin,self.axis,self.basis,clearance_m=0)
        centered=polygon-result['offset']
        self.assertTrue(np.all(centered@result['hull_normals_2d'].T<=result['hull_support_m']+1e-13))
        radial=np.column_stack((np.cos(result['angles']),np.sin(result['angles'])))*result['angles_radii'][:,None]
        self.assertTrue(np.all(radial@result['hull_normals_2d'].T<=result['hull_support_m']+1e-13))
        self.assertAlmostEqual(result['body_hull_perimeter_m'],.24)
        self.assertAlmostEqual(result['miter_perimeter_m'],.24)
        self.assertLess(float(np.max(result['angles_radii'])),float(np.max(result['radii'])))

    def test_circle_offset_perimeter_matches_circumference_plus_two_pi_clearance(self):
        for count in (32,128):
            angles=np.arange(count)*(2*np.pi/count)
            polygon=np.column_stack((.035*np.cos(angles),.035*np.sin(angles)))+(.06,-.02)
            result=offset_radial_profile(self.world(polygon),self.origin,self.axis,self.basis,clearance_m=.01)
            expected=result['body_hull_perimeter_m']+2*np.pi*.01
            self.assertLess(abs(result['target_perimeter_m']-expected)/expected,.01)
            self.assertLess(abs(result['miter_perimeter_m']-expected)/expected,.01)

    def test_rectangle_offset_uses_miter_clearance_not_enclosing_ellipse(self):
        polygon=rectangle(half_width=.04,half_depth=.02)
        result=offset_radial_profile(self.world(polygon),self.origin,self.axis,self.basis,clearance_m=.01)
        self.assertAlmostEqual(result['body_hull_perimeter_m'],.24)
        self.assertAlmostEqual(result['miter_perimeter_m'],.32)
        # The exact miter has 320 mm perimeter. Uniform angular samples omit
        # rectangle corners, so their connecting chords give a shorter polygon.
        self.assertLessEqual(result['target_perimeter_m'],.32+1e-13)
        self.assertGreater(result['target_perimeter_m'],.32*.96)
        self.assertAlmostEqual(float(result['angles_radii'][0]),.05)
        self.assertAlmostEqual(float(result['angles_radii'][16]),.03)

    def test_radial_offset_is_invariant_to_density_winding_and_mirror(self):
        reference=offset_radial_profile(self.world(rectangle()),self.origin,self.axis,self.basis)
        for polygon in (rectangle(dense=True),rectangle(dense=True)[::-1]):
            result=offset_radial_profile(self.world(polygon),self.origin,self.axis,self.basis)
            np.testing.assert_allclose(result['offset'],reference['offset'],atol=1e-13)
            np.testing.assert_allclose(result['angles_radii'],reference['angles_radii'],atol=1e-13)
            self.assertAlmostEqual(result['body_hull_perimeter_m'],reference['body_hull_perimeter_m'])
        mirror=np.diag((-1.,1.,1.));loop=self.world(rectangle())
        result=offset_radial_profile(loop@mirror.T,self.origin@mirror.T,self.axis@mirror.T)
        np.testing.assert_allclose(result['angles_radii'],reference['angles_radii'][(-np.arange(64))%64],atol=1e-13)
        np.testing.assert_allclose(result['center'],reference['center']@mirror.T,atol=1e-13)

    def test_radial_offset_rejects_invalid_sampling_and_inherits_plane_validation(self):
        loop=self.world(rectangle())
        for samples in (0,15,64.,True,float('nan'),'64',None):
            with self.subTest(samples=samples),self.assertRaises(ValueError):
                offset_radial_profile(loop,self.origin,self.axis,samples=samples)
        bad=loop.copy();bad[0]+=self.axis*.001
        with self.assertRaises(ValueError):offset_radial_profile(bad,self.origin,self.axis)
        with self.assertRaises(ValueError):offset_radial_profile(loop,self.origin,self.axis,clearance_m=-.01)

    def test_periodic_radial_sampling_wraps_tiny_negative_and_full_turn_angles(self):
        angles=np.array((-1e-18,0.,2*np.pi,-2*np.pi,8*np.pi))
        tables=np.tile(np.arange(1.,65.),(len(angles),1))
        np.testing.assert_allclose(sample_radial_profiles(tables,angles),1.,atol=1e-13)

    def test_periodic_radial_sampling_interpolates_each_points_own_table(self):
        ray=2*np.pi/16
        tables=np.vstack((np.full(16,.04),np.arange(1.,17.),np.arange(1.,17.),np.arange(2.,18.)))
        angles=np.array((.37,ray*.5,-ray*.5,ray*4.25+6*np.pi))
        np.testing.assert_allclose(sample_radial_profiles(tables,angles),(.04,1.5,8.5,6.25),atol=1e-12)
        self.assertEqual(sample_radial_profiles(np.empty((0,16)),np.empty(0)).shape,(0,))

    def test_periodic_radial_sampling_rejects_invalid_dimensions_or_values(self):
        valid=np.ones((2,16));angles=np.zeros(2)
        cases=[(valid[0],angles),(np.ones((2,15)),angles),(valid,angles[:,None]),
               (valid,np.zeros(3)),(valid,np.array((0.,np.nan))),
               (np.full((2,16),np.inf),angles),(np.zeros((2,16)),angles),
               (-valid,angles),(np.ones((2,16),dtype=bool),angles),
               (valid,np.array(('0','1')))]
        for tables,directions in cases:
            with self.subTest(tables=tables,directions=directions),self.assertRaises(ValueError):
                sample_radial_profiles(tables,directions)


if __name__=='__main__':unittest.main()
