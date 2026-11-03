"""2027 scoring boundaries, decoy exclusion and single final map award."""
import ast,sys,math
from pathlib import Path
from types import SimpleNamespace as NS
main=Path(sys.argv[1]).resolve()
def method(file,cls,name,namespace):
 tree=ast.parse((main/file).read_text())
 node=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name==cls for n in c.body if isinstance(n,ast.FunctionDef) and n.name==name)
 node.decorator_list=[]
 exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'),namespace)
 return namespace[name]
ns={'Victim':NS(HARMED='harmed',STABLE='stable',UNHARMED='unharmed')}
kind=method('Victim.py','Victim','get_simple_type',ns)
for source,expected in [('harmed','H'),('stable','S'),('unharmed','U'),('omega',''),('phi',''),('psi','')]:
 assert kind(NS(_victim_type=source))==expected
check=method('Victim.py','VictimObject','check_position',{'math':math})
v=NS(position=[0,0,0])
assert check(v,[.059999,0,0]) and check(v,[.06,0,0]) and not check(v,[.060001,0,0])
score=[100.0];events=[]
robot=NS(get_score=lambda:score[0],map_score_percent=1.0,increase_score=lambda name,value:(events.append((name,value)),score.__setitem__(0,score[0]+value)))
s=NS(robot_obj=robot,_map_bonus_applied=False)
award=method('MainSupervisor.py','Erebus','_add_map_multiplier',{})
award(s);award(s)
assert score[0]==220 and len(events)==1
class Field:
 def __init__(self,value):self.value=value
 def getSFString(self):return self.value
 def getSFInt32(self):return self.value
 def getCount(self):return len(self.value)
 def getMFNode(self,i):return self.value[i]
def node(kind):return NS(getField=lambda name:Field(kind if name=='type' else 15))
items=[node('harmed'),node('omega'),node('stable'),node('phi'),node('unharmed'),node('psi')]
created=[]
class Victim:
 VICTIM_TYPES=['harmed','stable','unharmed']
 def __init__(self,node,kind,score):created.append(kind)
root=NS(getFromDef=lambda name:NS(getField=lambda name:Field(items)))
get=method('Victim.py','VictimManager','_get_victims',{'Victim':Victim})
assert len(get(NS(_erebus=root)))==3 and created==['harmed','stable','unharmed']
print('PASS: 6 cm scoring boundary, H/S/U, all three 3D decoys excluded, and map bonus awarded once.')

# A duplicate must not fall through to a nearby second sign. A cross-category
# report is a misidentification, even when a different sign is also in range.
import numpy as np
class Sign:
 def __init__(self,distance,kind,identified=False):
  self.simple_victim_type=kind;self.identified=identified;self.distance=distance
 def check_position(self,p):return True
 def on_same_side(self,r):return True
 def get_distance(self,p):return self.distance
 def get_simple_type(self):return self.simple_victim_type
 score_worth=5
 wb_translation_field=NS(getSFVec3f=lambda:[0,0,0])
console=NS(log_debug=lambda *args:None)
ns=dict(Any=object,Console=console,CognitiveTarget=NS(TARGET_TYPES=['F','P','C','O']),to_lower=str.lower,np=np)
detect=method('MainSupervisor.py','Erebus','_detect_victim',ns)
robot=NS(position=[0,0,0],increase_score=lambda *args,**kwargs:events.append(args))
first=Sign(0,'H',True);second=Sign(.02,'H')
s=NS(robot_obj=robot,victim_manager=NS(victims=[first,second],targets=[]))
events.clear();detect(s,[[0,0,0],'H']);assert not events and not second.identified
first=Sign(0,'F');second=Sign(.02,'H');s.victim_manager=NS(victims=[second],targets=[first])
events.clear();detect(s,[[0,0,0],'H']);assert events==[('Misidentification of Victim',-5)] and not second.identified
print('PASS: duplicate reports cannot award neighboring signs; cross-category reports are penalized.')
