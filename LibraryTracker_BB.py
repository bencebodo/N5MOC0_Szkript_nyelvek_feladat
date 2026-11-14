import re
import sqlite3
from html import unescape

import requests

BASE_URL = "https://fszekonline.fszek.hu"
SEARCH_URL = BASE_URL + "/search"
AVAILABILITY_URL = (
    BASE_URL
    + "/record?p_p_id=BibCirc_WAR_circulationportlet&p_p_lifecycle=2&p_p_state=normal"
    + "&p_p_mode=view&p_p_resource_id=serveActualView&p_p_cacheability=cacheLevelPage"
    + "&p_p_col_id=column-opac-plugins&p_p_col_pos=2&p_p_col_count=6"
    + "&_BibCirc_WAR_circulationportlet_bibId={bib_id}"
    + "&_BibCirc_WAR_circulationportlet_status=active"
    + "&_BibCirc_WAR_circulationportlet_recordSourceCode=sclib"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT_SECONDS = 15
BRANCH_KEYWORDS = ("könyvtár", "fiók", "kerület")
MAX_BRANCH_LENGTH = 120


class LibraryDatabase_BB:
    def __init__(self, path="books.db"):
        self.connection = sqlite3.connect(path)
        self.create_table_BB()

    def create_table_BB(self):
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS books (id INTEGER PRIMARY KEY, title TEXT, bibId TEXT)"
        )
        self.connection.commit()

    def book_exists_BB(self, bib_id):
        cursor = self.connection.execute(
            "SELECT 1 FROM books WHERE bibId = ?", (bib_id,)
        )
        return cursor.fetchone() is not None

    def add_book_BB(self, title, bib_id):
        if self.book_exists_BB(bib_id):
            return False
        self.connection.execute(
            "INSERT INTO books (title, bibId) VALUES (?, ?)", (title, bib_id)
        )
        self.connection.commit()
        return True

    def get_books_BB(self):
        cursor = self.connection.execute(
            "SELECT id, title, bibId FROM books ORDER BY id"
        )
        return cursor.fetchall()

    def delete_book_BB(self, book_id):
        self.connection.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self.connection.commit()

    def close_BB(self):
        self.connection.close()


def extract_bib_id_BB(text):
    match = re.search(r"(\d+)\s*/?\s*$", text.strip())
    if match is None:
        return None
    return match.group(1)


def is_branch_line_BB(line):
    lowered = line.lower()
    if len(line) > MAX_BRANCH_LENGTH:
        return False
    return any(keyword in lowered for keyword in BRANCH_KEYWORDS)


def parse_branches_BB(html):
    text = re.sub(r"<[^>]+>", "\n", html)
    branches = []
    for raw_line in text.split("\n"):
        line = unescape(raw_line).strip()
        if line and is_branch_line_BB(line) and line not in branches:
            branches.append(line)
    return branches


def fetch_availability_BB(bib_id):
    with requests.Session() as session:
        session.headers.update({"User-Agent": USER_AGENT})

        warmup_response = session.get(
            f"{BASE_URL}/record/-/record/{bib_id}", timeout=TIMEOUT_SECONDS
        )
        warmup_response.raise_for_status()

        response = session.get(
            AVAILABILITY_URL.format(bib_id=bib_id),
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": SEARCH_URL,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return parse_branches_BB(response.text)
