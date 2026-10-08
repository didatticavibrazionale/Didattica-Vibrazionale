"""Offline structural checks. Optional regeneration dependency: lxml."""
from pathlib import Path
from urllib.parse import urlsplit,unquote
import json
from lxml import html
ROOT=Path(__file__).resolve().parents[1];bad=[];count=0;anchors=[]
for p in ROOT.rglob('*.html'):
 d=html.parse(str(p))
 for e in d.xpath('//*[@href or @src]'):
  u=urlsplit(e.get('href') or e.get('src'))
  if u.scheme or u.netloc:continue
  if not u.path:
   if u.fragment and u.fragment not in {el.get('id') for el in d.xpath('//*[@id]')}:anchors.append([str(p.relative_to(ROOT)),u.fragment])
   continue
  count+=1;t=ROOT/unquote(u.path).lstrip('/') if u.path.startswith('/') else p.parent/unquote(u.path)
  if t.is_dir():t=t/'index.html'
  if not t.exists():bad.append([str(p.relative_to(ROOT)),u.path])
index=json.loads((ROOT/'search-index.json').read_text());posts=[x for x in index if x['type']=='post'];assert len(posts)==70
assert len({x['url'] for x in posts})==70
for p in posts:assert (ROOT/p['url'].strip('/')/'index.html').is_file()
scenes=json.loads((ROOT/'assets/data/scenes.json').read_text());assert len(scenes['home']['hotspots'])==9
for scene in scenes.values():
 assert (ROOT/scene['image'].lstrip('/')).is_file()
 for h in scene['hotspots']:
  assert 0<=h['x']<=1 and 0<=h['y']<=1
  if h['url'].startswith('/'):assert (ROOT/h['url'].strip('/')/'index.html').is_file(),h['url']
print(json.dumps({'articles':len(posts),'local_links_checked':count,'broken_links':bad,'missing_fragment_targets':anchors,'home_hotspots':len(scenes['home']['hotspots'])},ensure_ascii=False,indent=2))
assert not bad
assert not anchors
