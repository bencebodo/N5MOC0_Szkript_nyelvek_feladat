import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import requests

from LibraryTracker_BB import (
    LibraryDatabase_BB,
    extract_bib_id_BB,
    fetch_availability_BB,
)

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.db")
NO_COPIES_TEXT = "No available copies found / nincs elérhető példány"
NETWORK_ERROR_TEXT = "Network error / hálózati hiba"
CHECK_DELAY_SECONDS = 0.5


class LibraryApp_BB:
    def __init__(self, master):
        self.master = master
        self.master.title("FSZEK Library Tracker")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.database = LibraryDatabase_BB(DB_FILE)
        self.title_var = tk.StringVar()
        self.bib_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready / Kész")
        self.action_buttons = []
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        input_frame = ttk.Frame(self.master, padding=10)
        input_frame.pack(fill="x")
        ttk.Label(input_frame, text="Title / Cím:").grid(row=0, column=0, sticky="w")
        ttk.Entry(input_frame, textvariable=self.title_var, width=40).grid(
            row=0, column=1, padx=5, pady=2
        )
        ttk.Label(input_frame, text="bibId or URL / azonosító vagy URL:").grid(
            row=1, column=0, sticky="w"
        )
        ttk.Entry(input_frame, textvariable=self.bib_var, width=40).grid(
            row=1, column=1, padx=5, pady=2
        )
        add_button = ttk.Button(input_frame, text="Add Book", command=self.add_book)
        add_button.grid(row=0, column=2, rowspan=2, padx=5)

        table_frame = ttk.Frame(self.master, padding=(10, 0))
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            table_frame,
            columns=("title", "bib_id", "available"),
            show="headings",
            height=12,
        )
        self.tree.heading("title", text="Title")
        self.tree.heading("bib_id", text="bibId")
        self.tree.heading("available", text="Available at")
        self.tree.column("title", width=250)
        self.tree.column("bib_id", width=90)
        self.tree.column("available", width=350)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.show_branches)

        button_frame = ttk.Frame(self.master, padding=10)
        button_frame.pack(fill="x")
        check_selected_button = ttk.Button(
            button_frame, text="Check Selected", command=self.check_selected
        )
        check_all_button = ttk.Button(
            button_frame, text="Check All", command=self.check_all
        )
        delete_button = ttk.Button(
            button_frame, text="Delete Selected", command=self.delete_selected
        )
        for button in (check_selected_button, check_all_button, delete_button):
            button.pack(side="left", padx=5)
        self.action_buttons = [
            add_button,
            check_selected_button,
            check_all_button,
            delete_button,
        ]

        ttk.Label(self.master, textvariable=self.status_var, padding=10).pack(fill="x")

    def add_book(self):
        title = self.title_var.get().strip()
        raw_id = self.bib_var.get().strip()
        if not title or not raw_id:
            messagebox.showwarning(
                "Warning / Figyelem", "Fill in both fields. / Töltsd ki mindkét mezőt!"
            )
            return
        bib_id = extract_bib_id_BB(raw_id)
        if bib_id is None:
            messagebox.showwarning(
                "Warning / Figyelem", "Invalid bibId or URL. / Érvénytelen azonosító vagy URL!"
            )
            return
        if not self.database.add_book_BB(title, bib_id):
            messagebox.showwarning(
                "Warning / Figyelem", "This book is already listed. / Ez a könyv már szerepel!"
            )
            return
        self.title_var.set("")
        self.bib_var.set("")
        self.refresh_list()

    def refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for book_id, title, bib_id in self.database.get_books_BB():
            self.tree.insert("", "end", iid=str(book_id), values=(title, bib_id, ""))

    def get_selected_item(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning(
                "Warning / Figyelem", "Select a book first. / Válassz ki egy könyvet!"
            )
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
            messagebox.showinfo("Info", "The list is empty. / A lista üres.")
            return
        self.start_checks(items)

    def start_checks(self, items):
        self.set_buttons_state("disabled")
        worker = threading.Thread(target=self.run_checks, args=(items,), daemon=True)
        worker.start()

    def run_checks(self, items):
        total = len(items)
        for index, (item_id, bib_id) in enumerate(items, start=1):
            self.master.after(
                0, self.set_status, f"Checking {index}/{total}... / Ellenőrzés {index}/{total}..."
            )
            result_text = self.check_book_availability(bib_id)
            self.master.after(0, self.set_row_text, item_id, result_text)
            time.sleep(CHECK_DELAY_SECONDS)
        self.master.after(0, self.finish_checks)

    def check_book_availability(self, bib_id):
        try:
            branches = fetch_availability_BB(bib_id)
        except requests.exceptions.RequestException:
            return NETWORK_ERROR_TEXT
        if not branches:
            return NO_COPIES_TEXT
        return ", ".join(branches)

    def set_status(self, text):
        self.status_var.set(text)

    def set_row_text(self, item_id, text):
        if self.tree.exists(item_id):
            self.tree.set(item_id, "available", text)

    def finish_checks(self):
        self.set_buttons_state("normal")
        self.status_var.set("Done / Kész")

    def set_buttons_state(self, state):
        for button in self.action_buttons:
            button.config(state=state)

    def show_branches(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        title = self.tree.set(item_id, "title")
        available = self.tree.set(item_id, "available")
        messagebox.showinfo(title, available or "Not checked yet / Még nincs ellenőrizve")

    def delete_selected(self):
        item_id = self.get_selected_item()
        if item_id is None:
            return
        self.database.delete_book_BB(int(item_id))
        self.refresh_list()

    def on_close(self):
        self.database.close_BB()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryApp_BB(root)
    root.mainloop()
