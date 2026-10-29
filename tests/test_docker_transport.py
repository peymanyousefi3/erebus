"""Docker message and legacy-config checks without starting Webots or Docker."""
import ast
from enum import Enum
from pathlib import Path
from types import SimpleNamespace as NS
from urllib.parse import quote, unquote
import sys

main = Path(sys.argv[1]).resolve()
class State(Enum):
    MATCH_NOT_STARTED = 1
    MATCH_RUNNING = 2
class Sender:
    def __init__(self): self.messages=[]
    def send(self,*message): self.messages.append(message)
    def update_history(self,*message): self.messages.append(message)
    def update_received_history(self,*message): pass
scope = {'unquote':unquote,'Console':NS(update_debug_mode=lambda flag:None,log_info=lambda *args:None)}
config_node=next(n for n in ast.parse((main/'Config.py').read_text()).body if isinstance(n,ast.ClassDef))
exec(compile(ast.Module(body=[config_node],type_ignores=[]),'Config.py','exec'),scope)
Config=scope['Config']
for raw in ['/tmp/team folder',r'C:\Team\project','/tmp/name%20literal']:
    assert Config(['1','0','1','0','0','0',raw],'').docker_path==raw
    assert Config(['1','0','1','0','0','0','uri:'+quote(raw,safe='')],'').docker_path==raw
klass=next(n for n in ast.parse((main/'MainSupervisor.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Erebus')
method=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='_process_rw_message')
calls=[]
scope.update(GameState=State,Erebus=NS(TIME_STEP=16),run_docker_container=lambda self,p:calls.append(p) or object())
exec(compile(ast.Module(body=[method],type_ignores=[]),'MainSupervisor.py','exec'),scope)
self=NS(_game_state=State.MATCH_NOT_STARTED,rws=Sender(),step=lambda duration:None)
scope['_process_rw_message'](self,'runDocker,/tmp/team, demo')
scope['_process_rw_message'](self,'runDocker,/tmp/team, demo')
assert calls==['/tmp/team, demo'] and self._game_state==State.MATCH_RUNNING
self._game_state=State.MATCH_NOT_STARTED
scope['run_docker_container']=lambda *args:None
scope['_process_rw_message'](self,'runDocker,/tmp/project')
assert self.rws.messages[-1][0]=='dockerError'
scope['_process_rw_message'](self,'runDocker,')
assert self.rws.messages[-1][0]=='dockerError'
print('PASS: legacy/encoded paths, comma-preserving launch, duplicate-start guard and failure messages.')
