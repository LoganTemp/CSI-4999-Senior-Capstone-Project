import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import hashlib

DB_NAME = "healthcare.db"

# ---------- Dashboard color palette ----------
BG_LIGHT         = "#e6f2ec"
BG_SIDEBAR       = "#5FAF90"
BG_SIDEBAR_LIGHT = "#A2DDC6"
BG_PANEL         = "#ffffff"
CARD_BG          = "#f7fff7"
ACCENT           = "#308684"
TEXT             = "#0b3d2e"
BTN_DANGER       = "#c0392b"
BTN_SAFE         = "#308684"
BTN_INFO         = "#2980b9"
BTN_WARN         = "#f39c12"
BTN_NEUTRAL      = "#95a5a6"
BTN_RED          = "#e53935"
BTN_ORANGE       = "#FF9800"

SIDEBAR_WIDTH = 170
FONT_TITLE    = ("Helvetica", 18, "bold")
FONT_HEADER   = ("Helvetica", 13, "bold")
FONT_TABLE    = ("Helvetica", 10)
FONT_SMALL    = ("Helvetica", 10)
FONT_MEDIUM   = ("Helvetica", 11)
FONT_NAV      = ("Helvetica", 10)
FONT_LOGO     = ("Helvetica", 13, "bold")

ROLES = ["doctor", "billing", "records", "nurse"]
CONFIRMATION_CODE = "1234"


def hash_password(password: str, iterations: int = 200_000) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def is_valid_email(s: str) -> bool:
    import re
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", s))


def is_valid_phone(s: str) -> bool:
    import re
    return bool(re.match(r"^\d{3}-\d{4}$", s))


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


class StaffManagementFrame(tk.Frame):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self.location_list = []
        self._all_rows = []
        self._selected_staff_id = None
        self._total_var  = tk.StringVar(value="0")
        self._active_var = tk.StringVar(value="0")
        self._build_ui()
        self._load_locations()
        self._load_staff()

    # ================================================================= UI ==
    def _build_ui(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer)

        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # -- White header --
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x", padx=12, pady=(12, 0))
        tk.Label(header, text="Staff Management", font=FONT_TITLE,
                 bg=BG_PANEL, fg=TEXT).pack(side="left", padx=14, pady=14)

        # -- White body: summary cards + split content --
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 12))
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._build_filter_bar(body)
        self._build_split_content(body)
        self._build_action_bar(body)

    # ---------------------------------------------------------- Sidebar --
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nAdmin Portal", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left", padx=8, pady=8).pack(anchor="w")

        nav_map = {
            "Dashboard": "HomePage",
            "Patient":   None,
            "Staff":     None,
            "Clinic":    "LocationMenuPage",
            "Records":   "RecordsMenuPage",
            "Billing":   "BillingMenuPage",
        }
        for item, page in nav_map.items():
            is_active = item == "Staff"
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

    # --------------------------------------------------------- Filter bar --
    def _build_filter_bar(self, parent):
        filter_bar = tk.Frame(parent, bg=BG_PANEL)
        filter_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 4))
        filter_bar.grid_columnconfigure(1, weight=1)

        # Summary cards
        card_frame = tk.Frame(filter_bar, bg=BG_PANEL)
        card_frame.grid(row=0, column=0, sticky="w")
        for lbl, var in [("Total Staff", self._total_var), ("Active Staff", self._active_var)]:
            c = tk.Frame(card_frame, bg=CARD_BG, bd=1, relief="raised", width=130, height=56)
            c.pack(side="left", padx=(0, 8))
            c.pack_propagate(False)
            tk.Label(c, textvariable=var, bg=CARD_BG, fg=TEXT,
                     font=("Helvetica", 15, "bold")).pack(anchor="nw", padx=10, pady=(4, 0))
            tk.Label(c, text=lbl, bg=CARD_BG, fg=TEXT,
                     font=FONT_SMALL).pack(anchor="nw", padx=10)

        # Search
        search_frame = tk.Frame(filter_bar, bg=BG_PANEL)
        search_frame.grid(row=0, column=1, sticky="e", padx=(12, 0))
        tk.Label(search_frame, text="Search:", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 10, "bold")).pack(side="left", padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_staff())
        tk.Entry(search_frame, textvariable=self.search_var, width=28,
                 font=FONT_SMALL, bg=CARD_BG, fg=TEXT, relief="flat",
                 highlightthickness=1, highlightbackground="#cde8dc",
                 highlightcolor=ACCENT).pack(side="left")

        # Divider
        tk.Frame(parent, bg="#e0e0e0", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=10)

    # --------------------------------------------------- Split: table + form --
    def _build_split_content(self, parent):
        self._build_table_section(parent)
        self._build_form_section(parent)

    # ----------------------------------------------------------- Table --
    def _build_table_section(self, parent):
        container = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid")
        container.grid(row=2, column=0, sticky="nsew", padx=(10, 6), pady=8)
        container.grid_rowconfigure(1, weight=1)
        container.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(2, weight=1)

        tk.Label(container, text="Staff", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        # Treeview
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

        cols = ("id", "name", "role", "email", "phone", "status")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="CareFlow.Treeview")

        headings = {
            "id":     ("ID",     50,  "center"),
            "name":   ("Name",   180, "w"),
            "role":   ("Role",   90,  "w"),
            "email":  ("Email",  200, "w"),
            "phone":  ("Phone",  100, "center"),
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

    # ------------------------------------------------------------ Form --
    def _build_form_section(self, parent):
        panel = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid", padx=16, pady=14)
        panel.grid(row=2, column=1, sticky="nsew", padx=(0, 10), pady=8)
        parent.grid_columnconfigure(1, minsize=290)

        tk.Label(panel, text="Staff Details", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self.entries = {}

        def _lbl_entry(row_idx, label, key):
            tk.Label(panel, text=label, bg=BG_PANEL, fg=TEXT,
                     font=("Helvetica", 9)).grid(
                row=row_idx, column=0, sticky="w", pady=3)
            e = tk.Entry(panel, width=22, bg=CARD_BG, fg=TEXT,
                         relief="flat", highlightthickness=1,
                         highlightbackground="#cde8dc",
                         highlightcolor=ACCENT)
            e.grid(row=row_idx, column=1, pady=3, padx=(8, 0), sticky="ew")
            self.entries[key] = e

        _lbl_entry(1, "First Name *",       "first_name")
        _lbl_entry(2, "Last Name *",        "last_name")
        _lbl_entry(3, "Email *",            "email")
        _lbl_entry(4, "Phone (###-####) *", "phone")

        # Role dropdown
        tk.Label(panel, text="Role *", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=5, column=0, sticky="w", pady=3)
        self.role_var = tk.StringVar()
        role_combo = ttk.Combobox(panel, textvariable=self.role_var,
                                   values=ROLES, state="readonly", font=FONT_SMALL, width=20)
        role_combo.grid(row=5, column=1, pady=3, padx=(8, 0), sticky="ew")
        role_combo.current(0)

        # Active checkbox
        tk.Label(panel, text="Active", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=6, column=0, sticky="w", pady=3)
        self.active_var = tk.IntVar(value=1)
        tk.Checkbutton(panel, variable=self.active_var,
                       bg=BG_PANEL, activebackground=BG_PANEL,
                       selectcolor=CARD_BG).grid(row=6, column=1, sticky="w", padx=(8, 0))

        # Clinic assignments listbox
        tk.Label(panel, text="Clinic Assignments", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=7, column=0, sticky="nw", pady=3)
        loc_frame = tk.Frame(panel, bg=BG_PANEL)
        loc_frame.grid(row=7, column=1, pady=3, padx=(8, 0), sticky="ew")
        self.loc_listbox = tk.Listbox(loc_frame, selectmode="multiple", height=4,
                                       exportselection=False, font=("Helvetica", 9),
                                       bd=0, relief="flat",
                                       highlightthickness=1,
                                       highlightbackground="#cde8dc",
                                       highlightcolor=ACCENT,
                                       bg=CARD_BG, fg=TEXT,
                                       selectbackground=ACCENT, selectforeground="white")
        loc_sb = ttk.Scrollbar(loc_frame, orient="vertical", command=self.loc_listbox.yview)
        self.loc_listbox.configure(yscrollcommand=loc_sb.set)
        self.loc_listbox.pack(side="left", fill="both", expand=True)
        loc_sb.pack(side="left", fill="y")
        tk.Label(panel, text="Ctrl+click for multiple", bg=BG_PANEL,
                 fg="gray", font=("Helvetica", 8)).grid(
            row=8, column=1, sticky="w", padx=(8, 0))

        # Password fields
        tk.Label(panel, text="Password *", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=9, column=0, sticky="w", pady=3)
        self.pw_entry = tk.Entry(panel, show="*", width=22, bg=CARD_BG, fg=TEXT,
                                  relief="flat", highlightthickness=1,
                                  highlightbackground="#cde8dc", highlightcolor=ACCENT)
        self.pw_entry.grid(row=9, column=1, pady=3, padx=(8, 0), sticky="ew")

        tk.Label(panel, text="Confirm Password *", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=10, column=0, sticky="w", pady=3)
        self.pw_confirm_entry = tk.Entry(panel, show="*", width=22, bg=CARD_BG, fg=TEXT,
                                          relief="flat", highlightthickness=1,
                                          highlightbackground="#cde8dc", highlightcolor=ACCENT)
        self.pw_confirm_entry.grid(row=10, column=1, pady=3, padx=(8, 0), sticky="ew")

        tk.Label(panel, text="Confirmation Code *", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9)).grid(row=11, column=0, sticky="w", pady=3)
        self.code_entry = tk.Entry(panel, show="*", width=22, bg=CARD_BG, fg=TEXT,
                                    relief="flat", highlightthickness=1,
                                    highlightbackground="#cde8dc", highlightcolor=ACCENT)
        self.code_entry.grid(row=11, column=1, pady=3, padx=(8, 0), sticky="ew")

        tk.Label(panel,
                 text="Leave password blank to keep existing.",
                 bg=BG_PANEL, fg="gray", font=("Helvetica", 8), justify="left"
                 ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(2, 0))

        panel.grid_columnconfigure(1, weight=1)

    # --------------------------------------------------------- Action bar --
    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=BG_LIGHT)
        bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 4))

        btn_cfg = dict(
            relief="flat", fg="white", padx=16, pady=8,
            font=("Helvetica", 10, "bold"),
            activeforeground="white", cursor="hand2"
        )

        tk.Button(bar, text="＋  Add",       bg=BTN_SAFE,    activebackground=TEXT,
                  command=self._do_add,                       **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="✎  Update",     bg=BTN_INFO,    activebackground="#1a5276",
                  command=self._do_update,                    **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="⏸  Deactivate", bg=BTN_WARN,    activebackground="#9a7d0a",
                  command=self._deactivate_selected,          **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="✕  Delete",     bg=BTN_DANGER,  activebackground="#922b21",
                  command=self._delete_selected,              **btn_cfg).pack(side="left", padx=(0, 6))
        tk.Button(bar, text="Clear",          bg=BTN_NEUTRAL, activebackground="#6c7a7d",
                  command=self._clear_form,                   **btn_cfg).pack(side="left")

        tk.Label(bar,
                 text="★ = required fields   |   Inactive staff shown in grey.",
                 bg=BG_LIGHT, fg="#5a8a76", font=("Helvetica", 9)).pack(side="right")

    # ============================================================ Data ==
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

    def _load_staff(self):
        self._all_rows = []
        try:
            conn = get_conn()
            rows = conn.execute(
                """SELECT s.staff_id, s.first_name, s.last_name, s.email, s.phone,
                          s.role, s.active_flag,
                          COALESCE(GROUP_CONCAT(cl.name, ', '), '') AS locations
                   FROM Staff s
                   LEFT JOIN StaffLocationAssignment sla
                          ON sla.staff_id = s.staff_id AND sla.end_date IS NULL
                   LEFT JOIN ClinicLocation cl ON cl.location_id = sla.location_id
                   GROUP BY s.staff_id
                   ORDER BY s.last_name, s.first_name"""
            ).fetchall()
            total  = conn.execute("SELECT COUNT(*) FROM Staff").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM Staff WHERE active_flag=1").fetchone()[0]
            conn.close()
            self._all_rows = rows
            self._total_var.set(str(total))
            self._active_var.set(str(active))
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not load staff.\n\n{e}")
        self._populate_table(self._all_rows)

    def _populate_table(self, rows):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            sid, fn, ln, email, phone, role, active, _ = row
            status = "Active" if active else "Inactive"
            tag    = "inactive" if not active else ""
            self.tree.insert("", "end", iid=str(sid),
                             values=(sid, f"{ln}, {fn}", role or "",
                                     email or "", phone or "", status),
                             tags=(tag,))

    def _filter_staff(self):
        term = self.search_var.get().lower()
        if not term:
            self._populate_table(self._all_rows)
            return
        filtered = [r for r in self._all_rows
                    if term in f"{r[1]} {r[2]}".lower()
                    or term in (r[3] or "").lower()
                    or term in (r[5] or "").lower()
                    or term in (r[7] or "").lower()]
        self._populate_table(filtered)

    # --------------------------------------------------------- Selection --
    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_staff_id = int(sel[0])
        self._load_form_for_edit(self._selected_staff_id)

    def _load_form_for_edit(self, staff_id):
        try:
            conn = get_conn()
            row = conn.execute(
                "SELECT first_name, last_name, email, phone, role, active_flag "
                "FROM Staff WHERE staff_id=?", (staff_id,)
            ).fetchone()
            assigned_ids = {r[0] for r in conn.execute(
                "SELECT location_id FROM StaffLocationAssignment "
                "WHERE staff_id=? AND end_date IS NULL", (staff_id,)
            ).fetchall()}
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
            return
        if not row:
            return
        fn, ln, email, phone, role, active = row
        self.entries["first_name"].delete(0, tk.END);  self.entries["first_name"].insert(0, fn or "")
        self.entries["last_name"].delete(0, tk.END);   self.entries["last_name"].insert(0, ln or "")
        self.entries["email"].delete(0, tk.END);       self.entries["email"].insert(0, email or "")
        self.entries["phone"].delete(0, tk.END);       self.entries["phone"].insert(0, phone or "")
        self.role_var.set(role if role in ROLES else ROLES[0])
        self.active_var.set(1 if active else 0)
        self.pw_entry.delete(0, tk.END)
        self.pw_confirm_entry.delete(0, tk.END)
        self.code_entry.delete(0, tk.END)
        self.loc_listbox.selection_clear(0, tk.END)
        for i, (_, loc_id) in enumerate(self.location_list):
            if loc_id in assigned_ids:
                self.loc_listbox.selection_set(i)

    # ======================================================== Form ops ==
    def _collect_form(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["role"]             = self.role_var.get().strip()
        data["active"]           = self.active_var.get()
        data["password"]         = self.pw_entry.get()
        data["confirm_password"] = self.pw_confirm_entry.get()
        data["code"]             = self.code_entry.get().strip()
        return data

    def _clear_form(self):
        for e in self.entries.values():
            e.delete(0, tk.END)
        self.role_var.set(ROLES[0])
        self.active_var.set(1)
        self.pw_entry.delete(0, tk.END)
        self.pw_confirm_entry.delete(0, tk.END)
        self.code_entry.delete(0, tk.END)
        self.loc_listbox.selection_clear(0, tk.END)
        self._selected_staff_id = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())

    # ======================================================== CRUD ==
    def _do_add(self):
        data = self._collect_form()
        if not self._validate_base(data):
            return
        if len(data["password"]) < 8:
            messagebox.showerror("Weak Password", "Password must be at least 8 characters.")
            return
        if data["password"] != data["confirm_password"]:
            messagebox.showerror("Password Mismatch", "Passwords do not match.")
            return
        if data["code"] != CONFIRMATION_CODE:
            messagebox.showerror("Invalid Code", "Invalid staff confirmation code.")
            return
        pw_hash = hash_password(data["password"])
        selected_locs = [self.location_list[i][1] for i in self.loc_listbox.curselection()]
        try:
            conn = get_conn()
            cur = conn.execute(
                "INSERT INTO Staff (first_name, last_name, email, phone, role, active_flag, password_hash) "
                "VALUES (?,?,?,?,?,?,?)",
                (data["first_name"], data["last_name"], data["email"], data["phone"],
                 data["role"], data["active"], pw_hash)
            )
            new_id = cur.lastrowid
            for loc_id in selected_locs:
                conn.execute(
                    "INSERT INTO StaffLocationAssignment "
                    "(staff_id, location_id, assignment_role, start_date) VALUES (?,?,?,date('now'))",
                    (new_id, loc_id, data["role"])
                )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not add staff.\n\n{e}")
            return
        messagebox.showinfo("Success",
                            f"Staff member {data['first_name']} {data['last_name']} added.")
        self._clear_form()
        self._load_staff()

    def _do_update(self):
        if not self._selected_staff_id:
            messagebox.showwarning("Select", "Please select a staff member first.")
            return
        data = self._collect_form()
        if not self._validate_base(data):
            return
        new_loc_ids = {self.location_list[i][1] for i in self.loc_listbox.curselection()}
        pw = data["password"]
        if pw or data["confirm_password"]:
            if len(pw) < 8:
                messagebox.showerror("Weak Password", "Password must be at least 8 characters.")
                return
            if pw != data["confirm_password"]:
                messagebox.showerror("Password Mismatch", "Passwords do not match.")
                return
            if data["code"] != CONFIRMATION_CODE:
                messagebox.showerror("Invalid Code", "Invalid staff confirmation code.")
                return
            pw_hash = hash_password(pw)
            sql    = ("UPDATE Staff SET first_name=?, last_name=?, email=?, phone=?, "
                      "role=?, active_flag=?, password_hash=? WHERE staff_id=?")
            params = (data["first_name"], data["last_name"], data["email"], data["phone"],
                      data["role"], data["active"], pw_hash, self._selected_staff_id)
        else:
            sql    = ("UPDATE Staff SET first_name=?, last_name=?, email=?, phone=?, "
                      "role=?, active_flag=? WHERE staff_id=?")
            params = (data["first_name"], data["last_name"], data["email"], data["phone"],
                      data["role"], data["active"], self._selected_staff_id)
        try:
            conn = get_conn()
            conn.execute(sql, params)
            current_locs = {r[0] for r in conn.execute(
                "SELECT location_id FROM StaffLocationAssignment "
                "WHERE staff_id=? AND end_date IS NULL", (self._selected_staff_id,)
            ).fetchall()}
            for loc_id in new_loc_ids - current_locs:
                conn.execute(
                    "INSERT INTO StaffLocationAssignment "
                    "(staff_id, location_id, assignment_role, start_date) VALUES (?,?,?,date('now'))",
                    (self._selected_staff_id, loc_id, data["role"])
                )
            for loc_id in current_locs - new_loc_ids:
                conn.execute(
                    "UPDATE StaffLocationAssignment SET end_date=date('now') "
                    "WHERE staff_id=? AND location_id=? AND end_date IS NULL",
                    (self._selected_staff_id, loc_id)
                )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not update staff.\n\n{e}")
            return
        messagebox.showinfo("Success", "Staff information updated.")
        self._clear_form()
        self._load_staff()

    def _deactivate_selected(self):
        if not self._selected_staff_id:
            messagebox.showwarning("Select", "Please select a staff member first.")
            return
        name = self._get_name(self._selected_staff_id)
        if not messagebox.askyesno("Confirm Deactivate",
                                   f"Deactivate {name}?\nThey will remain in the database but marked inactive."):
            return
        try:
            conn = get_conn()
            conn.execute("UPDATE Staff SET active_flag=0 WHERE staff_id=?",
                         (self._selected_staff_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not deactivate staff.\n\n{e}")
            return
        messagebox.showinfo("Deactivated", f"{name} has been deactivated.")
        self._clear_form()
        self._load_staff()

    def _delete_selected(self):
        if not self._selected_staff_id:
            messagebox.showwarning("Select", "Please select a staff member first.")
            return
        name = self._get_name(self._selected_staff_id)
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete {name}?\nThis cannot be undone."):
            return
        try:
            conn = get_conn()
            conn.execute("DELETE FROM StaffLocationAssignment WHERE staff_id=?",
                         (self._selected_staff_id,))
            conn.execute("DELETE FROM Staff WHERE staff_id=?",
                         (self._selected_staff_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not delete staff.\n\n{e}")
            return
        messagebox.showinfo("Deleted", f"{name} has been permanently deleted.")
        self._clear_form()
        self._load_staff()

    # ======================================================= Helpers ==
    def _get_name(self, staff_id):
        try:
            conn = get_conn()
            row = conn.execute(
                "SELECT first_name, last_name FROM Staff WHERE staff_id=?", (staff_id,)
            ).fetchone()
            conn.close()
            return f"{row[0]} {row[1]}" if row else f"ID {staff_id}"
        except sqlite3.Error:
            return f"ID {staff_id}"

    def _validate_base(self, data):
        required = ["first_name", "last_name", "email", "phone", "role"]
        missing  = [k for k in required if not data.get(k)]
        if missing:
            messagebox.showerror("Missing Fields",
                                 "Missing: " + ", ".join(m.replace("_", " ") for m in missing))
            return False
        if not is_valid_email(data["email"]):
            messagebox.showerror("Invalid Email", "Enter a valid email (e.g. alice@clinic.com).")
            return False
        if not is_valid_phone(data["phone"]):
            messagebox.showerror("Invalid Phone", "Phone must be ###-#### (e.g. 555-1234).")
            return False
        return True


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Staff Management")
    root.geometry("1200x720")
    root.configure(bg=BG_LIGHT)
    frame = StaffManagementFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()