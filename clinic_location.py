#!/usr/bin/env python3
"""
clinic_locations.py

Standalone Clinic Location Management window styled to match
the CareFlow dashboard (BG_LIGHT / BG_SIDEBAR / BG_PANEL / ACCENT palette).
No menu pages, no patient/staff code — clinic CRUD only.

Form panel is now inline on the right side (mirrors StaffManagementFrame layout).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from PIL import Image, ImageTk

# ── DB ──────────────────────────────────────────────────────────────
DB_NAME = "healthcare.db"

# ── Style (mirrors careflow_dashboard.py) ───────────────────────────
BG_LIGHT         = "#e6f2ec"
BG_SIDEBAR       = "#5FAF90"
BG_SIDEBAR_LIGHT = "#A2DDC6"
BG_PANEL         = "#ffffff"
ACCENT           = "#308684"
CARD_BG          = "#f7fff7"
TEXT             = "#0b3d2e"
BORDER           = "#cfd8d3"

FONT_TITLE  = ("Helvetica", 20, "bold")
FONT_HEADER = ("Helvetica", 14, "bold")
FONT_BODY   = ("Helvetica", 10)
FONT_BTN    = ("Helvetica", 10, "bold")
FONT_SMALL  = ("Helvetica", 9)

BTN_GREEN  = ACCENT
BTN_ORANGE = "#e07b2a"
BTN_RED    = "#c0392b"
BTN_GRAY   = "#95a5a6"
BTN_BLUE   = "#2980b9"
BTN_SIDEBAR = BG_SIDEBAR


# ── DB helpers ───────────────────────────────────────────────────────
def get_all_active_clinics():
    try:
        conn = sqlite3.connect(DB_NAME)
        cur  = conn.cursor()
        cur.execute("""
            SELECT location_id, name, city, state
            FROM   ClinicLocation
            WHERE  status = 'active'
        """)
        rows = cur.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch clinics:\n\n{e}")
        return []


def add_clinic_location(name, address, city, state, zip_code, phone):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur  = conn.cursor()
        cur.execute("""
            INSERT INTO ClinicLocation (name, address, city, state, zip, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (name, address, city, state, zip_code, phone))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to add clinic:\n\n{e}")
        return False


def update_clinic_location(location_id, name, address, city, state, zip_code, phone):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur  = conn.cursor()
        cur.execute("""
            UPDATE ClinicLocation
            SET    name=?, address=?, city=?, state=?, zip=?, phone=?
            WHERE  location_id=?
        """, (name, address, city, state, zip_code, phone, location_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to update clinic:\n\n{e}")
        return False


def soft_delete_clinic_location(clinic_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur  = conn.cursor()
        cur.execute("""
            UPDATE ClinicLocation SET status = 'inactive'
            WHERE  location_id = ?
        """, (clinic_id,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to delete clinic:\n\n{e}")
        return False


def get_clinic_full(clinic_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur  = conn.cursor()
        cur.execute("""
            SELECT name, address, city, state, zip, phone
            FROM   ClinicLocation
            WHERE  location_id = ?
        """, (clinic_id,))
        row = cur.fetchone()
        conn.close()
        return row
    except sqlite3.Error:
        return None


# ── Shared base class with all data / CRUD logic ─────────────────────
class _ClinicBase:
    """
    Mixin that provides the table + inline form panel UI and all CRUD logic.
    Subclasses must call _build_clinic_ui() and set self.status_var / self._count_var.
    """

    def _build_clinic_ui(self, parent):
        """
        Build the split content (table left, form right) + action bar
        inside *parent* Frame.
        """
        self._selected_id = None
        self._count_var   = tk.StringVar(value="—")
        self.status_var   = tk.StringVar(value="Ready.")

        # ── Summary card row ─────────────────────────────────────────
        card_row = tk.Frame(parent, bg=BG_PANEL)
        card_row.pack(fill="x", padx=14, pady=(12, 6))
        self._make_card(card_row, "Active Clinics", self._count_var)

        tk.Label(parent, text="All Active Locations",
                 bg=BG_PANEL, fg=TEXT, font=FONT_HEADER
                 ).pack(anchor="w", padx=20, pady=(4, 4))

        # ── Split container ──────────────────────────────────────────
        split = tk.Frame(parent, bg=BG_PANEL)
        split.pack(fill="both", expand=True, padx=14, pady=(0, 0))
        split.grid_rowconfigure(0, weight=1)
        split.grid_columnconfigure(0, weight=1)
        split.grid_columnconfigure(1, minsize=290)

        self._build_table_section(split)
        self._build_form_section(split)

        # ── Action bar ───────────────────────────────────────────────
        self._build_action_bar(parent)

        # ── Status bar ───────────────────────────────────────────────
        tk.Label(parent, textvariable=self.status_var,
                 bg=BG_SIDEBAR_LIGHT, fg=TEXT, font=FONT_SMALL,
                 anchor="w", padx=12, pady=4
                 ).pack(fill="x", side="bottom", padx=14, pady=(0, 8))

    # ── Table section ────────────────────────────────────────────────
    def _build_table_section(self, parent):
        container = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid")
        container.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=8)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("CareFlow.Treeview",
                        background=CARD_BG, fieldbackground=CARD_BG,
                        foreground=TEXT, rowheight=30, font=FONT_BODY)
        style.configure("CareFlow.Treeview.Heading",
                        background=BG_SIDEBAR_LIGHT, foreground=TEXT,
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("CareFlow.Treeview",
                  background=[("selected", BG_SIDEBAR)],
                  foreground=[("selected", TEXT)])

        cols = ("ID", "Name", "City", "State")
        col_widths = (60, 240, 180, 90)

        self.tree = ttk.Treeview(container, columns=cols, show="headings",
                                 selectmode="browse", style="CareFlow.Treeview")
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")

        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns", pady=8)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _: self._on_select())

    # ── Form section (right panel) ───────────────────────────────────
    def _build_form_section(self, parent):
        panel = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid", padx=16, pady=14)
        panel.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=8)
        panel.grid_columnconfigure(1, weight=1)

        tk.Label(panel, text="Clinic Details", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.entries = {}
        fields = [
            ("Name *",    "name"),
            ("Address *", "address"),
            ("City *",    "city"),
            ("State *",   "state"),
            ("ZIP *",     "zip"),
            ("Phone",     "phone"),
        ]

        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(panel, text=label, bg=BG_PANEL, fg=TEXT,
                     font=("Helvetica", 9)).grid(
                row=i, column=0, sticky="w", pady=3)
            e = tk.Entry(panel, width=22, bg=CARD_BG, fg=TEXT,
                         relief="flat", highlightthickness=1,
                         highlightbackground="#cde8dc",
                         highlightcolor=ACCENT)
            e.grid(row=i, column=1, pady=3, padx=(8, 0), sticky="ew")
            self.entries[key] = e

        tk.Label(panel, text="* Required fields",
                 bg=BG_PANEL, fg="gray", font=("Helvetica", 8)
                 ).grid(row=len(fields) + 1, column=0, columnspan=2,
                        sticky="w", pady=(8, 0))

    # ── Action bar ───────────────────────────────────────────────────
    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=BG_PANEL)
        bar.pack(fill="x", padx=14, pady=(0, 8))

        btn_cfg = dict(
            relief="flat", fg="white", padx=14, pady=7,
            font=("Helvetica", 10, "bold"),
            activeforeground="white", cursor="hand2"
        )

        tk.Button(bar, text="＋  Add",     bg=BTN_GREEN,  activebackground=TEXT,
                  command=self._do_add,                    **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="✎  Update",   bg=BTN_BLUE,   activebackground="#1a5276",
                  command=self._do_update,                 **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="✕  Delete",   bg=BTN_RED,    activebackground="#922b21",
                  command=self._do_delete,                 **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="↺  Refresh",  bg=BTN_GRAY,   activebackground="#5d6d7e",
                  command=self.refresh_table,              **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="Clear",       bg=BTN_GRAY,   activebackground="#5d6d7e",
                  command=self._clear_form,                **btn_cfg).pack(side="left")

    # ── Summary card ─────────────────────────────────────────────────
    def _make_card(self, parent, label, str_var):
        card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="raised", width=160, height=70)
        card.pack(side="left", padx=8, pady=4)
        card.pack_propagate(False)
        tk.Label(card, textvariable=str_var, bg=CARD_BG, fg=TEXT,
                 font=("Helvetica", 20, "bold")).pack(anchor="nw", padx=12, pady=(8, 0))
        tk.Label(card, text=label, bg=CARD_BG, fg=ACCENT,
                 font=FONT_SMALL).pack(anchor="nw", padx=12)

    # ── Table helpers ────────────────────────────────────────────────
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        clinics = get_all_active_clinics()
        for c in clinics:
            self.tree.insert("", "end", iid=str(c[0]), values=c)
        self._count_var.set(str(len(clinics)))
        self.status_var.set(f"Loaded {len(clinics)} active clinic(s).")

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        cid = int(sel[0])
        self._selected_id = cid
        row = get_clinic_full(cid)
        if not row:
            return
        keys = ("name", "address", "city", "state", "zip", "phone")
        for key, val in zip(keys, row):
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, val or "")
        self.status_var.set(f"Selected clinic ID {cid}.")

    # ── Form helpers ─────────────────────────────────────────────────
    def _collect_form(self):
        return {k: v.get().strip() for k, v in self.entries.items()}

    def _clear_form(self):
        for e in self.entries.values():
            e.delete(0, tk.END)
        self._selected_id = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        self.status_var.set("Form cleared.")

    def _validate(self, data):
        required = [k for k in ("name", "address", "city", "state", "zip")
                    if not data.get(k)]
        if required:
            messagebox.showwarning("Missing Fields",
                                   "Name, Address, City, State, and ZIP are required.")
            return False
        return True

    # ── CRUD ─────────────────────────────────────────────────────────
    def _do_add(self):
        data = self._collect_form()
        if not self._validate(data):
            return
        ok = add_clinic_location(
            data["name"], data["address"], data["city"],
            data["state"], data["zip"], data["phone"]
        )
        if ok:
            self.refresh_table()
            self.status_var.set(f"Added clinic '{data['name']}'.")
            self._clear_form()

    def _do_update(self):
        if not self._selected_id:
            messagebox.showwarning("No Selection",
                                   "Please select a clinic from the table first.")
            return
        data = self._collect_form()
        if not self._validate(data):
            return
        ok = update_clinic_location(
            self._selected_id, data["name"], data["address"],
            data["city"], data["state"], data["zip"], data["phone"]
        )
        if ok:
            self.refresh_table()
            self.status_var.set(f"Updated clinic '{data['name']}'.")
            self._clear_form()

    def _do_delete(self):
        if not self._selected_id:
            messagebox.showwarning("No Selection",
                                   "Please select a clinic from the table first.")
            return
        name = self.entries["name"].get() or f"ID {self._selected_id}"
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete '{name}'?\n\nThis will mark it as inactive."):
            return
        ok = soft_delete_clinic_location(self._selected_id)
        if ok:
            self.refresh_table()
            self.status_var.set(f"Deleted clinic '{name}'.")
            self._clear_form()


# ── Standalone window ────────────────────────────────────────────────
class ClinicLocationApp(tk.Tk, _ClinicBase):
    def __init__(self):
        super().__init__()
        self.title("CareFlow — Clinic Locations")
        self.geometry("1060x660")
        self.minsize(860, 520)
        self.configure(bg=BG_LIGHT)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        # ── Left sidebar ──────────────────────────────────────────────
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=180)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nClinic Locations",
                 bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left",
                 padx=8, pady=8).pack(anchor="w")

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=10, pady=4)

        items = ["Dashboard", "Patient", "Staff", "Clinic", "Records", "Billing"]
        for item in items:
            bg = BG_SIDEBAR_LIGHT if item == "Clinic" else BG_SIDEBAR
            tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_BODY,
                     anchor="w", padx=10, pady=6).pack(fill="x", padx=10, pady=2)

        # ── Main panel ────────────────────────────────────────────────
        main = tk.Frame(self, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True)

        # White header
        hdr = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        hdr.pack(fill="x", padx=14, pady=(12, 0))
        tk.Label(hdr, text="Clinic Location Management",
                 bg=BG_PANEL, fg=TEXT, font=FONT_TITLE
                 ).pack(side="left", padx=18, pady=14)

        # White body — hands off to shared mixin
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=14, pady=(10, 12))

        self._build_clinic_ui(body)


# ── Embeddable frame used by main.py portal ──────────────────────────
class ClinicFrame(tk.Frame, _ClinicBase):
    def __init__(self, parent, controller=None, role="Admin"):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self.role = role
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Load icons (keep references to avoid garbage collection)
        def load_icon(path, size=(18, 20)):
            img = Image.open(path)
            img = img.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        
        self.icons = {
            "Dashboard": load_icon("icons/dashboard_icon.png"),
            "Patient": load_icon("icons/patient_icon.png"),
            "Staff": load_icon("icons/staff_icon.png"),
            "Clinic": load_icon("icons/clinic_icon.png"),
            "Records": load_icon("icons/folder_icon.png"),
            "Billing": load_icon("icons/credit_icon.png"),
        }

        # ── Sidebar ────────────────────────────────────────────────
        sidebar = tk.Frame(outer, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        portal_label = "Staff Portal" if self.role == "Staff" else "Admin Portal"
        tk.Label(logo_box, text=f"CareFlow\n{portal_label}",
                 bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left",
                 padx=8, pady=8).pack(anchor="w")

        nav_map = {
            "Dashboard": "HomePage",
            "Patient":   "PatientMenuPage",
            "Staff":     "StaffMenuPage",
            "Clinic":    None,
            "Records":   "RecordsMenuPage",
            "Billing":   "BillingMenuPage",
        }
        for item, page in nav_map.items():
            is_active = item == "Clinic"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR
            icon = self.icons.get(item)

            def make_cmd(p=page):
                if p and self.controller:
                    return lambda: self.controller.show_frame(p)
                return None

            cmd = make_cmd()
            if cmd:
                tk.Button(sidebar, text=item, image=icon, compound="left",
                          bg=bg, fg=TEXT, font=FONT_BODY,
                          anchor="w", padx=10, pady=6, relief="flat",
                          activebackground=BG_SIDEBAR_LIGHT, cursor="hand2",
                          command=cmd).pack(fill="x", padx=10, pady=2)
            else:
                tk.Label(sidebar, text=item, image=icon, compound="left",
                         bg=bg, fg=TEXT, font=FONT_BODY,
                         anchor="w", padx=10, pady=6).pack(fill="x", padx=10, pady=2)

        if self.controller:
            tk.Button(sidebar, text="← Dashboard", bg=BG_SIDEBAR, fg=TEXT,
                      font=FONT_BTN, relief="flat", anchor="w",
                      padx=12, pady=6, cursor="hand2",
                      command=lambda: self.controller.show_frame("HomePage")
                      ).pack(side="bottom", fill="x", padx=10, pady=(0, 12))

        # ── Main area ─────────────────────────────────────────────
        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # White header
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(header, text="Clinic Location Management",
                 bg=BG_PANEL, fg=TEXT, font=FONT_TITLE
                 ).pack(side="left", padx=14, pady=14)
        signed_in = "Staff" if self.role == "Staff" else "Administrator"
        tk.Label(header, text=f"Signed in as: {signed_in}",
                 bg=BG_PANEL, fg=TEXT, font=("Helvetica", 10)).pack(side="right", padx=14)

        # White body — hands off to shared mixin
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        self._build_clinic_ui(body)


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ClinicLocationApp()
    app.mainloop()