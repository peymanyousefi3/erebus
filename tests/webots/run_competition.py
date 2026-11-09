"""Run competition fixtures with official Webots; platform-neutral process handling."""
from pathlib import Path
import argparse, json, os, subprocess, sys, time

root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser()
p.add_argument('--output',type=Path,default=root/'validation/competition')
p.add_argument('--docker',action='store_true')
p.add_argument('--port',default='1255')
p.add_argument('--only-mode')
args=p.parse_args();out=args.output.resolve()
prepare=[sys.executable,str(Path(__file__).with_name('prepare.py')),'--competition-only','--output',str(out)]
if args.docker:prepare.append('--docker')
if args.only_mode:prepare+=['--only-mode',args.only_mode]
subprocess.run(prepare,cwd=root,check=True)
home=Path(os.environ['WEBOTS_HOME'])
choices=[home/'webots',home/'webots.exe',home/'msys64/mingw64/bin/webots.exe',home/'Contents/MacOS/webots']
engine=next((path for path in choices if path.is_file()),None)
assert engine is not None,'Official Webots executable not found'
first=json.loads((out/'queue.json').read_text())['jobs'][0]['world']
command=[str(engine),'--batch','--mode=fast','--no-rendering','--stdout','--stderr','--port='+args.port,str(out/'runtime/game/worlds'/(first+'.wbt'))]
if sys.platform=='darwin':command.insert(1,'--minimize')
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'):
    command=['xvfb-run','-a','-s','-screen 0 1280x720x24',*command]
env=dict(os.environ,EREBUS_TEST_CLOSE_ON_COMPLETE='1',PYTHONUTF8='1')
with (out/'webots.log').open('w') as log:
    process=subprocess.Popen(command,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    monitor=None
    try:
        monitor=subprocess.Popen([sys.executable,str(Path(__file__).with_name('monitor.py')),'--output',str(out),'--webots-home',str(home),'--port',args.port,'--engine-log',str(out/'webots.log')],cwd=root,env=env)
        while monitor.poll() is None:
            if process.poll() is not None:
                queue=json.loads((out/'queue.json').read_text())
                assert queue['index']==len(queue['jobs']),'Webots exited before competition checks completed; inspect webots.log'
            time.sleep(.25)
        assert monitor.returncode==0,'Some competition checks failed'
        assert process.wait(timeout=30)==0,'Webots returned a failure'
    finally:
        if monitor is not None and monitor.poll() is None:
            monitor.terminate();monitor.wait(timeout=10)
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait()
