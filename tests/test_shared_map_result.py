"""Run the actual accepted-map and manual-button methods against real saved files."""
import ast,json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import numpy as np
sys.path.insert(0,sys.argv[1]);import MapReview,MapScorer
main=Path(sys.argv[1]).resolve()
cls=next(n for n in ast.parse((main/'MainSupervisor.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='Erebus')
branch=next(n for method in cls.body if isinstance(method,ast.FunctionDef) for n in ast.walk(method) if isinstance(n,ast.If) and ast.unparse(n.test)=="robot_message[0] == 'M'")
evaluate=ast.FunctionDef(name='evaluate',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='self')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=branch.body,decorator_list=[])
show=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_save_and_open_map_review')
module=ast.fix_missing_locations(ast.Module(body=[evaluate,show],type_ignores=[]))
messages=[];opens=[]
console=NS(DEBUG_MODE=False,log_err=lambda *a:None,log_info=lambda *a:None)
scope=dict(np=np,json=json,MapScorer=MapScorer,MapReview=MapReview,Console=console)
exec(compile(module,'<actual accepted-map/manual methods>','exec'),scope)
class Supervisor:pass
Supervisor.evaluate=scope['evaluate'];Supervisor._save_and_open_map_review=scope['_save_and_open_map_review']
MapReview.open_review=lambda path:opens.append(Path(path))
answer=np.array([['1','1','1'],['0','5','0'],['0','1','0']])
checks=0
with TemporaryDirectory() as temp:
 root=Path(temp)/'match-results'
 for automatic in [False,True]:
  messages.clear();opens.clear();history=[]
  s=Supervisor();s._submitted_map=None;s._map_review=None;s._match_folder=root/f'match-{automatic}'
  s._map_sol=answer;s.time_elapsed=61;s.config=NS(map_review=automatic)
  s.robot_obj=NS(map_data=answer.copy(),sent_maps=False,history=NS(enqueue=history.append));s.wwiSendText=messages.append
  s._save_and_open_map_review();assert messages[-1].startswith('mapReviewError,') and not s._match_folder.exists()
  s.evaluate();assert s.robot_obj.sent_maps and s.robot_obj.map_score_percent==1 and s.robot_obj.map_data.size==0
  assert history==['Map Correctness 100.0%'] and messages[-(2 if automatic else 1)].startswith('mapReviewAvailable,')
  assert len(opens)==int(automatic)
  if not automatic:assert not s._match_folder.exists() and s._map_review is None
  # Robot is already removed: export uses the retained submission, never its node.
  s.robot_obj.map_data=np.full((3,3),'wrong');s.robot_obj.in_simulation=False
  s._save_and_open_map_review();folder=s._match_folder/'map'
  assert opens[-1]==folder/'map-review.html'
  assert set(p.name for p in folder.iterdir())=={'map-review.html','map-result.json','reported-map.json'}
  assert json.loads((folder/'reported-map.json').read_text())==answer.tolist()
  assert 'id="cellPopup"' in (folder/'map-review.html').read_text()
  (folder/'reported-map.json').unlink();(folder/'map-review.html').unlink()
  s._save_and_open_map_review();assert (folder/'reported-map.json').exists() and (folder/'map-review.html').exists()
  assert set(p.name for p in s._match_folder.iterdir())=={'map'}
  assert s.robot_obj.map_score_percent==1 and len(history)==1
  before=len(opens);s.evaluate();assert len(opens)==before and len(history)==1
  checks+=1
 # Saving failure preserves accepted score and retained data, allowing retry.
 messages.clear();opens.clear();history=[]
 s.config.map_review=True;s.robot_obj.sent_maps=False;s.robot_obj.map_data=answer.copy();s._map_review=None
 original=MapReview.save_review
 MapReview.save_review=lambda *a,**k:(_ for _ in ()).throw(PermissionError('test'))
 s.evaluate();assert s.robot_obj.sent_maps and s.robot_obj.map_score_percent==1 and s._submitted_map is not None
 assert messages[-1].startswith('mapReviewError,') and not opens
 MapReview.save_review=original;s._save_and_open_map_review();assert opens and messages[-1].startswith('mapReviewSaved,')
 # Empty or invalid maps never create a result or change the normal rejection behaviour.
 for raw in [np.array([]),np.full((3,3),'0')]:
  messages.clear();s.robot_obj.sent_maps=False;s.robot_obj.map_data=raw;s._submitted_map=None
  s.evaluate();assert not s.robot_obj.sent_maps and s._submitted_map is None and not messages
print('PASS: automatic on/off; manual export after robot removal; one shared map folder; repeated clicks/repair; duplicate rejection; save-failure recovery; invalid/empty maps.')
