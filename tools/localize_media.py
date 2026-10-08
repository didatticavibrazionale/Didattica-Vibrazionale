"""Replace mapped remote media URLs in HTML and JSON; does not download anything.
Usage: copy files into assets/images/imported, edit assets/data/media-map.json,
then python tools/localize_media.py
"""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[1]
mapping=json.loads((ROOT/'assets/data/media-map.json').read_text())
pairs={k:v for k,v in mapping.items() if v}
for remote,local in pairs.items():
 if not local.startswith('/') or not (ROOT/local.lstrip('/')).is_file():raise SystemExit('File locale mancante: '+local)
changed=0
for p in list(ROOT.rglob('*.html'))+[ROOT/'search-index.json']:
 s=p.read_text();new=s
 for remote,local in pairs.items():new=new.replace(remote,local).replace(html.escape(remote,quote=True),html.escape(local,quote=True))
 if new!=s:p.write_text(new);changed+=1
print('File aggiornati:',changed)
