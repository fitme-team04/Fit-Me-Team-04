# 역할: SAM의 원본 사진 투영 좌표와 사람 검출 영역으로 전신 프레이밍을 검사합니다.
"""Conservative framing gate, not an independent visibility/occlusion detector.

SAM keypoints are projections of the predicted 3D person. Their presence inside
the image does not prove that the corresponding anatomy was actually observed.
The detector box adds image support, but this gate cannot guarantee visibility
behind objects or remove every amodal full-body hallucination.
"""
from collections.abc import Mapping
from numbers import Integral

import numpy as np


FULL_BODY_PHOTO_MESSAGE='머리부터 양쪽 발끝까지 잘리지 않고 보이도록 조금 뒤로 물러나 전신 사진을 다시 촬영해 주세요.'
_REQUIRED_KEYPOINTS=tuple(range(21))+(41,62)
_IMAGE_TOLERANCE_RATIO=.01
_BOX_SUPPORT_TOLERANCE_RATIO=.06
_REASONS=frozenset(('invalid_image_shape','missing_body_evidence','invalid_bbox',
                    'invalid_keypoints','person_touches_image_boundary',
                    'required_keypoints_outside_image','required_keypoints_outside_person_box'))


class PhotoFramingError(ValueError):
    def __init__(self,reason):
        if not isinstance(reason,str) or reason not in _REASONS:reason='missing_body_evidence'
        self.reason=self.reason_code=reason
        self.public_message=FULL_BODY_PHOTO_MESSAGE
        super().__init__(reason)


def _array(value,reason):
    try:
        values=np.asarray(value)
        if values.dtype.kind not in 'fiu':raise ValueError('Expected numeric coordinates')
        values=np.asarray(values,dtype=float)
    except (TypeError,ValueError,OverflowError) as exc:
        raise PhotoFramingError(reason) from exc
    if not np.isfinite(values).all():raise PhotoFramingError(reason)
    return values


def _image_size(shape):
    try:
        if len(shape) not in (2,3):raise ValueError('Expected image dimensions')
        height,width=shape[:2]
        if any(not isinstance(value,Integral) or isinstance(value,(bool,np.bool_)) or value<=0
               for value in (height,width)):
            raise ValueError('Expected positive integer dimensions')
        if len(shape)==3 and (not isinstance(shape[2],Integral)
                             or isinstance(shape[2],(bool,np.bool_)) or shape[2]<=0):
            raise ValueError('Expected channel dimension')
        return int(height),int(width)
    except (TypeError,ValueError,IndexError,OverflowError) as exc:
        raise PhotoFramingError('invalid_image_shape') from exc


def validate_full_body(person,image_shape):
    """Reject unsupported/cropped MHR70 framing before canonical pose conversion.

    person['bbox'] is the original-image XYXY detection box. Keypoints must be
    SAM's original-image Nx2 pixel projections in MHR70 order (at least 70).
    No aspect ratio, body shape, gender or physical measurement heuristic is
    used. Missing/malformed evidence fails closed rather than bypassing checks.
    """
    height,width=_image_size(image_shape)
    if not isinstance(person,Mapping) or not {'bbox','pred_keypoints_2d'}<=person.keys():
        raise PhotoFramingError('missing_body_evidence')
    box=_array(person['bbox'],'invalid_bbox')
    if box.shape!=(4,) or not box[0]<box[2] or not box[1]<box[3]:
        raise PhotoFramingError('invalid_bbox')
    keypoints=_array(person['pred_keypoints_2d'],'invalid_keypoints')
    if keypoints.ndim!=2 or keypoints.shape[0]<70 or keypoints.shape[1]!=2:
        raise PhotoFramingError('invalid_keypoints')
    required=keypoints[list(_REQUIRED_KEYPOINTS)]
    x1,y1,x2,y2=(float(value) for value in box)
    horizontal_margin=max(2.,.003*width);vertical_margin=max(2.,.003*height)
    box_margins={'left':x1/width,'right':(width-x2)/width,
                 'top':y1/height,'bottom':(height-y2)/height}
    if (x1<horizontal_margin or width-x2<horizontal_margin
            or y1<vertical_margin or height-y2<vertical_margin):
        raise PhotoFramingError('person_touches_image_boundary')
    min_x,min_y=required.min(axis=0);max_x,max_y=required.max(axis=0)
    image_margins={'left':float(min_x/width),'right':float((width-max_x)/width),
                   'top':float(min_y/height),'bottom':float((height-max_y)/height)}
    if min(image_margins.values()) < -_IMAGE_TOLERANCE_RATIO:
        raise PhotoFramingError('required_keypoints_outside_image')
    box_height=y2-y1
    support_margins={'left':float((min_x-x1)/box_height),
                     'right':float((x2-max_x)/box_height),
                     'top':float((min_y-y1)/box_height),
                     'bottom':float((y2-max_y)/box_height)}
    if min(support_margins.values()) < -_BOX_SUPPORT_TOLERANCE_RATIO:
        raise PhotoFramingError('required_keypoints_outside_person_box')
    return {'schema_version':1,'method':'sam_projected_full_body_v1','passed':True,
            'image_width_px':width,'image_height_px':height,
            'required_keypoint_count':len(_REQUIRED_KEYPOINTS),
            'bbox_margins_ratio':box_margins,
            'bbox_minimum_margin_ratio':{'horizontal':horizontal_margin/width,
                                         'vertical':vertical_margin/height},
            'required_keypoint_image_margins_ratio':image_margins,
            'required_keypoint_bbox_margins_per_bbox_height':support_margins,
            'keypoint_image_tolerance_ratio':_IMAGE_TOLERANCE_RATIO,
            'bbox_support_tolerance_ratio':_BOX_SUPPORT_TOLERANCE_RATIO,
            'independent_visibility_confidence_available':False}
