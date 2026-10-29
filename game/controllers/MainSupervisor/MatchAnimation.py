# Erebus customizations by Peyman Yousefi; original RoboCupJunior credits retained.
"""HTML replay recording and result packaging, controlled by the Recording setting."""
from datetime import datetime
import json
import base64
import mimetypes
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit
from bisect import bisect_left
import re
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from Recorder import Recorder



EVENT_PLAYBACK_SCRIPT = r'''<script>
(() => {
  const events = JSON.parse(document.getElementById('match-event-data').textContent);
  const output = document.getElementById('match-current-event');
  const player = document.querySelector('webots-view');
  const update = milliseconds => {
    let low = 0, high = events.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (events[middle].playback_time_ms <= milliseconds) low = middle + 1;
      else high = middle;
    }
    const event = events[low - 1];
    const text = event ? `${event.timestamp} — ${event.text}` : 'No events yet';
    if (output.textContent !== text) output.textContent = text;
  };
  update(0);
  const connect = () => {
    if (!player.isConnected) return;
    if (!player.setAnimationStepCallback?.(update)) setTimeout(connect, 100);
  };
  customElements.whenDefined('webots-view').then(connect);
})();
</script>'''


def write_match_result(target, final_score, elapsed_seconds, max_seconds, history, hud_enabled=None):
    """Add the final result and terminal HUD state without advancing simulation."""
    target = Path(target)
    def bonus(name):
        return round(sum(float(value) for value in re.findall(
            rf"\b{re.escape(name)} ([+-]\d+(?:\.\d+)?)", history)), 2)
    elapsed = max(0, min(round(elapsed_seconds), int(max_seconds)))
    # Match time can jump after penalties; align events to the recorded HUD clock.
    animation = json.loads(target.with_suffix('.json').read_text(encoding='utf-8'))
    frames = animation['frames']
    clocks = []
    for frame in frames:
        for label in frame.get('labels', []):
            match = re.match(r'Time: (\d+):(\d{2}) /', label.get('text', ''))
            if match:
                clocks.append((int(match[1]) * 60 + int(match[2]), frame['time']))
    clock_seconds = [clock[0] for clock in clocks]
    events = []
    for match in re.finditer(r'^(\d+):(\d{2}) (.+)$', history, flags=re.M):
        seconds = int(match[1]) * 60 + int(match[2])
        index = bisect_left(clock_seconds, seconds)
        if clocks:
            playback_ms = clocks[index][1] if index < len(clocks) else frames[-1]['time']
        else:
            playback_ms = min(seconds * 1000, frames[-1]['time'])
        events.append(dict(time_seconds=seconds, timestamp=f'{match[1]}:{match[2]}',
                           text=match[3].strip(), playback_time_ms=playback_ms))
    # setLabel queues changes until Webots steps. Keep terminal events in the
    # final recorded frame without stepping or delaying robot removal.
    event_label = next((label for frame in reversed(frames) for label in frame.get('labels', [])
                        if label.get('x') == 0.02 and label.get('y') in (0.15, 0.27)), None)
    if event_label is not None:
        final_label = dict(event_label, text=Recorder.event_text(
            [(event['timestamp'], event['text']) for event in events]))
        final_labels = frames[-1].setdefault('labels', [])
        final_labels[:] = [label for label in final_labels if label['id'] != final_label['id']]
        final_labels.append(final_label)
        if hud_enabled is not None:
            # Honor a last-moment toggle, even before Webots flushes setLabel.
            latest = {}
            for frame in frames:
                for label in frame.get('labels', []):
                    if label.get('x') == 0.02 and label.get('y') in (0.02, 0.09, 0.15, 0.14, 0.27):
                        latest[label['id']] = label
            for label in latest.values():
                visibility = dict(label, rgba=label['rgba'].rsplit(',', 1)[0] + (',1' if hud_enabled else ',0'))
                final_labels[:] = [item for item in final_labels if item['id'] != label['id']]
                final_labels.append(visibility)
        target.with_suffix('.json').write_text(json.dumps(animation, separators=(',', ':')) + '\n', encoding='utf-8')
    result = {
        'last_event': f"{events[-1]['timestamp']} {events[-1]['text']}" if events else None,
        'events': events,
        'final_score': round(float(final_score), 2),
        'exit_bonus': bonus('Exit Bonus'),
        'map_bonus': bonus('Map Bonus'),
        'elapsed_seconds': elapsed,
        'max_seconds': int(max_seconds),
        'remaining_seconds': max(0, int(max_seconds) - elapsed),
    }
    result['field_score'] = round(result['final_score'] - result['exit_bonus'] - result['map_bonus'], 2)
    def clock(seconds):
        minutes, seconds = divmod(seconds, 60)
        return f"{minutes:02d}:{seconds:02d}"
    event_data = json.dumps(events, ensure_ascii=True).replace('<', r'\u003c')
    markup = f'''<!-- MATCH_RESULT_START -->
<section aria-label="Final match result" style="font-family:Arial,sans-serif;color:#24384c;line-height:1.45">
  <h2 style="font-size:20px;margin:0 0 5px">Final score: {result['final_score']:,.2f}</h2>
  <p style="padding:0;margin:0 0 4px">Field: {result['field_score']:,.2f} &nbsp;·&nbsp; Exit bonus: +{result['exit_bonus']:,.2f} &nbsp;·&nbsp; Map bonus: +{result['map_bonus']:,.2f}</p>
  <p style="padding:0;margin:0">Match time: {clock(elapsed)} / {clock(result['max_seconds'])} &nbsp;·&nbsp; Remaining: {clock(result['remaining_seconds'])}</p>
  <p style="padding:0;margin:4px 0 0">Latest event: <span id="match-current-event">No events yet</span></p>
</section>
<script type="application/json" id="match-event-data">{event_data}</script>
''' + EVENT_PLAYBACK_SCRIPT + '\n<!-- MATCH_RESULT_END -->'
    html = target.read_text(encoding='utf-8')
    if '<!-- MATCH_RESULT_START -->' in html:
        html = re.sub(r'<!-- MATCH_RESULT_START -->.*?<!-- MATCH_RESULT_END -->', lambda match: markup, html, flags=re.S)
    else:
        anchor = '<p><strong>Description:</strong><br><br></p>'
        if anchor not in html:
            raise ValueError('Cannot locate the replay description for the final result')
        html = html.replace(anchor, markup, 1)
    target.with_name('match-result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    target.write_text(html, encoding='utf-8')
    return result


# The viewer's supported raw-data API avoids file:// XHR/CORS restrictions.
DIRECT_PLAYBACK_SCRIPT = r'''<script>
(async () => {
  const status = document.getElementById('replay-load-status');
  try {
    const data = JSON.parse(document.getElementById('replay-package').textContent);
    const urls = new Map();
    for (const [name, asset] of Object.entries(data.assets)) {
      const bytes = Uint8Array.from(atob(asset.base64), char => char.charCodeAt(0));
      // Retain the extension for Webots' mesh importer while fetching a Blob.
      urls.set(name, URL.createObjectURL(new Blob([bytes], {type: asset.type})) + '#' + name.split('/').pop());
    }
    const scene = new DOMParser().parseFromString(data.scene, 'application/xml');
    if (scene.querySelector('parsererror')) throw new Error('The recorded 3D scene is invalid.');
    for (const node of scene.querySelectorAll('*')) {
      for (const attr of Array.from(node.attributes)) {
        if (!attr.name.toLowerCase().endsWith('url') || attr.name === 'docUrl') continue;
        attr.value = attr.value.replace(/"([^"]*)"/g, (whole, name) =>
          urls.has(name) ? '"' + urls.get(name) + '"' : whole);
      }
    }
    await import(data.viewer);
    await customElements.whenDefined('webots-view');
    const player = document.querySelector('webots-view');
    player.onready = () => { status.hidden = true; };
    player.loadAnimation(new XMLSerializer().serializeToString(scene), data.animation,
      data.autoplay, undefined, urls.get(data.thumbnail), true);
  } catch (error) {
    status.textContent = 'Playback could not load: ' + error.message +
      ' Internet access to the Webots viewer and a WebGL-capable browser are required.';
    status.setAttribute('role', 'alert');
  }
})();
</script>'''


def make_replay_portable(target):
    """Embed recording data/assets so the HTML also works when double-clicked."""
    target = Path(target)
    html = target.read_text(encoding='utf-8')
    view = re.search(r'<webots-view\b[^>]*>', html)
    if view is None:
        raise ValueError('No Webots player found in the recording HTML')
    # Rebuild from original companions, so reruns pick up result/HUD corrections.
    previous = re.search(r'<script type="application/json" id="replay-package">(.*?)</script>', html, re.S)
    prior = json.loads(previous[1]) if previous else {}
    def attribute(name, default):
        found = re.search(r'\b' + re.escape(name) + r'=(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))', view[0])
        return next(value for value in found.groups() if value is not None) if found else default
    scene_name = attribute('data-scene', prior.get('scene_name', target.with_suffix('.x3d').name))
    animation_name = attribute('data-animation', prior.get('animation_name', target.with_suffix('.json').name))
    thumbnail = attribute('data-thumbnail', prior.get('thumbnail', target.with_suffix('.jpg').name))
    root = target.parent.resolve()
    def local_file(name):
        path = (root / unquote(name)).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f'Recording asset is outside its folder: {name}')
        return path
    scene = local_file(scene_name).read_text(encoding='utf-8')
    animation = json.loads(local_file(animation_name).read_text(encoding='utf-8'))
    if not animation.get('frames'):
        raise ValueError('The recording contains no animation frames')
    tree = ET.fromstring(scene)
    names = {thumbnail} if local_file(thumbnail).is_file() else set()
    for node in tree.iter():
        for key, value in node.attrib.items():
            if not key.lower().endswith('url') or key == 'docUrl':
                continue
            for name in re.findall(r'"([^"]*)"', value):
                if name and not urlsplit(name).scheme and not name.startswith('//'):
                    names.add(name)
    assets = {}
    for name in sorted(names):
        path = local_file(name)
        assets[name] = dict(type=mimetypes.guess_type(name)[0] or 'application/octet-stream',
                            base64=base64.b64encode(path.read_bytes()).decode('ascii'))
    module = re.search(r'<script\b[^>]*src=["\']([^"\']*WebotsView\.js)["\'][^>]*>\s*</script>', html)
    viewer = module[1] if module else prior.get('viewer')
    if not viewer:
        raise ValueError('Cannot identify the Webots viewer version')
    payload = dict(viewer=viewer, scene_name=scene_name, animation_name=animation_name,
                   scene=scene, animation=animation, thumbnail=thumbnail, assets=assets,
                   autoplay=attribute('data-autoplay', str(prior.get('autoplay', True)).lower()) != 'false')
    if module:
        html = html.replace(module[0], '')
    opening = re.sub(r'\sdata-(?:scene|animation|thumbnail|autoplay)=(?:"[^"]*"|\'[^\']*\'|[^\s>]+)', '', view[0])
    html = html.replace(view[0], opening, 1)
    # Inline local CSS too; remote viewer libraries remain versioned on Cyberbotics.
    def inline_css(match):
        name = match[1]
        if urlsplit(name).scheme or name.startswith('//'):
            return match[0]
        return '<style>\n' + local_file(name).read_text(encoding='utf-8') + '\n</style>'
    html = re.sub(r'<link\b[^>]*href=["\']([^"\']+\.css)["\'][^>]*>', inline_css, html)
    html = re.sub(r'\s*<!-- DIRECT_REPLAY_START -->.*?<!-- DIRECT_REPLAY_END -->\s*', '', html, flags=re.S)
    packed = json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    block = ('\n<!-- DIRECT_REPLAY_START -->\n'
             '<p id="replay-load-status" role="status" style="font-family:Arial,sans-serif">Loading interactive recording…</p>\n'
             '<script type="application/json" id="replay-package">' + packed + '</script>\n' +
             DIRECT_PLAYBACK_SCRIPT + '\n<!-- DIRECT_REPLAY_END -->\n')
    html = re.sub(r'<div class="bottom-container">.*?</div>',
                  '<div class="bottom-container"><p>Interactive 3D recording · Play, pause, seek and change the camera view.</p></div>',
                  html, flags=re.S)
    html = re.sub(r'\s*</body>', lambda match: block + '</body>', html)
    target.write_text(html, encoding='utf-8')


class MatchAnimation:
    def __init__(self, supervisor, log_info, log_error, root=None):
        self.supervisor = supervisor
        self.log_info = log_info
        self.log_error = log_error
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[3] / 'match-results'
        self.target = None

    def start(self, folder=None):
        if self.target is not None:
            return
        try:
            # The supervisor supplies this match's shared recording subfolder.
            folder = Path(folder) if folder is not None else self.root / datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S-%f') / 'recording'
            folder.mkdir(parents=True, exist_ok=False)
            target = folder / 'replay.html'
            self.supervisor.exportImage(str(target.with_suffix('.jpg')), 90)
            if not self.supervisor.animationStartRecording(str(target)):
                raise RuntimeError('Webots refused to start HTML animation recording')
            self.target = target
            self.log_info(f'Automatic replay recording started: {target}')
        except (OSError, RuntimeError) as error:
            self.log_error(f'Automatic replay could not start: {error}')

    def stop(self, final_score=None, elapsed_seconds=0, max_seconds=480, history=""):
        if self.target is None:
            return
        target = self.target
        try:
            # This synchronous call must finish while the robot still exists.
            if not self.supervisor.animationStopRecording():
                raise RuntimeError('Webots reported an HTML animation export failure')
            data = json.loads(target.with_suffix('.json').read_text(encoding='utf-8'))
            frames = data.get('frames', [])
            if not frames or not any(frame.get('time', 0) > 0 for frame in frames):
                raise ValueError('The animation contains no recorded simulation steps')
            if not target.is_file():
                raise ValueError('The replay HTML file is missing')
            if final_score is not None:
                write_match_result(target, final_score, elapsed_seconds, max_seconds, history,
                                   hud_enabled=self.supervisor.config.show_hud)
            make_replay_portable(target)
            archive = target.parent / f'{target.parent.parent.name}.zip'
            with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as package:
                for asset in sorted(target.parent.rglob('*')):
                    if asset.is_file() and asset != archive:
                        package.write(asset, asset.relative_to(target.parent.parent))
            self.log_info(f'Automatic replay saved: {target}')
            self.log_info(f'Automatic replay ZIP saved: {archive}')
        except (OSError, RuntimeError, ValueError, AttributeError, TypeError) as error:
            self.log_error(f'Automatic replay is incomplete ({target.parent}): {error}')
        finally:
            self.target = None
