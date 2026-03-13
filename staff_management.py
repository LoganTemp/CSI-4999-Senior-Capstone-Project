import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import hashlib

DB_NAME = "healthcare.db"

BG_COLOR = "#dddede"
FG_COLOR = "#222"
BTN_GREEN = "#4CAF50"
BTN_BLUE = "#2196F3"
BTN_GRAY = "#e0e0e0"
BTN_RED = "#e53935"
CONTAINER_COLOR = "#f2efef"
FONT_LARGE = ("Arial", 16, "bold")
FONT_MEDIUM = ("Arial", 12)
FONT_SMALL = ("Arial", 11)

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
    def __init__(self, parent=None):
        super().__init__(parent, bg=BG_COLOR)
        self.location_map = {}  # display label -> location_id
        # Add location_id column to Staff if not already present
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("ALTER TABLE Staff ADD COLUMN location_id INTEGER")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass  # column already exists
        self._build_ui()
        self._load_locations()
        self._load_staff()

    # ------------------------------------------------------------------ UI --
    def _build_ui(self):
        # ---- Left panel: staff list ----
        left = tk.Frame(self, bg=BG_COLOR)
        left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)

        tk.Label(left, text="Staff Members", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack(anchor="w")

        search_row = tk.Frame(left, bg=BG_COLOR)
        search_row.pack(fill="x", pady=(4, 6))

        tk.Label(search_row, text="Search:", font=FONT_SMALL, bg=BG_COLOR).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_staff())
        tk.Entry(search_row, textvariable=self.search_var, width=22).pack(side="left", padx=6)

        cols = ("ID", "Name", "Role", "Email", "Phone", "Active", "Location")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=16)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Name", width=130)
        self.tree.column("Role", width=70)
        self.tree.column("Email", width=140)
        self.tree.column("Phone", width=75)
        self.tree.column("Active", width=50, anchor="center")
        self.tree.column("Location", width=120)

        vsb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---- Right panel: form ----
        right = tk.Frame(self, bg=CONTAINER_COLOR, padx=16, pady=16)
        right.pack(side="left", fill="y", padx=(5, 10), pady=10)

        tk.Label(right, text="Staff Details", font=FONT_LARGE, bg=CONTAINER_COLOR, fg=FG_COLOR).grid(
            row=0, column=0, columnspan=2, pady=(0, 12), sticky="w"
        )

        self.entries = {}
        fields = [
            ("First Name *", "first_name"),
            ("Last Name *", "last_name"),
            ("Email *", "email"),
            ("Phone (###-####) *", "phone"),
        ]
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(right, text=label, bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
                row=i, column=0, sticky="w", pady=4
            )
            e = tk.Entry(right, width=26)
            e.grid(row=i, column=1, padx=8, pady=4)
            self.entries[key] = e

        # Role dropdown
        r = len(fields) + 1
        tk.Label(right, text="Role *", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", pady=4
        )
        self.role_var = tk.StringVar()
        self.role_combo = ttk.Combobox(right, textvariable=self.role_var, values=ROLES, width=24, state="readonly")
        self.role_combo.grid(row=r, column=1, padx=8, pady=4)
        self.role_combo.current(0)
        r += 1

        # Active flag
        tk.Label(right, text="Active", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", pady=4
        )
        self.active_var = tk.IntVar(value=1)
        tk.Checkbutton(right, variable=self.active_var, bg=CONTAINER_COLOR).grid(row=r, column=1, sticky="w", padx=8)
        r += 1

        # Clinic location (mirrors billing pattern)
        tk.Label(right, text="Clinic Location", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", pady=4
        )
        self.loc_var = tk.StringVar()
        self.loc_combo = ttk.Combobox(right, textvariable=self.loc_var, state="readonly", width=26)
        self.loc_combo.grid(row=r, column=1, padx=8, pady=4)
        r += 1

        # Password fields (only required for Add)
        tk.Label(right, text="Password *", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", pady=4
        )
        self.pw_entry = tk.Entry(right, width=26, show="*")
        self.pw_entry.grid(row=r, column=1, padx=8, pady=4)
        r += 1

        tk.Label(right, text="Confirm Password *", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", pady=4
        )
        self.pw_confirm_entry = tk.Entry(right, width=26, show="*")
        self.pw_confirm_entry.grid(row=r, column=1, padx=8, pady=4)
        r += 1

        tk.Label(right, text="Confirm Code *", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", pady=4
        )
        self.code_entry = tk.Entry(right, width=26, show="*")
        self.code_entry.grid(row=r, column=1, padx=8, pady=4)
        r += 1

        self.pw_note = tk.Label(
            right,
            text="(Password fields required for Add only;\nleave blank on Update to keep existing)",
            bg=CONTAINER_COLOR, fg="gray", font=("Arial", 9), justify="left"
        )
        self.pw_note.grid(row=r, column=0, columnspan=2, sticky="w", pady=(0, 8))
        r += 1

        # Action buttons
        btn_frame = tk.Frame(right, bg=CONTAINER_COLOR)
        btn_frame.grid(row=r, column=0, columnspan=2, pady=(8, 0))

        tk.Button(
            btn_frame, text="Add Staff",
            font=FONT_SMALL, bg=BTN_GREEN, fg="white",
            width=13, height=2, relief="flat",
            command=self._add_staff
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="Update Staff",
            font=FONT_SMALL, bg=BTN_BLUE, fg="white",
            width=13, height=2, relief="flat",
            command=self._update_staff
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="Deactivate Staff",
            font=FONT_SMALL, bg="#FF9800", fg="white",
            width=13, height=2, relief="flat",
            command=self._remove_staff
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="Delete Staff",
            font=FONT_SMALL, bg=BTN_RED, fg="white",
            width=13, height=2, relief="flat",
            command=self._delete_staff
        ).pack(side="left", padx=4)

        tk.Button(
            btn_frame, text="Clear Form",
            font=FONT_SMALL, bg=BTN_GRAY, fg="#222",
            width=10, height=2, relief="flat",
            command=self._clear_form
        ).pack(side="left", padx=4)

        # Status bar
        self.status_var = tk.StringVar(value="Select a staff member or fill in the form to add.")
        tk.Label(right, textvariable=self.status_var, bg=CONTAINER_COLOR, fg="gray",
                 font=("Arial", 9), wraplength=340, justify="left").grid(
            row=r + 1, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

        self._selected_staff_id = None

    # --------------------------------------------------------- Data loading --
    def _load_locations(self):
        try:
            conn = sqlite3.connect(DB_NAME)
            rows = conn.execute(
                "SELECT location_id, name, status FROM ClinicLocation ORDER BY name"
            ).fetchall()
            conn.close()
            self.location_map.clear()
            display = []
            for loc_id, name, status in rows:
                label = f"{name}  (ID {loc_id})" + (f" [{status}]" if status else "")
                self.location_map[label] = loc_id
                display.append(label)
            self.loc_combo["values"] = display
            if display:
                self.loc_combo.current(0)
            else:
                self.loc_combo.set("No locations found")
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def _load_staff(self):
        self._all_rows = []
        try:
            conn = sqlite3.connect(DB_NAME)
            rows = conn.execute(
                """SELECT s.staff_id, s.first_name, s.last_name, s.email, s.phone, s.role, s.active_flag,
                          COALESCE(cl.name, '') AS location_name
                   FROM Staff s
                   LEFT JOIN ClinicLocation cl ON cl.location_id = s.location_id
                   ORDER BY s.last_name, s.first_name"""
            ).fetchall()
            conn.close()
            self._all_rows = rows
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not load staff.\n\n{e}")
        self._populate_tree(self._all_rows)

    def _populate_tree(self, rows):
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            sid, fn, ln, email, phone, role, active, loc_name = row
            self.tree.insert("", "end", iid=str(sid), values=(
                sid, f"{fn} {ln}", role, email or "", phone or "",
                "Yes" if active else "No", loc_name
            ))

    def _filter_staff(self):
        term = self.search_var.get().lower()
        if not term:
            self._populate_tree(self._all_rows)
            return
        filtered = [
            r for r in self._all_rows
            if term in f"{r[1]} {r[2]}".lower()
            or term in (r[3] or "").lower()
            or term in (r[5] or "").lower()
            or term in (r[7] or "").lower()
        ]
        self._populate_tree(filtered)

    def _on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        staff_id = int(sel[0])
        self._selected_staff_id = staff_id
        try:
            conn = sqlite3.connect(DB_NAME)
            row = conn.execute(
                "SELECT first_name, last_name, email, phone, role, active_flag, location_id FROM Staff WHERE staff_id=?",
                (staff_id,)
            ).fetchone()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
            return
        if not row:
            return
        fn, ln, email, phone, role, active, loc_id = row
        self.entries["first_name"].delete(0, tk.END); self.entries["first_name"].insert(0, fn or "")
        self.entries["last_name"].delete(0, tk.END);  self.entries["last_name"].insert(0, ln or "")
        self.entries["email"].delete(0, tk.END);      self.entries["email"].insert(0, email or "")
        self.entries["phone"].delete(0, tk.END);      self.entries["phone"].insert(0, phone or "")
        if role in ROLES:
            self.role_combo.set(role)
        else:
            self.role_combo.current(0)
        self.active_var.set(1 if active else 0)
        self.pw_entry.delete(0, tk.END)
        self.pw_confirm_entry.delete(0, tk.END)
        self.code_entry.delete(0, tk.END)
        self.loc_combo.set("")
        for label, lid in self.location_map.items():
            if lid == loc_id:
                self.loc_combo.set(label)
                break
        self.status_var.set(f"Loaded staff ID {staff_id}. Edit fields then click Update, Remove, or Delete.")

    # ----------------------------------------------------------- Validation --
    def _collect_form(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["role"] = self.role_var.get().strip()
        data["active"] = self.active_var.get()
        data["password"] = self.pw_entry.get()
        data["confirm_password"] = self.pw_confirm_entry.get()
        data["code"] = self.code_entry.get().strip()
        return data

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

    # --------------------------------------------------------- CRUD actions --
    def _add_staff(self):
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
        loc_id = self.location_map.get(self.loc_var.get().strip()) or None
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute(
                "INSERT INTO Staff (first_name, last_name, email, phone, role, active_flag, password_hash, location_id) VALUES (?,?,?,?,?,?,?,?)",
                (data["first_name"], data["last_name"], data["email"], data["phone"], data["role"], data["active"], pw_hash, loc_id)
            )
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not add staff.\n\n{e}")
            return
        messagebox.showinfo("Success", f"Staff member {data['first_name']} {data['last_name']} added.")
        self._clear_form()
        self._load_staff()

    def _update_staff(self):
        if not self._selected_staff_id:
            messagebox.showwarning("No Selection", "Select a staff member from the list first.")
            return
        data = self._collect_form()
        if not self._validate_base(data):
            return
        loc_id = self.location_map.get(self.loc_var.get().strip()) or None
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
            sql = "UPDATE Staff SET first_name=?, last_name=?, email=?, phone=?, role=?, active_flag=?, password_hash=?, location_id=? WHERE staff_id=?"
            params = (data["first_name"], data["last_name"], data["email"], data["phone"], data["role"], data["active"], pw_hash, loc_id, self._selected_staff_id)
        else:
            sql = "UPDATE Staff SET first_name=?, last_name=?, email=?, phone=?, role=?, active_flag=?, location_id=? WHERE staff_id=?"
            params = (data["first_name"], data["last_name"], data["email"], data["phone"], data["role"], data["active"], loc_id, self._selected_staff_id)
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute(sql, params)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not update staff.\n\n{e}")
            return
        messagebox.showinfo("Success", "Staff information updated.")
        self._load_staff()

    def _remove_staff(self):
        """Soft delete — sets active_flag = 0, keeps the record in the DB."""
        if not self._selected_staff_id:
            messagebox.showwarning("No Selection", "Select a staff member from the list first.")
            return
        name = self._get_selected_name()
        if not messagebox.askyesno("Confirm Remove", f"Deactivate {name}? They will remain in the database but marked inactive."):
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE Staff SET active_flag=0 WHERE staff_id=?", (self._selected_staff_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not remove staff.\n\n{e}")
            return
        messagebox.showinfo("Removed", f"{name} has been deactivated.")
        self._clear_form()
        self._load_staff()

    def _delete_staff(self):
        """Permanently deletes the staff record."""
        if not self._selected_staff_id:
            messagebox.showwarning("No Selection", "Select a staff member from the list first.")
            return
        name = self._get_selected_name()
        if not messagebox.askyesno("Confirm Delete", f"Permanently delete {name}? This cannot be undone."):
            return
        try:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM Staff WHERE staff_id=?", (self._selected_staff_id,))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not delete staff.\n\n{e}")
            return
        messagebox.showinfo("Deleted", f"{name} has been permanently deleted.")
        self._clear_form()
        self._load_staff()

    # ------------------------------------------------------------ Helpers --
    def _get_selected_name(self):
        try:
            conn = sqlite3.connect(DB_NAME)
            row = conn.execute(
                "SELECT first_name, last_name FROM Staff WHERE staff_id=?", (self._selected_staff_id,)
            ).fetchone()
            conn.close()
            return f"{row[0]} {row[1]}" if row else f"ID {self._selected_staff_id}"
        except sqlite3.Error:
            return f"ID {self._selected_staff_id}"

    def _clear_form(self):
        for e in self.entries.values():
            e.delete(0, tk.END)
        self.role_combo.current(0)
        self.active_var.set(1)
        self.pw_entry.delete(0, tk.END)
        self.pw_confirm_entry.delete(0, tk.END)
        self.code_entry.delete(0, tk.END)
        if self.loc_combo["values"]:
            self.loc_combo.current(0)
        self._selected_staff_id = None
        self.tree.selection_remove(self.tree.selection())
        self.status_var.set("Form cleared. Select a staff member or fill in the form to add.")
