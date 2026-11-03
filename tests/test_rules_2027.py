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

# PDF 5.6: independent numeric expectations for each sign/area combination.
# Exercise the production scoring methods without starting another simulator.
add_points=method('Robot.py','Robot','increase_score',{})
def scored_robot(initial=0):
 r=NS(_score=initial,history=NS(enqueue=lambda value:None),position=[0,0,0],victim_identified=False,time_stopped=lambda:1)
 r.increase_score=lambda *a,**kw:add_points(r,*a,**kw)
 r.get_score=lambda:r._score
 return r
multipliers=[1,1.25,1.5,2]
actual_tile=ast.parse((main/'Tile.py').read_text())
area_node=next(n for c in actual_tile.body if isinstance(c,ast.ClassDef) and c.name=='TileManager' for n in c.body if isinstance(n,ast.AnnAssign) and n.target.id=='ROOM_MULT')
assert ast.literal_eval(area_node.value)==multipliers
class RoomField:
 def __init__(self,area):self.area=area
 def getField(self,name):return self
 def getMFNode(self,index):return self
 def getSFInt32(self):return self.area
cases=0
for area,multiplier in enumerate(multipliers,1):
 for kind in 'HSUFPCO':
  target=kind in 'FPCO'
  for base in ([10,30] if target else [5,15]):
   sign=Sign(0,kind);sign.score_worth=base
   r=scored_robot()
   s=NS(robot_obj=r,victim_manager=NS(victims=[] if target else [sign],targets=[sign] if target else []),tile_manager=NS(coord2grid=lambda *a:0,ROOM_MULT=multipliers),getFromDef=lambda name:RoomField(area))
   detect(s,[[0,0,0],kind.lower()])
   expected=round(base*multiplier,2)+round((20 if target else 10)*multiplier,2)
   assert r._score==expected,(area,kind,base,r._score,expected)
   detect(s,[[0,0,0],kind]);assert r._score==expected
   sign.identified=False;r._score=0
   wrong=('P' if kind=='F' else 'F') if target else ('S' if kind=='H' else 'H')
   detect(s,[[0,0,0],wrong]);assert r._score==round(base*multiplier,2)
   cases+=1
# No sign, wrong side, out-of-range, category mismatch and score floor.
for mode in ('missing','wrong-side','out-of-range','cross-category'):
 r=scored_robot(3);sign=Sign(0,'F' if mode=='cross-category' else 'H')
 if mode=='wrong-side':sign.on_same_side=lambda r:False
 if mode=='out-of-range':sign.check_position=lambda p:False
 s=NS(robot_obj=r,victim_manager=NS(victims=[] if mode=='missing' else [sign],targets=[]))
 detect(s,[[0,0,0],'H']);assert r._score==0,(mode,r._score)
# Checkpoint values and duplicate visits use the same production accumulator.
checkpoint=method('Robot.py','Robot','update_checkpoints',dict(Checkpoint=object,TileManager=NS(coord2grid=lambda *a:0,ROOM_MULT=multipliers)))
for area,multiplier in enumerate(multipliers,1):
 r=scored_robot();r.visited_checkpoints=[];r._erebus=NS(getFromDef=lambda name:RoomField(area))
 tile=NS(center=[0,0,0]);checkpoint(r,tile);checkpoint(r,tile)
 assert r._score==10*multiplier and len(r.visited_checkpoints)==1
# Exit eligibility and partial map bonuses, including sequential rounding.
process=method('MainSupervisor.py','Erebus','_process_message',dict(Any=object,Console=console,GameState=NS(MATCH_FINISHED='finished')))
for at_start in (False,True):
 for identified in (False,True):
  for fraction in (0,.25,.5,1):
   r=scored_robot(123.45);r.victim_identified=identified;r.map_score_percent=fraction
   s=NS(robot_obj=r,tile_manager=NS(start_tile=NS(check_position=lambda p:at_start)),_map_bonus_applied=False,_robot_quit=lambda *a:None,rws=NS(send=lambda *a:None))
   s._add_map_multiplier=lambda:award(s)
   process(s,['E'])
   subtotal=123.45+(round(123.45*.1,2) if at_start and identified else 0)
   assert math.isclose(r._score,subtotal+round(subtotal*fraction*1.2,2))
   previous=r._score;award(s);assert r._score==previous
print(f'PASS: {cases} exact sign/area awards, wrong types, duplicates, misidentification score floor, four checkpoint multipliers and 16 exit/map combinations.')

# Every distinct PDF 5.6 map symbol: exact, missing and wrong value,
# with all four rotations tested through the public scoring function.
sys.path.insert(0,str(main))
import MapScorer
symbols='1234xkbygporHSUFPCO'
for symbol in symbols:
 expected=np.array([['0',symbol,'0'],['0','5','0'],['0','0','0']])
 for turns in range(4):
  assert MapScorer.calculateScore(expected,np.rot90(expected,turns))==1
 for replacement in ('0','wrong'):
  submitted=expected.astype('<U8');submitted[0,1]=replacement
  assert MapScorer.calculateScore(expected,submitted)==.5,(symbol,replacement)
# Area 4 is ignored by the scorer's internal marker; existing packet handling
# converts the submitted '*' marker before evaluation.
expected=np.array([['20','1','0'],['0','5','0'],['0','0','0']])
submitted=expected.copy();submitted[0,0]='0'
assert MapScorer.calculateScore(expected,submitted)==1
# Stopping for less than one second cannot invoke report scoring.
for seconds in (0,.999,1,1.001):
 calls=[];r=NS(time_stopped=lambda:seconds)
 s=NS(robot_obj=r,_detect_victim=lambda message:calls.append(message))
 process(s,[[0,0,0],'H']);assert bool(calls)==(seconds>=1)
print(f'PASS: {len(symbols)} map symbols with rotations/missing/wrong cells, Area 4 exclusion and one-second reporting boundary.')

# LoP applies an unmultiplied five-point deduction and notifies the controller.
import struct
relocate=method('MainSupervisor.py','Erebus','relocate_robot',dict(Console=console,struct=struct))
for initial,expected_score in ((3,0),(10,5)):
 for manual in (False,True):
  packets=[];r=scored_robot(initial);r.last_visited_checkpoint_pos=[.1,0,.2];r.reset_physics=lambda:None
  s=NS(robot_obj=r,emitter=NS(send=packets.append),config=NS(automatic_camera=False))
  relocate(s,manual)
  assert r._score==expected_score and packets==[b'L'] and r.position==[.1,-.03,.2]
print('PASS: manual/robot LoP deductions, zero floor, checkpoint relocation and controller notification.')
