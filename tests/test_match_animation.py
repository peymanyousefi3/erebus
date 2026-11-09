"""Run with python3 test_match_animation.py; no Webots process required."""
import ast
from datetime import datetime
import math
import json
from zipfile import ZipFile
from pathlib import Path
import sys
if len(sys.argv) != 2:
    raise SystemExit('Pass the path to the Erebus MainSupervisor folder.')
SUPERVISOR_DIR = Path(sys.argv[1]).expanduser().resolve()
sys.path.insert(0, str(SUPERVISOR_DIR))
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from MatchAnimation import MatchAnimation, write_match_result
from Recorder import Recorder


def check():
    events, infos, errors = [], [], []

    class Supervisor:
        config = NS(show_hud=True)
        start_ok = True
        stop_ok = True
        valid = True

        def exportImage(self, filename, quality):
            Path(filename).write_bytes(b'preview')

        def animationStartRecording(self, filename):
            events.append('record-start')
            self.file = Path(filename)
            self.file.write_text('<html><head><script type="module" src="https://cyberbotics.com/wwi/R2023b/WebotsView.js"></script></head><body><webots-view data-scene="replay.x3d" data-animation="replay.json"></webots-view><p><strong>Description:</strong><br><br></p></body></html>')
            self.file.with_suffix('.x3d').write_text("<X3D><Scene><ImageTexture url='&quot;textures/sample.png&quot;'/></Scene></X3D>")
            assets = self.file.parent / 'textures'
            assets.mkdir()
            (assets / 'sample.png').write_bytes(b'texture')
            return self.start_ok

        def animationStopRecording(self):
            events.append('record-stop')
            self.file.with_suffix('.json').write_text(
                json.dumps({'frames': [{'time': 0}, {'time': 32}]}) if self.valid else '{')
            return self.stop_ok

    with TemporaryDirectory() as folder:
        supervisor = Supervisor()
        recorder = MatchAnimation(supervisor, infos.append, errors.append, folder)
        recorder.start()
        first = recorder.target
        recorder.start()
        assert events == ['record-start']
        recorder.stop(final_score=12.5, elapsed_seconds=1, history='00:01 Successful Exit')
        recorder.stop()
        assert events == ['record-start', 'record-stop'] and not errors
        assert first.parent.name == 'recording' and first.parent.parent.parent == Path(folder)
        archive = first.parent / f'{first.parent.parent.name}.zip'
        assert archive.is_file()
        with ZipFile(archive) as package:
            assert package.testzip() is None
            assert not any(name.endswith('.zip') for name in package.namelist())
            expected = {p.relative_to(first.parent.parent).as_posix() for p in first.parent.rglob('*') if p.is_file() and p != archive}
            assert {n for n in package.namelist() if not n.endswith('/')} == expected
            result = json.loads(package.read(f'{first.parent.name}/match-result.json'))
            assert result['final_score'] == 12.5
            assert result['events'][-1]['text'] == 'Successful Exit'
            assert package.read(f'{first.parent.name}/textures/sample.png') == b'texture'

        recorder.start()
        assert recorder.target.parent != first.parent
        supervisor.valid = False
        recorder.stop()
        assert errors and recorder.target is None
        supervisor.start_ok = False
        count = events.count('record-stop')
        recorder.start()
        recorder.stop()
        assert recorder.target is None and events.count('record-stop') == count
        supervisor.start_ok = supervisor.valid = True
        supervisor.stop_ok = False
        recorder.start()
        recorder.stop()
        assert 'export failure' in errors[-1]

    with TemporaryDirectory() as folder:
        target = Path(folder) / 'replay.html'
        target.write_text('<html><p><strong>Description:</strong><br><br></p></html>')
        target.with_suffix('.json').write_text(json.dumps({'frames': [{'time': 0}, {'time': 324000}]}))
        history = '05:24 Exit Bonus +106.12\n05:24 Map Bonus +1393.35\n05:24 Successful Exit'
        result = write_match_result(target, 2560.72, 324, 480, history)
        assert {k: v for k, v in result.items() if k != 'events'} == dict(last_event='05:24 Successful Exit', final_score=2560.72, exit_bonus=106.12, map_bonus=1393.35,
                              field_score=1061.25, elapsed_seconds=324, max_seconds=480, remaining_seconds=156)
        write_match_result(target, 2560.72, 324, 480, history)
        assert target.read_text().count('MATCH_RESULT_START') == 1
        assert 'Final score: 2,560.72' in target.read_text()
        assert result['events'][-1] == dict(time_seconds=324, timestamp='05:24', text='Successful Exit', playback_time_ms=324000)
        special = r'00:01 Target <unknown> & \path'
        write_match_result(target, 0, 1, 480, special)
        assert r'Target \u003cunknown> &' in target.read_text()
        assert json.loads(target.with_name('match-result.json').read_text())['last_event'] == special
        assert write_match_result(target, 0, 0, 480, '')['last_event'] is None
        # A penalty jumps the match clock ahead of the animation clock.
        target.with_suffix('.json').write_text(json.dumps({'frames': [
            {'time': 0, 'labels': [{'text': 'Time: 00:00 / 08:00'}]},
            {'time': 1000, 'labels': [{'text': 'Time: 00:01 / 08:00'}]},
            {'time': 2000, 'labels': [{'text': 'Time: 00:11 / 08:00'}]},
            {'time': 3000, 'labels': [{'text': 'Time: 00:12 / 08:00'}]},
        ]}))
        history = '00:01 First event\n00:11 Penalty event\n00:11 Second event\n00:12 Successful Exit'
        result = write_match_result(target, 0, 12, 480, history)
        assert [e['playback_time_ms'] for e in result['events']] == [1000, 2000, 2000, 3000]
        assert [e['text'] for e in result['events']] == ['First event', 'Penalty event', 'Second event', 'Successful Exit']
        dangerous = '00:01 Target </script> & \\path'
        write_match_result(target, 0, 12, 480, dangerous)
        assert 'Target </script>' not in target.read_text()
        assert json.loads(target.with_name('match-result.json').read_text())['events'][0]['text'] == dangerous[6:]


    # Execute the actual modified lifecycle methods with harmless stand-ins.
    source = (SUPERVISOR_DIR / 'MainSupervisor.py').read_text()
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Erebus')
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('_game_init', '_robot_quit')]
    quit_method = next(n for n in methods if n.name == '_robot_quit')
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'step' for n in ast.walk(quit_method))
    namespace = {'MatchDateTime': datetime, 'math': math, 'Recorder': Recorder, 'Erebus': NS(TIME_STEP=16), 'Console': NS(DEBUG_MODE=False), 'Logger': NS(write_log=lambda *args: events.append('log')), 'time': NS(time=lambda: 0)}
    exec(compile(ast.Module(body=methods, type_ignores=[]), '<lifecycle>', 'exec'), namespace)
    events.clear()
    def removed():
        assert 'record-stop' in events and events.index('record-stop') > events.index('record-start')
        events.append('remove')
    robot = NS(get_log_str=lambda: "00:20 Exit Bonus +1.25\n00:20 Map Bonus +2.50", get_score=lambda: 12.5, set_node=lambda node: events.append('node'),
               set_start_pos=lambda tile: events.append('position'),
               set_max_velocity=lambda v: None, reset_physics=lambda: events.append('physics'),
               remove_node=removed, history=NS(master_history=[], enqueue=lambda message: events.append(('history', message))), in_simulation=False)
    world_info = NS(getTypeName=lambda: 'WorldInfo', getField=lambda name: NS(getSFFloat=lambda: 60.0))
    children = NS(getCount=lambda: 1, getMFNode=lambda index: world_info)
    active = NS(getRoot=lambda: NS(getField=lambda name: children), config=NS(recording=True, automatic_camera=False, show_hud=True), getFromDef=lambda name: None,
                _add_robot=lambda: events.append('spawn'), robot_obj=robot,
                tile_manager=NS(start_tile=None), DEFAULT_MAX_MULT=1,
                _match_animation=NS(root=Path('match-results'), target=Path('replay.html'), start=lambda folder: events.append('record-start'), stop=lambda **kwargs: events.append('record-stop')),
                time_elapsed=65.9, setLabel=lambda *args: events.append(('label', args[0], args[1])), step=lambda value: events.append(('step', value)),
                getTime=lambda: 0, rws=NS(send=lambda message: None), max_time=480)
    namespace['_game_init'](active)
    assert events.index('record-start') > events.index('position') > events.index('spawn')
    assert events.index('record-start') > events.index('physics')
    assert ('label', 0, 'Score: 12.50') in events
    assert ('label', 1, 'Time: 01:05 / 08:00') in events
    active.config.recording = False  # Finish an already-started export even if settings change.
    namespace['_robot_quit'](active, False)
    assert events.index(('history', 'Successful Exit')) < events.index('record-stop') < events.index('remove') and not robot.in_simulation
    assert not any(isinstance(event, tuple) and event[0] == 'step' and event[1] > 0 for event in events)
    # With recording off, HUD/game startup still work without any export or delay.
    events.clear()
    active._match_animation = NS(root=Path('match-results'), target=None, start=lambda folder: (_ for _ in ()).throw(AssertionError('Recording disabled')),
                                 stop=lambda **kwargs: None)
    robot.remove_node = lambda: events.append('remove-without-recording')
    namespace['_game_init'](active)
    assert robot.in_simulation and 'record-start' not in events
    assert not any(isinstance(event, tuple) and event[0] == 'step' for event in events)
    namespace['_robot_quit'](active, False)
    assert 'remove-without-recording' in events and not robot.in_simulation
    assert all(token not in source for token in ('movieStartRecording', 'movieStopRecording', 'Recorder.start_recording', 'Recorder.stop_recording'))
    # All match-end callers must use the same stop-before-removal path.
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    assert sum(n.func.attr == 'remove_node' for n in calls) == 1
    assert sum(n.func.attr == '_robot_quit' for n in calls) == 4
    print('PASS: HTML recording on/off, no video calls, no export/delay when off, start ordering, and stop before deletion for all four ending paths.')


if __name__ == '__main__':
    check()
