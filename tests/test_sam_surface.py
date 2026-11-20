"""SAM normalization preserves body proportions without a template or NumPy."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'avatar/src'))
from core.sam_surface import height_transform, normalize_points


class SamSurfaceTests(unittest.TestCase):
    def test_uniform_scale_and_floor_preserve_relative_shape(self):
        vertices = [[-.3,.1,-.2],[.3,-.2,.8],[0.,0.,1.8]]
        scale, floor = height_transform(vertices, 170.)
        result = normalize_points(vertices, scale, floor)
        self.assertAlmostEqual(scale, .85)
        self.assertAlmostEqual(min(p[2] for p in result), 0.)
        self.assertAlmostEqual(max(p[2] for p in result), 1.7)
        for axis in range(3):
            self.assertAlmostEqual(result[1][axis]-result[0][axis],
                                   (vertices[1][axis]-vertices[0][axis])*.85)
        guides = [[.2,.1,.5]]
        self.assertEqual(normalize_points(guides,scale,floor), [[.17,.085,.595]])

    def test_invalid_mesh_or_height_fails_without_template_fallback(self):
        vertices = [[0.,0.,0.],[1.,0.,1.],[0.,1.,2.]]
        for height in (0, -1, float('nan'), True):
            with self.subTest(height=height), self.assertRaises(ValueError):
                height_transform(vertices,height)
        for invalid in ([], [[0.,0.,1.]]*3, [[float('nan'),0.,0.]]*3):
            with self.assertRaises(ValueError):
                height_transform(invalid,170.)


if __name__ == '__main__':
    unittest.main()
