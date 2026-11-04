"""Monitor an existing Webots test queue; never launch or resize Webots."""
from pathlib import Path
import argparse,json,subprocess,os,time,sys,socket,atexit
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--webots-home',type=Path,required=True);p.add_argument('--port',default='1255');p.add_argument('--webots-pid',type=int);p.add_argument('--engine-log',type=Path);args=p.parse_args()
out=args.output.resolve();started=set();reported=set();children=[];active={};exited_at={};deadline=time.monotonic()+1800
while time.monotonic()<deadline:
 if args.engine_log and args.engine_log.exists():
  errors=[line for line in args.engine_log.read_text(errors='replace').splitlines() if line.startswith('ERROR:')]
  if errors:raise SystemExit('Simulator error: '+errors[0])
 q=json.loads((out/'queue.json').read_text())
 for f in sorted((out/'results').glob('*.json')) if (out/'results').exists() else []:
  if f.name not in reported:
   r=json.loads(f.read_text());print(f.name,'PASS' if r['passed'] else 'FAIL',r.get('error',''),flush=True);reported.add(f.name)
 if q['index']>=len(q['jobs']):break
 if args.webots_pid:
  try:os.kill(args.webots_pid,0)
  except ProcessLookupError:raise SystemExit('Webots exited before its validation queue completed; inspect the engine log.')
 i=q['index'];job=q['jobs'][i];ready=out/'runtime/remote-ready'
 if i in active and active[i].poll() is not None:
  exited_at.setdefault(i,time.monotonic())
  expected=out/'results'/f"{i:02d}-{job['world']}-{job['mode']}.json"
  if not expected.exists() and time.monotonic()-exited_at[i]>2:
   raise SystemExit(f'External controller exited before check {i} completed; inspect remote-{i}.txt.')
 if job['mode'].startswith('remote-') and i not in started and ready.exists() and ready.read_text()==str(i):
  log=(out/f'remote-{i}.txt').open('w')
  protocol=job['mode'].split('-')[1]
  controller_port=args.port
  if protocol=='secure':
   protocol='tcp';controller_port=str(int(args.port)+1)
   gateway_log=(out/'gateway.log').open('w')
   gateway=subprocess.Popen([sys.executable,str(Path(__file__).resolve().parents[2]/'scripts/controller_gateway.py'),'--port',controller_port,'--backend-port',args.port],stdout=gateway_log,stderr=subprocess.STDOUT)
   atexit.register(gateway.terminate)
   until=time.monotonic()+5
   while True:
    try:
     with socket.create_connection(('127.0.0.1',int(controller_port)),timeout=.1):break
    except OSError:
     assert gateway.poll() is None and time.monotonic()<until,'Gateway startup failed'
     time.sleep(.05)
   # The known organizer preview must remain inaccessible through this port.
   with socket.create_connection(('127.0.0.1',int(controller_port)),timeout=2) as attempt:
    attempt.sendall(b'GET /robot_windows/MainSupervisorWindow/thumbnails/world4.png HTTP/1.1\r\nHost: localhost\r\n\r\n')
    try:assert attempt.recv(100)==b''
    except ConnectionResetError:pass
  if protocol=='docker':
   import sys
   from types import SimpleNamespace
   sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'game/controllers/MainSupervisor'))
   import DockerHelper
   def capture(pipe,target_log=log):
    for raw in iter(pipe.readline,b''):
     line=raw.decode('utf-8',errors='replace').strip();print(line,flush=True);target_log.write(line+'\n');target_log.flush()
     for prefix,file in [('EREBUS_TEST_DEVICES ','device-info.json'),('EREBUS_TEST_GAME_INFO ','game-info.json')]:
      if line.startswith(prefix):
       payload=json.loads(line[len(prefix):]);(out/'runtime'/file).write_text(json.dumps(payload))
    pipe.close()
   DockerHelper.print_stdout=capture
   run_docker_container=DockerHelper.run_docker_container
   os.environ['EREBUS_CONTROLLER_PORT']=args.port
   child=run_docker_container(SimpleNamespace(TIME_STEP=16,step=lambda ms:None),str(out/'docker-project'))
   assert child is not None, 'Docker controller did not start'
   children.append(child);active[i]=child;started.add(i);continue
  command=[str((args.webots_home/'webots-controller') if (args.webots_home/'webots-controller').is_file() else (args.webots_home/'Contents/MacOS/webots-controller')),'--protocol='+protocol,'--port='+controller_port,'--robot-name=Erebus_Bot']
  if protocol=='tcp':command+=['--ip-address=127.0.0.1']
  command+=[str(out/'runtime/game/controllers/robot0Controller/robot0Controller.py')]
  child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,WEBOTS_HOME=str(args.webots_home)))
  children.append(child);active[i]=child
  started.add(i)
 time.sleep(.25)
else:raise SystemExit('Test queue did not finish; inspect the existing Webots console.')
for child in children:
 try:child.wait(timeout=5)
 except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=5)
results=[json.loads(f.read_text()) for f in sorted((out/'results').glob('*.json'))]
assert len(results)==len(q['jobs']),(len(results),len(q['jobs']))
assert all(r['passed'] for r in results),'Some checks failed; results retained.'
print('PASS:',len(results),'Webots R2025a checks in one persistent window.',flush=True)
