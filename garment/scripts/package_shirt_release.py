# 역할: 확정한 상의 모델과 치수 재생성 자료를 Blob 업로드용 폴더와 ZIP으로 묶습니다.
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--body', type=Path, required=True)
    parser.add_argument('--measurements', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new output directory to preserve existing releases')
    release = args.release.resolve()
    registry = json.loads((release / 'models/registry.json').read_text(encoding='utf-8'))
    if len(registry['templates']) != 1:
        raise ValueError('Expected exactly one approved shirt')
    template_id, entry = next(iter(registry['templates'].items()))
    validation = json.loads((release / 'output/delivered-glb-validation.json').read_text())[template_id]
    if validation['body_triangle_intersections'] or any(validation[k]['inside'] for k in ('vertices', 'edge_midpoints', 'triangle_centroids')):
        raise ValueError('Release has not passed body clearance checks')
    output.mkdir(parents=True)
    shutil.copytree(release / 'models', output / 'models', ignore=shutil.ignore_patterns('*.blend1'))
    for name in ('model.glb', 'anchors.json'):
        target = output / 'preview' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(release / 'output' / template_id / name, target)
    for name in ('garment-spec.json', 'proportional-report.json'):
        shutil.copy2(release / name, output / name)
    shutil.copy2(release / 'output/delivered-glb-validation.json', output / 'validation.json')
    for source, name in ((args.body, 'body.glb'), (args.measurements, 'body-measurements.json')):
        target = output / 'reference' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
    for folder in ('scripts', 'src'):
        for source in (root / folder).rglob('*.py'):
            target = output / 'code' / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    shutil.copytree(root / 'architecture', output / 'architecture', ignore=shutil.ignore_patterns('*.sh'))
    import re
    for name in ('ARCHITECTURE', 'FILE_CONNECTIONS'):
        blocks = re.findall(r'```mermaid\s*\n(.*?)```', (output / 'architecture' / (name + '.md')).read_text(encoding='utf-8'), re.S)
        if blocks:
            (output / 'architecture' / (name + '.mmd')).write_text(blocks[-1], encoding='utf-8')
    shutil.copy2(root / 'docs/shirt-blob-release.md', output / 'README.md')
    configuration = {
        'container': 'avatar-models', 'blob_prefix': 'garments/crewneck/v18',
        'template_id': template_id, 'local_template_subdirectory': 'models',
        'base_spec_cm': entry['base_spec'], 'deformation_policy': entry['deformation_policy'],
        'automatic_blob_download_implemented': False,
    }
    (output / 'release.json').write_text(json.dumps(configuration, indent=2) + '\n', encoding='utf-8')
    manifest = {}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            manifest[path.relative_to(output).as_posix()] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    archive = output.with_suffix('.zip')
    if archive.exists():
        raise ValueError('Archive already exists')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in output.rglob('*'):
            if path.is_file():
                z.write(path, path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Archive verification failed')
    print(json.dumps({'folder': str(output), 'zip': str(archive), 'files': len(manifest) + 1}))


if __name__ == '__main__':
    main()
