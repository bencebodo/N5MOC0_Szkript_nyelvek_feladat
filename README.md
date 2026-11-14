# FSZEK Library Tracker

**Hallgató neve:** Bodó Bence (BB)

## A feladat rövid leírása

Az alkalmazás asztali program, amellyel a FSZEK könyvtári katalógusban kiválasztott könyvek elérhetőségét lehet nyomon követni. A felhasználó beilleszti a könyv katalógusbeli URL-jét (benne a `bibFSZ…` azonosítóval), a program pedig a címet és a szerzőt lekéri, majd a könyvet SQLite adatbázisban tárolja. Az elérhetőség ellenőrzése a FSZEK online katalógusának lekérdezésével történik, az eredmény könyvtáranként megmutatja, hány példány elérhető. A lekérdezés háttérszálon fut, így a felület nem fagy le.

## Modulok

- `tkinter` (tanult): grafikus felület, `ttk` widgetek és `messagebox` párbeszédablakok
- `sqlite3` (tanult): adatbázis-kezelés
- `re` (tanult): reguláris kifejezések az azonosító kinyeréséhez és a katalógusválasz feldolgozásához
- `json` (tanult): a katalógusválaszban lévő példánylista beolvasása
- `threading` (tanult): háttérszál a hálózati lekérdezésekhez
- `time` (tanult): rövid várakozás a lekérdezések között
- `os` (tanult): az adatbázisfájl útvonalának meghatározása
- `webbrowser` (tanult): a rekord közvetlen linkjének megnyitása böngészőben
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
- `LibraryApp_BB`: felépíti a grafikus felületet (az útmutató panellel együtt) és kezeli az eseményeket (gombok, kijelölés, a közvetlen link kattintása, ablak bezárása)

### Saját függvények

- `extract_bib_id_BB(text)`: a `bibFSZ…` katalógusazonosítót keresi a szövegben vagy az URL-ben, ha nincs ilyen, `None`-t ad vissza
- `parse_items_BB(html)`: a válaszban lévő példánylistát (JSON) olvassa ki
- `library_counts_BB(items)`: könyvtáranként megadja az elérhető példányok számát
- `parse_title_author_BB(items)`: a példányadatokból kiolvassa a címet és a szerzőt
- `fetch_availability_BB(bib_id)`: a FSZEK katalógusától lekéri az elérhetőséget, a címet és a szerzőt (három kérésben)
- `count_available_BB(items)`: az elérhető példányokat könyvtáranként összesíti
- `add_session_cookies_BB(session)`: a katalógus által elvárt munkamenet-sütiket állítja be

### A tanult modulok függvényei

- `tkinter`
  - `tk.Tk()`: az alapablak (`root`) létrehozása
  - `tk.StringVar()`: beviteli mezőhöz és állapotsorhoz kötött szöveg
  - `ttk.Frame`, `ttk.LabelFrame`, `ttk.Label`, `ttk.Entry`, `ttk.Button`, `ttk.Scrollbar`: felületelemek
  - `ttk.Treeview` (`insert`, `delete`, `set`, `selection`, `identify_row`, `identify_column`, `identify_region`, `bind`): táblázatok és eseménykezelés
  - `tkinter.font.Font(...)`: aláhúzott link betűtípusa
  - `messagebox.showwarning(...)`, `messagebox.showinfo(...)`: párbeszédablakok
  - `root.after(...)`, `root.mainloop()`, `root.protocol(...)`, `root.destroy()`: ablak- és eseménykezelés
- `sqlite3`
  - `sqlite3.connect(...)`: kapcsolat megnyitása
  - `connection.execute(...)`, `connection.commit()`, `connection.close()`: lekérdezések, mentés, lezárás
  - `cursor.fetchone()`, `cursor.fetchall()`: eredmények olvasása
- `re`
  - `re.compile(...)`: reguláris kifejezések előfordítása
  - `pattern.search(...)`: az azonosító és a példánylista keresése
- `json`
  - `json.loads(...)`: a példánylista beolvasása szövegből
- `threading`
  - `threading.Thread(...)`, `thread.start()`: háttérszál a hálózati kérésekhez
- `time`
  - `time.time()`: aktuális idő a munkamenet-sütikhez
  - `time.sleep(...)`: várakozás a lekérdezések között
- `os`
  - `os.path.join(...)`, `os.path.dirname(...)`, `os.path.abspath(...)`: az adatbázisfájl útvonala
- `webbrowser`
  - `webbrowser.open(...)`: link megnyitása a böngészőben

### A requests függvényei

- `requests.Session()`: munkamenet, amely a cookie-kat automatikusan kezeli
- `session.headers.update(...)`: böngészőszerű User-Agent beállítása
- `session.get(...)`: GET-kérés a munkameneten belül
- `session.post(...)`: POST-kérések (JSON és űrlap-adat) a munkameneten belül
- `session.cookies.set(...)`: sütik beállítása
- `response.raise_for_status()`: HTTP-hibák jelzése
- `requests.exceptions.RequestException`: hálózati hibák kezelése (a `main.py`-ban is importálva)

## Futtatás

1. Telepítsd a függőségeket: `pip install -r requirements.txt`
2. Indítsd el a programot: `python main.py`

Az adatbázis (`books.db`) a program mellett jön létre.
