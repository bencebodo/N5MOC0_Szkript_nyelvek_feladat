# FSZEK Library Tracker

**Hallgató neve:** Bodó Bence (BB)

## A feladat rövid leírása

Az alkalmazás asztali program, amellyel a FSZEK könyvtári katalógusban kiválasztott könyvek elérhetőségét lehet nyomon követni. A felhasználó megadja a könyv címét és a katalógusazonosítót (bibId) vagy a katalógus teljes URL-jét, a program ezeket SQLite adatbázisban tárolja. Az elérhetőség ellenőrzése a FSZEK online katalógusának lekérdezésével történik, az eredmény könyvtáranként megmutatja, hány példány elérhető. A lekérdezés háttérszálon fut, így a felület nem fagy le.

## Modulok

- `tkinter` (tanult): grafikus felület, `ttk` widgetek és `messagebox` párbeszédablakok
- `sqlite3` (tanult): adatbázis-kezelés
- `re` (tanult): reguláris kifejezések az azonosító kinyeréséhez és a katalógusválasz feldolgozásához
- `json` (tanult): a katalógusválaszban lévő példánylista beolvasása
- `threading` (tanult): háttérszál a hálózati lekérdezésekhez
- `time` (tanult): rövid várakozás a lekérdezések között
- `requests` (bemutatott): HTTP-kérések a FSZEK katalógusához
- `LibraryTracker_BB` (saját modul): az alkalmazás logikája, GUI-kód nélkül

## Függvények és osztályok

### Saját osztályok

- `LibraryDatabase_BB`
  - `__init__(path)`: megnyitja az adatbázist és létrehozza a táblát
  - `create_table_BB()`: létrehozza a `books` táblát, ha még nem létezik
  - `book_exists_BB(bib_id)`: ellenőrzi, hogy a katalógusazonosító már szerepel-e
  - `add_book_BB(title, bib_id, author)`: új könyvet ment, duplikáció esetén `False`-t ad vissza
  - `get_books_BB()`: visszaadja az összes könyvet `(id, title, bibId, author)` rekordokként
  - `delete_book_BB(book_id)`: törli a megadott könyvet
  - `close_BB()`: lezárja az adatbázis-kapcsolatot
- `LibraryApp_BB`: felépíti a grafikus felületet és kezeli az eseményeket (gombok, kijelölés, dupla kattintás, ablak bezárása)

### Saját függvények

- `extract_bib_id_BB(text)`: a `bibFSZ` azonosítót keresi, ennek hiányában a végén álló számjegyeket veszi ki
- `fetch_record_info_BB(bib_id)`: lekéri a rekord címét és szerzőjét
- `parse_record_info_BB(html)`: a rekord HTML-jéből kiolvassa a címet és a szerzőt
- `fetch_availability_BB(bib_id)`: a FSZEK katalógusától lekéri az elérhetőséget (három kérésben)
- `parse_branches_BB(html)`: a válaszban lévő példánylistából könyvtáranként megszámolja az elérhető példányokat
- `count_available_BB(items)`: az elérhető példányokat könyvtáranként összesíti
- `normalize_location_BB(location)`: a példány helyét a listában szereplő könyvtár nevére alakítja
- `add_session_cookies_BB(session)`: a katalógus által elvárt munkamenet-sütiket állítja be

### A requests függvényei

- `requests.Session()`: munkamenet, amely a cookie-kat automatikusan kezeli
- `session.headers.update(...)`: böngészőszerű User-Agent beállítása
- `session.get(...)`: GET-kérés a munkameneten belül
- `session.post(...)`: POST-kérések (JSON és űrlap-adat) a munkameneten belül
- `session.cookies.set(...)`: sütik beállítása
- `response.raise_for_status()`: HTTP-hibák jelzése
- `requests.exceptions.RequestException`: hálózati hibák kezelése

## Futtatás

1. Telepítsd a függőségeket: `pip install -r requirements.txt`
2. Indítsd el a programot: `python main.py`

Az adatbázis (`books.db`) a program mellett jön létre.
