from pathlib import Path
import sys,numpy as np
sys.path.insert(0,sys.argv[1]);import MapReview,MapScorer
answer=np.array([['1','1','1'],['1','5','0'],['0','0','0']])
for turns in range(4):
 for border in [0,5,30]:
  rotated=np.rot90(answer,turns);raw=np.pad(rotated,border,constant_values='0')
  base=MapReview.build_review(answer,raw,MapScorer.calculateScore(answer,raw),10)
  assert sorted([len(base['values']),len(base['values'][0])])==[2,3] and base['outside_nonzero']==0
  if border:
   raw[0,0]='H';raw[-1,-1]='1';score=MapScorer.calculateScore(answer,raw)
   result=MapReview.build_review(answer,raw,score,10)
   assert result['outside_nonzero']==2 and result['correctness']==1 and result['counts']['incorrect']==0
   assert len(result['values'])==raw.shape[0] and len(result['values'][0])==raw.shape[1]
   assert result['values'][0][0]=='H' and result['values'][-1][-1]=='1'
# Nonzero cells near all edges, with additional zero rows/columns outside them.
raw=np.full((20,30),'0',dtype='<U2');raw[8:11,10:13]=answer;raw[2,1]='H';raw[17,27]='1';raw[10,12]='1'
score=MapScorer.calculateScore(answer,raw);result=MapReview.build_review(answer,raw,score,10)
assert result['outside_nonzero']==2 and result['counts']['incorrect']==1
assert len(result['values'])==16 and len(result['values'][0])==27 and result['raw_origin']==[-2,-1]
for r,row in enumerate(raw):
 for c,v in enumerate(row):
  if v!='0':assert result['values'][r+result['raw_origin'][0]][c+result['raw_origin'][1]]==v
assert result['status'][8][11]==0  # Raw [10,12], a scored false wall.
print('PASS: zero-only crop across 4 rotations and 3 padding sizes; all nonzero outliers preserved; outside and scored errors distinguished; raw indices unchanged.')
