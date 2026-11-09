"""Verify self-contained replay data; no browser rendering is claimed."""
from pathlib import Path
import sys,json,base64,re,shutil
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
from MatchAnimation import make_replay_portable
with TemporaryDirectory() as temp:
    folder=Path(temp)
    (folder/'textures').mkdir();(folder/'meshes').mkdir()
    (folder/'textures/a.png').write_bytes(b'png bytes')
    (folder/'meshes/test.stl').write_bytes(b'mesh bytes')
    (folder/'replay.jpg').write_bytes(b'thumbnail')
    scene='''<X3D><Scene><ImageTexture url='"textures/a.png"'/><Mesh url='"meshes/test.stl"'/><Background backUrl='"https://example.com/sky.jpg"'/></Scene></X3D>'''
    (folder/'replay.x3d').write_text(scene)
    animation={'frames':[{'time':0},{'time':1000,'labels':[{'text':'</script><script>bad</script>'}]}]}
    (folder/'replay.json').write_text(json.dumps(animation))
    (folder/'replay.css').write_text('body{margin:0}')
    html='''<html><head><link rel="stylesheet" href="replay.css"><script type="module" src="https://cyberbotics.com/wwi/R2023b/WebotsView.js"></script></head><body><webots-view data-scene=replay.x3d data-animation=replay.json data-thumbnail=replay.jpg data-autoplay="false"></webots-view><p id="match-current-event">No events yet</p></body></html>'''
    target=folder/'replay.html';target.write_text(html)
    make_replay_portable(target)
    text=target.read_text()
    assert 'data-scene=' not in text and 'data-animation=' not in text
    assert 'href="replay.css"' not in text and 'body{margin:0}' in text
    payload=json.loads(re.search(r'id="replay-package">(.*?)</script>',text,re.S)[1])
    assert payload['scene']==scene and payload['animation']==animation
    assert payload['autoplay'] is False
    assert base64.b64decode(payload['assets']['textures/a.png']['base64'])==b'png bytes'
    assert base64.b64decode(payload['assets']['meshes/test.stl']['base64'])==b'mesh bytes'
    assert base64.b64decode(payload['assets']['replay.jpg']['base64'])==b'thumbnail'
    assert '</script><script>bad' not in text
    assert 'match-current-event' in text
    make_replay_portable(target)
    assert target.read_text()==text,'Packaging must be idempotent'
    (folder/'replay.json').write_text('{"frames":[{"time":0},{"time":2000}]}')
    make_replay_portable(target)
    updated=json.loads(re.search(r'id="replay-package">(.*?)</script>',target.read_text(),re.S)[1])
    assert updated['animation']['frames'][-1]['time']==2000
    (folder/'textures/a.png').unlink()
    before=target.read_bytes()
    try:make_replay_portable(target)
    except FileNotFoundError:pass
    else:raise AssertionError('Missing texture accepted')
    assert target.read_bytes()==before
print('PASS: embedded scene, animation, textures/meshes, thumbnail, CSS, script escaping, autoplay, event markup, idempotence, refreshed payload and missing-asset guard.')
