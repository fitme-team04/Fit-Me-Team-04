"""Acceptance tests for DB-sized cloth; no Blender or NumPy dependency."""
from hashlib import sha256
from pathlib import Path
import sys
import unittest
import json
import struct

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'garment/src'))
from core.cloth_contract import validate_simulation, stop_reason, mass_settings
from core.cloth_checkpoint import interrupted_preview
from storage.body_asset import body_path


class ClothContractTests(unittest.TestCase):
    def test_total_mass_does_not_grow_with_mesh_density(self):
        for vertices in (340,680,2720):
            settings=mass_settings('crewneck',vertices,{})
            self.assertAlmostEqual(settings['vertex_mass_kg']*vertices,.2)
            self.assertEqual(settings['source'],'preview_default')
        self.assertAlmostEqual(mass_settings('crewneck',340,{})['vertex_mass_kg'],.000588235294)

    def test_kind_defaults_and_explicit_total_mass(self):
        self.assertEqual(mass_settings('slacks',575,{})['total_mass_kg'],.5)
        settings=mass_settings('crewneck',340,{'CLOTH_CREWNECK_TOTAL_MASS_KG':'0.35'})
        self.assertEqual(settings['source'],'configured')
        self.assertAlmostEqual(settings['vertex_mass_kg']*340,.35)

    def test_invalid_mass_and_vertex_count_are_not_silently_used(self):
        for value in ('nan','inf','', 'abc', '0', '-1', '5.1', True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                mass_settings('crewneck',340,{'CLOTH_CREWNECK_TOTAL_MASS_KG':value})
        for count in (0,-1,True,1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                mass_settings('crewneck',count,{})
        with self.assertRaises(ValueError): mass_settings('unknown',340,{})

    def test_stop_policy_bounds_time_and_divergence_without_changing_size(self):
        self.assertIsNone(stop_reason(4,4,10.,1.001))
        self.assertEqual(stop_reason(12,5,20.,1.001),'settled')
        self.assertEqual(stop_reason(5,0,180.,1.001),'simulation_timeout')
        self.assertEqual(stop_reason(3,0,5.,1.2),'simulation_diverged')
        self.assertEqual(stop_reason(3,0,5.,1.,False),'non_finite_simulation')

    def test_timeout_keeps_original_binary_and_marks_both_reports_failed(self):
        doc={'scene':0,'scenes':[{'extras':{'fitme_garment':{'fitting_mode':'db_cloth_collision'},
             'cloth_simulation':{'status':'failed','failure_reasons':['simulation_incomplete'],'frames':4}}}]}
        header=json.dumps(doc).encode(); header+=b' '*(-len(header)%4)
        binary=struct.pack('<I4s',4,b'BIN\0')+b'\x01\x02\x03\x04'
        glb=struct.pack('<4sII',b'glTF',2,20+len(header)+len(binary))+struct.pack('<I4s',len(header),b'JSON')+header+binary
        result=interrupted_preview(glb,'simulation_timeout')
        size=struct.unpack_from('<I',result,12)[0]
        extras=json.loads(result[20:20+size])['scenes'][0]['extras']
        self.assertEqual(result[20+size:],binary)
        self.assertEqual(struct.unpack_from('<I',result,8)[0],len(result))
        self.assertEqual(extras['fitme_garment']['simulation_status'],'failed')
        self.assertIn('simulation_timeout',extras['cloth_simulation']['failure_reasons'])
        self.assertEqual(extras['cloth_simulation']['frames'],4)
        with self.assertRaises(ValueError): interrupted_preview(glb[:-4],'simulation_timeout')

    def test_accept_settled_nonstretched_cloth(self):
        result = validate_simulation([1., 2.], [1.001, 2.], .0002, 0.)
        self.assertAlmostEqual(result['max_edge_stretch_ratio'], 1.001)
        self.assertEqual(result['status'], 'passed')

    def test_preserve_stretched_result_as_failed_without_rescaling(self):
        result = validate_simulation([1.], [1.02], 0., 0.)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reasons'], ['stretch_exceeded'])
        self.assertEqual(result['max_edge_stretch_ratio'], 1.02)

    def test_preserve_penetration_and_unsettled_cloth_with_all_reasons(self):
        result = validate_simulation([1.], [1.02], .003, .002)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['failure_reasons'], ['stretch_exceeded','unsettled','body_penetration'])
        self.assertEqual(result['sampled_max_penetration_m'], .002)
        with self.assertRaises(ValueError):
            validate_simulation([1.], [1.], float('nan'), 0.)

    def test_reject_invalid_edges(self):
        for rest, final in [([], []), ([1.], []), ([0.], [1.]), ([1.], [float('nan')])]:
            with self.subTest(rest=rest, final=final), self.assertRaises(ValueError):
                validate_simulation(rest, final, 0., 0.)

    def test_collision_asset_is_bound_to_owner(self):
        digest = 'a'*64
        self.assertEqual(body_path('alice', digest),
                         f'v2/avatars/{sha256(b"alice").hexdigest()}/{digest}/model.glb')
        self.assertNotEqual(body_path('alice', digest), body_path('bob', digest))
        for invalid in ['../model', 'https://example.com', 'A'*64, 'a'*63]:
            with self.assertRaises(ValueError):
                body_path('alice', invalid)


if __name__ == '__main__':
    unittest.main()
