"""Scoring parity, original matrix preservation, offline exports, and failure isolation."""
import ast,json,sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import numpy as np
sys.path.insert(0,sys.argv[1])
import MapReview,MapScorer
from Config import Config
main=Path(sys.argv[1])
assert not Config(['1','0','0','0','0','0',''],'').map_review
assert Config(['1','0','0','0','0','0','','0','','','1','1'],'').map_review
rng=np.random.default_rng(2026)
checks=0
for h,w in [(3,3),(5,9),(10,6),(21,25)]:
 for rotation in range(4):
  for padding in [0,2]:
   for mistakes in [0,4]:
    answer=rng.choice(['0','1','2','3','4','HS','20'],(h,w));answer[h//2,w//2]='5'
    raw=np.rot90(answer,rotation).copy()
    raw=np.pad(raw,padding,constant_values='0')
    if mistakes:
     for i in range(mistakes):
      y,x=rng.integers(raw.shape)
      if raw[y,x]!='5':raw[y,x]='Z'
    old=raw.copy();score=MapScorer.calculateScore(answer,raw)
    result=MapReview.build_review(answer,raw,score,61.7)
    assert result['reported_matrix']==old.tolist() and np.array_equal(old,raw)
    assert result['timestamp']=='01:01'
    assert result['counts']['correct']/(result['counts']['correct']+result['counts']['incorrect'])==score
    assert sum(v==0 for row in result['status'] for v in row)==result['counts']['incorrect']
    assert sum(v==1 for row in result['status'] for v in row)==result['counts']['correct']
    dy,dx=result['raw_origin']
    assert Counter(v for row in result['expected'] for v in row if v is not None and v!='0')==Counter(v for row in answer for v in row if v!='0')
    for rr,row in enumerate(raw):
     for cc,value in enumerate(row):
      if value!='0':assert result['values'][rr+dy][cc+dx]==str(value)
    for r,row in enumerate(result['values']):
     for c,value in enumerate(row):
      rr,cc=r-dy,c-dx
      assert value==(str(raw[rr,cc]) if 0<=rr<raw.shape[0] and 0<=cc<raw.shape[1] else None)
    checks+=1
answer=np.array([['0','1','0'],['HS','5','20'],['0','1','0']])
raw=answer.copy();raw[1,0]='SH';raw[1,2]='incorrect but ignored'
result=MapReview.build_review(answer,raw,MapScorer.calculateScore(answer,raw),0)
assert result['correctness']==1 and result['counts']['incorrect']==0
# Crop zero padding, but preserve non-zero outside entries without changing the official score.
raw=np.pad(answer,3,constant_values='X');result=MapReview.build_review(answer,raw,MapScorer.calculateScore(answer,raw),0)
assert len(result['values'])==9 and len(result['values'][0])==9
assert result['values'][0][0]=='X' and result['status'][0][0]==3 and result['outside_nonzero']==72
assert result['raw_origin']==[0,0]
raw=np.pad(answer,3,constant_values='0');result=MapReview.build_review(answer,raw,MapScorer.calculateScore(answer,raw),0)
assert len(result['values'])==3 and len(result['values'][0])==3 and result['raw_origin']==[-3,-3]
# Missing submitted locations are visible; exact scorer behaviour is preserved.
raw=np.array([['5']]);result=MapReview.build_review(answer,raw,MapScorer.calculateScore(answer,raw),0)
assert any(None in row for row in result['values'])
try:MapReview.build_review(answer,answer,.1,0)
except ValueError:pass
else:raise AssertionError('Disagreement must not produce misleading highlights')
with TemporaryDirectory() as temp:
 result=MapReview.build_review(answer,answer,1,12)
 # Arbitrary reported strings cannot terminate the embedded JSON script.
 result['reported_matrix'][0][0]='</script><script>bad()</script>'
 assets=main.parents[1]/'plugins/robot_windows/MainSupervisorWindow'
 folder=MapReview.save_review(result,temp,assets)
 assert json.loads((folder/'reported-map.json').read_text())==result['reported_matrix']
 assert json.loads((folder/'map-result.json').read_text())==result
 html=(folder/'map-review.html').read_text()
 assert '<script src=' not in html and '<link rel="stylesheet"' not in html
 assert '</script><script>bad()' not in html and '\\u003c/script>' in html
 assert MapReview.save_review(result,temp,assets)==folder
print(f'PASS: {checks} map comparisons, equivalent/ignored/missing/outside cells, offline export, safe embedding and idempotent saving.')
