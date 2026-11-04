"""Start the private organizer simulator; the public gateway is a separate service."""
from pathlib import Path
import os
import re
import subprocess

root=Path('/erebus')
name=os.environ.get('EREBUS_WORLD','mapping_example_1_cyan_tiles')
if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):
    raise SystemExit('Select a bundled world by its filename stem.')
world=root/'game/worlds'/(name+'.wbt')
if not world.is_file():
    raise SystemExit('World not found: '+name)
config=root/'game/controllers/MainSupervisor/config.txt'
values=config.read_text().strip().split(',')
values[4]='1'  # Remote controller, controlled by the organizer interface.
values[5]='0'  # Do not publish answer diagnostics through debug logs.
config.write_text(','.join(values)+'\n')
print('Organizer UI: http://127.0.0.1:1240/robot_windows/MainSupervisorWindow/MainSupervisorWindow.html?name=robot',flush=True)
command=['xvfb-run','-a','-s','-screen 0 1280x720x24',os.environ['WEBOTS_HOME']+'/webots','--batch','--mode=fast','--stream','--stdout','--stderr','--port=1255',str(world)]
raise SystemExit(subprocess.call(command,cwd=root))
