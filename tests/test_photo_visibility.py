# 역할: 전신 프레이밍 검사에서 부분 사진·근거 누락을 차단하고 정상 전신과 넓은 팔 자세를 유지합니다.
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'avatar/src'))
from core.photo_visibility import FULL_BODY_PHOTO_MESSAGE, PhotoFramingError, validate_full_body


def person():
    keypoints=np.full((70,2),(300.,500.))
    keypoints[:21]=((300,100),(290,90),(310,90),(280,100),(320,100),
                    (230,220),(370,220),(190,370),(410,370),(270,510),(330,510),
                    (260,700),(340,700),(255,880),(345,880),
                    (245,950),(250,948),(260,935),(355,950),(350,948),(340,935))
    keypoints[41]=(180,480);keypoints[62]=(420,480)
    return {'bbox':np.array((150.,70.,450.,960.)),'pred_keypoints_2d':keypoints}


class PhotoVisibilityTests(unittest.TestCase):
    def assert_rejected(self,data,reason,shape=(1000,600,3)):
        with self.assertRaises(PhotoFramingError) as caught:validate_full_body(data,shape)
        self.assertEqual(caught.exception.reason,reason)
        self.assertEqual(caught.exception.reason_code,reason)
        self.assertEqual(str(caught.exception),reason)
        self.assertEqual(caught.exception.public_message,FULL_BODY_PHOTO_MESSAGE)

    def test_supported_whole_body_returns_plain_json_framing_evidence(self):
        report=validate_full_body(person(),(1000,600,3))
        self.assertTrue(report['passed'])
        self.assertEqual(report['schema_version'],1)
        self.assertEqual(report['method'],'sam_projected_full_body_v1')
        self.assertEqual(report['required_keypoint_count'],23)
        self.assertFalse(report['independent_visibility_confidence_available'])
        self.assertAlmostEqual(report['bbox_margins_ratio']['bottom'],.04)
        self.assertEqual(json.loads(json.dumps(report)),report)
        self.assertEqual(validate_full_body(person(),(1000,600)),report)

    def test_person_box_touching_each_image_edge_is_rejected(self):
        for label,index,value in (('head_crop',1,0.),('feet_crop',3,1000.),
                                  ('left_crop',0,0.),('right_crop',2,600.)):
            with self.subTest(label=label):
                data=person();data['bbox'][index]=value
                self.assert_rejected(data,'person_touches_image_boundary')

    def test_margin_boundary_passes_but_any_smaller_margin_is_rejected(self):
        data=person();data['bbox']=np.array((2.,3.,598.,997.))
        self.assertTrue(validate_full_body(data,(1000,600,3))['passed'])
        for index,change in ((0,-1e-6),(1,-1e-6),(2,1e-6),(3,1e-6)):
            with self.subTest(index=index):
                data=person();data['bbox']=np.array((2.,3.,598.,997.));data['bbox'][index]+=change
                self.assert_rejected(data,'person_touches_image_boundary')

    def test_head_feet_core_and_wrists_outside_image_are_rejected(self):
        for index,position in ((0,(300.,-11.)),(20,(300.,1011.)),
                               (9,(-7.,500.)),(41,(607.,500.)),(62,(-7.,500.))):
            with self.subTest(index=index):
                data=person();data['pred_keypoints_2d'][index]=position
                self.assert_rejected(data,'required_keypoints_outside_image')

    def test_full_body_extrapolated_outside_detection_box_is_rejected(self):
        for label,box in (('upper_body_only',(150,70,450,600)),
                          ('lower_body_only',(150,450,450,960)),
                          ('head_outside_support',(150,200,450,960)),
                          ('hand_outside_support',(260,70,450,960))):
            with self.subTest(label=label):
                data=person();data['bbox']=np.array(box)
                self.assert_rejected(data,'required_keypoints_outside_person_box')

    def test_box_support_tolerance_uses_person_height_not_image_height(self):
        data=person();data['bbox']=np.array((150.,100.,450.,950.))
        tolerance=.06*850
        data['pred_keypoints_2d'][0]=(300.,100.-tolerance)
        self.assertTrue(validate_full_body(data,(1000,600,3))['passed'])
        data['pred_keypoints_2d'][0,1]-=.01
        self.assert_rejected(data,'required_keypoints_outside_person_box')

    def test_wide_a_pose_is_accepted_without_body_aspect_ratio_heuristic(self):
        data=person();data['pred_keypoints_2d'][:,0]+=500
        data['bbox']=np.array((20.,40.,1580.,960.))
        data['pred_keypoints_2d'][41]=(30.,480.)
        data['pred_keypoints_2d'][62]=(1570.,480.)
        report=validate_full_body(data,(1000,1600,3))
        self.assertTrue(report['passed'])
        self.assertGreater((data['bbox'][2]-data['bbox'][0])/(data['bbox'][3]-data['bbox'][1]),1.6)

    def test_missing_evidence_never_bypasses_gate(self):
        for data in (None,[],{}, {'bbox':[1,2,3,4]}, {'pred_keypoints_2d':np.zeros((70,2))}):
            with self.subTest(data=data):self.assert_rejected(data,'missing_body_evidence')

    def test_invalid_box_shape_order_values_and_type_fail_closed(self):
        for box in ((150,70,450),((150,70,450,960),), (450,70,150,960),
                    (150,960,450,70),(150,70,150,960),(150,70,450,float('nan')),
                    (150,70,450,float('inf')),(True,True,True,True),('150','70','450','960')):
            with self.subTest(box=box):
                data=person();data['bbox']=box;self.assert_rejected(data,'invalid_bbox')

    def test_invalid_keypoint_shape_values_and_type_fail_closed(self):
        invalid=[np.ones((69,2)),np.ones((70,3)),np.ones(140),
                 np.full((70,2),True),np.full((70,2),'1'),
                 np.full((70,2),np.nan),np.full((70,2),np.inf)]
        data=person();bad=data['pred_keypoints_2d'].copy();bad[69,0]=np.nan;invalid.append(bad)
        for points in invalid:
            with self.subTest(points=points):
                data=person();data['pred_keypoints_2d']=points
                self.assert_rejected(data,'invalid_keypoints')

    def test_invalid_image_dimensions_fail_closed(self):
        for shape in (None,(),(1000,), (0,600,3),(-1,600,3),(1000,True,3),
                      (1000,600.,3),(1000,600,0),(1000,600,True),(1000,600,3,1)):
            with self.subTest(shape=shape):self.assert_rejected(person(),'invalid_image_shape',shape)

    def test_unknown_error_reason_cannot_be_logged_as_arbitrary_user_data(self):
        for reason in ('untrusted-person-data',None,{},[]):
            error=PhotoFramingError(reason)
            self.assertEqual(str(error),'missing_body_evidence')
            self.assertEqual(error.reason,'missing_body_evidence')


if __name__=='__main__':unittest.main()
