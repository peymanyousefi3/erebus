"""Start the isolated competition services after checking Docker's safety baseline."""
import argparse,os,subprocess,time,webbrowser,urllib.request
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--world',default='mapping_example_1_cyan_tiles')
a=p.parse_args()
try:
    version=subprocess.check_output(['docker','version','--format','{{.Server.Version}}'],text=True).strip()
    if int(version.split('.')[0])<28:raise SystemExit('Update Docker Engine to 28 or newer before starting protected competition mode.')
except (OSError,subprocess.CalledProcessError,ValueError):
    raise SystemExit('Start Docker Engine 28 or newer, then run this launcher again.')
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,EREBUS_WORLD=a.world)
compose=['docker','compose','-f',str(root/'docker/competition/compose.yaml')]
subprocess.run(compose+['up','--build','-d','webots','gateway'],env=env,cwd=root,check=True)
for _ in range(180):
    result=subprocess.run(compose+['exec','-T','webots','cat','/tmp/erebus-referee.cfg'],capture_output=True,text=True,env=env,cwd=root)
    if result.returncode==0:
        try:
            with urllib.request.urlopen(result.stdout.strip(),timeout=2) as response:
                if response.status==200:
                    webbrowser.open_new_tab(result.stdout.strip())
                    break
        except OSError:
            pass
    time.sleep(1)
else:
    raise SystemExit('The referee service did not start. Check the organizer container logs.')
