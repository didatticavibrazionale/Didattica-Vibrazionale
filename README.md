# Didattica Vibrazionale

**In risonanza con l’armonia** — sito statico completo, esportazione del 08/10/2026.

## Contenuto del pacchetto

- 70 articoli pubblicati, con testo integrale, data, slug, categorie, tag, immagini e collegamenti presenti nel SQL.
- 35 pagine WordPress elaborate: 26 pagine di contenuto migrate/riprogettate e 9 pagine tecniche di iscrizione sostituite da rimandi all’archivio pubblico.
- 21 categorie con descrizioni e gerarchie; 219 tag conservati e navigabili.
- 13 episodi podcast recuperati (12 della stagione 1, uno della stagione 2).
- Home con l’immagine approvata e 9 aree trasparenti sulle porte.
- Risorse, Podcast e Universo con ambienti panoramici provvisori, esplorabili a rotazione continua e accessi funzionanti.
- Ricerca locale in articoli e pagine; archivio con filtri, ordinamento e caricamento progressivo.
- Nessun PHP, database runtime, dipendenza CDN, modulo, login, tracciamento o build obbligatoria.

Il SQL originale, le bozze, gli utenti, gli ordini, le password e le impostazioni private WordPress **non sono inclusi** nel sito.

## Aprire il sito sul proprio computer

Aprire direttamente `index.html` con doppio clic non basta: il browser blocca normalmente la lettura dei JSON da `file://`.

Con Python installato, aprire un terminale dentro la cartella del progetto:

```sh
python -m http.server 8000
```

Aprire `http://localhost:8000`. In alternativa usare un server statico locale, per esempio Live Server. Anche senza JavaScript gli articoli restano leggibili e il menu accessibile degli ambienti conserva tutti i collegamenti.

## GitHub + Cloudflare Pages

1. Estrarre lo ZIP. Creare un repository GitHub e caricare **il contenuto** della cartella `didattica-vibrazionale`, con `index.html` nella radice del repository. Non caricare lo ZIP come unico file.
2. In Cloudflare aprire **Workers & Pages → Create application → Pages → Import an existing Git repository**. Collegare il repository.
3. Impostare:

| Impostazione | Valore |
| --- | --- |
| Production branch | `main` (o il nome effettivo del ramo) |
| Framework preset | None |
| Build command | `exit 0` |
| Build output directory | `.` |
| Root directory | vuota, se `index.html` è nella radice |

4. Pubblicare. Aprire il dominio `pages.dev` assegnato e controllare la home e un articolo.
5. Le modifiche caricate nel repository saranno usate per le successive pubblicazioni.

Il progetto è per **Cloudflare Pages**, non richiede la procedura Workers con Wrangler. Il file `_redirects` è già incluso. La fonte ufficiale consultata per le impostazioni è: https://developers.cloudflare.com/pages/framework-guides/deploy-anything/ (consultata 08/10/2026).

Per una pubblicazione manuale si può usare Pages Direct Upload caricando la cartella. Il pacchetto non è stato pubblicato su un account esterno.

### GitHub Pages, se usato come hosting

Il percorso consigliato è un dominio personalizzato o un sito nella radice `nomeutente.github.io`. Il progetto usa URL assoluti rispetto alla radice (`/assets/...`). La pubblicazione sotto `nomeutente.github.io/nome-repository/` richiede di adattare **anche i percorsi nei JSON e negli script** al prefisso del repository: non basta cambiare gli HTML. GitHub come deposito del codice collegato a Cloudflare non ha questo problema. Gli alias HTML funzionano anche senza `_redirects`.

## Struttura

```text
index.html
assets/css/site.css
assets/js/site.js
assets/js/panorama.js
assets/images/
assets/data/scenes.json
assets/data/books.json
assets/data/media-map.json
assets/data/categories.json
assets/data/original-menu.json
articoli/index.html
articoli/<slug>/index.html
categorie/<slug>/index.html
tag/<slug>/index.html
risorse/{storytelling,escape-room,matematica-ricreativa,micro-strategie,app-educative,...}/
podcast/  libri/  chi-sono/  educreativo/  universo/  contatti/  inizia-da-qui/
ricerca/  mappa-del-sito/  legale/  privacy-policy/  cookie-policy-ue/
search-index.json
_redirects
404.html
tools/
```

## Hotspot e panorami

Modificare `assets/data/scenes.json`:

- `image`: percorso locale dello sfondo.
- `mode: "panorama"`: vista piana panoramica limitata ai bordi, adatta alla home fornita.
- `mode: "360"`: ambiente cilindrico provvisorio con rotazione continua, pannelli e collegamenti disposti intorno al visitatore.
- `mode: "equirectangular"`: visualizzatore sferico WebGL integrato per un futuro panorama realmente equirettangolare 2:1. In questo caso usare `placeholder: false` e coordinate dei centri degli accessi.
- `initial`: posizione orizzontale iniziale, fra 0 e 1.
- `aspect`: rapporto larghezza/altezza del panorama piano.
- `hotspots`: etichetta accessibile, URL e coordinate normalizzate `x`, `y`, `w`, `h`.

Nella home `x,y` sono l’angolo superiore sinistro dell’area. Nei placeholder `x` è il centro del pannello. Nel modo sferico `x,y` sono il centro nella texture 2:1 (0.5,0.5 = direzione iniziale centrale).

**L’immagine approvata, pur avendo proporzioni 2:1, è un’illustrazione panoramica prospettica: non è una sfera senza giunture.** Viene mantenuta intatta in una vista trascinabile, senza forzare una chiusura a 360°. Su smartphone si esplora lateralmente, con i nove accessi nelle rispettive posizioni reali. I tre sfondi interni sono volutamente astratti e dichiarati provvisori, non illustrazioni definitive di stanze.

I pannelli provvisori identificano i temi; gli hotspot di collegamento sovrapposti sono trasparenti. Nessun pallino sulla home. Tastiera: Tab per i collegamenti, frecce per spostare la vista, Home per ripristinarla. L’autorotazione è sempre spenta all’avvio e non parte con `prefers-reduced-motion`. Nessun sensore di movimento richiesto.

Per sostituire Risorse/Podcast/Universo: copiare il panorama in `assets/images`, aggiornare `image`, impostare il `mode` corretto, rimuovere i pannelli con `placeholder: false` e riposizionare gli hotspot. Il menu accessibile resta disponibile sotto ogni scena, anche senza WebGL.

## Immagini remote

Le due copertine e la home sono locali. Le immagini WordPress continuano a usare i riferimenti originali del database. Se non si caricano, compare un placeholder leggibile. Le immagini del vecchio dominio **dipendono dalla permanenza di `wp-content/uploads`**: se si sposta il dominio su Cloudflare senza trasferire uploads, gli URL remoti sullo stesso dominio non raggiungeranno più il vecchio server.

Per sostituirle automaticamente:

1. Copiare i file recuperati in `assets/images/imported/`.
2. In `assets/data/media-map.json`, assegnare a ciascun URL remoto il nuovo percorso locale (`/assets/images/imported/nome.jpg`). Lasciare vuoti quelli non disponibili.
3. Eseguire `python tools/localize_media.py` per riscrivere gli HTML e l’indice. Lo script verifica prima che i nuovi file esistano. Non scarica file e non richiede pacchetti esterni.

La mappa è applicata anche dal browser, ma la riscrittura statica è preferibile perché evita la prima richiesta all’URL vecchio. `tools/media-inventory.json` indica gli ID dei contenuti che usano ciascuna immagine.

## Anteprime dei libri

In `assets/data/books.json`, sostituire `preview: null` con l’URL del PDF locale o del flipbook. Il pulsante apre un dialogo con visualizzatore e collegamento alternativo. Un flipbook esterno deve consentire l’incorporamento. Finché il file manca, il pulsante mostra chiaramente “anteprima non ancora disponibile”, senza link fittizi.

## Migrazione e contenuti

- Gli slug originali sono mantenuti negli articoli sotto `/articoli/<slug>/`; i vecchi URL nella radice hanno alias e redirect 301.
- Le vecchie categorie semplici e gerarchiche hanno redirect. Gli URL `?p=ID` e `?page_id=ID` vengono risolti lato browser dalla mappa degli ID. `_redirects` non viene usato per fingere il supporto a filtri sulle query string.
- Tag, date, bibliografia, note Gutenberg memorizzate nei metadati e link agli allegati sono conservati.
- I commenti Gutenberg e il divisore `more` sono rimossi: il testo successivo resta liberamente leggibile.
- I riquadri dinamici “ultimi articoli” sono sostituiti da accessi all’archivio. I componenti PMPro, Contact Form 7 e Complianz non vengono eseguiti.
- Video, iframe, contenuti Genially e incorporamenti PDF sono trasformati in collegamenti alla fonte. I link PDF di download restano presenti. I materiali di terzi richiedono una connessione e dipendono dai relativi fornitori.
- Menu WordPress: conservato per consultazione in `assets/data/original-menu.json`, con la navigazione principale riorganizzata secondo la nuova struttura richiesta.
- Le date e le indicazioni temporali presenti nei testi originali (per esempio orari provvisori del podcast) non sono state aggiornate arbitrariamente.

Rapporti: `tools/import-report.json`, `tools/content-audit.json` e `tools/verification-report.json`.

## Rigenerare da un nuovo SQL (facoltativo)

Il sito è già generato: non serve eseguire questi comandi per pubblicarlo. Gli script sono inclusi per consentire una nuova estrazione automatica, senza ricopiare gli articoli.

```sh
python -m pip install lxml pillow
python tools/rebuild.py /percorso/del/nuovo-export.sql
python tools/verify.py
```

Fare prima una copia del progetto: `rebuild.py` ricrea le pagine e i file dati editoriali, quindi può sovrascrivere modifiche manuali a tali file. Mantiene CSS/JavaScript, home e copertine esistenti. Il lettore SQL supporta il formato INSERT esteso di phpMyAdmin usato dall’esportazione allegata; non esegue istruzioni SQL. Il prefisso atteso è `wp_`. Lo script di verifica contiene il conteggio atteso di questa esportazione (70), da aggiornare se cambia il numero degli articoli.

## Elementi ancora da completare

- Panorami illustrati definitivi per Risorse, Podcast e Universo; illustrazioni dei singoli universi (India/consapevolezza, Circonia, trenino).
- PDF/flipbook delle anteprime.
- URL Instagram e indirizzo postale: non ricavati dai documenti.
- Materiali di “Flipped Classroom” e “Concetti (sor)RIDENDO”: nel SQL erano presenti le voci ma non i collegamenti.
- Pagina PiGrecopolis: presente ma vuota nel database. Non sono stati inseriti URL presi dalla memoria o da fonti diverse dagli allegati.
- Informativa privacy definitiva del nuovo hosting e testo generale delle condizioni di riuso. La vecchia privacy è conservata come documento storico identificato. La Cookie Policy Complianz non aveva testo statico nel SQL.
- Eventuali immagini/allegati remoti mancanti: sostituibili con i file di uploads quando saranno disponibili.

## Librerie, accessibilità e privacy tecnica

Il browser usa solo HTML/CSS/JavaScript locale, font di sistema e un visualizzatore panoramico originale. Nessuna libreria esterna o CDN in produzione. `lxml` e Pillow servono solo per l’eventuale rigenerazione offline.

Contrasto, focus tastiera, testi alternativi, menu mobile, dialogo chiudibile con X/Esc, ricerca con stato annunciato, lettura senza JavaScript e preferenze di movimento ridotto sono previsti nel codice. Nessuna promessa di certificazione automatica WCAG: il rapporto di verifica specifica le prove effettivamente eseguite.
