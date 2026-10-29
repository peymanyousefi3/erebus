"""HUD regression check; pass the Erebus MainSupervisor directory."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))
from Recorder import Recorder
from MatchAnimation import write_match_result
from tempfile import TemporaryDirectory
import json

labels = {}
history = NS(master_history=[])
supervisor = NS(time_elapsed=75, max_time=480, config=NS(show_hud=True),
                robot_obj=NS(get_score=lambda: 1234.5, history=history),
                setLabel=lambda *args: labels.update({args[0]: args[1:]}))
Recorder.update_hud(supervisor)
assert labels[0][0] == 'Score: 1234.50' and labels[0][3] > .055
assert labels[1][0] == 'Time: 01:15 / 08:00' and labels[1][3] > .055
assert labels[2][0] == 'No events yet'
history.master_history = [('00:01', 'First'), ('00:02', 'Second'),
                          ('00:03', 'Third'), ('00:04', 'Fourth')]
Recorder.update_events(supervisor)
assert labels[2][0] == '[00:04] Fourth\n[00:03] Third\n[00:02] Second'
supervisor.config.show_hud = False
Recorder.update_hud(supervisor)
assert all(labels[i][5] == 1 for i in [0, 1, 2])
supervisor.config.show_hud = True
Recorder.update_hud(supervisor)
assert all(labels[i][5] == 0 for i in [0, 1, 2])
previous = labels[2]
Recorder.update_hud(supervisor)
assert labels[2] == previous
assert labels[0][2] == .02 and labels[1][2] == .09 and labels[2][2] == .15
assert labels[1][2] >= labels[0][2] + labels[0][3] * .5
assert labels[2][2] >= labels[1][2] + labels[1][3] * .5
assert labels[2][3] == .055
with TemporaryDirectory() as folder:
    target = Path(folder) / 'replay.html'
    target.write_text('<p><strong>Description:</strong><br><br></p>')
    animation = {'frames': [{'time': 0, 'labels': [
        {'id': 72, 'x': .02, 'y': .15, 'size': .055, 'rgba':'251,197,49,1', 'text': 'No events yet'}]},
        {'time': 5000}]}
    target.with_suffix('.json').write_text(json.dumps(animation))
    history = '00:01 First\n00:02 Second\n00:03 Third\n00:04 Finished'
    write_match_result(target, 10, 5, 480, history)
    saved = json.loads(target.with_suffix('.json').read_text())
    assert saved['frames'][-1]['labels'][0]['text'] == '[00:04] Finished\n[00:03] Third\n[00:02] Second'
    assert [frame['time'] for frame in saved['frames']] == [0, 5000]
    write_match_result(target, 10, 5, 480, history)
    assert len(json.loads(target.with_suffix('.json').read_text())['frames'][-1]['labels']) == 1
    write_match_result(target, 10, 5, 480, history, hud_enabled=False)
    assert json.loads(target.with_suffix('.json').read_text())['frames'][-1]['labels'][0]['rgba'].endswith(',0')
    write_match_result(target, 10, 5, 480, history, hud_enabled=True)
    assert json.loads(target.with_suffix('.json').read_text())['frames'][-1]['labels'][0]['rgba'].endswith(',1')
# The HUD class must no longer expose the MP4/countdown recorder.
for name in ('start_recording', 'stop_recording', 'reset_countdown', 'update'):
    assert not hasattr(Recorder, name)
print('PASS: HUD toggle, persistent events, final-frame visibility and removal of video recorder methods.')
