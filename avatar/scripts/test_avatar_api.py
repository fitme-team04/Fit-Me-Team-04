# 역할: 지정한 전신 사진으로 실제 신체 API를 호출하고 GLB·기준점·치수 결과를 다운로드·검증합니다.
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from geometry.mesh_anchors import extract


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def read_bytes(opener, request, timeout, maximum):
    with opener.open(request, timeout=timeout) as response:
        data = response.read(maximum+1)
        if len(data)>maximum:
            raise ValueError('Response exceeds test size limit')
        return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--photo',required=True,type=Path)
    parser.add_argument('--height-cm',required=True,type=float)
    parser.add_argument('--weight-kg',required=True,type=float)
    parser.add_argument('--subject',required=True,help='Authenticated test account ID; run from trusted web VM')
    parser.add_argument('--url',default='http://10.4.2.4:8001/api/avatars')
    parser.add_argument('--output',type=Path,required=True,help='New private result directory')
    args=parser.parse_args()
    if not args.subject.isascii() or not args.subject.isprintable() or not 1<=len(args.subject)<=255:
        parser.error('Invalid test account ID')
    address=urlsplit(args.url)
    if (address.username or address.password or address.query or address.fragment
            or address.path!='/api/avatars' or not
            (address.scheme=='https' or address.scheme=='http' and address.hostname in {'10.4.2.4','127.0.0.1','localhost'})):
        parser.error('Use the private body API or an authenticated HTTPS ingress')
    if not 0<args.height_cm<1000 or not 0<args.weight_kg<1000:
        parser.error('Invalid height or weight')
    if args.photo.stat().st_size>3*1024*1024:
        parser.error('Photo exceeds 3 MiB')
    photo=args.photo.read_bytes()
    mime='image/png' if photo.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if photo.startswith(b'\xff\xd8\xff') else None
    if mime is None:
        parser.error('Expected an explicitly selected JPEG or PNG photograph')
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    report={'status':'running','started_at':datetime.now(timezone.utc).isoformat()}
    opener=build_opener(ProxyHandler({}), NoRedirect())
    try:
        request=Request(args.url,data=photo,method='POST',headers={
            'Content-Type':mime,'Accept':'application/json','height-cm':str(args.height_cm),
            'weight-kg':str(args.weight_kg),'X-FitMe-Subject':args.subject})
        receipt=json.loads(read_bytes(opener,request,600,65536))
        digest=receipt.get('model_id','')
        if receipt.get('status')!='ready' or not re.fullmatch(r'[0-9a-f]{64}',digest):
            raise ValueError('Invalid completed model receipt')
        owner=hashlib.sha256(args.subject.encode()).hexdigest()
        prefix=f'/body-glb/v2/avatars/{owner}/{digest}/'
        files={}
        for name,limit in [('model.glb',128*1024*1024),('anchors.json',2*1024*1024),('measurements.json',2*1024*1024)]:
            url=receipt.get('urls',{}).get(name,'')
            parsed=urlsplit(url)
            query=parse_qs(parsed.query)
            if (parsed.scheme!='https' or parsed.hostname!='fitmemlstdev.blob.core.windows.net'
                    or parsed.port not in (None,443) or parsed.username or parsed.password
                    or parsed.fragment or parsed.path!=prefix+name
                    or query.get('sp')!=['r'] or query.get('sr')!=['b'] or not query.get('sig')):
                raise ValueError('Unexpected result Blob link')
            files[name]=read_bytes(opener,Request(url),120,limit)
            (args.output/name).write_bytes(files[name])
        glb=files['model.glb']
        if (hashlib.sha256(glb).hexdigest()!=digest or len(glb)<20 or glb[:4]!=b'glTF'
                or struct.unpack_from('<II',glb,4)!=(2,len(glb))):
            raise ValueError('GLB integrity verification failed')
        anchors=json.loads(files['anchors.json'])
        measurements=json.loads(files['measurements.json'])
        for metadata in (anchors,measurements):
            if metadata.get('schema_version')!=1 or metadata.get('model_sha256')!=digest:
                raise ValueError('Result metadata differs from model')
        if not isinstance(anchors.get('anchors'),dict) or not anchors['anchors'] or not measurements.get('measurements'):
            raise ValueError('Missing anchors or measurement report')
        parent, actual_anchors, actual_measures=extract(glb,'avatars')
        if (parent!=anchors.get('parent_node') or actual_anchors!=anchors['anchors']
                or actual_measures!=measurements['measurements']):
            raise ValueError('Downloaded metadata differs from actual GLB anchors or measurements')
        report.update(status='passed',model_id=digest,glb_bytes=len(glb),
                      anchors=len(anchors['anchors']),measurement_fields=len(measurements['measurements']))
        print('PASS: actual photo inference, Blob result download, GLB hash and result metadata')
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__)
        if isinstance(error,HTTPError): report['http_status']=error.code
        print('FAIL: see test-result.json for the sanitized result; no signed links or credentials printed')
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        (args.output/'test-result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    sys.exit(main())
