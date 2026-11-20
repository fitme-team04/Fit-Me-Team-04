# 역할: 확정 상의의 몸통·어깨·소매 기준을 보존하면서 네 치수의 변화량을 부드럽게 적용합니다.
import numpy as np
def smooth(value):
    value = np.clip(value, 0., 1.)
    return value*value*(3.-2.*value)


def reshape(vertices, entry, baseline, spec, basis):
    if entry.get('deformation_policy')=='shape_preserving_center_back_v1':
        from geometry.garment_cages import back_neck_path
        baseline={**baseline,'sleeve_length':baseline['sleeve_length']-back_neck_path(baseline['garment_shoulder_width'])}
        if basis=='center_back':
            spec={**spec,'sleeve_length':spec['sleeve_length']-back_neck_path(spec['garment_shoulder_width'])}
        elif basis!='shoulder':raise ValueError('Unsupported sleeve basis')
        if spec['sleeve_length']<=0:raise ValueError('Full arm length does not reach the shoulder')
    elif basis != 'shoulder':
        raise ValueError('Shape-preserving shirt requires shoulder-based sleeve measurements')
    ratios = {key: spec[key]/baseline[key] for key in baseline}
    if entry.get('deformation_policy')!='shape_preserving_center_back_v1' and any(not .90 <= value <= 1.10 for value in ratios.values()):
        raise ValueError('Shape-preserving shirt supports 90..110 percent of its base settings')
    width = ratios['chest_width']
    shoulder = ratios['garment_shoulder_width']
    length = ratios['body_length']
    sleeve = ratios['sleeve_length']
    # Keep the original waist inset and sleeve cross-section, rather than adding cage offsets.
    top = baseline['garment_shoulder_width']/100*.15
    upper = smooth((vertices[:, 2]+.20)/.18)
    torso = vertices.copy()
    torso[:, 0] *= width*(1-upper)+shoulder*upper
    torso[:, 1] *= width
    lower = smooth((-vertices[:, 2]-.02)/.18)
    torso[:, 2] += (vertices[:, 2]-top)*(length-1)*lower
    moved = torso.copy()
    anchors = {'fit_anchor': np.zeros(3)}
    for label, side in (('L', 1), ('R', -1)):
        start = np.array(entry['anchor_bindings']['fit_shoulder_'+label]['reference'])
        end = np.array(entry['anchor_bindings']['fit_cuff_'+label]['reference'])
        axis = end-start
        axis /= np.linalg.norm(axis)
        relative = vertices-start
        axial = relative@axis
        radial = relative-axial[:, None]*axis
        target = start.copy()
        target[0] *= shoulder
        arm = target+axial[:, None]*sleeve*axis+radial*np.sqrt(width)
        weight = smooth((side*vertices[:, 0]-.12)/.13)*smooth((axial+.025)/.10)
        moved = moved*(1-weight[:, None])+arm*weight[:, None]
        anchors['fit_shoulder_'+label] = target
        anchors['fit_cuff_'+label] = target+(end-start)*sleeve
    return moved, anchors
