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
BTN_RED          = "#e53935"
BTN_ORANGE       = "#FF9800"
FONT_TITLE       = ("Helvetica", 20, "bold")
FONT_HEADER      = ("Helvetica", 13, "bold")
FONT_TABLE       = ("Helvetica", 10)
FONT_SMALL       = ("Helvetica", 10)
FONT_MEDIUM      = ("Helvetica", 11)

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


class StaffManagementFrame(tk.Frame):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self.location_list = []
        self._all_rows = []
        self._selected_staff_id = None
        self._form_mode = "add"          # "add" or "edit"
        self._total_var  = tk.StringVar(value="0")
        self._active_var = tk.StringVar(value="0")
        self._form_title_var = tk.StringVar(value="Add Staff")
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
        tk.Button(header, text="+ Add Staff", font=FONT_MEDIUM,
                  bg=ACCENT, fg="white", relief="flat", padx=12, pady=6,
                  cursor="hand2", command=self._set_add_mode
                  ).pack(side="right", padx=14, pady=14)

        # -- White body: summary cards + split content --
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        # Summary cards + search
        top_row = tk.Frame(body, bg=BG_PANEL)
        top_row.pack(fill="x", padx=10, pady=(10, 6))
        for lbl, var in [("Total Staff", self._total_var), ("Active Staff", self._active_var)]:
            c = tk.Frame(top_row, bg=CARD_BG, bd=1, relief="raised", width=140, height=64)
            c.pack(side="left", padx=6)
            c.pack_propagate(False)
            tk.Label(c, textvariable=var, bg=CARD_BG, fg=TEXT,
                     font=("Helvetica", 15, "bold")).pack(anchor="nw", padx=10, pady=(6, 0))
            tk.Label(c, text=lbl, bg=CARD_BG, fg=TEXT,
                     font=FONT_SMALL).pack(anchor="nw", padx=10)

        sf = tk.Frame(top_row, bg=BG_PANEL)
        sf.pack(side="left", padx=18)
        tk.Label(sf, text="Search:", bg=BG_PANEL, fg=TEXT, font=FONT_SMALL).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_staff())
        tk.Entry(sf, textvariable=self.search_var, width=26,
                 font=FONT_SMALL).pack(side="left", padx=6)

        # Divider
        tk.Frame(body, bg="#e0e0e0", height=1).pack(fill="x", padx=10)

        # Split: table left | form right
        split = tk.Frame(body, bg=BG_PANEL)
        split.pack(fill="both", expand=True)

        self._build_table_section(split)
        self._build_form_section(split)

    # ---------------------------------------------------------- Sidebar --
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nAdmin Portal", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left", padx=8, pady=8).pack(anchor="w")

        nav_map = {
            "Dashboard": "HomePage",
            "Patient":   "PatientMenuPage",
            "Staff":     None,
            "Clinic":    "LocationMenuPage",
            "Records":   "MedicalRecordsPage",
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

        tk.Label(sidebar, text="Signed in as:\nAdmin", bg=BG_SIDEBAR, fg=TEXT,
                 font=("Helvetica", 9), justify="left"
                 ).pack(side="bottom", anchor="w", padx=10, pady=12)

    # ----------------------------------------------------------- Table --
    def _build_table_section(self, parent):
        left = tk.Frame(parent, bg=BG_PANEL)
        left.pack(side="left", fill="both", expand=True, padx=(10, 4), pady=10)

        # Column header
        col_defs = [("ID", 4), ("Name", 16), ("Role", 10), ("Email", 20),
                    ("Phone", 10), ("Status", 7), ("Actions", 18)]
        hdr = tk.Frame(left, bg="#d4ece3")
        hdr.pack(fill="x")
        for col, w in col_defs:
            tk.Label(hdr, text=col, bg="#d4ece3", fg=TEXT,
                     font=("Helvetica", 9, "bold"), width=w, anchor="w"
                     ).pack(side="left", padx=5, pady=5)

        # Scrollable rows
        scroll_body = tk.Frame(left, bg=BG_PANEL)
        scroll_body.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(scroll_body, bg=BG_PANEL, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_body, orient="vertical", command=self._canvas.yview)
        self._scrollable = tk.Frame(self._canvas, bg=BG_PANEL)
        self._scrollable.bind("<Configure>",
            lambda _: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.create_window((0, 0), window=self._scrollable, anchor="nw")
        self._canvas.configure(yscrollcommand=vsb.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self._canvas.bind_all("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ------------------------------------------------------------ Form --
    def _build_form_section(self, parent):
        """Inline form panel — always visible on the right."""
        right = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid", width=280)
        right.pack(side="right", fill="y", padx=(4, 10), pady=10)
        right.pack_propagate(False)

        # Form title bar
        title_bar = tk.Frame(right, bg=ACCENT)
        title_bar.pack(fill="x")
        tk.Label(title_bar, textvariable=self._form_title_var, bg=ACCENT, fg="white",
                 font=("Helvetica", 11, "bold"), padx=12, pady=10).pack(side="left")

        # Scrollable form body
        form_canvas = tk.Canvas(right, bg=CARD_BG, highlightthickness=0)
        form_sb = ttk.Scrollbar(right, orient="vertical", command=form_canvas.yview)
        form_inner = tk.Frame(form_canvas, bg=CARD_BG)
        form_inner.bind("<Configure>",
            lambda _: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.create_window((0, 0), window=form_inner, anchor="nw")
        form_canvas.configure(yscrollcommand=form_sb.set)
        form_canvas.pack(side="left", fill="both", expand=True)
        form_sb.pack(side="right", fill="y")

        def _lbl(text):
            tk.Label(form_inner, text=text, bg=CARD_BG, fg=TEXT,
                     font=("Helvetica", 8, "bold"), anchor="w"
                     ).pack(fill="x", padx=12, pady=(8, 1))

        def _entry(show=None):
            e = tk.Entry(form_inner, font=FONT_SMALL, bd=1, relief="solid",
                         bg="white", fg=TEXT, insertbackground=TEXT, show=show or "")
            e.pack(fill="x", padx=12, pady=(0, 2))
            return e

        self.entries = {}
        _lbl("First Name *");        self.entries["first_name"]  = _entry()
        _lbl("Last Name *");         self.entries["last_name"]   = _entry()
        _lbl("Email *");             self.entries["email"]       = _entry()
        _lbl("Phone (###-####) *");  self.entries["phone"]       = _entry()

        _lbl("Role *")
        self.role_var = tk.StringVar()
        role_combo = ttk.Combobox(form_inner, textvariable=self.role_var,
                                   values=ROLES, state="readonly", font=FONT_SMALL)
        role_combo.pack(fill="x", padx=12, pady=(0, 2))
        role_combo.current(0)

        _lbl("Active")
        self.active_var = tk.IntVar(value=1)
        tk.Checkbutton(form_inner, variable=self.active_var,
                       bg=CARD_BG, activebackground=CARD_BG).pack(anchor="w", padx=10)

        _lbl("Clinic Assignments")
        loc_frame = tk.Frame(form_inner, bg=CARD_BG)
        loc_frame.pack(fill="x", padx=12, pady=(0, 2))
        self.loc_listbox = tk.Listbox(loc_frame, selectmode="multiple", height=5,
                                       exportselection=False, font=("Helvetica", 9),
                                       bd=1, relief="solid", bg="white", fg=TEXT,
                                       selectbackground=ACCENT, selectforeground="white")
        loc_sb2 = ttk.Scrollbar(loc_frame, orient="vertical", command=self.loc_listbox.yview)
        self.loc_listbox.configure(yscrollcommand=loc_sb2.set)
        self.loc_listbox.pack(side="left", fill="both", expand=True)
        loc_sb2.pack(side="left", fill="y")
        tk.Label(form_inner, text="Ctrl+click for multiple", bg=CARD_BG,
                 fg="gray", font=("Helvetica", 8)).pack(anchor="w", padx=12)

        _lbl("Password *");          self.pw_entry           = _entry(show="*")
        _lbl("Confirm Password *");  self.pw_confirm_entry   = _entry(show="*")
        _lbl("Confirmation Code *"); self.code_entry         = _entry(show="*")

        tk.Label(form_inner, text="Leave password blank on Edit\nto keep existing.",
                 bg=CARD_BG, fg="gray", font=("Helvetica", 8), justify="left"
                 ).pack(anchor="w", padx=12, pady=(2, 6))

        # Buttons
        btn_frame = tk.Frame(form_inner, bg=CARD_BG)
        btn_frame.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btn_frame, text="Save", font=("Helvetica", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", padx=12, pady=6,
                  cursor="hand2", command=self._save_form
                  ).pack(side="left", padx=(0, 6))
        tk.Button(btn_frame, text="Clear", font=FONT_SMALL,
                  bg="#e0e0e0", fg=TEXT, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=self._set_add_mode
                  ).pack(side="left")

    # ============================================================ Data ==
    def _load_locations(self):
        try:
            conn = sqlite3.connect(DB_NAME)
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
            conn = sqlite3.connect(DB_NAME)
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
        for w in self._scrollable.winfo_children():
            w.destroy()
        for row in rows:
            sid, fn, ln, email, phone, role, active, _ = row
            self._build_table_row(self._scrollable, {
                "id": sid, "name": f"{fn} {ln}", "role": role or "",
                "email": email or "", "phone": phone or "",
                "status": "Active" if active else "Inactive",
            })
        if not rows:
            tk.Label(self._scrollable, text="No staff records found.",
                     bg=BG_PANEL, fg="gray", font=FONT_SMALL).pack(pady=20)

    def _build_table_row(self, parent, row):
        row_frame = tk.Frame(parent, bg=BG_PANEL, pady=4)
        row_frame.pack(fill="x", padx=4)
        tk.Frame(parent, bg="#e0e0e0", height=1).pack(fill="x")

        col_widths = [4, 16, 10, 20, 10, 7]
        col_keys   = ["id", "name", "role", "email", "phone", "status"]
        for key, width in zip(col_keys, col_widths):
            val = str(row.get(key, ""))
            fg  = (ACCENT if val == "Active" else BTN_RED) if key == "status" else TEXT
            tk.Label(row_frame, text=val, bg=BG_PANEL, fg=fg,
                     font=FONT_TABLE, width=width, anchor="w"
                     ).pack(side="left", padx=5)

        sid = row["id"]
        af  = tk.Frame(row_frame, bg=BG_PANEL)
        af.pack(side="left", padx=4)
        tk.Button(af, text="Edit", font=("Helvetica", 9), bg=ACCENT, fg="white",
                  relief="flat", padx=5, cursor="hand2",
                  command=lambda i=sid: self._load_form_for_edit(i)
                  ).pack(side="left", padx=2)
        tk.Button(af, text="Deactivate", font=("Helvetica", 9), bg=BTN_ORANGE, fg="white",
                  relief="flat", padx=5, cursor="hand2",
                  command=lambda i=sid: self._deactivate_staff(i)
                  ).pack(side="left", padx=2)
        tk.Button(af, text="Delete", font=("Helvetica", 9), bg=BTN_RED, fg="white",
                  relief="flat", padx=5, cursor="hand2",
                  command=lambda i=sid: self._delete_staff(i)
                  ).pack(side="left", padx=2)

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

    # ======================================================== Form ops ==
    def _set_add_mode(self):
        self._form_mode = "add"
        self._selected_staff_id = None
        self._form_title_var.set("Add Staff")
        for e in self.entries.values():
            e.delete(0, tk.END)
        self.role_var.set(ROLES[0])
        self.active_var.set(1)
        self.pw_entry.delete(0, tk.END)
        self.pw_confirm_entry.delete(0, tk.END)
        self.code_entry.delete(0, tk.END)
        self.loc_listbox.selection_clear(0, tk.END)

    def _load_form_for_edit(self, staff_id):
        try:
            conn = sqlite3.connect(DB_NAME)
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
        self._form_mode = "edit"
        self._selected_staff_id = staff_id
        self._form_title_var.set(f"Edit — {fn} {ln}")
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

    def _collect_form(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["role"]             = self.role_var.get().strip()
        data["active"]           = self.active_var.get()
        data["password"]         = self.pw_entry.get()
        data["confirm_password"] = self.pw_confirm_entry.get()
        data["code"]             = self.code_entry.get().strip()
        return data

    def _save_form(self):
        if self._form_mode == "add":
            self._do_add()
        else:
            self._do_update()

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
            conn = sqlite3.connect(DB_NAME)
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
        self._set_add_mode()
        self._load_staff()

    def _do_update(self):
        if not self._selected_staff_id:
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
            conn = sqlite3.connect(DB_NAME)
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
        self._set_add_mode()
        self._load_staff()

    def _deactivate_staff(self, staff_id):
        name = self._get_name(staff_id)
        if not messagebox.askyesno("Confirm Deactivate",
                                   f"Deactivate {name}? They will remain in the database but marked inactive."):
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE Staff SET active_flag=0 WHERE staff_id=?", (staff_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not deactivate staff.\n\n{e}")
            return
        messagebox.showinfo("Deactivated", f"{name} has been deactivated.")
        self._load_staff()

    def _delete_staff(self, staff_id):
        name = self._get_name(staff_id)
        if not messagebox.askyesno("Confirm Delete",
                                   f"Permanently delete {name}? This cannot be undone."):
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM StaffLocationAssignment WHERE staff_id=?", (staff_id,))
            conn.execute("DELETE FROM Staff WHERE staff_id=?", (staff_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not delete staff.\n\n{e}")
            return
        messagebox.showinfo("Deleted", f"{name} has been permanently deleted.")
        if self._selected_staff_id == staff_id:
            self._set_add_mode()
        self._load_staff()

    # ======================================================= Helpers ==
    def _get_name(self, staff_id):
        try:
            conn = sqlite3.connect(DB_NAME)
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
