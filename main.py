import os
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import ttk, messagebox

import requests

from LibraryTracker_BB import (
    LibraryDatabase_BB,
    extract_bib_id_BB,
    fetch_availability_BB,
)

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")
CATALOGUE_URL = "https://fszekonline.fszek.hu/"
RECORD_LINK_TEMPLATE = "https://fszekonline.fszek.hu/record/-/record/{bib_id}"
EXAMPLE_URL = "https://fszekonline.fszek.hu/record/-/record/bibFSZ123456"
GUIDE_STEPS = (
    "1. Nyisd meg a katalógust:",
    "2. Keress rá a könyvre.",
    "3. Nyisd meg a könyv oldalát, és másold ki az URL-t a címsorból. "
    "Tartalmaznia kell egy bibFSZ azonosítót, például:\n" + EXAMPLE_URL,
    "4. Illeszd be az URL-t a fenti mezőbe, és kattints a „Könyv hozzáadása” gombra.",
    "5. Válassz ki egy könyvet, és kattints a „Kijelölt ellenőrzése” vagy az "
    "„Összes ellenőrzése” gombra. A könyvtáranként elérhető példányok az "
    "elérhetőség táblázatban jelennek meg.",
    "6. A „Közvetlen link” oszlopban a linkre kattintva megnyílik a könyv oldala.",
)
WARNING_TITLE = "Figyelmeztetés"
INFO_TITLE = "Információ"
READY_TEXT = "Kész"
NO_COPIES_TEXT = "Nincs elérhető példány"
NETWORK_ERROR_TEXT = "Hálózati hiba"
PARSE_ERROR_TEXT = "Feldolgozási hiba"
CHECK_DELAY_SECONDS = 0.5


class LibraryApp_BB:
    def __init__(self, master):
        self.master = master
        self.master.title("FSZEK Könyvtárkövető")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.database = LibraryDatabase_BB(DB_FILE)
        self.bib_var = tk.StringVar()
        self.status_var = tk.StringVar(value=READY_TEXT)
        self.action_buttons = []
        self.results = {}
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        container = ttk.Frame(self.master)
        container.pack(side="left", fill="both", expand=True)

        input_frame = ttk.Frame(container, padding=10)
        input_frame.pack(fill="x")
        ttk.Label(input_frame, text="Könyv URL-je:").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.bib_var, width=50).grid(
            row=0, column=1, padx=5, pady=2
        )
        add_button = ttk.Button(input_frame, text="Könyv hozzáadása", command=self.add_book)
        add_button.grid(row=0, column=2, padx=5)

        table_frame = ttk.Frame(container, padding=(10, 0))
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            table_frame,
            columns=("title", "author", "bib_id", "link"),
            show="headings",
            height=10,
        )
        self.tree.heading("title", text="Cím")
        self.tree.heading("author", text="Szerző")
        self.tree.heading("bib_id", text="bibId")
        self.tree.heading("link", text="Közvetlen link")
        self.tree.column("title", width=250)
        self.tree.column("author", width=160)
        self.tree.column("bib_id", width=110)
        self.tree.column("link", width=300)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Motion>", self.on_tree_motion)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        button_frame = ttk.Frame(container, padding=10)
        button_frame.pack(fill="x")
        check_selected_button = ttk.Button(
            button_frame, text="Kijelölt ellenőrzése", command=self.check_selected
        )
        check_all_button = ttk.Button(
            button_frame, text="Összes ellenőrzése", command=self.check_all
        )
        delete_button = ttk.Button(
            button_frame, text="Kijelölt törlése", command=self.delete_selected
        )
        for button in (check_selected_button, check_all_button, delete_button):
            button.pack(side="left", padx=5)
        self.action_buttons = [
            add_button,
            check_selected_button,
            check_all_button,
            delete_button,
        ]

        output_frame = ttk.LabelFrame(
            container, text="Elérhetőség (a kiválasztott könyv)", padding=10
        )
        output_frame.pack(fill="x", padx=10)
        self.output_tree = ttk.Treeview(
            output_frame,
            columns=("location", "available"),
            show="headings",
            height=7,
        )
        self.output_tree.heading("location", text="Könyvtár")
        self.output_tree.heading("available", text="Elérhető")
        self.output_tree.column("location", width=400)
        self.output_tree.column("available", width=150, anchor="center")
        self.output_tree.pack(fill="x")

        ttk.Label(container, textvariable=self.status_var, padding=10).pack(fill="x")

        self.create_guide()

    def create_guide(self):
        guide = ttk.LabelFrame(self.master, text="Útmutató", padding=10)
        guide.pack(side="right", fill="y", padx=10, pady=10)
        for step in GUIDE_STEPS[:1]:
            ttk.Label(guide, text=step, wraplength=280, justify="left").pack(
                anchor="w", pady=(0, 2)
            )
        link_font = tkfont.Font(self.master, font="TkDefaultFont")
        link_font.configure(underline=True)
        link = ttk.Label(
            guide, text=CATALOGUE_URL, foreground="blue", cursor="hand2", font=link_font
        )
        link.pack(anchor="w", pady=(0, 8))
        link.bind("<Button-1>", lambda event: webbrowser.open(CATALOGUE_URL))
        for step in GUIDE_STEPS[1:]:
            ttk.Label(guide, text=step, wraplength=280, justify="left").pack(
                anchor="w", pady=(0, 8)
            )

    def add_book(self):
        raw_id = self.bib_var.get().strip()
        if not raw_id:
            messagebox.showwarning(WARNING_TITLE, "Először illeszd be a könyv URL-jét.")
            return
        bib_id = extract_bib_id_BB(raw_id)
        if bib_id is None:
            messagebox.showwarning(
                WARNING_TITLE,
                "Az URL-nek tartalmaznia kell egy bibFSZ azonosítót, például:\n" + EXAMPLE_URL,
            )
            return
        if self.database.book_exists_BB(bib_id):
            messagebox.showwarning(WARNING_TITLE, "Ez a könyv már szerepel a listában.")
            return
        self.set_buttons_state("disabled")
        self.set_status("Rekord betöltése...")
        worker = threading.Thread(target=self.load_record, args=(bib_id,), daemon=True)
        worker.start()

    def load_record(self, bib_id):
        title, author, error = "", "", ""
        try:
            _counts, title, author = fetch_availability_BB(bib_id)
        except requests.exceptions.RequestException as exc:
            error = f"{NETWORK_ERROR_TEXT}: {exc}"
        except ValueError as exc:
            error = f"{PARSE_ERROR_TEXT}: {exc}"
        self.master.after(0, self.finish_add, bib_id, title, author, error)

    def finish_add(self, bib_id, title, author, error):
        self.set_buttons_state("normal")
        self.status_var.set(READY_TEXT)
        if not title:
            reason = error or "A válasz nem tartalmaz címet."
            messagebox.showwarning(
                WARNING_TITLE,
                "A könyv címét nem sikerült betölteni.\n\n" + reason,
            )
            return
        if not self.database.add_book_BB(title, bib_id, author):
            messagebox.showwarning(WARNING_TITLE, "Ez a könyv már szerepel a listában.")
            return
        self.bib_var.set("")
        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for book_id, title, bib_id, author in self.database.get_books_BB():
            self.tree.insert(
                "",
                "end",
                iid=str(book_id),
                values=(title, author, bib_id, RECORD_LINK_TEMPLATE.format(bib_id=bib_id)),
            )
        self.show_output(None)

    def get_selected_item(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(WARNING_TITLE, "Előbb válassz ki egy könyvet.")
            return None
        return selection[0]

    def check_selected(self):
        item_id = self.get_selected_item()
        if item_id is None:
            return
        self.start_checks([(item_id, self.tree.set(item_id, "bib_id"))])

    def check_all(self):
        items = [
            (item_id, self.tree.set(item_id, "bib_id"))
            for item_id in self.tree.get_children()
        ]
        if not items:
            messagebox.showinfo(INFO_TITLE, "A lista üres.")
            return
        self.start_checks(items)

    def start_checks(self, items):
        self.set_buttons_state("disabled")
        worker = threading.Thread(target=self.run_checks, args=(items,), daemon=True)
        worker.start()

    def run_checks(self, items):
        total = len(items)
        for index, (item_id, bib_id) in enumerate(items, start=1):
            self.master.after(0, self.set_status, f"Ellenőrzés {index}/{total}...")
            counts, error = self.check_book_availability(bib_id)
            self.master.after(0, self.set_row_result, item_id, counts, error)
            time.sleep(CHECK_DELAY_SECONDS)
        self.master.after(0, self.finish_checks)

    def check_book_availability(self, bib_id):
        try:
            counts, _title, _author = fetch_availability_BB(bib_id)
        except requests.exceptions.RequestException as exc:
            return [], f"{NETWORK_ERROR_TEXT}: {exc}"
        except ValueError as exc:
            return [], f"{PARSE_ERROR_TEXT}: {exc}"
        return counts, ""

    def set_status(self, text):
        self.status_var.set(text)

    def set_row_result(self, item_id, counts, error):
        if not self.tree.exists(item_id):
            return
        self.results[item_id] = (counts, error)
        if error:
            self.set_status(error)
        if self.get_current_item() == item_id:
            self.show_output(item_id)

    def finish_checks(self):
        self.set_buttons_state("normal")
        self.status_var.set(READY_TEXT)

    def set_buttons_state(self, state):
        for button in self.action_buttons:
            button.config(state=state)

    def get_current_item(self):
        selection = self.tree.selection()
        return selection[0] if selection else None

    def on_select(self, event):
        self.show_output(self.get_current_item())

    def show_output(self, item_id):
        self.output_tree.delete(*self.output_tree.get_children())
        if item_id is None or item_id not in self.results:
            return
        counts, error = self.results[item_id]
        if error:
            self.output_tree.insert("", "end", values=(error, ""))
            return
        if not counts:
            self.output_tree.insert("", "end", values=(NO_COPIES_TEXT, 0))
            return
        for location, count in counts:
            self.output_tree.insert("", "end", values=(location, count))

    def link_row_at(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell":
            return ""
        column_index = int(self.tree.identify_column(event.x)[1:]) - 1
        if self.tree["columns"][column_index] != "link":
            return ""
        return self.tree.identify_row(event.y)

    def on_tree_motion(self, event):
        cursor = "hand2" if self.link_row_at(event) else ""
        self.tree.configure(cursor=cursor)

    def on_tree_click(self, event):
        item_id = self.link_row_at(event)
        if item_id:
            webbrowser.open(self.tree.set(item_id, "link"))

    def delete_selected(self):
        item_id = self.get_selected_item()
        if item_id is None:
            return
        self.database.delete_book_BB(int(item_id))
        self.results.pop(item_id, None)
        self.refresh_list()

    def on_close(self):
        self.database.close_BB()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryApp_BB(root)
    root.mainloop()
