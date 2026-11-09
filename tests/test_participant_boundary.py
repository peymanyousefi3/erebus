"""Participant inputs must not write supervisor files or inject scene authority."""
import ast,copy,http.client,json,math,struct,sys,threading
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import numpy as np
main=Path(sys.argv[1]).resolve();sys.path.insert(0,str(main))
import ControllerUploader,ProtoGenerator
with TemporaryDirectory() as temp:
 root=Path(temp);allowed=root/'controllers/robot0Controller';allowed.mkdir(parents=True)
 protected=root/'controllers/MainSupervisor';protected.mkdir();config=protected/'sensorEnergyConfig.txt';config.write_text('protected')
 secret=b'private-victim-position-92.314-type-H'
 for route in ('worlds/world1.wbt','protos/Victim.proto','worlds/textures/victim_harmed_not_found.png'):
  target=root/route;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(secret)
 class Handler(ControllerUploader.SimpleHTTPRequestHandler):
  upload_directory=allowed
  def translate_path(self,path):return str(root/Path(path.lstrip('/')))
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 try:
  for route in ('/controllers/MainSupervisor/','/controllers/robot0Controller/../MainSupervisor/','/protos/','/controllers/robot0Controller/../../controllers/MainSupervisor/'):
   c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);c.request('POST',route,b'');r=c.getresponse();r.read();assert r.status==403;c.close()
  for verb in ('GET','HEAD'):
   for route in ('/worlds/','/worlds/world1.wbt','/worlds/world1.wbt?download=1','/protos/Victim.proto','/worlds/textures/victim_harmed_not_found.png','/controllers/MainSupervisor/Victim.py','/controllers/MainSupervisor/sensorEnergyConfig.txt','/%2e%2e/worlds/world1.wbt'):
    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);c.request(verb,route);r=c.getresponse();body=r.read();assert r.status==403 and secret not in body,(verb,route,r.status);c.close()
  c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3);c.request('POST','/controllers/robot0Controller/',b'',{'Origin':'https://untrusted.example'});r=c.getresponse();r.read();assert r.status==403;c.close()
  assert config.read_text()=='protected' and list(allowed.iterdir())==[]
 finally:server.shutdown();server.server_close();thread.join()
 # Generate only in a temporary destination, never overwrite the live robot.
 (root/'protos').mkdir(exist_ok=True)
 def path(game_relative,supervisor_relative):
  return str(main/'protoHeaderTemplateFLU.txt') if 'protoHeaderTemplate' in game_relative else str(root/'protos')
 base={'wheel':dict(name='Wheel',customName='left wheel',dictName='wheel',x=0,y=0,z=0,rx=0,ry=0,rz=1,a=0)}
 with patch.object(ProtoGenerator,'get_file_path',side_effect=path):
  assert ProtoGenerator.generate_robot_proto(base)
  model=root/'protos/custom_robot.proto';before=model.read_bytes()
  assert b'supervisor FALSE' in before and b'supervisor TRUE' not in before
  for key,value in [('customName','x"\n supervisor TRUE\n name "x'),('customName','x\\"'),('customName','x\n'),('customName','%< injected_template >%'),('rx','0\n supervisor TRUE'),('a',float('nan')),('x',float('inf')),('rz',True),('a',10**400)]:
   attack=copy.deepcopy(base);attack['wheel'][key]=value
   assert not ProtoGenerator.generate_robot_proto(attack),(key,value)
   assert model.read_bytes()==before
# Run the actual packet parser with ordinary stand-in robot state.
tree=ast.parse((main/'Robot.py').read_text());node=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Robot' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='set_message')
scope=dict(Console=NS(log_debug=lambda *a:None,log_err=lambda *a:None),struct=struct,np=np)
exec(compile(ast.Module(body=[node],type_ignores=[]),'Robot.py','exec'),scope)
robot=NS(message=['E'],map_data=np.array([]),battery=NS(level=42),_score=25)
for packet in (b'B',b'R',b'Z',b'\xff',b'batteryUpdate,0,100',b'config,ChangeBatteryTime=0'):
 scope['set_message'](robot,packet);assert robot.message==[] and robot.battery.level==42 and robot._score==25
for command in 'EMLG':
 scope['set_message'](robot,command.encode());assert robot.message==[command]
scope['set_message'](robot,struct.pack('i i c',12,-5,b'H'));assert robot.message==[(.12,0,-.05),'H']
scope['set_message'](robot,struct.pack('2i',1,2)+b'5,k');assert robot.message==[] and robot.map_data.tolist()==[['5','k']]
print('PASS: protected upload routes and reads, external browser origin, scene injection, non-finite poses, unsupported/forged commands and valid participant protocol.')
