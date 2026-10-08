import json,re,html,shutil,urllib.parse,collections,hashlib
from pathlib import Path
from lxml import html as LH, etree
from PIL import Image
import sys
from sql_reader import load_sql
if len(sys.argv)!=2: raise SystemExit('Uso: python tools/rebuild.py /percorso/export.sql')
ROOT=Path(__file__).resolve().parents[1]; D=load_sql(sys.argv[1]); P={p['ID']:p for p in D['wp_posts']}; meta=collections.defaultdict(dict)
for x in D['wp_postmeta']: meta[x['post_id']][x['meta_key']]=x['meta_value']
terms={t['term_id']:t for t in D['wp_terms']}; tax={t['term_taxonomy_id']:dict(t,**terms[t['term_id']]) for t in D['wp_term_taxonomy']}; rel=collections.defaultdict(list)
for r in D['wp_term_relationships']: rel[r['object_id']].append(tax[r['term_taxonomy_id']])
posts=[p for p in P.values() if p['post_type']=='post' and p['post_status']=='publish']; pages=[p for p in P.values() if p['post_type']=='page' and p['post_status']=='publish']; cats=[t for t in tax.values() if t['taxonomy']=='category']; tags=[t for t in tax.values() if t['taxonomy']=='post_tag']
mapping={2:'inizia-da-qui/origini',3:'privacy-policy',45:'didattica-vibrazionale',88:'contatti',95:'articoli',255:'educreativo',434:'cookie-policy-ue',626:'risorse/escape-room',709:'inizia-da-qui',905:'podcast',951:'risorse',1032:'risorse/storytelling',1283:'chi-sono',1302:'libri',1355:'competenze-socio-emotive-clima-di-classe',1422:'risorse/micro-strategie',1484:'risorse/app-educative'}
account=set(range(165,174))
routes={p['ID']:'/'+('articoli/'+p['post_name'] if p['post_type']=='post' else mapping.get(p['ID'],p['post_name']))+'/' for p in posts+pages}
for i in account: routes[i]='/articoli/'
old={('/'+p['post_name']+'/'):routes[p['ID']] for p in posts+pages}
old['/registrazione/']='/articoli/'
old['/categoria/matematica/']='/categorie/matematica/'
caturl={t['term_id']:'/categorie/'+t['slug']+'/' for t in cats}
for t in cats:
 chain=[t['slug']]; parent=t['parent']; seen=set()
 while parent and parent not in seen:
  seen.add(parent); tt=next((c for c in cats if c['term_id']==parent),None)
  if not tt: break
  chain.insert(0,tt['slug']); parent=tt['parent']
 old['/category/'+'/'.join(chain)+'/']=caturl[t['term_id']]; old['/category/'+t['slug']+'/']=caturl[t['term_id']]
for t in tags: old['/tag/'+t['slug']+'/']='/tag/'+t['slug']+'/'
issues=[]; media={}; external=set(); unknown_internal=set(); conversion=[]
def esc(x): return html.escape(str(x),quote=True)
def plain(x):
 try:return ' '.join(LH.fromstring('<div>'+x+'</div>').text_content().split())
 except:return re.sub('<[^>]+>',' ',x)
def rewrite(url):
 url=html.unescape(url).strip(); u=urllib.parse.urlsplit(url)
 if u.scheme in ['javascript','data','vbscript']:return '#'
 if (u.netloc in ['www.didatticavibrazionale.it','didatticavibrazionale.it'] or not u.netloc) and not u.path.startswith('/wp-content/'):
  q=urllib.parse.parse_qs(u.query)
  id_=q.get('p',q.get('page_id',[None]))[0]
  if id_ and id_.isdigit() and int(id_) in routes:return routes[int(id_)]+('#'+u.fragment if u.fragment else '')
  path='/'+u.path.strip('/')+'/' if u.path.strip('/') else '/'
  if path in old:return old[path]+('#'+u.fragment if u.fragment else '')
  if path=='/' and not u.fragment:return '/'
  if u.netloc:unknown_internal.add(url)
 if u.netloc:external.add(url)
 return url

def clean(raw,pid=0):
 if not raw.strip():return '<p class="notice">Contenuto non presente nel database: pagina in preparazione.</p>'
 for b in re.findall(r'<!-- wp:([\w/-]+).*?-->',raw):
  if b in ['complianz/document','query','post-template','post-title','post-featured-image','read-more']:issues.append({'id':pid,'type':'dynamic-block','block':b})
 # Expand metadata-backed Gutenberg footnotes before removing comments.
 if '<!-- wp:footnotes' in raw:
  try: notes=json.loads(meta[pid].get('footnotes') or '[]')
  except (ValueError,TypeError): notes=[]
  if notes:
   foot='<section class="footnotes"><h2>Note e riferimenti</h2><ol>'+''.join('<li id="'+esc(n['id'])+'">'+n['content'].replace('\\"','"')+' <a href="#'+esc(n['id'])+'-link" aria-label="Torna al riferimento">↩</a></li>' for n in notes)+'</ol></section>'
   raw=re.sub(r'<!-- wp:footnotes.*?-->',lambda m:foot,raw,flags=re.S)
  else: issues.append({'id':pid,'type':'footnotes-missing'})
 raw=re.sub(r'<!--.*?-->','',raw,flags=re.S)
 def shortcode(m):
  issues.append({'id':pid,'type':'shortcode','shortcode':m.group(0)});return ''
 raw=re.sub(r'\[/?(?:pmpro_[\w_]+|contact-form-7|caption|gallery|audio|video)[^\]]*\]',shortcode,raw)
 doc=LH.fromstring('<div>'+raw+'</div>')
 for el in list(doc.iter()):
  if not isinstance(el.tag,str): continue
  if el.tag in ['script','style','form','input','button','textarea','select']:
   issues.append({'id':pid,'type':'removed-element','element':el.tag});el.drop_tree();continue
  if el.tag in ['p','div'] and len(el)==0 and not el.text_content().strip():continue
  for k in list(el.attrib):
   if k.startswith('on') or k in ['srcset','sizes','style','width','height']: del el.attrib[k]
  if el.tag in ['iframe','object','embed']:
   src=el.get('src') or el.get('data',''); a=LH.Element('a',href=rewrite(src),attrib={'class':'external-embed','target':'_blank','rel':'noopener noreferrer'});a.text=el.get('title') or el.get('aria-label') or 'Apri il contenuto interattivo';el.getparent().replace(el,a);conversion.append({'id':pid,'type':'iframe-link','url':src});continue
  if el.tag=='img':
   src=el.get('src','');media.setdefault(src,{'url':src,'local':'','used_by':[]})['used_by'].append(pid)
   el.set('loading','lazy');el.set('decoding','async')
   if not el.get('alt'):el.set('alt', P.get(pid,{}).get('post_title','Immagine del contenuto'))
   el.set('data-original-src',src)
  if el.get('href'):el.set('href',rewrite(el.get('href')))
  if el.tag=='a' and el.get('target')=='_blank':el.set('rel','noopener noreferrer')
  if el.tag=='a' and not el.text_content().strip() and not len(el):el.text='Apri la risorsa'
  if el.tag=='h1':el.tag='h2'
 # Replace dynamic query templates with a static path to the archive.
 for query in list(doc.xpath('.//*[contains(@class,"wp-block-query")]')):
  query.clear(); a=etree.SubElement(query,'a',href='/articoli/');a.text='Esplora tutti gli articoli'
 # Old login-only invitation, not article text.
 for el in list(doc.xpath('.//p')):
  if re.search(r'ACCEDI.*visualizzare.*ISCRIVITI',el.text_content(),re.I):el.drop_tree();conversion.append({'id':pid,'type':'removed-login-invitation'})
 for el in list(doc.xpath('.//*[contains(@class,"wp-block-embed__wrapper")]')):
  tx=el.text_content().strip()
  if re.fullmatch(r'https?://\S+',tx):
   el.clear(); a=etree.SubElement(el,'a',href=rewrite(tx),attrib={'class':'external-embed','target':'_blank','rel':'noopener noreferrer'});a.text='Apri video o contenuto · '+urllib.parse.urlsplit(tx).netloc
 # WordPress paragraphs that contain plain URLs only
 for el in doc.xpath('.//p'):
  if not len(el) and re.fullmatch(r'https?://\S+',el.text_content().strip()):
   tx=el.text_content().strip();el.text='';a=etree.SubElement(el,'a',href=rewrite(tx));a.text=tx
 return (esc(doc.text) if doc.text else '')+''.join(LH.tostring(e,encoding='unicode') for e in doc)
content={p['ID']:clean(p['post_content'],p['ID']) for p in posts+pages if p['ID'] not in account}
for p in posts:
 thumb=meta[p['ID']].get('_thumbnail_id');p['featured']=P.get(int(thumb),{}).get('guid','') if thumb and thumb.isdigit() else ''
 if p['featured']:media.setdefault(p['featured'],{'url':p['featured'],'local':'','used_by':[]})['used_by'].append(p['ID'])

def put(path,s):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf8')
def jput(path,obj):put(path,json.dumps(obj,ensure_ascii=False,indent=2))
nav=[('Home','/'),('Articoli','/articoli/'),('Risorse','/risorse/'),('Libri','/libri/'),('Podcast','/podcast/'),('Universo','/universo/')]
allnav=nav+[('Chi sono','/chi-sono/'),('Inizia da qui','/inizia-da-qui/'),('Progetto EduCreativo','/educreativo/'),('Contatti','/contatti/')]
def anchors(items):return ''.join(f'<a href="{u}">{esc(t)}</a>' for t,u in items)
def page(route,title,body,kind='',description=''):
 relpath=(route.strip('/')+'/index.html') if route!='/' else 'index.html'
 h=f'''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{esc(description or 'Didattica Vibrazionale — In risonanza con l’armonia. Esperienze, risorse e percorsi educativi di Claudia Bartoli.')}"><meta name="theme-color" content="#081b31"><title>{esc(title)} · Didattica Vibrazionale</title><link rel="icon" href="/assets/images/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/css/site.css"><script src="/assets/js/site.js" defer></script><script src="/assets/js/panorama.js" defer></script></head><body class="{kind}"><a class="skip" href="#contenuto">Salta al contenuto</a><header class="site-header"><a class="brand" href="/" aria-label="Didattica Vibrazionale, Home"><span class="monogram">DV</span><span>Didattica Vibrazionale<small>In risonanza con l’armonia</small></span></a><button class="menu-toggle" aria-expanded="false" aria-controls="menu">Menu <span aria-hidden="true">☰</span></button><nav id="menu" aria-label="Navigazione principale">{anchors(nav)}<a href="/ricerca/" aria-label="Cerca nel sito">Cerca</a></nav></header><main id="contenuto">{body}</main><footer><a class="brand" href="/">Didattica Vibrazionale</a><p>In risonanza con l’armonia</p><nav aria-label="Esplora il sito">{anchors(allnav[6:])}<a href="/categorie/">Categorie</a><a href="/mappa-del-sito/">Mappa del sito</a><a href="/legale/">Copyright e attribuzioni</a><a href="/privacy-policy/">Privacy</a></nav><small>© Claudia Bartoli · Didattica Vibrazionale</small></footer><dialog id="preview"><button class="dialog-close" aria-label="Chiudi anteprima">×</button><h2>Anteprima del libro</h2><div class="preview-content"></div></dialog></body></html>'''
 put(relpath,h)
def intro(title,over='DIDATTICA VIBRAZIONALE',desc=''):
 return f'<div class="page-top"><a class="back" href="/">Torna all’atrio</a><p class="eyebrow">{esc(over)}</p><h1>{esc(title)}</h1>{"<p class=lead>"+esc(desc)+"</p>" if desc else ""}</div>'
def card(p):
 cs=[t for t in rel[p['ID']] if t['taxonomy']=='category'];im=p.get('featured','');txt=plain(content[p['ID']])
 return f'''<article class="card"><a class="card-image" href="{routes[p['ID']]}">{f'<img src="{esc(im)}" alt="{esc(p["post_title"])}" loading="lazy">' if im else '<span class="image-motif" aria-hidden="true">DV</span>'}</a><div class="card-copy"><p class="eyebrow">{esc(cs[0]['name'] if cs else 'Dal diario')} · <time datetime="{p['post_date'][:10]}">{p['post_date'][8:10]}/{p['post_date'][5:7]}/{p['post_date'][:4]}</time></p><h2><a href="{routes[p['ID']]}">{esc(p['post_title'])}</a></h2><p>{esc(txt[:170])}…</p><a class="text-link" href="{routes[p['ID']]}">Leggi l’articolo</a></div></article>'''
def feature(p):
 return '<figure class="article-cover container"><img src="'+esc(p['featured'])+'" alt="'+esc(p['post_title'])+'" loading="eager"></figure>' if p.get('featured') else ''
posts.sort(key=lambda p:p['post_date'],reverse=True)
for p in posts:
 cs=[t for t in rel[p['ID']] if t['taxonomy']=='category'];ts=[t for t in rel[p['ID']] if t['taxonomy']=='post_tag']
 body=intro(p['post_title'],'IL DIARIO · '+p['post_date'][:10])+feature(p)+f'<div class="article-shell"><aside><a href="/articoli/">Tutti gli articoli</a><div class="chips">'+''.join(f'<a href="{caturl[t["term_id"]]}">{esc(t["name"])}</a>' for t in cs)+'</div><p>Lettura integrale · '+str(max(1,len(plain(content[p['ID']]).split())//200))+' min</p></aside><article class="prose">'+content[p['ID']]+'<div class="tags"><span>Tag</span>'+''.join(f'<a href="/tag/{t["slug"]}/">{esc(t["name"])}</a>' for t in ts)+'</div></article></div>'
 page(routes[p['ID']],p['post_title'],body,'reading',plain(content[p['ID']])[:155])
# categories, keeping hierarchy and descriptions
for t in cats:
 ids={t['term_id']};changed=True
 while changed:
  new={c['term_id'] for c in cats if c['parent'] in ids};changed=bool(new-ids);ids|=new
 subset=[p for p in posts if any(x['taxonomy']=='category' and x['term_id'] in ids for x in rel[p['ID']])]
 parent=next((c for c in cats if c['term_id']==t['parent']),None);children=[c for c in cats if c['parent']==t['term_id']]
 body=intro(t['name'],'CATEGORIE')+(f'<p class="container"><a href="{caturl[parent["term_id"]]}">{esc(parent["name"])}</a> / {esc(t["name"])}</p>' if parent else '')+f'<div class="prose category-description">{clean(t["description"]) if t["description"] else ""}</div><div class="container chips">'+''.join(f'<a href="{caturl[c["term_id"]]}">{esc(c["name"])}</a>' for c in children)+'</div><div class="container grid">'+''.join(card(p) for p in subset)+'</div>'
 page(caturl[t['term_id']],t['name'],body)
for t in tags:
 subset=[p for p in posts if any(x['taxonomy']=='post_tag' and x['term_id']==t['term_id'] for x in rel[p['ID']])]
 page('/tag/'+t['slug']+'/',t['name'],intro(t['name'],'TAG')+'<div class="container grid">'+''.join(card(p) for p in subset)+'</div>')
page('/categorie/','Categorie',intro('Le strade della didattica','ESPLORA PER TEMA')+'<div class="container category-list">'+''.join(f'<a class="category-item {"child" if t["parent"] else ""}" href="{caturl[t["term_id"]]}"><span>{esc(t["name"])}</span><small>{sum(any(x["term_id"]==t["term_id"] and x["taxonomy"]=="category" for x in rel[p["ID"]]) for p in posts)} articoli diretti</small></a>' for t in cats)+'</div>')
# remaining public WordPress pages, including substantive historical pages
special={88,95,951,905,1302,3,434}
for p in pages:
 if p['ID'] in account|special:continue
 page(routes[p['ID']],p['post_title'],intro(p['post_title'])+'<article class="prose page-prose">'+content[p['ID']]+'</article>')
# index with progressive enhancement: all articles still available without JS
filters='''<div class="search-controls"><label>Cerca<input type="search" id="query" placeholder="Una parola, un’idea, un’esperienza…"></label><label>Categoria<select id="category"><option value="">Tutti i temi</option>'''+''.join(f'<option>{esc(t["name"])}</option>' for t in cats)+'''</select></label><label>Ordina<select id="sort"><option value="new">Più recenti</option><option value="old">Meno recenti</option><option value="title">Titolo A–Z</option></select></label></div><p id="result-count" role="status" aria-live="polite"></p>'''
page('/articoli/','Articoli',intro('Idee che diventano esperienza','IL DIARIO','70 articoli da leggere, esplorare e portare in classe.')+f'<section class="container" data-search="articles">{filters}<div id="results" class="grid">'+''.join(card(p) for p in posts)+'</div><button id="load-more" class="button" hidden>Mostra altri articoli</button></section>')
page('/ricerca/','Cerca nel sito',intro('Segui una curiosità','RICERCA','Cerca negli articoli e nelle pagine del sito.')+f'<section class="container" data-search="all">{filters}<div id="results" class="grid"></div><button id="load-more" class="button" hidden>Mostra altri risultati</button><noscript><p>La ricerca richiede JavaScript. Puoi consultare la <a href="/mappa-del-sito/">mappa del sito</a>.</p></noscript></section>')
# Panorama UI, links always also available in fallback below scene
scene_data={}
def panorama(key,title,links,home=False):
 fallback=anchors([(x['label'],x['url']) for x in links])
 return f'''<section class="panorama {'home-panorama' if home else ''}" data-scene="{key}" aria-label="{esc(title)}"><div class="pano-view" tabindex="0" role="group" aria-label="Ambiente esplorabile: trascina o usa le frecce della tastiera"><div class="pano-strip"></div></div>{'' if home else '<div class="scene-caption"><a class="back" href="/">Torna all’atrio</a><p class="eyebrow">AMBIENTE PROVVISORIO</p><h1>'+esc(title)+'</h1><p>Esplora e scegli un percorso</p></div>'}<div class="pano-controls"><button data-action="reset" aria-label="Torna alla vista iniziale" title="Vista iniziale">⌂</button><button data-action="rotate" aria-label="Avvia esplorazione automatica" aria-pressed="false" title="Esplorazione automatica">↻</button><button data-action="fullscreen" aria-label="Schermo intero" title="Schermo intero"><svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg></button></div><p class="pano-help">Trascina per esplorare · tocca una porta</p><span class="pano-tooltip" role="status"></span></section><details class="scene-fallback"><summary>Esplora con il menu accessibile</summary><nav aria-label="Percorsi di {esc(title)}">{fallback}</nav></details>'''
homeLinks=[]
for label,url,x,y,w,h in [('Chi sono','/chi-sono/',0.006,.21,.115,.45),('Libri','/libri/',.125,.285,.103,.36),('Inizia da qui','/inizia-da-qui/',.242,.24,.116,.39),('Podcast','/podcast/',.587,.373,.055,.245),('Risorse','/risorse/',.648,.38,.044,.23),('Progetto EduCreativo','/educreativo/',.696,.34,.064,.28),('Articoli','/articoli/',.767,.312,.062,.30),('Accedi al mio universo','/universo/',.836,.237,.093,.416),('Contatti','/contatti/',.936,.25,.064,.41)]:homeLinks.append(dict(label=label,url=url,x=x,y=y,w=w,h=h))
scene_data['home']={'image':'/assets/images/atrio.webp','mode':'panorama','aspect':2,'initial':.50,'hotspots':homeLinks}
page('/','In risonanza con l’armonia','<h1 class="sr-only">Didattica Vibrazionale — In risonanza con l’armonia</h1>'+panorama('home','Atrio',homeLinks,True),'home')
resourceLinks=[('Storytelling','/risorse/storytelling/'),('Escape Room','/risorse/escape-room/'),('Matematica (ri)creativa','/risorse/matematica-ricreativa/'),('Micro Strategie Pratiche di Didattica Socio-Emotiva','/risorse/micro-strategie/'),('App educative','/risorse/app-educative/'),('Flipped Classroom','/risorse/flipped-classroom/'),('Concetti (sor)RIDENDO','/risorse/sorridendo/')]
def room(key,title,links):
 hotspots=[{'label':l,'url':u,'x':(i+.5)/len(links),'y':.49,'w':min(.15,.75/len(links)),'h':.42,'theme':i%3} for i,(l,u) in enumerate(links)]
 scene_data[key]={'image':'/assets/images/'+key+'-placeholder.webp','mode':'360','aspect':4,'initial':.5,'placeholder':True,'hotspots':hotspots}
 return panorama(key,title,hotspots)
page('/risorse/','Risorse',room('risorse','Il laboratorio delle possibilità',resourceLinks)+intro('Risorse da portare in classe','IL LABORATORIO')+'<nav class="container path-grid">'+anchors(resourceLinks)+'</nav><article class="prose page-prose">'+content[951]+'</article>')
page('/risorse/matematica-ricreativa/','Matematica (ri)creativa',intro('Matematica (ri)creativa')+'<nav class="container path-grid">'+anchors([('Matematica','/categorie/matematica/'),('Matematica Divertente','/categorie/'+next(t['slug'] for t in cats if t['term_id']==7)+'/'),('I Giochi nella Didattica della Matematica',routes[556]),('PiGrecopolis',routes[560])])+'</nav>')
for slug,title in [('flipped-classroom','Risorse per la Flipped Classroom'),('sorridendo','Risorse per fissare concetti (sor)RIDENDO')]:
 page('/risorse/'+slug+'/',title,intro(title)+'<div class="prose page-prose"><p class="notice">Questa sezione è presente nella pagina Risorse originale, ma non contiene collegamenti a materiali nel database. Materiali da aggiungere.</p><a href="/risorse/">Torna alle risorse</a></div>')
# 13 podcast episode links preserved
pd=LH.fromstring('<div>'+content[905]+'</div>'); episodes=[]
for a in pd.xpath('.//figcaption/a'):
 episodes.append((('Stagione 2 · ' if len(episodes)==12 else 'Stagione 1 · ')+a.text_content(),a.get('href')))
page('/podcast/','Podcast',room('podcast','Lo studio delle voci',episodes)+intro('Preferisci ascoltare?','PODCAST')+'<article class="prose page-prose podcast-content">'+content[905]+'</article>')
universe=[('Emozioni · Consapevolezza · Meditazione','/universo/consapevolezza/'),('Mate e Matica · Circonia','/universo/mate-e-matica/'),('Storytelling Express','/universo/storytelling-express/')]
page('/universo/','Accedi al mio universo',room('universo','Tre universi, un’unica curiosità',universe)+'<nav class="container path-grid">'+anchors(universe)+'</nav>')
page('/universo/consapevolezza/','Emozioni, consapevolezza e meditazione',intro('Emozioni · Consapevolezza · Meditazione','IL TUO PERCORSO INTERIORE')+'<nav class="container path-grid">'+anchors([('Mindfulness','/categorie/mindfulness/'),('Respirazione','/categorie/respirazione/'),('Competenze socio-emotive','/risorse/micro-strategie/')])+'</nav>')
page('/universo/mate-e-matica/','Mate e Matica',intro('Benvenuti a Circonia','MATE E MATICA')+'<nav class="container path-grid">'+anchors([('App educative','/risorse/app-educative/'),('Storytelling matematico','/categorie/storytelling-matematico/'),('Il libro Mate Matica e la magia nella formula','https://www.amazon.it/Mate-Matica-magia-nella-formula/dp/B0H85C3ZZ1')])+'</nav><p class="prose notice">Ambiente di Circonia: immagine definitiva da inserire.</p>')
page('/universo/storytelling-express/','Storytelling Express',intro('Storytelling Express','TUTTI A BORDO')+'<div class="prose page-prose"><p class="train" aria-label="Un trenino">🚂</p><p class="notice">Ambiente del trenino: illustrazione definitiva da inserire.</p><a class="button" href="https://www.amazon.it/dp/B0HJX65LSB">Scopri il libro</a><p><a href="/risorse/storytelling/">Esplora le risorse di storytelling</a></p></div>')
# books
books=[{'id':'didattica','title':'Didattica Vibrazionale – In risonanza con l’armonia','cover':'/assets/images/cover1.jpg','page':routes[45],'source':45,'preview':None,'previewType':'pdf'},{'id':'diario','title':'Diario delle Competenze Socio-Emotive','cover':'/assets/images/cover2.jpg','page':routes[1355],'source':1355,'preview':None,'previewType':'pdf'}]
body=intro('Libri per abitare la didattica','LA BIBLIOTECA')
for b in books:
 body+=f'<section class="book container"><div class="book-cover"><img src="{b["cover"]}" alt="Copertina di {esc(b["title"])}"></div><div><p class="eyebrow">CLAUDIA BARTOLI</p><h2>{esc(b["title"])}</h2><p>{esc(plain(content[b["source"]])[:560])}…</p><div class="actions"><a class="button" href="{b["page"]}">Scopri il libro</a><button class="button secondary" data-preview="{b["id"]}">Sfoglia l’anteprima</button></div><small>Anteprima in preparazione</small></div></section>'
body+='<section class="container"><h2>Altri libri e percorsi</h2><div class="prose">'+content[1302]+'</div></section>'
page('/libri/','Libri',body)
social=[('Facebook · Didattica Vibrazionale','https://www.facebook.com/profile.php?id=61562103593563'),('Facebook · Mate Matica','https://www.facebook.com/profile.php?id=61594381105227'),('Canale WhatsApp','https://whatsapp.com/channel/0029Vb8uh2P7dmecXqdI0h1U'),('Email · didatticavibrazionale@gmail.com','mailto:didatticavibrazionale@gmail.com')]
page('/contatti/','Contatti',intro('Restiamo in risonanza','CONTATTI','Segui i progetti, scopri le nuove risorse e condividi le tue esperienze.')+'<nav class="container contact-list">'+anchors(social)+'</nav><div class="container"><p class="notice">Instagram · link da inserire.</p><p>Indirizzo postale non disponibile negli allegati.</p></div>')
# Legal: source text saved but never presented as up-to-date policy for new hosting
page('/privacy-policy/','Privacy',intro('Privacy','INFORMAZIONI SUL SITO')+'<article class="prose page-prose"><p class="notice">Informativa del nuovo sito statico da completare dopo la scelta dell’hosting. Il testo WordPress originale è conservato sotto come documento storico, non come informativa aggiornata.</p><p>Il sito non contiene moduli, account, commenti o strumenti di analytics. La ricerca avviene nel browser. Le immagini remote possono collegare il browser al sito di origine. Video, podcast e risorse esterne si aprono solo attraverso i relativi collegamenti.</p><p>Titolare indicata nel database: Claudia Bartoli · <a href="mailto:didatticavibrazionale@gmail.com">didatticavibrazionale@gmail.com</a>.</p><details><summary>Informativa WordPress originale · 21/02/2026</summary>'+content[3]+'</details></article>')
page('/cookie-policy-ue/','Cookie',intro('Cookie e contenuti esterni')+'<article class="prose page-prose"><p>Il codice di questo sito statico non imposta cookie né usa archivi persistenti nel browser. I siti esterni aperti tramite link hanno le proprie condizioni.</p><p class="notice">Nel database la Cookie Policy era generata dal plugin Complianz: il testo non è incluso nell’esportazione. Informativa da completare con i servizi dell’hosting scelto.</p></article>')
page('/legale/','Copyright e attribuzioni',intro('Copyright e attribuzioni')+'<article class="prose page-prose"><h2>Copyright del sito</h2><p>© Claudia Bartoli · Didattica Vibrazionale.</p><p class="notice">Condizioni generali di riuso del sito: testo definitivo da inserire.</p><h2>Risorse di terzi</h2><p>I collegamenti e le eventuali indicazioni di attribuzione contenuti negli articoli sono conservati dai testi originali. Le condizioni dei singoli materiali restano da consultare presso le rispettive fonti.</p><h2>Privacy</h2><p><a href="/privacy-policy/">Informazioni sulla privacy</a> · <a href="/cookie-policy-ue/">Cookie e contenuti esterni</a></p></article>')
# accessible directory
page('/mappa-del-sito/','Mappa del sito',intro('Tutti i percorsi')+'<nav class="container sitemap">'+anchors(allnav+[('Categorie','/categorie/'),('Ricerca','/ricerca/')])+''.join(f'<a href="{routes[p["ID"]]}">{esc(p["post_title"])}</a>' for p in pages if p['ID'] not in account)+''.join(f'<a href="{routes[p["ID"]]}">{esc(p["post_title"])}</a>' for p in posts)+'</nav>')
page('/404/','Pagina non trovata',intro('Questo sentiero ha cambiato strada')+'<div class="container"><p>Prova la ricerca o ritorna all’atrio.</p><a class="button" href="/ricerca/">Cerca nel sito</a> <a class="button secondary" href="/">Torna all’atrio</a></div>');shutil.copy(ROOT/'404/index.html',ROOT/'404.html');shutil.rmtree(ROOT/'404')
index=[]
for p in posts+pages:
 if p['ID'] in account|{3,434}:continue
 if p['ID']==88: content[p['ID']]='Facebook · Didattica Vibrazionale. Facebook · Mate Matica. Canale WhatsApp. Email: didatticavibrazionale@gmail.com. Instagram: link da inserire.'
 if p['ID']==95: content[p['ID']]='Archivio completo degli articoli, con ricerca, categorie e ordinamento cronologico.'
 index.append({'id':p['ID'],'type':p['post_type'],'title':p['post_title'],'slug':p['post_name'],'url':routes[p['ID']],'date':p['post_date'][:10],'excerpt':plain(content.get(p['ID'],''))[:220],'categories':[t['name'] for t in rel[p['ID']] if t['taxonomy']=='category'],'tags':[t['name'] for t in rel[p['ID']] if t['taxonomy']=='post_tag'],'text':plain(content.get(p['ID'],'')),'image':p.get('featured','')})
jput('search-index.json',index);jput('assets/data/scenes.json',scene_data);jput('assets/data/books.json',books);jput('assets/data/media-map.json',{u:'' for u in media if u});jput('assets/data/legacy-ids.json',{str(k):v for k,v in routes.items()})
jput('assets/data/categories.json',cats)
# readable static aliases work on GitHub Pages where _redirects isn't interpreted
redirects=[]
for a,b in old.items():
 if a==b:continue
 redirects.append(f'{a} {b} 301');redirects.append(f'{a.rstrip("/")} {b} 301')
 alias=ROOT/(a.strip('/')+'/index.html')
 if not alias.exists():put(str(alias.relative_to(ROOT)),f'<!doctype html><html lang="it"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={esc(b)}"><title>Pagina trasferita</title></head><body><p><a href="{esc(b)}">Vai alla nuova pagina</a></p></body></html>')
put('_redirects','\n'.join(redirects)+'\n')
# no unknown IDs/users/options/SQL in publishable output
menus=[]
for p in P.values():
 if p['post_type']=='nav_menu_item' and p['post_status']=='publish':
  m=meta[p['ID']]; oid=m.get('_menu_item_object_id','');target=routes.get(int(oid)) if oid.isdigit() else None
  if not target:target=rewrite(m.get('_menu_item_url',''))
  menus.append({'title':p['post_title'] or P.get(int(oid) if oid.isdigit() else 0,{}).get('post_title',''),'url':target,'parent':m.get('_menu_item_menu_item_parent'),'order':p['menu_order']})
jput('assets/data/original-menu.json',menus)
report={'source':'Esportazione WordPress 08/10/2026','published_articles':len(posts),'published_pages':len(pages),'content_pages':len(pages)-len(account),'account_pages_redirected':len(account),'categories':len(cats),'tags':len(tags),'podcast_episodes':len(episodes),'removed_dynamic_components':issues,'converted_components':conversion,'old_domain_links_to_review':sorted(unknown_internal),'media_references':len(media),'placeholders':['Sfondi Risorse, Podcast e Universo','Anteprime PDF dei due libri','Instagram e indirizzo postale','Informativa privacy del nuovo hosting e condizioni generali di riuso','Flipped Classroom e (sor)RIDENDO: nessun link nel SQL','PiGrecopolis: pagina originale vuota','Illustrazioni definitive dei singoli universi'],'note':'Testi completi importati; nessun utente, password, ordine o tabella privata incluso.'}
jput('tools/import-report.json',report)
# public source makes audit possible; original legal wording preserved above
jput('tools/content-audit.json',[{'id':p['ID'],'title':p['post_title'],'type':p['post_type'],'source_characters':len(p['post_content']),'converted_characters':len(content.get(p['ID'],'')),'url':routes[p['ID']]} for p in posts+pages])
jput('tools/media-inventory.json',list(media.values()))
put('assets/images/favicon.svg','<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="15" fill="#081b31"/><text x="32" y="43" text-anchor="middle" font-family="Georgia" font-size="32" fill="#e6c98a">DV</text></svg>')
# The approved home image and local covers already exist in assets/images.

print(json.dumps({k:report[k] for k in ['published_articles','published_pages','content_pages','categories','podcast_episodes','media_references']},indent=2));print('Unresolved legacy',report['old_domain_links_to_review'])
