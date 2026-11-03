"""Run real supervisor code in an isolated copy; outputs are machine-checkable."""
from pathlib import Path
import sys, json, traceback, os, math, time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'MainSupervisor'))
import ControllerUploader
ControllerUploader.start = lambda: None  # No upload server needed for this automated fixture.
from MainSupervisor import Erebus, GameState
Erebus._get_erebus_version = lambda self: self.rws.send('version', self.version)
root = Path(__file__).resolve().parents[3]
queue_path = root.parent / 'queue.json'
queue = json.loads(queue_path.read_text())
job = queue['jobs'][queue['index']]
mode = job['mode']
os.environ.update(EREBUS_TEST_MODE=mode, EREBUS_TEST_WORLD=job['world'], EREBUS_TEST_ENGINE='R2025a')
for name in ('game-info.json','remote-ready','device-info.json'):
    (root/name).unlink(missing_ok=True)

result = dict(world=os.environ.get('EREBUS_TEST_WORLD'), engine=os.environ.get('EREBUS_TEST_ENGINE'), mode=mode, passed=False)
root = Path(__file__).resolve().parents[3]
s = None

def advance(seconds):
    until = s.time_elapsed + seconds
    while s.time_elapsed < until:
        s.update()
        assert s._game_state == GameState.MATCH_RUNNING, 'Unexpected match termination'

try:
    s = Erebus()
    s.simulationSetMode(s.SIMULATION_MODE_FAST)
    result.update(world=s._get_current_world(), contacts=len(s.tile_manager.contacts), swamps=len(s.tile_manager.swamps), victims=len(s.victim_manager.victims), targets=len(s.victim_manager.targets))
    if mode in ('four-wheels','no-camera','custom-camera','all-sensors'):
        from ProtoGenerator import generate_robot_proto
        model = {}
        for i, (x,z) in enumerate(([(-260,-180),(260,-180),(-260,180),(260,180)] if mode=='four-wheels' else [(-260,0),(260,0)]),1):
            model[str(i)] = dict(name='Wheel',customName=f'wheel{i}',dictName=f'wheel{i}',x=x,y=0,z=z,rx=0,ry=0,rz=1,a=0)
        model['gps'] = dict(name='GPS',customName='gps',dictName='gps',x=0,y=0,z=0,rx=0,ry=0,rz=1,a=0)
        model['camera'] = dict(name='Camera',customName='front',dictName='front',x=0,y=0,z=0,rx=0,ry=0,rz=1,a=0)
        if mode=='no-camera':
            del model['camera']
        if mode in ('custom-camera','all-sensors'):
            model['camera']['custom'] = [256,128]
        if mode=='all-sensors':
            for kind,tag in [('Gyro','gyro'),('Accelerometer','accelerometer'),('InertialUnit','imu'),('Lidar','lidar'),('Colour sensor','floor'),('Distance Sensor','distance')]:
                model[tag] = dict(name=kind,customName=tag,dictName=tag,x=0,y=0,z=0,rx=0,ry=0,rz=1,a=0)
        assert generate_robot_proto(model)
        s.step(0)
    if mode.startswith('remote-'):
        s._remote_enabled = True
        (root/'remote-ready').write_text(str(queue['index']))
    if mode=='legacy-model':
        proto=root/'game/protos/custom_robot.proto'
        original=proto.read_text()
        proto.write_text('\n'.join(line for line in original.splitlines() if not line.startswith('# energy_sensors: ')))
        s._game_state=GameState.MATCH_RUNNING;s.update()
        assert s._game_state==GameState.MATCH_NOT_STARTED and not s.robot_obj.in_simulation
        assert s.getFromDef('ROBOT0') is None
        assert any(command=='sourceReloadError' for command,args in s.rws.history)
        proto.write_text(original)
        result['legacy_model_rejected_without_crash']=True
        s.simulationSetMode(s.SIMULATION_MODE_FAST)
    if mode=='scoring':s.max_time=10000
    s._game_state = GameState.MATCH_RUNNING
    s._game_init()
    s.simulationSetMode(s.SIMULATION_MODE_FAST)
    advance(1)
    result.update(wheels=len(s.robot_obj._wheel_monitor.wheels), moving_battery=s.robot_obj.battery.level, measured_speeds=s.robot_obj._measured_wheel_speeds)
    assert result['wheels'] == (4 if mode=='four-wheels' else 2)
    result['devices'] = json.loads((root/'device-info.json').read_text())
    if mode=='no-camera':assert not any(d['type']=='Camera' for d in result['devices'])
    if mode in ('custom-camera','all-sensors'):assert any(d.get('width')==256 and d.get('height')==128 for d in result['devices'])
    assert result['moving_battery'] < 99.9
    assert all(v>1 for v in result['measured_speeds'])
    info = json.loads((root/'game-info.json').read_text())
    assert info['kind']=='G' and 0<info['battery']<=100
    result['game_info'] = info
    # Paused UI processing must not consume battery or simulation time.
    before=(s.time_elapsed,s.robot_obj.battery.level)
    s._game_state=GameState.MATCH_PAUSED
    for _ in range(5):s.update()
    assert before == (s.time_elapsed,s.robot_obj.battery.level)
    s._game_state=GameState.MATCH_RUNNING
    result['pause_preserved_energy']=True
    if mode in ('scoring','full-match'):
        s.robot_obj._wb_node.getField('customData').setSFString('stop')
        advance(.5)
    if mode=='full-match':
        while s.robot_obj.in_simulation:
            s.update()
            assert s.time_elapsed <= 480.02
        assert s.time_elapsed >= 480 and s.robot_obj.battery.level > 98
        result['full_match_seconds'] = s.time_elapsed
    elif mode=='scoring':
        from Test import TestRunner
        result['scored_tokens']=0
        command_id=0
        def command(**values):
            global command_id
            command_id+=1
            s.robot_obj._wb_node.getField('customData').setSFString(json.dumps(dict(id=command_id,**values)))
        assert all(v._wb_found_field is not None and v.get_simple_type() in 'HSU' for v in s.victim_manager.victims)
        for token in [*s.victim_manager.victims,*s.victim_manager.targets]:
            if not token.get_simple_type():continue
            placed=False
            for angle in (0,-25,25,-40,40):
                s.robot_obj.rotation=[0,1,0,0]
                s.robot_obj.position=[s.robot_obj.position[0],-.03,s.robot_obj.position[2]]
                if not TestRunner.robotToVictim(s.robot_obj,token,offset=.055,angle=angle):continue
                s.robot_obj.reset_physics();s.robot_obj.reset_time_stopped();advance(.2)
                deadline=s.time_elapsed+4
                while s.robot_obj.time_stopped()<1.05 and s.time_elapsed<deadline:s.update()
                result['token_diagnostics']=dict(kind=token.get_simple_type(),token=token.position,robot=s.robot_obj.position,velocity=s.robot_obj.velocity,stopped=s.robot_obj.time_stopped(),same_side=bool(token.on_same_side(s.robot_obj)),in_range=bool(token.check_position(s.robot_obj.position)),angle=angle)
                if s.robot_obj.time_stopped()>=1.05 and token.on_same_side(s.robot_obj) and token.check_position(s.robot_obj.position):
                    placed=True;break
            assert placed, ('No stationary reachable test pose',result['token_diagnostics'])
            before=s.robot_obj.get_score()
            command(report=[token.position[0],token.position[2],token.get_simple_type()]);advance(.1)
            assert token.identified and s.robot_obj.get_score()>before, ('Token not awarded',token.get_simple_type(),token.position)
            result['scored_tokens']+=1
        assert result['scored_tokens']>0
        matrix=[[str(v) for v in row] for row in s._map_sol]
        (root/'expected-map.json').write_text(json.dumps(matrix))
        command(map=True);advance(.1);command(evaluate=True);advance(.1)
        assert s.robot_obj.map_score_percent==1.0
        s.robot_obj.set_start_pos(s.tile_manager.start_tile);s.robot_obj.reset_physics();advance(.2)
        before=s.robot_obj.get_score()
        command(exit=True)
        for _ in range(20):
            if not s.robot_obj.in_simulation:break
            s.update()
        assert not s.robot_obj.in_simulation
        with_exit=before+round(before*.1,2)
        assert math.isclose(s.robot_obj.get_score(),with_exit+round(with_exit*1.2,2),rel_tol=1e-9)
        score=s.robot_obj.get_score();s._add_map_multiplier();assert s.robot_obj.get_score()==score
        result['final_score']=score
    elif mode=='contact':
        assert result['contacts']>0 and any('k' in row for row in s._map_sol)
        tile=s.tile_manager.contacts[0]
        s.robot_obj._wb_node.getField('customData').setSFString('stop')
        s.robot_obj.position=[tile.center[0],s.robot_obj.position[1],tile.center[2]]
        s.robot_obj.reset_physics()
        s.robot_obj.battery.level=50
        started=None
        while not any(e[1]=='Battery replaced' for e in s.robot_obj.history.master_history):
            s.update()
            if s.robot_obj.battery._stationary_since is not None:started=s.robot_obj.battery._stationary_since
            assert s.time_elapsed<10, 'No replacement'
        result['replacement_stationary_seconds']=s.robot_obj.battery._last_send_time-started
        result['replaced_battery']=s.robot_obj.battery.level
        assert 5<=result['replacement_stationary_seconds']<5.02 and result['replaced_battery']==100
        # Saved map diagnostics must preserve the new k cells and agree with scorer.
        import MapScorer, MapReview, numpy as np
        expected=np.asarray(s._map_sol).astype(str)
        score=MapScorer.calculateScore(expected.copy(),expected.copy())
        review=MapReview.build_review(expected,expected,score,s.time_elapsed)
        MapReview.save_review(review,s._match_folder/'map')
        assert any('k' in row for row in review['values'])
        result['map_review_correctness']=float(score)
        # Empty battery and replacement eligibility at the same step must end once.
        s.robot_obj.battery.level=0
        s.update()
        assert not s.robot_obj.in_simulation and s._game_state==GameState.MATCH_FINISHED
        result['terminal_events']=s.robot_obj.history.master_history[-3:]
        assert sum(e[1]=='Battery depleted' for e in s.robot_obj.history.master_history)==1
    elif mode=='swamp':
        assert s.tile_manager.swamps
        tile=s.tile_manager.swamps[0]
        s.robot_obj.position=[tile.center[0],s.robot_obj.position[1],tile.center[2]]
        s.robot_obj.reset_physics()
        clock=s.getTime()
        elapsed=s.time_elapsed
        level=s.robot_obj.battery.level
        advance(1)
        actual=sum(s.robot_obj._measured_wheel_speeds)/2
        result['swamp_interval']=dict(simulation_seconds=s.time_elapsed-elapsed, physics_seconds=s.getTime()-clock, drain=level-s.robot_obj.battery.level, measured_speed=actual)
        assert abs((s.time_elapsed-elapsed)-(s.getTime()-clock))<.02
        assert level-s.robot_obj.battery.level>1.5
        s._robot_quit(True)
    elif mode=='natural-depletion':
        s.robot_obj._wb_node.getField('customData').setSFString('run')
        # Use a real, unrestricted wheel test above the floor so an obstacle
        # cannot stall the motor. No battery value or drain setting is changed.
        s.robot_obj.position=[s.robot_obj.position[0],0.3,s.robot_obj.position[2]]
        s.robot_obj.reset_physics()
        while s.robot_obj.in_simulation:
            s.update()
            assert s.time_elapsed<170
        assert s.robot_obj.battery.level==0
        result['natural_depletion_seconds']=s.time_elapsed
    else:
        s._robot_quit(True)
    result['replay_files']=[str(p.relative_to(root)) for p in s._match_folder.rglob('*') if p.is_file()]
    assert any(p.endswith('.zip') for p in result['replay_files']),result
    assert any(p.endswith('.w3d' if result['engine']=='R2025a' else '.x3d') for p in result['replay_files'])
    result['passed']=True
except Exception:
    result['error']=traceback.format_exc()
finally:
    target=root/'probe-result.json'
    target.write_text(json.dumps(result,indent=2,allow_nan=False))
    print('INTEGRATION_PROBE',json.dumps(result),flush=True)
    output = root.parent / 'results'
    output.mkdir(exist_ok=True)
    result['job_index']=queue['index']
    name = f"{queue['index']:02d}-{job['world']}-{mode}.json"
    (output/name).write_text(json.dumps(result,indent=2))
    queue['index'] += 1
    tmp=queue_path.with_suffix('.tmp');tmp.write_text(json.dumps(queue));tmp.replace(queue_path)
    if s is not None:
        import shutil
        shutil.copyfile(root/'game/proto_defaults/E-puck-custom-default-FLU.proto',root/'game/protos/custom_robot.proto')
        if queue['index'] < len(queue['jobs']):
            s.worldLoad(str(root/'game/worlds'/(queue['jobs'][queue['index']]['world']+'.wbt')))
        else:
            if os.environ.get('EREBUS_TEST_CLOSE_ON_COMPLETE')=='1':
                results=[json.loads(p.read_text()) for p in output.glob('*.json')]
                s.simulationQuit(0 if all(r['passed'] for r in results) else 1)
            s.simulationSetMode(s.SIMULATION_MODE_PAUSE)
        while s.step(16) != -1:
            pass
