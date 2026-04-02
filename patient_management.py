#!/usr/bin/env python3
"""
careflow_patients.py

CareFlow Patient Management page — structured and styled to match
careflow_records.py exactly (same sidebar, header, treeview, action bar).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from typing import Optional

# ==============================
# Config / Styles  (shared with dashboard)
# ==============================
BG_LIGHT         = "#e6f2ec"
BG_SIDEBAR       = "#5FAF90"
BG_SIDEBAR_LIGHT = "#A2DDC6"
BG_PANEL         = "#ffffff"
ACCENT           = "#308684"
CARD_BG          = "#f7fff7"
TEXT             = "#0b3d2e"
BTN_DANGER       = "#c0392b"
BTN_SAFE         = "#308684"
BTN_INFO         = "#2980b9"
BTN_WARN         = "#f39c12"
BTN_NEUTRAL      = "#95a5a6"

SIDEBAR_WIDTH = 160
FONT_TITLE    = ("Helvetica", 18, "bold")
FONT_HEADER   = ("Helvetica", 13, "bold")
FONT_TABLE    = ("Helvetica", 10)
FONT_NAV      = ("Helvetica", 10)
FONT_LOGO     = ("Helvetica", 13, "bold")

DB_NAME = "healthcare.db"

# ==============================
# DB helpers
# ==============================
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_patient_table() -> None:
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Patient (
            patient_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name        TEXT NOT NULL,
            last_name         TEXT NOT NULL,
            dob               TEXT,
            sex               TEXT,
            phone             TEXT,
            email             TEXT,
            address           TEXT,
            allergies         TEXT,
            conditions        TEXT,
            medications       TEXT,
            notes             TEXT,
            emergency_contact TEXT,
            active_flag       INTEGER DEFAULT 1,
            created_at        TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


# ==============================
# Nav helper
# ==============================
def on_nav(name: str):
    print(f"[NAV] {name} clicked")


# ==============================
# Main Window
# ==============================
class CareFlowPatients(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow Admin Portal – Patients")
        self.geometry("1200x720")
        self.configure(bg=BG_LIGHT)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ensure_patient_table()

        self._selected_id: Optional[int] = None

        self._build_sidebar()
        self._build_header()
        self._build_content()
        self._load_patients()

    # ------------------------------------------------------------------
    # Sidebar  (identical to records page)
    # ------------------------------------------------------------------
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH, relief="flat")
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        sidebar.grid_propagate(False)

        logo_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        logo_frame.pack(fill="x", padx=12, pady=(14, 8))
        tk.Label(logo_frame, text="CareFlow", bg=BG_SIDEBAR,
                 fg=TEXT, font=FONT_LOGO).pack(anchor="w")

        nav_items = [
            ("Dashboard", lambda: on_nav("Dashboard")),
            ("Patient",   lambda: on_nav("Patient")),   # active page
            ("Staff",     lambda: on_nav("Staff")),
            ("Clinic",    lambda: on_nav("Clinic")),
            ("Records",   lambda: on_nav("Records")),
            ("Billing",   lambda: on_nav("Billing")),
        ]

        for label, cmd in nav_items:
            is_active = label == "Patient"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR
            tk.Button(
                sidebar, text=label, anchor="w", command=cmd,
                relief="flat", bg=bg, fg=TEXT,
                font=FONT_NAV, padx=14, pady=6,
                activebackground=ACCENT, activeforeground="white",
            ).pack(fill="x", pady=2, padx=8)

    # ------------------------------------------------------------------
    # Header  (identical to records page)
    # ------------------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=BG_PANEL, height=90, relief="flat")
        header.grid(row=0, column=1, sticky="new", padx=(12, 12), pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        left = tk.Frame(header, bg=BG_PANEL)
        left.grid(row=0, column=0, sticky="w", padx=14, pady=14)
        tk.Label(left, text="Patient Management", bg=BG_PANEL,
                 fg=TEXT, font=FONT_TITLE).pack(anchor="w")

        right = tk.Frame(header, bg=BG_PANEL)
        right.grid(row=0, column=1, sticky="e", padx=14, pady=14)
        tk.Label(right, text="Signed in as\nAdministrators Name",
                 bg=BG_PANEL, fg=TEXT, justify="right").pack(anchor="e")
        tk.Button(right, text="♡", bg=BG_SIDEBAR, fg=TEXT, width=3,
                  relief="flat", command=lambda: on_nav("Profile")).pack(anchor="e", pady=(4, 0))

    # ------------------------------------------------------------------
    # Main content area
    # ------------------------------------------------------------------
    def _build_content(self):
        # Two-column layout: table on the left, form panel on the right
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.grid(row=1, column=1, sticky="nsew", padx=(12, 12), pady=(8, 12))
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._build_table_panel(outer)
        self._build_form_panel(outer)
        self._build_action_bar(outer)

    # ------------------------------------------------------------------
    # Left: table panel  (mirrors records table structure)
    # ------------------------------------------------------------------
    def _build_table_panel(self, parent):
        # Search / filter bar
        filter_bar = tk.Frame(parent, bg=BG_PANEL, relief="flat", bd=0)
        filter_bar.grid(row=0, column=0, sticky="new", pady=(0, 8))
        filter_bar.grid_columnconfigure(1, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TEntry", fieldbackground=CARD_BG, foreground=TEXT)

        tk.Label(filter_bar, text="Search:", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=(14, 6), pady=8)

        self.search_var = tk.StringVar()
        se = ttk.Entry(filter_bar, textvariable=self.search_var, width=40)
        se.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=8)
        se.bind("<KeyRelease>", lambda e: self._load_patients())

        tk.Button(
            filter_bar, text="Show All", bg=BG_SIDEBAR, fg=TEXT,
            relief="flat", padx=10, pady=3,
            activebackground=BG_SIDEBAR_LIGHT, activeforeground=TEXT,
            command=self._load_patients
        ).grid(row=0, column=2, padx=(0, 6), pady=8)

        self.show_inactive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            filter_bar, text="Show inactive", variable=self.show_inactive_var,
            bg=BG_PANEL, fg=TEXT, activebackground=BG_PANEL,
            selectcolor=CARD_BG, command=self._load_patients
        ).grid(row=0, column=3, padx=(0, 14), pady=8)

        # Table container — same card style as records
        container = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid")
        container.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        lbl_frame = tk.Frame(container, bg=BG_PANEL)
        lbl_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 0))
        tk.Label(lbl_frame, text="Patients", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).pack(anchor="w")

        # Treeview — same style as records
        style.configure("CareFlow.Treeview",
                        background=CARD_BG, fieldbackground=CARD_BG,
                        foreground=TEXT, rowheight=28, font=FONT_TABLE)
        style.configure("CareFlow.Treeview.Heading",
                        background=BG_SIDEBAR_LIGHT, foreground=TEXT,
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("CareFlow.Treeview",
                  background=[("selected", BG_SIDEBAR)],
                  foreground=[("selected", TEXT)])

        tree_frame = tk.Frame(container, bg=BG_PANEL)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        cols = ("id", "name", "dob", "phone", "email", "status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="CareFlow.Treeview")

        headings = {
            "id":     ("ID",     55,  "center"),
            "name":   ("Name",   200, "w"),
            "dob":    ("DOB",    100, "center"),
            "phone":  ("Phone",  120, "center"),
            "email":  ("Email",  200, "w"),
            "status": ("Status", 75,  "center"),
        }
        for col, (text, width, anchor) in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("inactive", foreground="#95a5a6")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # ------------------------------------------------------------------
    # Right: form panel  (same card style as filter/table panels)
    # ------------------------------------------------------------------
    def _build_form_panel(self, parent):
        panel = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid", padx=16, pady=14)
        panel.grid(row=0, column=1, rowspan=2, sticky="nsew",
                   padx=(10, 0), pady=(0, 8))
        parent.grid_columnconfigure(1, minsize=280)

        tk.Label(panel, text="Patient Details", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self.entries: dict = {}
        fields = [
            ("First Name *",       "first_name"),
            ("Last Name *",        "last_name"),
            ("Date of Birth",      "dob"),
            ("Sex",                "sex"),
            ("Phone",              "phone"),
            ("Email",              "email"),
            ("Address",            "address"),
            ("Allergies",          "allergies"),
            ("Conditions",         "conditions"),
            ("Medications",        "medications"),
            ("Notes",              "notes"),
            ("Emergency Contact",  "emergency_contact"),
        ]

        style = ttk.Style()
        style.configure("TEntry", fieldbackground=CARD_BG, foreground=TEXT)

        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(panel, text=label, bg=BG_PANEL, fg=TEXT,
                     font=("Helvetica", 9)).grid(
                row=i, column=0, sticky="w", pady=3)
            e = tk.Entry(panel, width=24, bg=CARD_BG, fg=TEXT,
                         relief="flat", highlightthickness=1,
                         highlightbackground="#cde8dc",
                         highlightcolor=ACCENT)
            e.grid(row=i, column=1, pady=3, padx=(8, 0), sticky="ew")
            self.entries[key] = e

        panel.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Action bar  (mirrors records action bar layout)
    # ------------------------------------------------------------------
    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=BG_LIGHT)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        btn_cfg = dict(
            relief="flat", fg="white", padx=16, pady=8,
            font=("Helvetica", 10, "bold"),
            activeforeground="white", cursor="hand2"
        )

        tk.Button(bar, text="＋  Add",        bg=BTN_SAFE,    activebackground=TEXT,
                  command=self._add_patient,           **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="✎  Update",      bg=BTN_INFO,    activebackground="#1a5276",
                  command=self._update_patient,         **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="⏸  Deactivate",  bg=BTN_WARN,    activebackground="#9a7d0a",
                  command=self._deactivate_patient,     **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="✕  Delete",      bg=BTN_DANGER,  activebackground="#922b21",
                  command=self._delete_patient,         **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="Clear",           bg=BTN_NEUTRAL, activebackground="#6c7a7d",
                  command=self._clear_form,             **btn_cfg).pack(side="left")

        tk.Label(bar,
                 text="★ = required fields   |   Inactive patients are shown in grey.",
                 bg=BG_LIGHT, fg="#5a8a76", font=("Helvetica", 9)).pack(side="right")

    # ------------------------------------------------------------------
    # Data methods
    # ------------------------------------------------------------------
    def _load_patients(self, event=None):
        search = self.search_var.get().strip().lower()
        show_inactive = self.show_inactive_var.get()

        conn = get_conn()
        rows = conn.execute("""
            SELECT patient_id, first_name, last_name, dob, phone, email, active_flag
            FROM Patient
            ORDER BY last_name, first_name
        """).fetchall()
        conn.close()

        self.tree.delete(*self.tree.get_children())

        for pid, fn, ln, dob, phone, email, active in rows:
            if not show_inactive and active == 0:
                continue
            name = f"{ln}, {fn}"
            if search and search not in name.lower() \
                    and search not in (phone or "").lower() \
                    and search not in (email or "").lower():
                continue
            status = "Active" if active else "Inactive"
            tag    = "inactive" if not active else ""
            self.tree.insert("", "end", iid=str(pid),
                             values=(pid, name, dob or "", phone or "",
                                     email or "", status),
                             tags=(tag,))

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_id = int(sel[0])

        conn = get_conn()
        row = conn.execute("""
            SELECT first_name, last_name, dob, sex, phone, email, address,
                   allergies, conditions, medications, notes, emergency_contact
            FROM Patient WHERE patient_id = ?
        """, (self._selected_id,)).fetchone()
        conn.close()

        if row:
            for i, key in enumerate(self.entries):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[i] if row[i] else "")

    def _collect(self) -> dict:
        return {k: e.get().strip() for k, e in self.entries.items()}

    def _add_patient(self):
        data = self._collect()
        if not data["first_name"] or not data["last_name"]:
            messagebox.showwarning("Required", "First Name and Last Name are required.")
            return
        try:
            conn = get_conn()
            conn.execute("""
                INSERT INTO Patient (
                    first_name, last_name, dob, sex, phone, email,
                    address, allergies, conditions, medications, notes, emergency_contact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(data.values()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Patient added successfully.")
            self._load_patients()
            self._clear_form()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def _update_patient(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Please select a patient first.")
            return
        data = self._collect()
        if not data["first_name"] or not data["last_name"]:
            messagebox.showwarning("Required", "First Name and Last Name are required.")
            return
        try:
            conn = get_conn()
            conn.execute("""
                UPDATE Patient SET
                    first_name=?, last_name=?, dob=?, sex=?, phone=?, email=?,
                    address=?, allergies=?, conditions=?, medications=?,
                    notes=?, emergency_contact=?
                WHERE patient_id=?
            """, (*data.values(), self._selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Updated", "Patient updated successfully.")
            self._load_patients()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def _deactivate_patient(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Please select a patient first.")
            return
        if not messagebox.askyesno("Confirm", "Deactivate this patient?"):
            return
        try:
            conn = get_conn()
            conn.execute("UPDATE Patient SET active_flag=0 WHERE patient_id=?",
                         (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Deactivated", "Patient has been deactivated.")
            self._load_patients()
            self._clear_form()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def _delete_patient(self):
        if not self._selected_id:
            messagebox.showwarning("Select", "Please select a patient first.")
            return
        if not messagebox.askyesno("Confirm Delete",
                                   "Permanently delete this patient?\nThis cannot be undone."):
            return
        try:
            conn = get_conn()
            conn.execute("DELETE FROM Patient WHERE patient_id=?", (self._selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Deleted", "Patient removed.")
            self._load_patients()
            self._clear_form()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def _clear_form(self):
        for e in self.entries.values():
            e.delete(0, tk.END)
        self._selected_id = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())


# ==============================
# Main
# ==============================
if __name__ == "__main__":
    app = CareFlowPatients()
    app.mainloop()