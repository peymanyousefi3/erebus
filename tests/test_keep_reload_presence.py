"""Keep and Reload are tested independently, including real reset-file methods."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import ast,sys,os,glob,shutil,stat,filecmp
folder=Path(sys.argv[1]).resolve();sys.path.insert(0,str(folder))
import ControllerUploader

def extract(filename,class_name,name,scope):
 tree=ast.parse((folder/filename).read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==class_name)
 node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-method>','exec'),scope);return scope[name]

with TemporaryDirectory() as temp:
 root=Path(temp);module=root/'game/controllers/MainSupervisor';module.mkdir(parents=True)
 runtime=module.parent/'robot0Controller';runtime.mkdir()
 proto=root/'game/protos/custom_robot.proto';proto.parent.mkdir()
 default=root/'game/proto_defaults/E-puck-custom-default-FLU.proto';default.parent.mkdir();default.write_bytes(b'default')
 original=root/'original.py';messages=[]
 scope=dict(Path=Path,ControllerUploader=ControllerUploader,__file__=str(module/'MainSupervisor.py'),Console=NS(log_err=lambda *a:None))
 prepare=extract('MainSupervisor.py','Erebus','_prepare_match',scope)
 reset_scope=dict(os=os,glob=glob,shutil=shutil,stat=stat,ControllerUploader=ControllerUploader,__file__=str(module/'Controller.py'))
 reset_file=extract('Controller.py','Controller','reset_file',reset_scope)
 proto_scope=dict(os=os,shutil=shutil,filecmp=filecmp,__file__=str(module/'Robot.py'),Console=NS(log_err=lambda *a:None))
 reset_proto=extract('Robot.py','Robot','reset_proto',proto_scope)
 s=NS(_remote_enabled=False,rws=NS(send=lambda *args:messages.append(args)))
 s.worldReload=lambda:(_ for _ in ()).throw(AssertionError('Unexpected reload'))
 checks=0
 for keep in (False,True):
  for reload in (False,True):
   s.config=NS(keep_controller=keep,auto_reload_sources=reload,controller_source=str(original))
   controller=NS(keep_controller=keep,_erebus=s);robot=NS(controller=controller,_erebus=s)
   ControllerUploader.install_controller('program.py',b'old copy',runtime);proto.write_bytes(b'custom');original.write_bytes(b'fresh source')
   reset_file(controller);reset_proto(robot)
   assert bool((runtime/'robot0Controller.py').stat().st_size)==keep
   assert (proto.read_bytes()!=default.read_bytes())==keep
   messages.clear();ok=prepare(s)
   assert ok==keep
   if not keep:assert 'JSON' in messages[-1][1]  # Keep off also removes the robot JSON.
   if keep:assert (runtime/'robot0Controller.py').read_bytes()==(b'fresh source' if reload else b'old copy')
   checks+=1
   for loaded in ('valid','empty','absent'):
    for source in ('valid','empty','missing'):
     for p in runtime.iterdir():
      if p.is_file():p.unlink()
      elif p.is_dir():shutil.rmtree(p)
     (runtime/'__pycache__').mkdir();(runtime/'__pycache__/old.pyc').write_bytes(b'cache')
     (runtime/'robot0Controller.backup').write_bytes(b'not an entrypoint')
     if loaded!='absent':(runtime/'robot0Controller.py').write_bytes(b'old copy' if loaded=='valid' else b'')
     original.unlink(missing_ok=True)
     if source!='missing':original.write_bytes(b'bad syntax =\n' if source=='valid' else b'')
     proto.write_bytes(b'custom');messages.clear()
     before={p.name:p.read_bytes() for p in runtime.iterdir() if p.is_file()}
     ok=prepare(s);expected=source=='valid' if reload else loaded=='valid'
     assert ok==expected,(keep,reload,loaded,source,messages)
     if reload and source!='valid':
      assert before=={p.name:p.read_bytes() for p in runtime.iterdir() if p.is_file()}
     if not ok:
      assert messages[-1][0]=='sourceReloadError'
      if not reload:assert ('empty' if loaded=='empty' else 'No controller') in messages[-1][1]
     checks+=1
print(f'PASS: {checks} scenarios across all four Keep/Reload combinations, actual reset behavior, empty/missing/valid copies and sources, stray files/cache, safe failed reload, and no syntax checks.')
