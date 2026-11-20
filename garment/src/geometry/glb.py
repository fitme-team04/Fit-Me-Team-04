# 역할: GLB 바이너리를 구성·해석하고 메시와 앵커를 내보냅니다.
"""Static mannequin GLB, no temporary/export files. Positions are in metres."""
import json
import struct
import numpy as np

def to_gltf(p):
    return np.column_stack((p[:,0], p[:,2], -p[:,1]))

def pack(doc, binary):
    header=json.dumps(doc, separators=(',',':'), allow_nan=False).encode()
    header+=b' '*(-len(header)%4)
    binary=bytes(binary)+b'\0'*(-len(binary)%4)
    return (struct.pack('<4sII',b'glTF',2,28+len(header)+len(binary))
            +struct.pack('<I4s',len(header),b'JSON')+header
            +struct.pack('<I4s',len(binary),b'BIN\0')+binary)

def unpack(data):
    size=struct.unpack_from('<I',data,12)[0]
    doc=json.loads(data[20:20+size])
    return doc,data[28+size:]

def body_positions(data):
    doc,buf=unpack(data)
    index=doc['meshes'][0]['primitives'][0]['attributes']['POSITION']
    a=doc['accessors'][index]
    v=doc['bufferViews'][a['bufferView']]
    p=np.frombuffer(buf,'<f4',count=a['count']*3,offset=v['byteOffset']).reshape(-1,3).astype(float)
    return np.column_stack((p[:,0],-p[:,2],p[:,1]))

def export(parts,anchors):
    binary=bytearray()
    doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
         'nodes':[{'name':'FitMeAvatar','children':[]}],'meshes':[],
         'buffers':[],'bufferViews':[],'accessors':[]}
    def accessor(a,typ,component,bounds=False):
        start=len(binary)
        binary.extend(a.tobytes())
        i=len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start})
        entry={'bufferView':i,'componentType':component,'type':typ,'count':len(a)}
        if bounds:entry.update(min=a.min(0).tolist(),max=a.max(0).tolist())
        doc['accessors'].append(entry)
        return i
    for name,vertices,faces in parts:
        p=to_gltf(vertices).astype('<f4')
        faces=faces.astype('<u4')
        normals=np.zeros_like(p)
        t=p[faces]
        face_normals=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])
        for col in faces.T:np.add.at(normals,col,face_normals)
        norms=np.linalg.norm(normals,axis=1)
        normals[norms==0]=[0,1,0]
        normals/=np.linalg.norm(normals,axis=1)[:,None]
        prim={'attributes':{'POSITION':accessor(p,'VEC3',5126,True),
                            'NORMAL':accessor(normals,'VEC3',5126)},
              'indices':accessor(faces.ravel(),'SCALAR',5125)}
        doc['nodes'].append({'name':name,'mesh':len(doc['meshes'])})
        doc['meshes'].append({'primitives':[prim]})
    doc['nodes'].extend(anchors)
    doc['nodes'][0]['children']=list(range(1,len(doc['nodes'])))
    doc['buffers']=[{'byteLength':len(binary)}]
    return pack(doc,binary)
