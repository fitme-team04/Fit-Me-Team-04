# 역할: 팔축에 수직인 단면의 실제 중심과 두께를 분리해 소매 프로파일을 계산합니다.
import math
from numbers import Integral

import numpy as np


def _vector(value,label):
    try:result=np.asarray(value,dtype=float)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid '+label) from exc
    if result.shape!=(3,) or not np.isfinite(result).all():
        raise ValueError('Invalid '+label)
    return result


def _axis(value):
    axis=_vector(value,'arm profile axis');length=math.hypot(*axis)
    if not math.isfinite(length) or length<1e-12:
        raise ValueError('Degenerate arm profile axis')
    return axis/length


def radial_basis(axis,preferred=(0.,1.,0.)):
    """Return a (3,2) orthonormal basis with a stable preferred front direction."""
    axis=_axis(axis);preferred=_vector(preferred,'arm profile front direction')
    length=math.hypot(*preferred)
    if not math.isfinite(length) or length<1e-12:
        raise ValueError('Degenerate arm profile front direction')
    preferred=preferred/length
    first=preferred-axis*float(preferred@axis)
    length=math.hypot(*first)
    if length<1e-8:
        reference=np.zeros(3);reference[int(np.argmin(np.abs(axis)))]=1.
        first=reference-axis*float(reference@axis);length=math.hypot(*first)
    first/=length
    second=np.cross(axis,first)
    return np.column_stack((first,second))


def ellipse_section(loop,origin,axis,basis=None,clearance_m=0.):
    """Describe a planar contour independently of its offset from the arm axis.

    The area centroid is insensitive to extra vertices along the same polygon
    edges. Radii enclose all contour points before adding physical clearance.
    center is a world position; offset/radii use the returned front/side basis.
    """
    axis=_axis(axis);origin=_vector(origin,'arm profile origin')
    try:
        points=np.asarray(loop,dtype=float)
        clearance=float(clearance_m)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid arm profile contour or clearance') from exc
    if (points.ndim!=2 or points.shape[1]!=3 or len(points)<3
            or not np.isfinite(points).all()):
        raise ValueError('Invalid arm profile contour')
    if isinstance(clearance_m,(bool,str,bytes)) or not math.isfinite(clearance) or clearance<0:
        raise ValueError('Invalid arm profile clearance')
    if basis is None:basis=radial_basis(axis)
    else:
        try:basis=np.asarray(basis,dtype=float)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError('Invalid arm profile basis') from exc
        if (basis.shape!=(3,2) or not np.isfinite(basis).all()
                or not np.allclose(basis.T@basis,np.eye(2),atol=1e-7,rtol=0)
                or not np.allclose(axis@basis,0,atol=1e-7,rtol=0)):
            raise ValueError('Arm profile basis must be orthonormal and perpendicular to axis')
    relative=points-origin
    if np.max(np.abs(relative@axis))>1e-5:
        raise ValueError('Arm contour does not lie in the requested section plane')
    projected=relative@basis
    # Translate before the shoelace products to avoid subtracting large offsets.
    shifted=projected-projected[0]
    following=np.roll(shifted,-1,axis=0)
    cross=shifted[:,0]*following[:,1]-following[:,0]*shifted[:,1]
    double_area=float(np.sum(cross))
    area=abs(double_area)/2
    if not math.isfinite(area) or area<=0:
        raise ValueError('Arm profile contour must have positive finite area')
    offset=projected[0]+np.sum((shifted+following)*cross[:,None],axis=0)/(3*double_area)
    centered=projected-offset
    radii=np.maximum(np.max(np.abs(centered),axis=0),.001)
    enclosure_scale=max(1.,float(np.max(np.linalg.norm(centered/radii,axis=1))))
    radii=radii*enclosure_scale+clearance
    perimeter=float(np.sum(np.linalg.norm(points-np.roll(points,-1,axis=0),axis=1)))
    center=origin+basis@offset
    if (not np.isfinite(center).all() or not np.isfinite(offset).all()
            or not np.isfinite(radii).all() or not math.isfinite(perimeter) or perimeter<=0):
        raise ValueError('Non-finite arm profile result')
    return {'center':center,'offset':offset,'radii':radii,'perimeter_m':perimeter,
            'area_m2':area,'enclosure_scale':enclosure_scale}


def _convex_hull(points):
    ordered=sorted(set(tuple(point) for point in points))
    if len(ordered)<3:raise ValueError('Arm profile hull needs three distinct points')
    scale=max(float(np.max(np.ptp(points,axis=0))),1e-12)
    epsilon=scale*scale*1e-12
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def chain(sequence):
        result=[]
        for point in sequence:
            while len(result)>=2 and cross(result[-2],result[-1],point)<=epsilon:
                result.pop()
            result.append(point)
        return result
    hull=np.asarray(chain(ordered)[:-1]+chain(reversed(ordered))[:-1])
    if len(hull)<3:raise ValueError('Arm profile hull must have positive area')
    return hull


def offset_radial_profile(loop,origin,axis,basis=None,clearance_m=.01,samples=64):
    """Offset the actual convex contour without replacing its shape by an ellipse.

    angles_radii contains one radius at each equally spaced angle, starting at
    zero without repeating 2*pi. The centroid offset remains separate from arm
    thickness. target_perimeter_m measures the sampled profile polygon, whose
    chords may cut a sharp corner between samples; miter_perimeter_m measures
    the exact convex half-plane offset polygon.
    """
    if not isinstance(samples,Integral) or isinstance(samples,bool) or samples<16:
        raise ValueError('Arm radial profile needs at least 16 angular samples')
    samples=int(samples)
    section=ellipse_section(loop,origin,axis,basis=basis,clearance_m=clearance_m)
    origin=_vector(origin,'arm profile origin');axis=_axis(axis)
    basis=radial_basis(axis) if basis is None else np.asarray(basis,dtype=float)
    clearance=float(clearance_m)
    centered=(np.asarray(loop,dtype=float)-origin)@basis-section['offset']
    hull=_convex_hull(centered)
    edges=np.roll(hull,-1,axis=0)-hull
    lengths=np.linalg.norm(edges,axis=1)
    if not np.isfinite(lengths).all() or np.any(lengths<=0):
        raise ValueError('Invalid arm profile hull edges')
    normals=np.column_stack((edges[:,1],-edges[:,0]))/lengths[:,None]
    supports=np.sum(normals*hull,axis=1)
    if not np.isfinite(supports).all() or np.any(supports<=0):
        raise ValueError('Arm profile area centroid must lie inside its convex hull')
    target_supports=supports+clearance
    angles=np.arange(samples,dtype=float)*(2*math.pi/samples)
    directions=np.column_stack((np.cos(angles),np.sin(angles)))
    denominators=normals@directions.T
    intersections=np.full(denominators.shape,np.inf)
    np.divide(target_supports[:,None],denominators,out=intersections,where=denominators>1e-12)
    radii=np.min(intersections,axis=0)
    profile=directions*radii[:,None]
    target_perimeter=float(np.sum(np.linalg.norm(profile-np.roll(profile,-1,axis=0),axis=1)))
    expanded=[]
    for i in range(len(hull)):
        previous=(i-1)%len(hull)
        matrix=normals[[previous,i]]
        if abs(float(np.linalg.det(matrix)))<1e-12:
            raise ValueError('Unstable arm profile miter intersection')
        expanded.append(np.linalg.solve(matrix,target_supports[[previous,i]]))
    expanded=np.asarray(expanded)
    miter_perimeter=float(np.sum(np.linalg.norm(expanded-np.roll(expanded,-1,axis=0),axis=1)))
    if (not np.isfinite(radii).all() or np.any(radii<=0) or not np.isfinite(expanded).all()
            or not math.isfinite(target_perimeter) or target_perimeter<=0
            or not math.isfinite(miter_perimeter) or miter_perimeter<=0):
        raise ValueError('Non-finite arm radial offset profile')
    return {**section,'method':'convex_hull_miter_radial_offset','angles_radii':radii,
            'angles':angles,'samples':samples,'clearance_m':clearance,
            'body_hull_perimeter_m':float(np.sum(lengths)),
            'target_perimeter_m':target_perimeter,'miter_perimeter_m':miter_perimeter,
            'hull_vertices_2d':hull,'hull_normals_2d':normals,'hull_support_m':supports}


def sample_radial_profiles(radii,angles):
    """Sample one periodic angular radius table per point using linear interpolation."""
    try:
        source=np.asarray(radii);directions=np.asarray(angles)
        if source.dtype.kind not in 'fiu' or directions.dtype.kind not in 'fiu':
            raise ValueError('Invalid radial profile sample values')
        source=np.asarray(source,dtype=float);directions=np.asarray(directions,dtype=float)
    except (TypeError,ValueError,OverflowError) as exc:
        raise ValueError('Invalid radial profile sample arrays') from exc
    if (source.ndim!=2 or source.shape[1]<16 or directions.ndim!=1
            or len(directions)!=len(source) or not np.isfinite(source).all()
            or np.any(source<=0) or not np.isfinite(directions).all()):
        raise ValueError('Radial profile samples require positive finite NxM tables and N angles')
    count=source.shape[1]
    angular=(directions%(2*math.pi))*count/(2*math.pi)
    floor=np.floor(angular)
    fraction=angular-floor
    # A tiny negative angle can round its modulo to exactly 2*pi. Wrap the
    # integer floor as well as the input angle to keep index count in range.
    left=floor.astype(np.int64)%count
    right=(left+1)%count
    rows=np.arange(len(source))
    return source[rows,left]*(1-fraction)+source[rows,right]*fraction
