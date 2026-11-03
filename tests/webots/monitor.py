"""Monitor an existing Webots test queue; never launch or resize Webots."""
from pathlib import Path
import argparse,json,subprocess,os,time
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--webots-home',type=Path,required=True);p.add_argument('--port',default='1255');p.add_argument('--webots-pid',type=int);args=p.parse_args()
out=args.output.resolve();started=set();reported=set();children=[];deadline=time.monotonic()+1200
while time.monotonic()<deadline:
 q=json.loads((out/'queue.json').read_text())
 for f in sorted((out/'results').glob('*.json')) if (out/'results').exists() else []:
  if f.name not in reported:
   r=json.loads(f.read_text());print(f.name,'PASS' if r['passed'] else 'FAIL',r.get('error',''),flush=True);reported.add(f.name)
 if q['index']>=len(q['jobs']):break
 if args.webots_pid:
  try:os.kill(args.webots_pid,0)
  except ProcessLookupError:raise SystemExit('Webots exited before its validation queue completed; inspect the engine log.')
 i=q['index'];job=q['jobs'][i];ready=out/'runtime/remote-ready'
 if job['mode'].startswith('remote-') and i not in started and ready.exists() and ready.read_text()==str(i):
  log=(out/f'remote-{i}.txt').open('w')
  protocol=job['mode'].split('-')[1]
  if protocol=='docker':
   import sys
   from types import SimpleNamespace
   sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'game/controllers/MainSupervisor'))
   import DockerHelper
   def capture(pipe):
    for raw in iter(pipe.readline,b''):
     line=raw.decode('utf-8',errors='replace').strip();print(line,flush=True)
     for prefix,file in [('EREBUS_TEST_DEVICES ','device-info.json'),('EREBUS_TEST_GAME_INFO ','game-info.json')]:
      if line.startswith(prefix):
       payload=json.loads(line[len(prefix):]);(out/'runtime'/file).write_text(json.dumps(payload))
    pipe.close()
   DockerHelper.print_stdout=capture
   run_docker_container=DockerHelper.run_docker_container
   os.environ['EREBUS_CONTROLLER_PORT']=args.port
   child=run_docker_container(SimpleNamespace(TIME_STEP=16,step=lambda ms:None),str(out/'docker-project'))
   assert child is not None, 'Docker controller did not start'
   children.append(child);started.add(i);continue
  command=[str((args.webots_home/'webots-controller') if (args.webots_home/'webots-controller').is_file() else (args.webots_home/'Contents/MacOS/webots-controller')),'--protocol='+protocol,'--port='+args.port,'--robot-name=Erebus_Bot']
  if protocol=='tcp':command+=['--ip-address=127.0.0.1']
  command+=[str(out/'runtime/game/controllers/robot0Controller/robot0Controller.py')]
  children.append(subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,WEBOTS_HOME=str(args.webots_home))))
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
