#!/usr/bin/env python3
"""
careflow_patients_updated.py

CareFlow Patient Management page — refactored to match StaffManagementFrame
pattern: tk.Frame subclass with optional controller for navigation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from typing import Optional

# ==============================
# Config / Styles
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

SIDEBAR_WIDTH = 170
FONT_TITLE    = ("Helvetica", 18, "bold")
FONT_HEADER   = ("Helvetica", 13, "bold")
FONT_TABLE    = ("Helvetica", 10)
FONT_NAV      = ("Helvetica", 10)
FONT_LOGO     = ("Helvetica", 13, "bold")
FONT_SMALL    = ("Helvetica", 10)

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
# Patient Management Frame
# ==============================
class PatientManagementFrame(tk.Frame):
    def __init__(self, parent=None, controller=None, role="Admin"):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self.role = role

        ensure_patient_table()

        self._selected_id: Optional[int] = None
        self._total_var    = tk.StringVar(value="0")
        self._active_var   = tk.StringVar(value="0")
        self._inactive_var = tk.StringVar(value="0")

        self._build_ui()
        self._load_patients()

    # ------------------------------------------------------------------
    # Top-level layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer)

        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # White header
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(header, text="Patient Management", font=FONT_TITLE,
                 bg=BG_PANEL, fg=TEXT).pack(side="left", padx=14, pady=14)
        tk.Label(header, text="Signed in as\nAdministrators Name",
                 bg=BG_PANEL, fg=TEXT, justify="right").pack(side="right", padx=14)

        # White body
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 12))
        body.grid_rowconfigure(2, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._build_filter_bar(body)
        self._build_table_section(body)
        self._build_form_section(body)
        self._build_action_bar(body)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        portal_label = "Staff Portal" if self.role == "Staff" else "Admin Portal"
        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text=f"CareFlow\n{portal_label}", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left", padx=8, pady=8).pack(anchor="w")

        if self.role == "Staff":
            nav_map = {
                "Dashboard": "HomePage",
                "Patient":   None,
                "Records":   "RecordsMenuPage",
                "Billing":   "BillingMenuPage",
            }
        else:
            nav_map = {
                "Dashboard": "HomePage",
                "Patient":   None,
                "Staff":     "StaffMenuPage",
                "Clinic":    "LocationMenuPage",
                "Records":   "RecordsMenuPage",
                "Billing":   "BillingMenuPage",
            }

        for item, page in nav_map.items():
            is_active = item == "Patient"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR

            def make_cmd(p=page):
                if p and self.controller:
                    return lambda: self.controller.show_frame(p)
                return None

            cmd = make_cmd()
            if cmd:
                tk.Button(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_SMALL,
                          anchor="w", padx=10, pady=6, relief="flat",
                          activebackground=BG_SIDEBAR_LIGHT, cursor="hand2",
                          command=cmd).pack(fill="x", padx=10, pady=2)
            else:
                tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_SMALL,
                         anchor="w", padx=10, pady=6).pack(fill="x", padx=10, pady=2)

        if self.controller:
            tk.Button(sidebar, text="← Dashboard", bg=BG_SIDEBAR, fg=TEXT,
                      font=FONT_SMALL, relief="flat", anchor="w",
                      padx=12, pady=6, cursor="hand2",
                      command=lambda: self.controller.show_frame("HomePage")
                      ).pack(side="bottom", fill="x", padx=10, pady=(0, 12))

    # ------------------------------------------------------------------
    # Filter / summary bar
    # ------------------------------------------------------------------
    def _build_filter_bar(self, parent):
        filter_bar = tk.Frame(parent, bg=BG_PANEL)
        filter_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))
        filter_bar.grid_columnconfigure(1, weight=1)

        # Summary cards
        card_frame = tk.Frame(filter_bar, bg=BG_PANEL)
        card_frame.grid(row=0, column=0, sticky="w")

        card_defs = [
            ("Total Patients",    self._total_var),
            ("Active Patients",   self._active_var),
            ("Inactive Patients", self._inactive_var),
        ]
        for lbl, var in card_defs:
            c = tk.Frame(card_frame, bg=CARD_BG, bd=1, relief="raised", width=140, height=56)
            c.pack(side="left", padx=(0, 8))
            c.pack_propagate(False)
            tk.Label(c, textvariable=var, bg=CARD_BG, fg=TEXT,
                     font=("Helvetica", 15, "bold")).pack(anchor="nw", padx=10, pady=(4, 0))
            tk.Label(c, text=lbl, bg=CARD_BG, fg=TEXT,
                     font=FONT_SMALL).pack(anchor="nw", padx=10)

        # Search + toggle
        search_frame = tk.Frame(filter_bar, bg=BG_PANEL)
        search_frame.grid(row=0, column=1, sticky="e", padx=(12, 0))

        tk.Label(search_frame, text="Search:", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 10, "bold")).pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._load_patients())
        tk.Entry(search_frame, textvariable=self.search_var, width=28,
                 font=FONT_SMALL, bg=CARD_BG, fg=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground="#cde8dc",
                 highlightcolor=ACCENT).pack(side="left")

        self.show_inactive_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            search_frame, text="Show inactive", variable=self.show_inactive_var,
            bg=BG_PANEL, fg=TEXT, activebackground=BG_PANEL,
            selectcolor=CARD_BG, command=self._load_patients
        ).pack(side="left", padx=(10, 0))

        # Divider
        tk.Frame(parent, bg="#e0e0e0", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=10)

    # ------------------------------------------------------------------
    # Table section
    # ------------------------------------------------------------------
    def _build_table_section(self, parent):
        container = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid")
        container.grid(row=2, column=0, sticky="nsew", padx=(10, 6), pady=8)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        tk.Label(container, text="Patients", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        style = ttk.Style()
        style.theme_use("clam")
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
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
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
    # Form section
    # ------------------------------------------------------------------
    def _build_form_section(self, parent):
        panel = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid", padx=16, pady=14)
        panel.grid(row=2, column=1, sticky="nsew", padx=(0, 10), pady=8)
        parent.grid_columnconfigure(1, minsize=290)

        tk.Label(panel, text="Patient Details", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

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
    # Action bar
    # ------------------------------------------------------------------
    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=BG_LIGHT)
        bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 4))

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

        total    = conn.execute("SELECT COUNT(*) FROM Patient").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM Patient WHERE active_flag=1").fetchone()[0]
        inactive = conn.execute("SELECT COUNT(*) FROM Patient WHERE active_flag=0").fetchone()[0]
        conn.close()

        self._total_var.set(str(total))
        self._active_var.set(str(active))
        self._inactive_var.set(str(inactive))

        self.tree.delete(*self.tree.get_children())

        for pid, fn, ln, dob, phone, email, active_flag in rows:
            if not show_inactive and active_flag == 0:
                continue
            name = f"{ln}, {fn}"
            if search and search not in name.lower() \
                    and search not in (phone or "").lower() \
                    and search not in (email or "").lower():
                continue
            status = "Active" if active_flag else "Inactive"
            tag    = "inactive" if not active_flag else ""
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
# Standalone entry point
# ==============================
if __name__ == "__main__":
    root = tk.Tk()
    root.title("CareFlow Admin Portal – Patients")
    root.geometry("1200x720")
    root.configure(bg=BG_LIGHT)
    frame = PatientManagementFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()