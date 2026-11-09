"""Docker daemon, build/run arguments and recoverable errors."""
from pathlib import Path
import sys,io,subprocess,os
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(sys.argv[1]).resolve()))
import DockerHelper as d
calls=[]
class Process:
 def __init__(self,args,**kwargs):
  calls.append(args);self.returncode=0;self.stdout=io.StringIO('built\n') if args[1]=='build' else io.BytesIO()
 def __enter__(self):return self
 def __exit__(self,*args):pass
s=NS(TIME_STEP=16,step=lambda ms:None)
with patch.object(d.subprocess,'run',return_value=NS(returncode=0)),patch.object(d.subprocess,'Popen',Process),patch.dict(os.environ,{'EREBUS_CONTROLLER_PORT':'1255','EREBUS_DOCKER_HOST':'host.docker.internal'}):
 assert d.run_docker_container(s,'/tmp/team, project') is not None
 assert calls[0]==['docker','build','--tag','erebus_internal','/tmp/team, project']
 assert 'EREBUS_CONTROLLER_PORT=1255' in calls[1] and 'EREBUS_SERVER=host.docker.internal' in calls[1]
 assert 'host.docker.internal:host-gateway' in calls[1]
with patch.object(d.subprocess,'run',side_effect=FileNotFoundError('docker')):
 assert d.run_docker_container(s,'/tmp/project') is None
with patch.object(d.subprocess,'run',return_value=NS(returncode=0)),patch.dict(os.environ,{'EREBUS_CONTROLLER_PORT':'invalid'}):
 assert d.run_docker_container(s,'/tmp/project') is None
print('PASS: daemon absence, selected build folder, host gateway, matching TCP port and invalid-port guard.')
