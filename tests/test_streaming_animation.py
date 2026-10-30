"""Recover only Webots R2023b's missing first-frame states, without guessing poses."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json, sys
sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from MatchAnimation import read_animation

header = '{"basicTimeStep":32,"labelsIds":"10","frames":[{"time":0,"updates":'
tail = ',{"time":0,"updates":[{"id":1,"translation":"0 0 0"},{"id":2,"rotation":"0 1 0 0"}]},{"time":32,"updates":[{"id":1,"translation":"1 0 0"}],"labels":[{"text":"literal \\\"updates\\\":[,,]"}]}]}'
scene = '<X3D><Scene><Transform id="n1" translation="1000 1000 1000"/><Transform id="n2" rotation="0 0 1 1"/><Transform id="n3" rotation="0 1 0 0"/></Scene></X3D>'
with TemporaryDirectory() as folder:
    path = Path(folder)/'replay.json'
    xml = path.with_suffix('.x3d')
    xml.write_text(scene, encoding='utf-8')
    for initial in ('[,]', '[,,{"id":3,"rotation":"0 1 0 0"}]'):
        path.write_text(header+initial+'}'+tail, encoding='utf-8')
        data = read_animation(path)
        first = {u['id']: u for u in data['frames'][0]['updates']}
        assert first[1]['translation'] == '1000 1000 1000'
        assert first[2]['rotation'] == '0 0 1 1'
        assert data['frames'][1]['updates'][0]['translation'] == '0 0 0'
        assert data['frames'][2]['updates'][0]['translation'] == '1 0 0'
        assert data['frames'][2]['labels'][0]['text'] == 'literal "updates":[,,]'
        before = path.read_bytes()
        assert read_animation(path) == data and path.read_bytes() == before
    invalid = [header+'[,,]}'+tail, header+'[,]}'+tail.replace('"time":32','"time":bad'), header+'[null,,]}'+tail, header+'[,   ']
    for text in invalid:
        path.write_text(text, encoding='utf-8')
        before = path.read_bytes()
        try:
            read_animation(path)
        except ValueError:
            pass
        else:
            raise AssertionError('Unrecognized corruption accepted')
        assert path.read_bytes() == before
    for invalid_scene in ('<X3D><Scene/></X3D>', '<X3D>'):
        path.write_text(header+'[,]}'+tail, encoding='utf-8')
        xml.write_text(invalid_scene, encoding='utf-8')
        before = path.read_bytes()
        try:
            read_animation(path)
        except ValueError:
            pass
        else:
            raise AssertionError('Unavailable initial state accepted')
        assert path.read_bytes() == before
print('PASS: streaming first-frame recovery, exact scene poses, later motion/labels, idempotence and fail-closed corruption guards.')
