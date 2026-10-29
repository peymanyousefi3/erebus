"""Run/Remove contract using the actual supervisor methods and temporary files."""
import ast,json,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from urllib.parse import quote,unquote
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
import ControllerUploader
source=Path(sys.argv[1])/'MainSupervisor.py'
cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Erebus')
names={'_process_rw_message','_prepare_match','_process_robot_json','_clear_controller_source'}
methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in names]
assert len(methods)==4
states=NS(MATCH_NOT_STARTED=0,MATCH_RUNNING=1,MATCH_PAUSED=2,MATCH_FINISHED=3)
with TemporaryDirectory() as temp:
 root=Path(temp);main=root/'game/controllers/MainSupervisor/MainSupervisor.py';main.parent.mkdir(parents=True)
 runtime=root/'game/controllers/robot0Controller';runtime.mkdir()
 proto=root/'game/protos/custom_robot.proto';proto.parent.mkdir()
 default=root/'game/proto_defaults/E-puck-custom-default-FLU.proto';default.parent.mkdir();default.write_bytes(b'default')
 original=root/'original.py';original.write_text('version = 1\n')
 robot=root/'robot.json';robot.write_text('{}')
 cfg=root/'config.txt';events=[]
 def generate(data):proto.write_bytes(b'custom');return True
 scope=dict(ControllerUploader=ControllerUploader,Path=Path,quote=quote,json=json,time=time,__file__=str(main),GameState=states,generate_robot_proto=generate,Console=NS(log_err=lambda msg:None))
 exec(compile(ast.Module(body=methods,type_ignores=[]),'<actual-supervisor-methods>','exec'),scope)
 class Supervisor:pass
 for name in names:setattr(Supervisor,name,scope[name])
 s=Supervisor();s.rws=NS(send=lambda *args:events.append(args),update_received_history=lambda *a:None,update_history=lambda *a:None)
 s._remote_enabled=False;s._source_picker=None;s._source_proto_at_load=b'custom'
 def reset_file(manual):
  for f in runtime.iterdir():f.unlink()
  (runtime/'robot0Controller.py').write_text('')
 def reset():reset_file(True);s.rws.send('unloaded0')
 def reset_proto(manual):proto.write_bytes(b'default');s.rws.send('unloaded1')
 s.robot_obj=NS(controller=NS(reset_file=reset_file,reset=reset),reset_proto=reset_proto)
 checks=0
 for keep in (False,True):
  for reload in (False,True):
   for removed in ((),(0,),(1,),(0,1)):
    s._game_state=states.MATCH_NOT_STARTED
    cfg.write_text(f'{int(keep)},0,0,0,0,0,,{int(reload)},,,1')
    s.config=NS(path=str(cfg),keep_controller=keep,auto_reload_sources=reload,controller_source=str(original),json_source=str(robot))
    reset_file(True);(runtime/'robot0Controller.py').write_bytes(original.read_bytes());s._process_robot_json(robot.read_text())
    for kind in removed:
     s._process_rw_message(f'robot{kind}Unload')
     if kind==0:
      assert events[-1]==('sourcePath','0,')
      assert s.config.controller_source==''
     else:assert events[-1]==('unloaded1',)
    # A stale path in the other field must not turn a removed input into optional data.
    before=(runtime/'robot0Controller.py').read_bytes();model=proto.read_bytes()
    events.clear();s._process_rw_message('run')
    if removed:
     assert s._game_state==states.MATCH_NOT_STARTED,(keep,reload,removed)
     assert events[-1][0]=='sourceReloadError'
     assert any(('controller' if kind==0 else 'JSON') in events[-1][1] for kind in removed)
     assert (runtime/'robot0Controller.py').read_bytes()==before and proto.read_bytes()==model
     assert not any(e[0]=='runPressed' for e in events)
     # Replacement must recover, without a supervisor restart or clearing the other file.
     for kind in removed:
      if kind==0:s.config.controller_source=str(original)
      else:s.config.json_source=str(robot)
      if kind==0:(runtime/'robot0Controller.py').write_bytes(original.read_bytes())
      else:s._process_robot_json(robot.read_text())
     s._process_rw_message('run');assert s._game_state==states.MATCH_RUNNING
    else:assert s._game_state==states.MATCH_RUNNING
    checks+=1
 # Loaded Python syntax is left to the controller, like official Erebus.
 s.config.auto_reload_sources=False
 s._game_state=states.MATCH_NOT_STARTED
 (runtime/'robot0Controller.py').write_text('invalid =\n')
 events.clear();s._process_rw_message('run');assert s._game_state==states.MATCH_RUNNING
 assert not any(e[0]=='sourceReloadError' for e in events)
 # A changed JSON model must not cause an automatic world reload or restart file.
 s._game_state=states.MATCH_NOT_STARTED
 (runtime/'robot0Controller.py').write_bytes(original.read_bytes())
 s._source_proto_at_load=b'old model'
 s.worldReload=lambda:(_ for _ in ()).throw(AssertionError('Unexpected automatic reload'))
 s._process_rw_message('run');assert s._game_state==states.MATCH_RUNNING
 assert not cfg.with_name('pending-match-run.json').exists()
 # Manual paths reread edited originals; off keeps the existing copied version.
 s.config.auto_reload_sources=True;s.config.controller_source=str(original);s.config.json_source=str(robot)
 s._game_state=states.MATCH_NOT_STARTED
 original.write_text('version = 2\n');assert s._prepare_match()
 assert (runtime/'robot0Controller.py').read_text()=='version = 2\n'
 s.config.auto_reload_sources=False;original.write_text('version = 3\n');assert s._prepare_match()
 assert (runtime/'robot0Controller.py').read_text()=='version = 2\n'
 s.config.auto_reload_sources=True
 original.write_text('invalid =\n');assert s._prepare_match()
 assert (runtime/'robot0Controller.py').read_text()=='invalid =\n'
 original.write_text('version = 3\n');robot.write_text('{broken');assert s._prepare_match()
 assert (runtime/'robot0Controller.py').read_text()=='version = 3\n'  # Original JSON is never reread on Run.
 robot.write_text('{}');s.config.controller_source='missing.py';assert not s._prepare_match()
 s.config.controller_source=original.name;s.config.json_source=robot.name
 assert s._prepare_match() and (runtime/'robot0Controller.py').read_text()=='version = 3\n'
 proto.write_bytes(b'default');assert not s._prepare_match()
 proto.write_bytes(b'custom')
 # Pause/resume retains the running match and does not reread sources.
 s._game_state=states.MATCH_PAUSED;s.config.controller_source=s.config.json_source=''
 s._process_rw_message('run');assert s._game_state==states.MATCH_RUNNING
 # External controllers do not need a local Python source.
 s._remote_enabled=True;s._game_state=states.MATCH_NOT_STARTED
 s._process_rw_message('run');assert s._game_state==states.MATCH_RUNNING
print(f'PASS: {checks} Keep/Reload/Remove cases, browser-copy validation, blocked Run without writes, replacement recovery, Python syntax left to controller, no automatic model reload, Python-only refresh, pause/resume and remote compatibility.')
