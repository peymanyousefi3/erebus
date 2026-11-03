"""Prepare isolated R2025a checks for loading in an existing Webots window."""
from pathlib import Path
import shutil,json,argparse
root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=root/'validation/release');p.add_argument('--docker',action='store_true');p.add_argument('--only-mode');args=p.parse_args()
out=args.output.resolve();runtime=out/'runtime';game=runtime/'game'
shutil.copytree(root/'game',game,dirs_exist_ok=True)
shutil.copyfile(game/'proto_defaults/E-puck-custom-default-FLU.proto',game/'protos/custom_robot.proto')
(game/'controllers/MainSupervisor/config.txt').write_text('1,1,1,0,0,0,,0,,,1,0\n')
probe=game/'controllers/ReleaseProbe';probe.mkdir(exist_ok=True)
shutil.copyfile(Path(__file__).with_name('ReleaseProbe.py'),probe/'ReleaseProbe.py')
shutil.copyfile(Path(__file__).with_name('robot0Controller.py'),game/'controllers/robot0Controller/robot0Controller.py')
worlds=sorted(p.stem for p in (game/'worlds').glob('*.wbt') if p.stem!='window_check')
for name in worlds:
 p=game/'worlds'/(name+'.wbt');s=p.read_text().replace('controller "MainSupervisor"','controller "ReleaseProbe"').replace('window "MainSupervisorWindow"','window "<none>"');p.write_text(s)
jobs=[dict(world=name,mode='load') for name in worlds]
jobs += [dict(world='mapping_example_1_cyan_tiles',mode=mode) for mode in ['contact','four-wheels','no-camera','custom-camera','all-sensors','legacy-model','swamp','natural-depletion','remote-ipc','remote-tcp','full-match']]
jobs += [dict(world=name,mode='scoring') for name in ['2027_d1r1','2027_d1r2','2027_d2r1','2027_d2r2','world1']]
# Exercise generated models and rules before the remaining field-loading checks.
jobs = jobs[:1] + jobs[len(worlds):] + jobs[1:len(worlds)]
if args.docker:
 jobs.append(dict(world='mapping_example_1_cyan_tiles',mode='remote-docker'))
 project=out/'docker-project';project.mkdir(exist_ok=True)
 shutil.copyfile(root/'docker/controller/Dockerfile',project/'Dockerfile')
 shutil.copyfile(root/'docker/controller/start.sh',project/'start.sh')
 driver=Path(__file__).with_name('robot0Controller.py').read_text()
 driver=driver.replace("root=Path(__file__).resolve().parents[3]", "root=Path('/tmp/erebus-test');root.mkdir(exist_ok=True)")
 (project/'controller.py').write_text(driver)
if args.only_mode:
 jobs=[job for job in jobs if job['mode']==args.only_mode]
 if not jobs:raise SystemExit('No checks matched --only-mode')
(out/'queue.json').write_text(json.dumps(dict(index=0,jobs=jobs),indent=2))
print('Open this world in the existing Webots R2025a window:')
print(game/'worlds'/(jobs[0]['world']+'.wbt'))
print(len(jobs),'checks prepared; the window stays open and pauses when finished.')
