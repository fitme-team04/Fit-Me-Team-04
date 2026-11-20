# 역할: SAM 크기 맞춤의 방사 윤곽 보존과 프로파일 보간을 Blender 없이 검증합니다.
from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.sam_sizing import bounded_radial_ratio, interpolate_profile


class SamSizingTests(unittest.TestCase):
    def test_reference_radius_is_unchanged_and_small_folds_keep_order(self):
        self.assertEqual(bounded_radial_ratio(1),1)
        ratios=[bounded_radial_ratio(r) for r in (.96,.98,.99,1,1.01,1.02,1.04)]
        self.assertTrue(all(a < b for a,b in zip(ratios,ratios[1:])))
        self.assertTrue(all(.98 < value < 1.02 for value in ratios))
        self.assertAlmostEqual(bounded_radial_ratio(.99)+bounded_radial_ratio(1.01),2)

    def test_extreme_source_folds_remain_positive_and_bounded(self):
        for ratio in (0,.1,.5,2,100,1e308):
            result=bounded_radial_ratio(ratio)
            self.assertTrue(.98 <= result <= 1.02)
        self.assertAlmostEqual(bounded_radial_ratio(2,.1),1.1,places=8)

    def test_invalid_radial_inputs_are_rejected(self):
        for ratio in (-.01,float('nan'),float('inf'),True,'1',None):
            with self.subTest(ratio=ratio),self.assertRaises(ValueError):
                bounded_radial_ratio(ratio)
        for amplitude in (0,-.1,1,float('nan'),True,'0.02',None):
            with self.subTest(amplitude=amplitude),self.assertRaises(ValueError):
                bounded_radial_ratio(1,amplitude)

    def test_profile_interpolates_centers_and_radii_together(self):
        levels=[0,.5,1]
        samples=[(0,-.1,.2,.15),(.1,-.05,.25,.2),(.2,0,.3,.25)]
        self.assertEqual(interpolate_profile(.5,levels,samples),samples[1])
        result=interpolate_profile(.25,levels,samples)
        for actual,expected in zip(result,(.05,-.075,.225,.175)):
            self.assertAlmostEqual(actual,expected)

    def test_profile_keeps_endpoints_and_single_sample(self):
        self.assertEqual(interpolate_profile(-2,[0,1],[(1,2),(3,4)]),(1,2))
        self.assertEqual(interpolate_profile(2,[0,1],[(1,2),(3,4)]),(3,4))
        self.assertEqual(interpolate_profile(10,[.5],[(1,2,3)]),(1,2,3))

    def test_profile_accepts_iterators_and_large_finite_values(self):
        self.assertEqual(interpolate_profile(.5,iter([0,1]),iter([(0,),(2,)])),(1,))
        result=interpolate_profile(0,[-1e308,1e308],[(-1e308,),(1e308,)])
        self.assertTrue(all(math.isfinite(v) for v in result))
        self.assertEqual(result,(0,))

    def test_invalid_profile_shapes_and_order_are_rejected(self):
        cases=[([],[]),([0],[]),([0,0],[(1,),(2,)]),([1,0],[(1,),(2,)]),
               ([0,1],[(1,),(2,3)]),([0],[()]),([0,float('nan')],[(1,),(2,)]),
               ([0,1],[(1,),(float('inf'),)]),(None,[(1,)]),([0],None),([True],[(1,)])]
        for levels,samples in cases:
            with self.subTest(levels=levels,samples=samples),self.assertRaises(ValueError):
                interpolate_profile(.5,levels,samples)
        with self.assertRaises(ValueError): interpolate_profile(float('nan'),[0],[(1,)])


if __name__=='__main__': unittest.main()
