import json
import re
import sqlite3
import time

import requests

BASE_URL = "https://fszekonline.fszek.hu"
SEARCH_URL = BASE_URL + "/search"
LOGIN_INFO_URL = (
    BASE_URL
    + "/circulation-proxy/rest/circulation/login-information-text?tenant_id=fszek"
)
AVAILABILITY_URL = (
    BASE_URL
    + "/record?p_p_id=BibCirc_WAR_circulationportlet&p_p_lifecycle=2&p_p_state=normal"
    + "&p_p_mode=view&p_p_resource_id=serveActualView&p_p_cacheability=cacheLevelPage"
    + "&p_p_col_id=column-opac-plugins&p_p_col_pos=2&p_p_col_count=6"
    + "&_BibCirc_WAR_circulationportlet_bibId={bib_id}"
    + "&_BibCirc_WAR_circulationportlet_status=active"
    + "&_BibCirc_WAR_circulationportlet_recordSourceCode=sclib"
)
MANIFESTATION_URL = (
    BASE_URL
    + "/record/-/record/display/manifestation/{bib_id}"
    + "/3a364be5-1b88-43fe-920c-11b3656bcdaf/solr/0/24/0/501/score/DESC"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT_SECONDS = 15
SESSION_LIFETIME_MS = 1800000
BIB_FSZ_PATTERN = re.compile(r"bibFSZ\d+")
ITEMS_PATTERN = re.compile(r'circTable\.data\("itemsJson",\s*(\[.*?\])\);', re.DOTALL)


class LibraryDatabase_BB:
    def __init__(self, path="books.db"):
        self.connection = sqlite3.connect(path)
        self.create_table_BB()

    def create_table_BB(self):
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY, title TEXT, bibId TEXT)"
        )
        columns = [row[1] for row in self.connection.execute("PRAGMA table_info(books)")]
        if "author" not in columns:
            self.connection.execute("ALTER TABLE books ADD COLUMN author TEXT")
        self.connection.commit()

    def book_exists_BB(self, bib_id):
        cursor = self.connection.execute(
            "SELECT 1 FROM books WHERE bibId = ?", (bib_id,)
        )
        return cursor.fetchone() is not None

    def add_book_BB(self, title, bib_id, author=""):
        if self.book_exists_BB(bib_id):
            return False
        self.connection.execute(
            "INSERT INTO books (title, bibId, author) VALUES (?, ?, ?)",
            (title, bib_id, author),
        )
        self.connection.commit()
        return True

    def get_books_BB(self):
        cursor = self.connection.execute(
            "SELECT id, title, bibId, COALESCE(author, '') FROM books ORDER BY id"
        )
        return cursor.fetchall()

    def delete_book_BB(self, book_id):
        self.connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.connection.commit()

    def close_BB(self):
        self.connection.close()


def extract_bib_id_BB(text):
    stripped = text.strip()
    match = BIB_FSZ_PATTERN.search(stripped)
    if match is None:
        return None
    return match.group(0)


def parse_items_BB(html):
    match = ITEMS_PATTERN.search(html)
    if match is None:
        return []
    return json.loads(match.group(1))


def count_available_BB(items):
    counts = {}
    for item in items:
        location = str(item.get("currentLocation", "")).strip()
        if not location:
            continue
        available = 1 if item.get("available") is True else 0
        counts[location] = counts.get(location, 0) + available
    return counts


def library_counts_BB(items):
    return list(count_available_BB(items).items())


def parse_title_author_BB(items):
    if not items:
        return "", ""
    first = items[0]
    title = str(first.get("title") or "").strip()
    author = str(first.get("author") or first.get("authors") or "").strip()
    return title, author


def add_session_cookies_BB(session):
    now_ms = int(time.time() * 1000)
    extra_cookies = {
        "redirectPosition": "",
        "loggedInUser": "null",
        "i18next": "hu-HU",
        "LFR_SESSION_STATE_10158": str(now_ms),
        "sessionExpiry": str(now_ms + SESSION_LIFETIME_MS),
    }
    for name, value in extra_cookies.items():
        session.cookies.set(name, value, domain="fszekonline.fszek.hu")


def fetch_availability_BB(bib_id):
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        warmup_response = session.get(
            f"{BASE_URL}/record/-/record/{bib_id}", timeout=TIMEOUT_SECONDS
        )
        warmup_response.raise_for_status()

        login_response = session.post(
            LOGIN_INFO_URL,
            json={"institutionId": "1", "language": "hu-HU"},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": SEARCH_URL,
            },
            timeout=TIMEOUT_SECONDS,
        )
        login_response.raise_for_status()

        add_session_cookies_BB(session)
        response = session.post(
            AVAILABILITY_URL.format(bib_id=bib_id),
            data={"bibId": bib_id, "titleId": bib_id},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "text/html, */*; q=0.01",
                "Origin": BASE_URL,
                "Referer": MANIFESTATION_URL.format(bib_id=bib_id),
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = parse_items_BB(response.text)

    title, author = parse_title_author_BB(items)
    return library_counts_BB(items), title, author
