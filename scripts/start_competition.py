"""Start the isolated competition services after checking Docker's safety baseline."""
import argparse,os,subprocess
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
raise SystemExit(subprocess.call(['docker','compose','-f',str(root/'docker/competition/compose.yaml'),'up','--build','-d','webots','gateway'],env=env,cwd=root))
