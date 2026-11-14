import json
import re
import sqlite3
import time
from html import unescape

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
TRAILING_DIGITS_PATTERN = re.compile(r"(\d+)\s*/?\s*$")
ITEMS_PATTERN = re.compile(r'circTable\.data\("itemsJson",\s*(\[.*?\])\);', re.DOTALL)
TITLE_META_PATTERN = re.compile(
    r'<meta\s+name="citation_title"\s+content="([^"]*)"', re.IGNORECASE
)
AUTHOR_META_PATTERN = re.compile(
    r'<meta\s+name="citation_author"\s+content="([^"]*)"', re.IGNORECASE
)
LIBRARY_ORDER = (
    "1117 Karinthy út 11.",
    "KK",
    "1093 Boráros tér 2.",
    "1066 Teréz krt. 2-4.",
    "1054 Vadász u. 42.",
    "1221 Kossuth u. 30.",
    "1126 Ugocsa u. 10.",
)


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
    if match is not None:
        return match.group(0)
    match = TRAILING_DIGITS_PATTERN.search(stripped)
    if match is None:
        return None
    return match.group(1)


def normalize_location_BB(location):
    if re.match(r"KK\s", location):
        return "KK"
    for library in LIBRARY_ORDER:
        if library != "KK" and library in location:
            return library
    return None


def count_available_BB(items):
    counts = {}
    for item in items:
        if item.get("available") is True:
            library = normalize_location_BB(str(item.get("currentLocation", "")))
            if library is not None:
                counts[library] = counts.get(library, 0) + 1
    return counts


def parse_branches_BB(html):
    match = ITEMS_PATTERN.search(html)
    if match is None:
        return []
    items = json.loads(match.group(1))
    counts = count_available_BB(items)
    return [
        f"{library}: {counts[library]} db"
        for library in LIBRARY_ORDER
        if library in counts
    ]


def parse_record_info_BB(html):
    title_match = TITLE_META_PATTERN.search(html)
    title = unescape(title_match.group(1)).strip() if title_match else ""
    authors = [unescape(author).strip() for author in AUTHOR_META_PATTERN.findall(html)]
    return title, ", ".join(author for author in authors if author)


def fetch_record_info_BB(bib_id):
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})
        response = session.get(
            MANIFESTATION_URL.format(bib_id=bib_id), timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return parse_record_info_BB(response.text)


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
        return parse_branches_BB(response.text)
