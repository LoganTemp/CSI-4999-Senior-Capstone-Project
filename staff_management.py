import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import hashlib

DB_NAME = "healthcare.db"

# ---------- Dashboard color palette ----------
BG_LIGHT        = "#e6f2ec"
BG_SIDEBAR      = "#5FAF90"
BG_SIDEBAR_LIGHT= "#A2DDC6"
BG_PANEL        = "#ffffff"
CARD_BG         = "#f7fff7"
ACCENT          = "#308684"
TEXT            = "#0b3d2e"
BTN_RED         = "#e53935"
BTN_ORANGE      = "#FF9800"
FONT_TITLE      = ("Helvetica", 20, "bold")
FONT_HEADER     = ("Helvetica", 14, "bold")
FONT_TABLE      = ("Helvetica", 10)
FONT_SMALL      = ("Helvetica", 10)
FONT_MEDIUM     = ("Helvetica", 12)

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
        self.location_list = []        # list of (label, location_id)
        self._all_rows = []            # cached DB rows
        self._total_var = tk.StringVar(value="0")
        self._active_var = tk.StringVar(value="0")
        self._build_ui()
        self._load_locations()
        self._load_staff()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        # ---- Outer layout: sidebar left, main right ----
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer)

        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # ---- White header panel ----
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x", padx=12, pady=(12, 0))

        tk.Label(header, text="Staff Management", font=FONT_TITLE,
                 bg=BG_PANEL, fg=TEXT).pack(side="left", padx=14, pady=14)

        tk.Button(
            header, text="+ Add Staff", font=FONT_MEDIUM,
            bg=ACCENT, fg="white", relief="flat", padx=12, pady=6,
            command=self._open_add_dialog
        ).pack(side="right", padx=14, pady=14)

        # ---- White body area ----
        body_outer = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body_outer.pack(fill="both", expand=True, padx=12, pady=(10, 12))

        # Cards + search row
        top_row = tk.Frame(body_outer, bg=BG_PANEL)
        top_row.pack(fill="x", padx=10, pady=(10, 6))

        for label_text, var in [("Total Staff", self._total_var), ("Active Staff", self._active_var)]:
            card = tk.Frame(top_row, bg=CARD_BG, bd=1, relief="raised", width=150, height=70)
            card.pack(side="left", padx=8)
            card.pack_propagate(False)
            tk.Label(card, textvariable=var, bg=CARD_BG, fg=TEXT,
                     font=("Helvetica", 16, "bold")).pack(anchor="nw", padx=10, pady=(8, 0))
            tk.Label(card, text=label_text, bg=CARD_BG, fg=TEXT,
                     font=FONT_SMALL).pack(anchor="nw", padx=10)

        search_frame = tk.Frame(top_row, bg=BG_PANEL)
        search_frame.pack(side="left", padx=20)
        tk.Label(search_frame, text="Search:", bg=BG_PANEL, fg=TEXT, font=FONT_SMALL).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_staff())
        tk.Entry(search_frame, textvariable=self.search_var, width=28,
                 font=FONT_SMALL).pack(side="left", padx=6)

        # Table inside body
        table_container = tk.Frame(body_outer, bg=BG_PANEL)
        table_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        col_defs = [
            ("ID", 5), ("Name", 20), ("Role", 12), ("Email", 24),
            ("Phone", 12), ("Status", 8), ("Actions", 22),
        ]
        hdr_frame = tk.Frame(table_container, bg="#d4ece3")
        hdr_frame.pack(fill="x")
        for col, width in col_defs:
            tk.Label(hdr_frame, text=col, bg="#d4ece3", fg=TEXT,
                     font=("Helvetica", 10, "bold"), width=width, anchor="w"
                     ).pack(side="left", padx=6, pady=6)

        scroll_body = tk.Frame(table_container, bg=BG_PANEL)
        scroll_body.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(scroll_body, bg=BG_PANEL, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_body, orient="vertical", command=self._canvas.yview)
        self._scrollable = tk.Frame(self._canvas, bg=BG_PANEL)

        self._scrollable.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        )
        self._canvas.create_window((0, 0), window=self._scrollable, anchor="nw")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._canvas.bind_all("<MouseWheel>", lambda e: self._canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo box
        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nAdmin Portal", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left", padx=8, pady=8).pack(anchor="w")

        # Nav items — Staff is the active page
        nav_map = {
            "Dashboard": "HomePage",
            "Patient":   "PatientMenuPage",
            "Staff":     None,              # current page
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
                btn = tk.Button(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_SMALL,
                                anchor="w", padx=10, pady=6, relief="flat",
                                activebackground=BG_SIDEBAR_LIGHT, cursor="hand2",
                                command=cmd)
            else:
                btn = tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_SMALL,
                               anchor="w", padx=10, pady=6)
            btn.pack(fill="x", padx=10, pady=2)

        # Signed-in label at bottom
        tk.Label(sidebar, text="Signed in as:\nAdmin", bg=BG_SIDEBAR, fg=TEXT,
                 font=("Helvetica", 9), justify="left"
                 ).pack(side="bottom", anchor="w", padx=10, pady=12)

    # --------------------------------------------------------- Data loading --
    def _load_locations(self):
        try:
            conn = sqlite3.connect(DB_NAME)
            rows = conn.execute(
                "SELECT location_id, name, status FROM ClinicLocation ORDER BY name"
            ).fetchall()
            conn.close()
            self.location_list.clear()
            for loc_id, name, status in rows:
                label = f"{name}  (ID {loc_id})" + (f" [{status}]" if status else "")
                self.location_list.append((label, loc_id))
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def _load_staff(self):
        self._all_rows = []
        try:
            conn = sqlite3.connect(DB_NAME)
            rows = conn.execute(
                """SELECT s.staff_id, s.first_name, s.last_name, s.email, s.phone, s.role, s.active_flag,
                          COALESCE(GROUP_CONCAT(cl.name, ', '), '') AS locations
                   FROM Staff s
                   LEFT JOIN StaffLocationAssignment sla ON sla.staff_id = s.staff_id AND sla.end_date IS NULL
                   LEFT JOIN ClinicLocation cl ON cl.location_id = sla.location_id
                   GROUP BY s.staff_id
                   ORDER BY s.last_name, s.first_name"""
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM Staff").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM Staff WHERE active_flag=1").fetchone()[0]
            conn.close()
            self._all_rows = rows
            self._total_var.set(str(total))
            self._active_var.set(str(active))
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not load staff.\n\n{e}")
        self._populate_table(self._all_rows)

    def _populate_table(self, rows):
        for widget in self._scrollable.winfo_children():
            widget.destroy()
        for row in rows:
            sid, fn, ln, email, phone, role, active, locations = row
            self._build_table_row(self._scrollable, {
                "id": sid,
                "name": f"{fn} {ln}",
                "role": role or "",
                "email": email or "",
                "phone": phone or "",
                "status": "Active" if active else "Inactive",
            })
        if not rows:
            tk.Label(self._scrollable, text="No staff records found.",
                     bg=BG_PANEL, fg="gray", font=FONT_SMALL
                     ).pack(pady=20)

    def _build_table_row(self, parent, row):
        bg = BG_PANEL
        row_frame = tk.Frame(parent, bg=bg, pady=4)
        row_frame.pack(fill="x", padx=4)
        # Separator line
        tk.Frame(parent, bg="#e0e0e0", height=1).pack(fill="x")

        col_widths = [5, 20, 12, 24, 12, 8]
        col_keys = ["id", "name", "role", "email", "phone", "status"]
        for key, width in zip(col_keys, col_widths):
            val = str(row.get(key, ""))
            fg = TEXT
            if key == "status":
                fg = ACCENT if val == "Active" else "#e53935"
            tk.Label(row_frame, text=val, bg=bg, fg=fg,
                     font=FONT_TABLE, width=width, anchor="w"
                     ).pack(side="left", padx=6)

        # Action buttons
        action_frame = tk.Frame(row_frame, bg=bg)
        action_frame.pack(side="left", padx=6)
        sid = row["id"]
        tk.Button(
            action_frame, text="Edit", font=FONT_SMALL,
            bg=ACCENT, fg="white", relief="flat", padx=6,
            command=lambda i=sid: self._open_edit_dialog(i)
        ).pack(side="left", padx=2)
        tk.Button(
            action_frame, text="Deactivate", font=FONT_SMALL,
            bg=BTN_ORANGE, fg="white", relief="flat", padx=6,
            command=lambda i=sid: self._deactivate_staff(i)
        ).pack(side="left", padx=2)
        tk.Button(
            action_frame, text="Delete", font=FONT_SMALL,
            bg=BTN_RED, fg="white", relief="flat", padx=6,
            command=lambda i=sid: self._delete_staff(i)
        ).pack(side="left", padx=2)

    def _filter_staff(self):
        term = self.search_var.get().lower()
        if not term:
            self._populate_table(self._all_rows)
            return
        filtered = [
            r for r in self._all_rows
            if term in f"{r[1]} {r[2]}".lower()
            or term in (r[3] or "").lower()
            or term in (r[5] or "").lower()
            or term in (r[7] or "").lower()
        ]
        self._populate_table(filtered)

    # ----------------------------------------------------------- Dialogs --
    def _make_dialog(self, title):
        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.configure(bg=BG_LIGHT)
        dlg.grab_set()
        dlg.resizable(False, False)

        # Colored header bar
        hdr = tk.Frame(dlg, bg=ACCENT)
        hdr.pack(fill="x")
        tk.Label(hdr, text=title, bg=ACCENT, fg="white",
                 font=("Helvetica", 14, "bold"), padx=20, pady=14).pack(side="left")

        return dlg

    def _field(self, parent, label, row, col=0, show=None, width=22):
        """Helper: renders a label + styled entry, returns the Entry widget."""
        tk.Label(parent, text=label, bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9, "bold"), anchor="w"
                 ).grid(row=row * 2, column=col, sticky="w", padx=16, pady=(10, 2))
        e = tk.Entry(parent, width=width, font=FONT_SMALL, bd=1, relief="solid",
                     bg="white", fg=TEXT, insertbackground=TEXT, show=show or "")
        e.grid(row=row * 2 + 1, column=col, sticky="ew", padx=16, pady=(0, 4))
        return e

    def _build_form_fields(self, dlg):
        """Build the shared form fields inside a dialog."""
        # White card body
        card = tk.Frame(dlg, bg=BG_PANEL, padx=4, pady=4)
        card.pack(fill="both", expand=True, padx=16, pady=(16, 8))
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)

        # ---- Left column: personal info ----
        entries = {}
        left_fields = [
            ("First Name *",        "first_name"),
            ("Last Name *",         "last_name"),
            ("Email *",             "email"),
            ("Phone (###-####) *",  "phone"),
        ]
        for i, (lbl, key) in enumerate(left_fields):
            entries[key] = self._field(card, lbl, i, col=0)

        # Role
        tk.Label(card, text="Role *", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9, "bold"), anchor="w"
                 ).grid(row=8, column=0, sticky="w", padx=16, pady=(10, 2))
        role_var = tk.StringVar()
        role_combo = ttk.Combobox(card, textvariable=role_var, values=ROLES, width=20, state="readonly")
        role_combo.grid(row=9, column=0, sticky="ew", padx=16, pady=(0, 4))
        role_combo.current(0)

        # Active checkbox
        tk.Label(card, text="Active", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9, "bold"), anchor="w"
                 ).grid(row=10, column=0, sticky="w", padx=16, pady=(10, 2))
        active_var = tk.IntVar(value=1)
        tk.Checkbutton(card, variable=active_var, bg=BG_PANEL,
                       activebackground=BG_PANEL
                       ).grid(row=11, column=0, sticky="w", padx=14)

        # ---- Right column: clinic + security ----
        tk.Label(card, text="Clinic Assignments", bg=BG_PANEL, fg=TEXT,
                 font=("Helvetica", 9, "bold"), anchor="w"
                 ).grid(row=0, column=1, sticky="w", padx=16, pady=(10, 2))
        loc_outer = tk.Frame(card, bg=BG_PANEL)
        loc_outer.grid(row=1, column=1, rowspan=5, sticky="nsew", padx=16, pady=(0, 4))
        loc_listbox = tk.Listbox(loc_outer, selectmode="multiple", height=7, width=28,
                                  exportselection=False, font=FONT_SMALL,
                                  bd=1, relief="solid", bg="white", fg=TEXT,
                                  selectbackground=ACCENT, selectforeground="white")
        loc_sb = ttk.Scrollbar(loc_outer, orient="vertical", command=loc_listbox.yview)
        loc_listbox.configure(yscrollcommand=loc_sb.set)
        loc_listbox.pack(side="left", fill="both", expand=True)
        loc_sb.pack(side="left", fill="y")
        for label, _ in self.location_list:
            loc_listbox.insert(tk.END, label)
        tk.Label(card, text="Ctrl+click to select multiple", bg=BG_PANEL, fg="gray",
                 font=("Helvetica", 8)
                 ).grid(row=6, column=1, sticky="w", padx=16)

        pw_entry         = self._field(card, "Password *",         4, col=1, show="*")
        pw_confirm_entry = self._field(card, "Confirm Password *", 5, col=1, show="*")
        code_entry       = self._field(card, "Confirmation Code *",6, col=1, show="*")

        tk.Label(card, text="Leave password blank on Edit to keep existing.",
                 bg=BG_PANEL, fg="gray", font=("Helvetica", 8)
                 ).grid(row=14, column=1, sticky="w", padx=16, pady=(0, 8))

        return card, entries, role_var, active_var, loc_listbox, pw_entry, pw_confirm_entry, code_entry

    def _dialog_footer(self, dlg, primary_text, primary_cmd):
        """Renders a styled footer bar with a primary action button and Cancel."""
        footer = tk.Frame(dlg, bg="#f0f0f0", bd=0)
        footer.pack(fill="x", padx=0, pady=0, side="bottom")
        tk.Frame(footer, bg="#d0d0d0", height=1).pack(fill="x")
        btn_row = tk.Frame(footer, bg="#f0f0f0")
        btn_row.pack(anchor="e", padx=16, pady=10)
        tk.Button(btn_row, text="Cancel", font=FONT_SMALL, bg="#e0e0e0", fg=TEXT,
                  relief="flat", padx=14, pady=7, cursor="hand2",
                  command=dlg.destroy).pack(side="left", padx=(0, 8))
        tk.Button(btn_row, text=primary_text, font=("Helvetica", 10, "bold"),
                  bg=ACCENT, fg="white", relief="flat", padx=14, pady=7, cursor="hand2",
                  command=primary_cmd).pack(side="left")

    def _open_add_dialog(self):
        dlg = self._make_dialog("Add Staff Member")
        _, entries, role_var, active_var, loc_listbox, pw_entry, pw_confirm_entry, code_entry = \
            self._build_form_fields(dlg)

        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            data["role"] = role_var.get().strip()
            data["active"] = active_var.get()
            data["password"] = pw_entry.get()
            data["confirm_password"] = pw_confirm_entry.get()
            data["code"] = code_entry.get().strip()
            if not self._validate_base(data):
                return
            if len(data["password"]) < 8:
                messagebox.showerror("Weak Password", "Password must be at least 8 characters.", parent=dlg)
                return
            if data["password"] != data["confirm_password"]:
                messagebox.showerror("Password Mismatch", "Passwords do not match.", parent=dlg)
                return
            if data["code"] != CONFIRMATION_CODE:
                messagebox.showerror("Invalid Code", "Invalid staff confirmation code.", parent=dlg)
                return
            pw_hash = hash_password(data["password"])
            selected_locs = [self.location_list[i][1] for i in loc_listbox.curselection()]
            try:
                conn = sqlite3.connect(DB_NAME)
                cur = conn.execute(
                    "INSERT INTO Staff (first_name, last_name, email, phone, role, active_flag, password_hash) VALUES (?,?,?,?,?,?,?)",
                    (data["first_name"], data["last_name"], data["email"], data["phone"],
                     data["role"], data["active"], pw_hash)
                )
                new_id = cur.lastrowid
                for loc_id in selected_locs:
                    conn.execute(
                        "INSERT INTO StaffLocationAssignment (staff_id, location_id, assignment_role, start_date) VALUES (?,?,?,date('now'))",
                        (new_id, loc_id, data["role"])
                    )
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not add staff.\n\n{e}", parent=dlg)
                return
            messagebox.showinfo("Success", f"Staff member {data['first_name']} {data['last_name']} added.", parent=dlg)
            dlg.destroy()
            self._load_staff()

        self._dialog_footer(dlg, "Add Staff", save)

    def _open_edit_dialog(self, staff_id):
        try:
            conn = sqlite3.connect(DB_NAME)
            row = conn.execute(
                "SELECT first_name, last_name, email, phone, role, active_flag FROM Staff WHERE staff_id=?",
                (staff_id,)
            ).fetchone()
            assigned_ids = {r[0] for r in conn.execute(
                "SELECT location_id FROM StaffLocationAssignment WHERE staff_id=? AND end_date IS NULL",
                (staff_id,)
            ).fetchall()}
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
            return
        if not row:
            return

        fn, ln, email, phone, role, active = row
        dlg = self._make_dialog(f"Edit Staff — {fn} {ln}")
        _, entries, role_var, active_var, loc_listbox, pw_entry, pw_confirm_entry, code_entry = \
            self._build_form_fields(dlg)

        # Pre-populate fields
        entries["first_name"].insert(0, fn or "")
        entries["last_name"].insert(0, ln or "")
        entries["email"].insert(0, email or "")
        entries["phone"].insert(0, phone or "")
        if role in ROLES:
            role_var.set(role)
        active_var.set(1 if active else 0)
        for i, (_, loc_id) in enumerate(self.location_list):
            if loc_id in assigned_ids:
                loc_listbox.selection_set(i)

        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            data["role"] = role_var.get().strip()
            data["active"] = active_var.get()
            data["password"] = pw_entry.get()
            data["confirm_password"] = pw_confirm_entry.get()
            data["code"] = code_entry.get().strip()
            if not self._validate_base(data):
                return
            new_loc_ids = set(self.location_list[i][1] for i in loc_listbox.curselection())
            pw = data["password"]
            if pw or data["confirm_password"]:
                if len(pw) < 8:
                    messagebox.showerror("Weak Password", "Password must be at least 8 characters.", parent=dlg)
                    return
                if pw != data["confirm_password"]:
                    messagebox.showerror("Password Mismatch", "Passwords do not match.", parent=dlg)
                    return
                if data["code"] != CONFIRMATION_CODE:
                    messagebox.showerror("Invalid Code", "Invalid staff confirmation code.", parent=dlg)
                    return
                pw_hash = hash_password(pw)
                sql = "UPDATE Staff SET first_name=?, last_name=?, email=?, phone=?, role=?, active_flag=?, password_hash=? WHERE staff_id=?"
                params = (data["first_name"], data["last_name"], data["email"], data["phone"],
                          data["role"], data["active"], pw_hash, staff_id)
            else:
                sql = "UPDATE Staff SET first_name=?, last_name=?, email=?, phone=?, role=?, active_flag=? WHERE staff_id=?"
                params = (data["first_name"], data["last_name"], data["email"], data["phone"],
                          data["role"], data["active"], staff_id)
            try:
                conn = sqlite3.connect(DB_NAME)
                conn.execute(sql, params)
                current_locs = {r[0] for r in conn.execute(
                    "SELECT location_id FROM StaffLocationAssignment WHERE staff_id=? AND end_date IS NULL",
                    (staff_id,)
                ).fetchall()}
                for loc_id in new_loc_ids - current_locs:
                    conn.execute(
                        "INSERT INTO StaffLocationAssignment (staff_id, location_id, assignment_role, start_date) VALUES (?,?,?,date('now'))",
                        (staff_id, loc_id, data["role"])
                    )
                for loc_id in current_locs - new_loc_ids:
                    conn.execute(
                        "UPDATE StaffLocationAssignment SET end_date=date('now') WHERE staff_id=? AND location_id=? AND end_date IS NULL",
                        (staff_id, loc_id)
                    )
                conn.commit()
                conn.close()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not update staff.\n\n{e}", parent=dlg)
                return
            messagebox.showinfo("Success", "Staff information updated.", parent=dlg)
            dlg.destroy()
            self._load_staff()

        self._dialog_footer(dlg, "Save Changes", save)

    # --------------------------------------------------------- CRUD actions --
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
        self._load_staff()

    # ------------------------------------------------------------ Helpers --
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
        missing = [k for k in required if not data.get(k)]
        if missing:
            messagebox.showerror("Missing Fields", "Missing: " + ", ".join(m.replace("_", " ") for m in missing))
            return False
        if not is_valid_email(data["email"]):
            messagebox.showerror("Invalid Email", "Enter a valid email (e.g. alice@clinic.com).")
            return False
        if not is_valid_phone(data["phone"]):
            messagebox.showerror("Invalid Phone", "Phone must be ###-#### (e.g. 555-1234).")
            return False
        return True
