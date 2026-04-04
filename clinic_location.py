#!/usr/bin/env python3
"""
clinic_locations.py

Standalone Clinic Location Management window styled to match
the CareFlow dashboard (BG_LIGHT / BG_SIDEBAR / BG_PANEL / ACCENT palette).
No menu pages, no patient/staff code — clinic CRUD only.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

# ── DB ──────────────────────────────────────────────────────────────
DB_NAME = "healthcare.db"

# ── Style (mirrors careflow_dashboard.py) ───────────────────────────
BG_LIGHT        = "#e6f2ec"
BG_SIDEBAR      = "#5FAF90"
BG_SIDEBAR_LIGHT = "#A2DDC6"
BG_PANEL        = "#ffffff"
ACCENT          = "#308684"
CARD_BG         = "#f7fff7"
TEXT            = "#0b3d2e"
BORDER          = "#cfd8d3"

FONT_TITLE  = ("Helvetica", 20, "bold")
FONT_HEADER = ("Helvetica", 14, "bold")
FONT_BODY   = ("Helvetica", 10)
FONT_BTN    = ("Helvetica", 10, "bold")
FONT_SMALL  = ("Helvetica", 9)

BTN_GREEN  = ACCENT
BTN_ORANGE = "#e07b2a"
BTN_RED    = "#c0392b"
BTN_GRAY   = "#ccc"
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


# ── Form dialog (shared by Add / Edit) ──────────────────────────────
def _open_form_dialog(parent, title, initial=None, on_submit=None):
    """
    Generic form window. initial = (name, address, city, state, zip, phone) or None.
    on_submit(name, address, city, state, zip, phone) → bool
    """
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("430x360")
    win.resizable(False, False)
    win.configure(bg=BG_LIGHT)
    win.grab_set()

    # Header bar
    hdr = tk.Frame(win, bg=BG_SIDEBAR, height=48)
    hdr.pack(fill="x")
    tk.Label(hdr, text=title, bg=BG_SIDEBAR, fg=TEXT,
             font=FONT_HEADER).pack(side="left", padx=16, pady=10)

    body = tk.Frame(win, bg=BG_LIGHT)
    body.pack(fill="both", expand=True, padx=20, pady=14)

    fields  = ["Name", "Address", "City", "State", "ZIP", "Phone"]
    defaults = initial if initial else ("", "", "", "", "", "")
    entries  = {}

    for i, (lbl, val) in enumerate(zip(fields, defaults)):
        tk.Label(body, text=lbl + " *" if lbl != "Phone" else lbl,
                 bg=BG_LIGHT, fg=TEXT, font=FONT_BODY, anchor="w").grid(
            row=i, column=0, sticky="w", padx=4, pady=5)
        ent = tk.Entry(body, width=32, font=FONT_BODY,
                       relief="solid", bd=1, highlightthickness=0)
        ent.insert(0, val or "")
        ent.grid(row=i, column=1, padx=8, pady=5)
        entries[lbl.lower()] = ent

    def submit():
        vals = {k: v.get().strip() for k, v in entries.items()}
        required = [k for k in ("name", "address", "city", "state", "zip") if not vals[k]]
        if required:
            messagebox.showwarning("Missing Fields",
                                   "Name, Address, City, State, and ZIP are required.",
                                   parent=win)
            return
        ok = on_submit(vals["name"], vals["address"], vals["city"],
                       vals["state"], vals["zip"], vals["phone"])
        if ok:
            win.destroy()

    btn_row = tk.Frame(win, bg=BG_LIGHT)
    btn_row.pack(pady=(0, 14))

    tk.Button(btn_row, text="Save", bg=BG_SIDEBAR, fg=TEXT,
              font=FONT_BTN, relief="flat", width=12,
              padx=6, pady=4, cursor="hand2",
              command=submit).pack(side="left", padx=8)

    tk.Button(btn_row, text="Cancel", bg=BTN_GRAY, fg=TEXT,
              font=FONT_BTN, relief="flat", width=12,
              padx=6, pady=4, cursor="hand2",
              command=win.destroy).pack(side="left", padx=8)


# ── Main window ──────────────────────────────────────────────────────
class ClinicLocationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow — Clinic Locations")
        self.geometry("1000x640")
        self.minsize(800, 500)
        self.configure(bg=BG_LIGHT)

        self._build_ui()
        self.refresh_table()

    # ── Layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Left sidebar ──────────────────────────────────────────
        sidebar = tk.Frame(outer, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nClinic Locations", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left", padx=8, pady=8).pack(anchor="w")

        items = ["Dashboard", "Patient", "Staff", "Clinic", "Records", "Billing"]
        for item in items:
            bg = BG_SIDEBAR_LIGHT if item == "Clinic" else BG_SIDEBAR
            tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_BODY,
                     anchor="w", padx=10, pady=6).pack(fill="x", padx=10, pady=2)

        # ── Main panel ────────────────────────────────────────────
        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # White header
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(header, text="Clinic Location Management",
                 bg=BG_PANEL, fg=TEXT, font=FONT_TITLE).pack(side="left", padx=14, pady=14)

        # White body
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        # Summary card row
        card_row = tk.Frame(body, bg=BG_PANEL)
        card_row.pack(fill="x", padx=14, pady=(12, 6))

        self._count_var = tk.StringVar(value="—")
        self._make_card(card_row, "Active Clinics", self._count_var)

        tk.Label(body, text="All Active Locations",
                 bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).pack(anchor="w", padx=20, pady=(4, 4))

        # Table
        table_wrap = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        table_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 0))

        cols = ("ID", "Name", "City", "State")

        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings",
                                 selectmode="browse")
        for col, w in zip(cols, (60, 280, 200, 100)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")

        # Style the treeview to match dashboard palette
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview",
                        background=BG_PANEL,
                        fieldbackground=BG_PANEL,
                        foreground=TEXT,
                        rowheight=30,
                        font=FONT_BODY)
        style.configure("Treeview.Heading",
                        background=ACCENT,
                        foreground="white",
                        font=("Helvetica", 10, "bold"),
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", BG_SIDEBAR)],
                  foreground=[("selected", TEXT)])
        style.map("Treeview.Heading", background=[("active", "#256b69")])

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # Double-click to edit
        self.tree.bind("<Double-1>", lambda _: self.open_edit_dialog())

        # Action button bar (bottom of body)
        action_bar = tk.Frame(body, bg=BG_PANEL)
        action_bar.pack(fill="x", padx=14, pady=(8, 10))

        for label, color, cmd in [
            ("＋  Add Clinic",      BTN_GREEN,  self.open_add_dialog),
            ("✎  Edit Selected",    BTN_ORANGE, self.open_edit_dialog),
            ("✕  Delete Selected",  BTN_RED,    self.delete_selected),
            ("↺  Refresh",          ACCENT,     self.refresh_table),
        ]:
            tk.Button(action_bar, text=label, bg=color, fg="white",
                      font=FONT_BTN, relief="flat",
                      padx=12, pady=6, cursor="hand2",
                      command=cmd).pack(side="left", padx=(0, 8))

        # Status bar
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(body, textvariable=self.status_var,
                 bg=BG_SIDEBAR_LIGHT, fg=TEXT, font=FONT_SMALL,
                 anchor="w", padx=12, pady=4).pack(fill="x", side="bottom", padx=14, pady=(0, 8))

    def _make_card(self, parent, label, str_var):
        card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="raised",
                        width=160, height=70)
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
            self.tree.insert("", "end", values=c)

        self._count_var.set(str(len(clinics)))
        self.status_var.set(f"Loaded {len(clinics)} active clinic(s).")

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a clinic row first.")
            return None
        return self.tree.item(sel[0])["values"][0]

    # ── CRUD actions ─────────────────────────────────────────────────
    def open_add_dialog(self):
        def do_add(name, address, city, state, zip_code, phone):
            ok = add_clinic_location(name, address, city, state, zip_code, phone)
            if ok:
                self.refresh_table()
                self.status_var.set(f"Added clinic '{name}'.")
            return ok

        _open_form_dialog(self, "Add Clinic", on_submit=do_add)

    def open_edit_dialog(self):
        cid = self._selected_id()
        if cid is None:
            return
        row = get_clinic_full(cid)
        if not row:
            messagebox.showerror("Error", "Could not load clinic details.")
            return

        def do_update(name, address, city, state, zip_code, phone):
            ok = update_clinic_location(cid, name, address, city, state, zip_code, phone)
            if ok:
                self.refresh_table()
                self.status_var.set(f"Updated clinic '{name}'.")
            return ok

        _open_form_dialog(self, "Edit Clinic", initial=row, on_submit=do_update)

    def delete_selected(self):
        cid = self._selected_id()
        if cid is None:
            return
        name = self.tree.item(self.tree.selection()[0])["values"][1]
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete '{name}'?\n\nThis will mark it as inactive."):
            return
        ok = soft_delete_clinic_location(cid)
        if ok:
            self.refresh_table()
            self.status_var.set(f"Deleted clinic '{name}'.")


# ── Embeddable frame used by main.py portal ──────────────────────────
class ClinicFrame(tk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self._count_var = tk.StringVar(value="—")
        self.status_var = tk.StringVar(value="Ready.")
        self.tree       = None
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Sidebar ──────────────────────────────────────────────
        sidebar = tk.Frame(outer, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nAdmin Portal",
                 bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left",
                 padx=8, pady=8).pack(anchor="w")

        nav_map = {
            "Dashboard": "HomePage",
            "Patient":   None,
            "Staff":     "StaffMenuPage",
            "Clinic":    None,
            "Records":   "RecordsMenuPage",
            "Billing":   "BillingMenuPage",
        }
        for item, page in nav_map.items():
            is_active = item == "Clinic"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR

            def make_cmd(p=page):
                if p and self.controller:
                    return lambda: self.controller.show_frame(p)
                return None

            cmd = make_cmd()
            if cmd:
                tk.Button(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_BODY,
                          anchor="w", padx=10, pady=6, relief="flat",
                          activebackground=BG_SIDEBAR_LIGHT, cursor="hand2",
                          command=cmd).pack(fill="x", padx=10, pady=2)
            else:
                tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_BODY,
                         anchor="w", padx=10, pady=6).pack(fill="x", padx=10, pady=2)

        if self.controller:
            tk.Button(sidebar, text="← Dashboard", bg=BG_SIDEBAR, fg=TEXT,
                      font=FONT_BTN, relief="flat", anchor="w",
                      padx=12, pady=6, cursor="hand2",
                      command=lambda: self.controller.show_frame("HomePage")
                      ).pack(side="bottom", fill="x", padx=10, pady=(0, 12))

        # ── Main panel ───────────────────────────────────────────
        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # White header
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(header, text="Clinic Location Management",
                 bg=BG_PANEL, fg=TEXT, font=FONT_TITLE).pack(side="left", padx=14, pady=14)

        # White body
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        # Summary card row
        card_row = tk.Frame(body, bg=BG_PANEL)
        card_row.pack(fill="x", padx=14, pady=(12, 6))
        self._make_card(card_row, "Active Clinics", self._count_var)

        tk.Label(body, text="All Active Locations",
                 bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).pack(anchor="w", padx=20, pady=(4, 4))

        # Table
        table_wrap = tk.Frame(body, bg=BG_PANEL, bd=1, relief="solid")
        table_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 0))

        cols = ("ID", "Name", "City", "State")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings",
                                 selectmode="browse")
        for col, w in zip(cols, (60, 280, 200, 100)):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="w")

        style = ttk.Style()
        style.configure("Treeview", background=BG_PANEL, fieldbackground=BG_PANEL,
                        foreground=TEXT, rowheight=30, font=FONT_BODY)
        style.configure("Treeview.Heading", background=ACCENT, foreground="white",
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("Treeview",
                  background=[("selected", BG_SIDEBAR)],
                  foreground=[("selected", TEXT)])

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _: self.open_edit_dialog())

        # Action button bar (bottom of body, not in sidebar)
        action_bar = tk.Frame(body, bg=BG_PANEL)
        action_bar.pack(fill="x", padx=14, pady=(8, 10))

        for label, color, cmd in [
            ("＋  Add Clinic",      BTN_GREEN,  self.open_add_dialog),
            ("✎  Edit Selected",    BTN_ORANGE, self.open_edit_dialog),
            ("✕  Delete Selected",  BTN_RED,    self.delete_selected),
            ("↺  Refresh",          ACCENT,     self.refresh_table),
        ]:
            tk.Button(action_bar, text=label, bg=color, fg="white",
                      font=FONT_BTN, relief="flat",
                      padx=12, pady=6, cursor="hand2",
                      command=cmd).pack(side="left", padx=(0, 8))

        # Status bar
        tk.Label(body, textvariable=self.status_var,
                 bg=BG_SIDEBAR_LIGHT, fg=TEXT, font=FONT_SMALL,
                 anchor="w", padx=12, pady=4).pack(fill="x", side="bottom", padx=14, pady=(0, 8))


# Copy data/action methods from ClinicLocationApp onto ClinicFrame
for _n, _v in vars(ClinicLocationApp).items():
    if not _n.startswith('__') and callable(_v) and _n != '_build_ui':
        setattr(ClinicFrame, _n, _v)


# ── Entry point ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ClinicLocationApp()
    app.mainloop()