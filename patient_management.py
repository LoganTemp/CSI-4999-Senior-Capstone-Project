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


def is_valid_phone(s: str) -> bool:
    import re
    return bool(re.match(r"^\d{3}-\d{4}$", s))

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
            created_at        TEXT DEFAULT (datetime('now')),
            location_id       INTEGER REFERENCES ClinicLocation(location_id)
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
        self.location_list = []

        self._build_ui()
        self._load_locations()
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
        signed_in = "Staff" if self.role == "Staff" else "Administrator"
        tk.Label(header, text=f"Signed in as: {signed_in}",
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

        def load_icon(path, size=(18, 20)):
            try:
                from PIL import Image, ImageTk
                img = Image.open(path).resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                return None

        self._patient_nav_icons = {
            "Dashboard": load_icon("icons/dashboard_icon.png"),
            "Patient":   load_icon("icons/patient_icon.png"),
            "Staff":     load_icon("icons/staff_icon.png"),
            "Clinic":    load_icon("icons/clinic_icon.png"),
            "Records":   load_icon("icons/folder_icon.png"),
            "Billing":   load_icon("icons/credit_icon.png"),
        }

        for item, page in nav_map.items():
            is_active = item == "Patient"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR
            icon = self._patient_nav_icons.get(item)

            def make_cmd(p=page):
                if p and self.controller:
                    return lambda: self.controller.show_frame(p)
                return None

            cmd = make_cmd()
            kw = dict(image=icon, compound="left") if icon else {}
            if cmd:
                tk.Button(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_SMALL,
                          anchor="w", padx=10, pady=6, relief="flat",
                          activebackground=BG_SIDEBAR_LIGHT, cursor="hand2",
                          command=cmd, **kw).pack(fill="x", padx=10, pady=2)
            else:
                tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_SMALL,
                         anchor="w", padx=10, pady=6, **kw).pack(fill="x", padx=10, pady=2)

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

        cols = ("id", "name", "dob", "phone", "email", "location", "status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="CareFlow.Treeview")

        headings = {
            "id":       ("ID",       55,  "center"),
            "name":     ("Name",     180, "w"),
            "dob":      ("DOB",      100, "center"),
            "phone":    ("Phone",    110, "center"),
            "email":    ("Email",    180, "w"),
            "location": ("Clinic",   130, "w"),
            "status":   ("Status",   75,  "center"),
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

        # Required fields are marked with * — keys listed in _REQUIRED_KEYS
        fields = [
            ("First Name *",       "first_name"),
            ("Last Name *",        "last_name"),
            ("Date of Birth *",     "dob"),
            ("Sex",                "sex"),
            ("Phone (###-####) *",  "phone"),
            ("Email *",            "email"),
            ("Address",            "address"),
            ("Allergies",          "allergies"),
            ("Conditions *",       "conditions"),
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

        # Active checkbox — matches StaffManagementFrame pattern exactly
        row_after_fields = len(fields) + 1
        tk.Label(panel, text="Active", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(
            row=row_after_fields, column=0, sticky="w", pady=3)
        self.active_var = tk.IntVar(value=1)
        tk.Checkbutton(panel, variable=self.active_var,
                       bg=BG_PANEL, activebackground=BG_PANEL,
                       selectcolor=CARD_BG).grid(
            row=row_after_fields, column=1, sticky="w", padx=(8, 0))

        # Clinic assignment listbox
        loc_row = row_after_fields + 1
        tk.Label(panel, text="Clinic Assignment", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(
            row=loc_row, column=0, sticky="nw", pady=3)
        loc_frame = tk.Frame(panel, bg=BG_PANEL)
        loc_frame.grid(row=loc_row, column=1, pady=3, padx=(8, 0), sticky="ew")
        self.loc_listbox = tk.Listbox(
            loc_frame, selectmode="single", height=4,
            exportselection=False, font=("Helvetica", 9),
            bd=0, relief="flat", highlightthickness=1,
            highlightbackground="#cde8dc", highlightcolor=ACCENT,
            bg=CARD_BG, fg=TEXT,
            selectbackground=ACCENT, selectforeground="white"
        )
        loc_sb = ttk.Scrollbar(loc_frame, orient="vertical",
                               command=self.loc_listbox.yview)
        self.loc_listbox.configure(yscrollcommand=loc_sb.set)
        self.loc_listbox.pack(side="left", fill="both", expand=True)
        loc_sb.pack(side="left", fill="y")
        tk.Label(panel, text="Select a clinic to assign this patient",
                 bg=BG_PANEL, fg="gray", font=("Helvetica", 8)).grid(
            row=loc_row + 1, column=1, sticky="w", padx=(8, 0))

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
    # Validation — mirrors StaffManagementFrame._validate_base
    # ------------------------------------------------------------------

    # Keys that must be non-empty before saving
    _REQUIRED_KEYS = ("first_name", "last_name", "dob", "phone", "email", "conditions")

    def _validate(self, data: dict) -> bool:
        """
        Highlight empty required fields in red (like staff) and return False
        if any are missing.  Resets border to normal on fields that are filled.
        """
        missing = []
        for key in self._REQUIRED_KEYS:
            entry = self.entries[key]
            if data.get(key):
                # restore normal border
                entry.config(highlightbackground="#cde8dc", highlightcolor=ACCENT)
            else:
                # red border to signal the problem
                entry.config(highlightbackground="#e74c3c", highlightcolor="#e74c3c")
                missing.append(key.replace("_", " ").title())

        if missing:
            messagebox.showerror(
                "Missing Required Fields",
                "Please fill in: " + ", ".join(missing)
            )
            return False

        # Phone format check — must be ###-#### (e.g. 555-1234)
        if not is_valid_phone(data.get("phone", "")):
            self.entries["phone"].config(
                highlightbackground="#e74c3c", highlightcolor="#e74c3c"
            )
            messagebox.showerror("Invalid Phone", "Phone must be ###-#### (e.g. 555-1234).")
            return False

        return True

    def _reset_required_highlights(self):
        """Remove any red borders left from a previous failed validation."""
        for key in self._REQUIRED_KEYS:
            self.entries[key].config(
                highlightbackground="#cde8dc", highlightcolor=ACCENT
            )

    # ------------------------------------------------------------------
    # Data methods
    # ------------------------------------------------------------------
    def _load_locations(self):
        try:
            conn = get_conn()
            rows = conn.execute(
                "SELECT location_id, name, status FROM ClinicLocation ORDER BY name"
            ).fetchall()
            conn.close()
            self.location_list.clear()
            self.loc_listbox.delete(0, tk.END)
            for loc_id, name, status in rows:
                label = f"{name}  (ID {loc_id})" + (f" [{status}]" if status else "")
                self.location_list.append((label, loc_id))
                self.loc_listbox.insert(tk.END, label)
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def _load_patients(self, event=None):
        search = self.search_var.get().strip().lower()
        show_inactive = self.show_inactive_var.get()

        conn = get_conn()
        rows = conn.execute("""
            SELECT p.patient_id, p.first_name, p.last_name, p.dob, p.phone, p.email,
                   p.active_flag,
                   COALESCE(cl.name, '') AS clinic_name
            FROM Patient p
            LEFT JOIN ClinicLocation cl ON cl.location_id = p.location_id
            ORDER BY p.last_name, p.first_name
        """).fetchall()

        total    = conn.execute("SELECT COUNT(*) FROM Patient").fetchone()[0]
        active   = conn.execute("SELECT COUNT(*) FROM Patient WHERE active_flag=1").fetchone()[0]
        inactive = conn.execute("SELECT COUNT(*) FROM Patient WHERE active_flag=0").fetchone()[0]
        conn.close()

        self._total_var.set(str(total))
        self._active_var.set(str(active))
        self._inactive_var.set(str(inactive))

        self.tree.delete(*self.tree.get_children())

        for pid, fn, ln, dob, phone, email, active_flag, clinic_name in rows:
            if not show_inactive and active_flag == 0:
                continue
            name = f"{ln}, {fn}"
            if search and search not in name.lower() \
                    and search not in (phone or "").lower() \
                    and search not in (email or "").lower() \
                    and search not in (clinic_name or "").lower():
                continue
            status = "Active" if active_flag else "Inactive"
            tag    = "inactive" if not active_flag else ""
            self.tree.insert("", "end", iid=str(pid),
                             values=(pid, name, dob or "", phone or "",
                                     email or "", clinic_name or "", status),
                             tags=(tag,))

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_id = int(sel[0])

        conn = get_conn()
        row = conn.execute("""
            SELECT first_name, last_name, dob, sex, phone, email, address,
                   allergies, conditions, medications, notes, emergency_contact,
                   active_flag, location_id
            FROM Patient WHERE patient_id = ?
        """, (self._selected_id,)).fetchone()
        conn.close()

        if row:
            # Unpack: first 12 are field values, then active_flag, then location_id
            *fields, active_flag, assigned_loc_id = row
            for i, key in enumerate(self.entries):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, fields[i] if fields[i] else "")

            # Set active checkbox to match the patient's current active_flag
            self.active_var.set(1 if active_flag else 0)

            self.loc_listbox.selection_clear(0, tk.END)
            if assigned_loc_id is not None:
                for i, (_, loc_id) in enumerate(self.location_list):
                    if loc_id == assigned_loc_id:
                        self.loc_listbox.selection_set(i)
                        self.loc_listbox.see(i)
                        break

            # Clear any leftover validation highlights when loading a record
            self._reset_required_highlights()

    def _collect(self) -> dict:
        return {k: e.get().strip() for k, e in self.entries.items()}

    def _add_patient(self):
        data = self._collect()
        if not self._validate(data):
            return
        sel_locs = self.loc_listbox.curselection()
        loc_id = self.location_list[sel_locs[0]][1] if sel_locs else None
        try:
            conn = get_conn()
            conn.execute("""
                INSERT INTO Patient (
                    first_name, last_name, dob, sex, phone, email,
                    address, allergies, conditions, medications, notes,
                    emergency_contact, active_flag, location_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*data.values(), self.active_var.get(), loc_id))
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
        if not self._validate(data):
            return
        sel_locs = self.loc_listbox.curselection()
        loc_id = self.location_list[sel_locs[0]][1] if sel_locs else None
        try:
            conn = get_conn()
            conn.execute("""
                UPDATE Patient SET
                    first_name=?, last_name=?, dob=?, sex=?, phone=?, email=?,
                    address=?, allergies=?, conditions=?, medications=?,
                    notes=?, emergency_contact=?, active_flag=?, location_id=?
                WHERE patient_id=?
            """, (*data.values(), self.active_var.get(), loc_id, self._selected_id))
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
        self.active_var.set(1)          # default to Active when clearing
        self.loc_listbox.selection_clear(0, tk.END)
        self._selected_id = None
        self._reset_required_highlights()
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