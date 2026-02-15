# Nikon Camera Controller - Implementation Plan

> Toteutussuunnitelma Claude Code + ihminen -työskentelyyn.
> Jokainen vaihe on itsenäinen, testattava kokonaisuus.
> Ihminen hyväksyy vaiheen ennen seuraavaan siirtymistä.

## Ohjeet Claude Codelle

- Toteuta yksi vaihe kerrallaan, älä hyppää eteenpäin
- Jokaisen vaiheen jälkeen: aja testit, näytä tulos ihmiselle
- Jos vaiheessa on epäselvyyttä, kysy ennen toteutusta
- Noudata speksiä (`docs/nikon-camera-controller-mvp-spec.md`)
- Käytä FastHTML:n nykyistä API:a (v0.12+, ei vanhentuneita patterneja)
- Merkitse valmistuneet vaiheet `[x]` kun ihminen hyväksyy

## Huomioita speksistä

Speksissä on joitain kohtia jotka eivät vastaa FastHTML:n nykyistä API:a:
- FastHTML-versio on nykyään 0.12.x (speksissä 0.8)
- Oletusportti on 5002 (speksissä 5000)
- Reitit käyttävät funktion nimeä HTTP-metodina (`def get():`, `def post():`), ei `methods=[]`-parametria
- `serve()` käynnistää sovelluksen, ei tarvita `if __name__ == "__main__"`
- Riippuvuuksien versiot tulee päivittää nykyisiin

---

## Phase 1: Project Foundation

### 1.1 Projektin perusrakenne
- [x] Luo hakemistorakenne speksin mukaisesti (`app/`, `app/camera/`, `app/analysis/`, `app/storage/`, `app/components/`, `app/static/`, `data/`, `tests/`)
- [x] Luo `pyproject.toml` projektin konfiguraatiolla
- [x] Luo `requirements.txt` **nykyisillä** versioilla (ei speksin vanhentuneilla)
- [x] Luo `.gitignore` (Python, venv, data/captures/, .DS_Store)
- [x] Luo tyhjät `__init__.py` -tiedostot kaikkiin paketteihin
- [x] Luo `LICENSE` -tiedosto (MIT, vaihdettavissa BSL 1.1:een myöhemmin)

**Hyväksyntä:** Ihminen tarkistaa rakenteen, ajaa `pip install -r requirements.txt`

### 1.2 FastHTML-sovelluksen runko
- [x] Luo `app/main.py` minimaalisella FastHTML-sovelluksella
- [x] Etusivu (`/`) renderöi peruslayoutin (header, tyhjät paneelit)
- [x] Staattisten tiedostojen tarjoilu (`app/static/`)
- [x] Perus-CSS (`app/static/css/style.css`) — layout-grid, värit speksistä
- [x] Sovellus käynnistyy: `python app/main.py` → `localhost:5002`

**Hyväksyntä:** Ihminen avaa selaimen, näkee tyhjän layout-pohjan

### 1.3 Testausinfra
- [x] Luo `tests/conftest.py` — FastHTML TestClient fixture
- [x] Luo `tests/test_routes.py` — testi: etusivu palauttaa 200
- [x] Varmista: `pytest tests/` ajautuu onnistuneesti
- [x] Lisää `Makefile` tai vastaava: `make test`, `make run`, `make lint`

**Hyväksyntä:** `pytest tests/` näyttää vihreää

---

## Phase 2: Camera Connection

### 2.1 CameraController-luokan perusrakenne
- [x] Luo `app/camera/controller.py` — `CameraController`-luokka
- [x] Toteuta `connect()` — gPhoto2-yhteys, PTPCamera-agentin tappaminen macOS:llä
- [x] Toteuta `disconnect()`
- [x] Toteuta `get_status()` — palauttaa dict (connected, battery, model, storage_free)
- [x] Toteuta virhekäsittely: `CameraConnectionError`, `CameraNotConnectedError` (oma exceptions-moduuli)
- [x] Kirjoita testit: `tests/test_camera.py` — mock-pohjaiset yksikkötestit (ei vaadi oikeaa kameraa)

**Hyväksyntä:** Testit menevät läpi. Ihminen voi halutessaan testata oikealla kameralla.

### 2.2 Camera Status -UI-komponentti
- [x] Luo `app/components/status.py` — `CameraStatus()`-funktio joka renderöi status-widgetin
- [x] Luo reitti `GET /api/camera/status` — palauttaa status-fragmentin
- [x] Lisää etusivulle status-widget, joka pollaa HTMX:llä (`hx_trigger="every 5s"`)
- [x] Luo reitit `POST /api/camera/connect` ja `POST /api/camera/disconnect`
- [x] Lisää UI:hin Connect/Disconnect -nappi

**Hyväksyntä:** UI näyttää "Disconnected". Connect-nappi yrittää yhdistää (onnistuu/epäonnistuu riippuen onko kamera kiinni).

### 2.3 Camera Settings — read & write
- [x] Luo `app/camera/settings.py` — `CameraSettings` dataclass
- [x] Toteuta `CameraController.get_settings()` — lukee asetukset gPhoto2:lta
- [x] Toteuta `CameraController.get_capabilities()` — kyselee tuetut arvot kameralta
- [x] Toteuta `CameraController.set_settings(**kwargs)` — asettaa yhden tai useamman asetuksen
- [x] Luo `app/camera/capabilities.py` — `CameraCapabilities` dataclass
- [x] Testit: settings luku/kirjoitus mock-pohjaisesti

**Hyväksyntä:** Testit menevät läpi. Ihminen voi testata oikealla kameralla: lue asetukset → muuta ISO → lue uudelleen → arvo muuttunut.

### 2.4 Camera Controls -UI-komponentti
- [x] Luo `app/components/controls.py` — `CameraControls()`-funktio
- [x] ISO-selector (Select-elementti, arvot capabilities-kyselystä)
- [x] Shutter speed -selector
- [x] Aperture-selector
- [x] Exposure compensation -slider
- [x] White balance -selector
- [x] Jokainen kontrolli lähettää `hx_post="/api/camera/settings"` muutoksella
- [x] Luo reitti `POST /api/camera/settings` — vastaanottaa yksittäisen asetuksen muutoksen
- [x] Luo reitti `GET /api/camera/settings` — palauttaa nykyiset asetukset fragmenttina

**Hyväksyntä:** UI näyttää kameran nykyiset asetukset select-elementeissä. Arvon vaihto päivittää kameran asetuksen ja UI päivittyy.

---

## Phase 3: Image Capture & Display

### 3.1 Kuvanotto-toiminto
- [ ] Toteuta `CameraController.capture()` — ottaa kuvan, lataa tiedoston
- [ ] Luo `app/storage/files.py` — tiedostonhallinta (nimeäminen, polut, `data/captures/`-kansion luonti)
- [ ] Tiedostonimi: `IMG_YYYYMMDD_HHMMSS.jpg`
- [ ] Testit: capture mock-pohjaisesti (palauttaa Path-objektin)

**Hyväksyntä:** Testit menevät läpi. Ihminen voi testata oikealla kameralla: kuva tallentuu `data/captures/`-kansioon.

### 3.2 Kuvan näyttö UI:ssa
- [ ] Luo `app/components/viewer.py` — `ImageViewer()`-funktio
- [ ] Luo reitti `GET /images/{filename}` — tarjoilee kuvatiedoston
- [ ] Luo Capture-nappi UI:hin, joka lähettää `POST /api/capture`
- [ ] `POST /api/capture` -reitti: ottaa kuvan → palauttaa HTMX-fragmentti (kuva + metadata)
- [ ] Placeholder "No image captured" kun kuvaa ei ole vielä otettu
- [ ] Kuvan perusmetadata UI:ssa (tiedostonimi, asetukset, aika)

**Hyväksyntä:** Capture-nappi ottaa kuvan → kuva näkyy UI:ssa muutamassa sekunnissa. Metadata näkyy kuvan yhteydessä.

### 3.3 Virhekäsittely
- [ ] Camera disconnected -tilanne capturen aikana → selkeä virheviesti UI:ssa
- [ ] Capture timeout → virheviesti
- [ ] Tiedostojärjestelmävirhe → virheviesti
- [ ] UI:n error-state: punainen banneri virheen kuvauksen kanssa, häviää seuraavalla onnistuneella toiminnolla

**Hyväksyntä:** Ihminen irrottaa kameran → yrittää capturia → näkee ymmärrettävän virheen UI:ssa.

---

## Phase 4: Image Analysis

### 4.1 Histogrammi ja metriikat
- [ ] Luo `app/analysis/processor.py` — `ImageAnalyzer`-luokka
- [ ] Toteuta `analyze()` — kokonainen analyysi yhdellä kutsulla
- [ ] Toteuta `calculate_histogram()` — RGB + luminanssi, 256 biniä
- [ ] Toteuta `calculate_metrics()` — keskikirkkaus, yli/alivalottuneet %, dynaaminen alue
- [ ] Toteuta `read_exif()` — EXIF-datan luku Pillowlla
- [ ] Luo `ImageAnalysis` dataclass
- [ ] Testit: analysoi testikuva, tarkista metriikat (käytä tunnettua testikuvaa)

**Hyväksyntä:** Testit menevät läpi. Analysoi tunnetun kuvan → metriikat vastaavat odotettuja.

### 4.2 Histogrammi-visualisointi
- [ ] Luo `app/analysis/histogram.py` — `generate_histogram_plot()`
- [ ] Matplotlib-histogrammi: RGB-kanavat + luminanssi, läpinäkyvä tausta
- [ ] Tallenna PNG-tiedostona `data/captures/`-kansioon kuvan viereen
- [ ] Luo reitti `GET /histogram/{capture_filename}.png`

**Hyväksyntä:** Histogrammi-PNG generoituu ja näyttää oikealta.

### 4.3 Analyysi-UI-komponentit
- [ ] Luo `app/components/histogram.py` — `HistogramDisplay()`-funktio
- [ ] Luo `app/components/metrics.py` — `MetricsPanel()`-funktio
- [ ] Varoitukset: punaisella jos ylivalottuneita > 5%, alivalottuneita > 5%
- [ ] Integroi capture-reittiin: kuvan oton jälkeen palautetaan myös histogrammi + metriikat
- [ ] Päivitä `POST /api/capture` — palauttaa koko preview-panelin (kuva + histogrammi + metriikat)

**Hyväksyntä:** Capture-nappi → kuva + histogrammi + metriikat näkyvät kaikki yhdellä painalluksella. Varoitukset näkyvät oikein.

---

## Phase 5: Iterative Workflow

### 5.1 Capture History
- [ ] Luo `app/storage/session.py` — `CaptureHistory`-luokka (in-memory)
- [ ] Tallenna jokainen kuvan otto + analyysi historiaan
- [ ] Rajoitus: viimeiset 50 kuvaa muistissa (konfiguroitava)
- [ ] Toteuta `get_recent(n)` — palauttaa viimeisimmät n kuvaa

**Hyväksyntä:** Ota useita kuvia → historia kasvaa. Sovelluksen uudelleenkäynnistys tyhjentää historian (mutta kuvat säilyvät levyllä).

### 5.2 Historia-UI ja navigaatio
- [ ] Lisää sivupalkkiin capture-historia (thumbnailit + asetustiivistelmä)
- [ ] Klikkaa aiempaa kuvaa → preview-paneeli päivittyy (kuva + histogrammi + metriikat)
- [ ] Korostus: aktiivinen/valittu kuva erottuu listasta
- [ ] Reitti `GET /api/captures` — palauttaa historialistan fragmenttina
- [ ] Reitti `GET /api/captures/{id}` — palauttaa yksittäisen kuvan tiedot

**Hyväksyntä:** Ota 3+ kuvaa → kaikki näkyvät sivupalkissa → klikkaa aiempaa → analyysi vaihtuu.

### 5.3 Settings Presets
- [ ] Luo preset-tallennuslogiikka (JSON-tiedostot `data/presets/`-kansiossa)
- [ ] UI: "Save preset" -nappi + nimi-kenttä
- [ ] UI: Preset-valitsin (dropdown) — lataa tallennetut asetukset
- [ ] Reitit: `POST /api/camera/presets` (tallenna), `GET /api/camera/presets` (listaa), `GET /api/camera/presets/{name}` (lataa)
- [ ] Lataus asettaa kameran asetukset ja päivittää UI:n

**Hyväksyntä:** Tallenna preset "Studio portrait" → vaihda asetuksia → lataa preset → asetukset palautuvat. Presetit säilyvät sovelluksen uudelleenkäynnistyksen yli.

---

## Phase 6: Viimeistely

### 6.1 UI-polish
- [ ] Responsiivinen layout (toimii kohtuullisesti myös kapeammalla näytöllä)
- [ ] Keyboard shortcuts: Enter = capture, Ctrl+S = save preset
- [ ] Loading-indikaattorit: capture-napin "Taking photo..." -tila
- [ ] Tyylien viimeistely speksin värimaailmalla

**Hyväksyntä:** Ihminen arvioi UI:n käytettävyyden kokonaisuutena.

### 6.2 Testien kattavuus ja laatu
- [ ] Varmista testikattavuus: kaikki ydinkomponentit katettu
- [ ] Integraatiotesti: connect → set settings → capture → analyze → historia
- [ ] Aja `ruff check app/` — ei virheitä
- [ ] Aja `mypy app/` — ei type-virheitä (tai dokumentoidut poikkeukset)

**Hyväksyntä:** `pytest tests/` — kaikki vihreää. `ruff` ja `mypy` puhtaat.

### 6.3 Dokumentaatio
- [ ] `README.md` — asennusohjeet (macOS), käyttöohjeet, kuvakaappaukset
- [ ] Docstringit kaikissa julkisissa luokissa ja funktioissa
- [ ] `CHANGELOG.md` — v0.1.0 release notes

**Hyväksyntä:** Ihminen lukee READMEn, seuraa ohjeita puhtaalta koneelta → sovellus käynnistyy.

---

## Vaiheiden yhteenveto

| Vaihe | Kuvaus | Tulos |
|-------|--------|-------|
| 1.1 | Projektin perusrakenne | Hakemistot, riippuvuudet, .gitignore |
| 1.2 | FastHTML-runko | Tyhjä layoutpohja selaimessa |
| 1.3 | Testausinfra | pytest toimii, 1 testi vihreänä |
| 2.1 | CameraController | Yhteys kameraan, mock-testit |
| 2.2 | Status-UI | Kameran tila näkyy selaimessa |
| 2.3 | Settings read/write | Asetusten luku ja kirjoitus |
| 2.4 | Controls-UI | Kameran säädöt selaimessa |
| 3.1 | Kuvanotto | capture() toimii, tiedosto tallentuu |
| 3.2 | Kuva UI:ssa | Otettu kuva näkyy selaimessa |
| 3.3 | Virhekäsittely | Selkeät virheviestit |
| 4.1 | Analyysi-backend | Histogrammi + metriikat |
| 4.2 | Histogrammi-visualisointi | PNG-histogrammi |
| 4.3 | Analyysi-UI | Histogrammi + metriikat selaimessa |
| 5.1 | Capture History | In-memory historia |
| 5.2 | Historia-UI | Kuvien selaus sivupalkissa |
| 5.3 | Presets | Asetusten tallennus/lataus |
| 6.1 | UI-polish | Viimeistellyt tyylit + shortcuts |
| 6.2 | Testit ja laatu | Kattavat testit, lintteri puhdas |
| 6.3 | Dokumentaatio | README, docstringit, changelog |

---

## Muistilista toteutuksen aikana

### FastHTML-kohtaiset huomiot
- Käytä `app, rt = fast_app()` -patternia
- Reitit: funktion nimi = HTTP-metodi (`def get():`, `def post():`)
- HTMX-attribuutit: `hx_get`, `hx_post`, `hx_target`, `hx_trigger`, `hx_swap`
- `serve()` käynnistää sovelluksen portissa 5002
- HTMX-pyynnöt saavat HTML-fragmentin, normaalit pyynnöt kokonaisen sivun

### gPhoto2-kohtaiset huomiot (macOS)
- `killall -9 PTPCamera` ja `killall -9 ptpcamerad` ennen yhteyden muodostamista
- Kamera pitää olla PTP/MTP-tilassa
- `gphoto2 --auto-detect` testaa onko kamera näkyvissä
- ISO-arvot ovat merkkijonoja gPhoto2:ssa ("800", ei 800)

### Riippuvuudet (päivitä nykyisiin versioihin asennusvaiheessa)
- python-fasthtml (nykyisin 0.12.x)
- gphoto2 (python-gphoto2)
- Pillow
- numpy
- matplotlib
- pytest, ruff, mypy

---

## Post-MVP prospektilista

Mahdollisia jatkokehityskohteita MVP:n jälkeen:

- [ ] WiFi-yhteys kameraan (Nikon SnapBridge/WMU) — vaatii protokollan reverse-engineerausta, ei gPhoto2-tukea
- [ ] Live View -striimaustuki
- [ ] Usean kameran samanaikainen hallinta
- [ ] Focus stacking -automaatio
- [ ] Timelapse-ohjaus
- [ ] Tethered shooting -tila (automaattinen kuvien siirto koneelle)
- [ ] Preset-järjestelmä (tallenna/lataa kamera-asetukset)
