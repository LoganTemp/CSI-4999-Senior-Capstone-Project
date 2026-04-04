import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import os
import hashlib
import hmac
from datetime import datetime

DB_NAME = "healthcare.db"

BG_LIGHT = "#e6f2ec"
BG_SIDEBAR = "#5FAF90"
BG_SIDEBAR_LIGHT = "#A2DDC6"
BG_PANEL = "#ffffff"
CARD_BG = "#f7fff7"
ACCENT = "#308684"
TEXT = "#0b3d2e"
BORDER = "#cfd8d3"

FONT_TITLE = ("Helvetica", 20, "bold")
FONT_HEADER = ("Helvetica", 14, "bold")
FONT_BODY = ("Helvetica", 10)
FONT_SMALL = ("Helvetica", 9)
FONT_BTN = ("Helvetica", 10, "bold")

BILLING_TEMPLATES = {
    "Checkup": 75.00,
    "Follow-up": 50.00,
    "Lab work": 120.00,
    "Vaccination": 40.00,
    "Other (custom)": None,
}


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def ensure_staff_password_column(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(Staff)").fetchall()]
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE Staff ADD COLUMN password_hash TEXT")


def ensure_bill_payment_columns(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(Bill)").fetchall()]
    if "paid_date" not in cols:
        conn.execute("ALTER TABLE Bill ADD COLUMN paid_date TEXT")
    if "payment_method_id" not in cols:
        conn.execute("ALTER TABLE Bill ADD COLUMN payment_method_id INTEGER")
    if "receipt_number" not in cols:
        conn.execute("ALTER TABLE Bill ADD COLUMN receipt_number TEXT")


def ensure_schema(conn):
    ensure_staff_password_column(conn)
    ensure_bill_payment_columns(conn)
    conn.commit()


def is_valid_date_yyyy_mm_dd(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


class BillingFrame(tk.Frame):
    def __init__(self, parent=None, controller=None, role="Admin"):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self.role = role
        self.conn = sqlite3.connect(DB_NAME)
        ensure_schema(self.conn)

        self.logged_in_staff_id = None
        self.logged_in_staff_name = ""
        self.patient_map = {}
        self.location_map = {}
        self.login_frame = None
        self.app_frame = None
        self.tree = None

        self._build_login_ui()

    def _db(self):
        return self.conn

    def _clear_root_frames(self):
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None
        if self.app_frame:
            self.app_frame.destroy()
            self.app_frame = None

    def _sidebar_button(self, parent, text, active=False):
        bg = BG_SIDEBAR_LIGHT if active else BG_SIDEBAR
        return tk.Label(
            parent, text=text, bg=bg, fg=TEXT, font=FONT_BODY, anchor="w", padx=10, pady=6
        )

    def _build_sidebar(self, parent, active_label="Billing"):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        portal_label = "Staff Portal" if self.role == "Staff" else "Admin Portal"
        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(
            logo_box, text=f"CareFlow\n{portal_label}", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
            font=("Helvetica", 9, "bold"), justify="left", padx=8, pady=8
        ).pack(anchor="w")

        if self.role == "Staff":
            nav_map = {
                "Dashboard": "HomePage",
                "Patient":   "PatientMenuPage",
                "Records":   "RecordsMenuPage",
                "Billing":   None,
            }
        else:
            nav_map = {
                "Dashboard": "HomePage",
                "Patient":   "PatientMenuPage",
                "Staff":     "StaffMenuPage",
                "Clinic":    "LocationMenuPage",
                "Records":   "RecordsMenuPage",
                "Billing":   None,
            }
        for item, page in nav_map.items():
            is_active = item == active_label
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

        return sidebar

    def _build_login_ui(self):
        self._clear_root_frames()

        self.login_frame = tk.Frame(self, bg=BG_LIGHT)
        self.login_frame.pack(fill="both", expand=True)

        outer = tk.Frame(self.login_frame, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer, active_label="Billing")

        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x")
        tk.Label(header, text="Staff Billing Login", bg=BG_PANEL, fg=TEXT, font=FONT_TITLE).pack(
            side="left", padx=14, pady=14
        )

        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, pady=(10, 0))

        card = tk.Frame(body, bg=CARD_BG, bd=1, relief="solid")
        card.place(relx=0.5, rely=0.45, anchor="center", width=420, height=230)

        tk.Label(card, text="Login to create and manage bills", bg=CARD_BG, fg=TEXT, font=FONT_HEADER).pack(pady=(18, 14))

        tk.Label(card, text="Email", bg=CARD_BG, fg=TEXT, font=FONT_BODY).pack(anchor="w", padx=30)
        self.email_var = tk.StringVar()
        tk.Entry(card, textvariable=self.email_var, width=34, bd=1, relief="solid").pack(padx=30, pady=(4, 12))

        tk.Label(card, text="Password", bg=CARD_BG, fg=TEXT, font=FONT_BODY).pack(anchor="w", padx=30)
        self.password_var = tk.StringVar()
        tk.Entry(card, textvariable=self.password_var, show="*", width=34, bd=1, relief="solid").pack(padx=30, pady=(4, 14))

        tk.Button(
            card, text="Login", bg=BG_SIDEBAR, fg=TEXT, font=FONT_BTN,
            relief="flat", padx=18, pady=8, command=self.login_staff
        ).pack()

    def login_staff(self):
        email = self.email_var.get().strip()
        password = self.password_var.get()

        if not email or not password:
            messagebox.showerror("Missing info", "Please enter email and password.")
            return

        cur = self._db().cursor()
        row = cur.execute("""
            SELECT staff_id, first_name, last_name, password_hash, active_flag, role
            FROM Staff WHERE LOWER(email) = LOWER(?)
        """, (email,)).fetchone()

        if not row:
            messagebox.showerror("Login failed", "No staff account was found with that email.")
            return

        staff_id, first_name, last_name, stored_hash, active_flag, role = row

        if not active_flag:
            messagebox.showerror("Login failed", "This staff account is inactive.")
            return

        if not stored_hash or not verify_password(password, stored_hash):
            messagebox.showerror("Login failed", "Incorrect password.")
            return

        self.logged_in_staff_id = staff_id
        self.logged_in_staff_name = f"{first_name} {last_name} ({role})"

        self._build_app_ui()
        self._load_locations()
        self._load_patients()
        self._load_recent_bills()

    def _build_app_ui(self):
        self._clear_root_frames()

        self.app_frame = tk.Frame(self, bg=BG_LIGHT)
        self.app_frame.pack(fill="both", expand=True)

        outer = tk.Frame(self.app_frame, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer, active_label="Billing")

        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x")

        left_header = tk.Frame(header, bg=BG_PANEL)
        left_header.pack(side="left", padx=14, pady=12)
        tk.Label(left_header, text="Staff Billing", bg=BG_PANEL, fg=TEXT, font=FONT_TITLE).pack(anchor="w")
        tk.Label(left_header, text=f"Signed in as {self.logged_in_staff_name}", bg=BG_PANEL, fg=TEXT, font=FONT_SMALL).pack(anchor="w")

        right_header = tk.Frame(header, bg=BG_PANEL)
        right_header.pack(side="right", padx=14, pady=12)
        tk.Button(right_header, text="Logout", bg=ACCENT, fg="white", relief="flat", command=self.logout).pack()

        cards_frame = tk.Frame(main, bg=BG_LIGHT)
        cards_frame.pack(fill="x", pady=(10, 10))

        self.recent_card = tk.Label(
            cards_frame, text="Recent Bills\n0", bg=CARD_BG, fg=TEXT, font=("Helvetica", 12, "bold"),
            bd=1, relief="solid", width=18, height=3, justify="left", anchor="w", padx=12
        )
        self.recent_card.pack(side="left", padx=(0, 10))

        self.template_card = tk.Label(
            cards_frame, text="Templates\n5", bg=CARD_BG, fg=TEXT, font=("Helvetica", 12, "bold"),
            bd=1, relief="solid", width=18, height=3, justify="left", anchor="w", padx=12
        )
        self.template_card.pack(side="left", padx=(0, 10))

        self.patient_card = tk.Label(
            cards_frame, text="Patients\n0", bg=CARD_BG, fg=TEXT, font=("Helvetica", 12, "bold"),
            bd=1, relief="solid", width=18, height=3, justify="left", anchor="w", padx=12
        )
        self.patient_card.pack(side="left")

        form_panel = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        form_panel.pack(fill="x")

        tk.Label(form_panel, text="Create Bill", bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        form = tk.Frame(form_panel, bg=BG_PANEL)
        form.pack(fill="x", padx=12, pady=(0, 12))

        r = 0
        tk.Label(form, text="Patient:", bg=BG_PANEL, fg=TEXT).grid(row=r, column=0, sticky="w", pady=6)
        self.patient_var = tk.StringVar()
        self.patient_combo = ttk.Combobox(form, textvariable=self.patient_var, state="readonly", width=45)
        self.patient_combo.grid(row=r, column=1, padx=8, pady=6, sticky="w")
        self.patient_combo.bind("<<ComboboxSelected>>", lambda e: self._auto_location_from_patient())
        r += 1

        tk.Label(form, text="Service template:", bg=BG_PANEL, fg=TEXT).grid(row=r, column=0, sticky="w", pady=6)
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(
            form, textvariable=self.template_var, state="readonly",
            values=list(BILLING_TEMPLATES.keys()), width=28
        )
        self.template_combo.grid(row=r, column=1, padx=8, pady=6, sticky="w")
        self.template_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_template())
        r += 1

        tk.Label(form, text="Amount ($):", bg=BG_PANEL, fg=TEXT).grid(row=r, column=0, sticky="w", pady=6)
        self.amount_var = tk.StringVar()
        self.amount_entry = tk.Entry(form, textvariable=self.amount_var, width=18, bd=1, relief="solid")
        self.amount_entry.grid(row=r, column=1, padx=8, pady=6, sticky="w")
        r += 1

        tk.Label(form, text="Due date (YYYY-MM-DD):", bg=BG_PANEL, fg=TEXT).grid(row=r, column=0, sticky="w", pady=6)
        self.due_var = tk.StringVar()
        self.due_entry = tk.Entry(form, textvariable=self.due_var, width=18, bd=1, relief="solid")
        self.due_entry.grid(row=r, column=1, padx=8, pady=6, sticky="w")
        r += 1

        tk.Label(form, text="Clinic location:", bg=BG_PANEL, fg=TEXT).grid(row=r, column=0, sticky="w", pady=6)
        self.loc_var = tk.StringVar()
        self.loc_combo = ttk.Combobox(form, textvariable=self.loc_var, state="readonly", width=45)
        self.loc_combo.grid(row=r, column=1, padx=8, pady=6, sticky="w")

        action_row = tk.Frame(form_panel, bg=BG_PANEL)
        action_row.pack(fill="x", padx=12, pady=(0, 12))

        tk.Button(
            action_row, text="Create Bill", bg=BG_SIDEBAR, fg=TEXT,
            font=FONT_BTN, relief="flat", command=self.create_bill
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            action_row, text="Clear", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
            font=FONT_BTN, relief="flat", command=self.clear_form
        ).pack(side="left")

        recent = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        recent.pack(fill="both", expand=True, pady=(10, 0))

        tk.Label(recent, text="Recent Bills", bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        table_wrap = tk.Frame(recent, bg=BG_PANEL)
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        cols = ("bill_id", "patient", "amount", "due_date", "status", "created_at")

        # FIX: both tree and scrollbar parented to table_wrap so they stay connected
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=11)
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=140 if c != "created_at" else 170)
        self.tree.column("bill_id", width=70)
        self.tree.column("amount", width=90)
        self.tree.column("status", width=90)

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.template_combo.set("Checkup")
        self._apply_template()

    def logout(self):
        self.logged_in_staff_id = None
        self.logged_in_staff_name = ""
        self._build_login_ui()

    def _load_patients(self):
        rows = self._db().cursor().execute("""
            SELECT patient_id, first_name, last_name, email, location_id
            FROM Patient ORDER BY last_name, first_name
        """).fetchall()

        self.patient_map.clear()
        display = []
        for pid, fn, ln, email, _loc_id in rows:
            label = f"{ln}, {fn}  (ID {pid})" + (f"  <{email}>" if email else "")
            self.patient_map[label] = pid
            display.append(label)

        self.patient_combo["values"] = display
        self.patient_card.config(text=f"Patients\n{len(display)}")
        if display:
            self.patient_combo.current(0)
            self._auto_location_from_patient()

    def _load_locations(self):
        rows = self._db().cursor().execute("""
            SELECT location_id, name, status FROM ClinicLocation ORDER BY name
        """).fetchall()

        self.location_map.clear()
        display = []
        for loc_id, name, status in rows:
            label = f"{name}  (ID {loc_id})" + (f" [{status}]" if status else "")
            self.location_map[label] = loc_id
            display.append(label)

        self.loc_combo["values"] = display
        if display:
            self.loc_combo.current(0)

    def _auto_location_from_patient(self):
        label = self.patient_var.get().strip()
        if not label or label not in self.patient_map:
            return
        pid = self.patient_map[label]
        row = self._db().cursor().execute(
            "SELECT location_id FROM Patient WHERE patient_id = ?", (pid,)
        ).fetchone()
        if not row or row[0] is None:
            return
        loc_id = row[0]
        for disp, mapped_id in self.location_map.items():
            if mapped_id == loc_id:
                self.loc_combo.set(disp)
                break

    def _apply_template(self):
        name = self.template_var.get().strip() or self.template_combo.get().strip()
        amt = BILLING_TEMPLATES.get(name)
        if amt is None:
            self.amount_entry.config(state="normal")
            if not self.amount_var.get().strip():
                self.amount_var.set("")
        else:
            self.amount_entry.config(state="normal")
            self.amount_var.set(f"{amt:.2f}")
            self.amount_entry.config(state="disabled")

    def clear_form(self):
        if self.patient_combo["values"]:
            self.patient_combo.current(0)
        if self.loc_combo["values"]:
            self.loc_combo.current(0)
        self.template_combo.set("Checkup")
        self.amount_entry.config(state="normal")
        self.amount_var.set("")
        self._apply_template()
        self.due_var.set("")

    def create_bill(self):
        if not self.logged_in_staff_id:
            messagebox.showerror("Not logged in", "Please log in first.")
            return

        patient_label = self.patient_var.get().strip()
        if not patient_label or patient_label not in self.patient_map:
            messagebox.showerror("Missing", "Please select a patient.")
            return
        patient_id = self.patient_map[patient_label]

        loc_label = self.loc_var.get().strip()
        if not loc_label or loc_label not in self.location_map:
            messagebox.showerror("Missing", "Please select a clinic location.")
            return
        location_id = self.location_map[loc_label]

        due = self.due_var.get().strip()
        if not is_valid_date_yyyy_mm_dd(due):
            messagebox.showerror("Invalid due date", "Due date must be YYYY-MM-DD.")
            return

        try:
            amount = float(self.amount_var.get().strip())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a positive number.")
            return

        self._db().execute("""
            INSERT INTO Bill (patient_id, location_id, amount, due_date, status)
            VALUES (?, ?, ?, ?, 'unpaid')
        """, (patient_id, location_id, amount, due))
        self._db().commit()

        messagebox.showinfo("Success", "Bill created.")
        self._load_recent_bills()

    def _load_recent_bills(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self._db().cursor().execute("""
            SELECT
                b.bill_id,
                p.last_name || ', ' || p.first_name || ' (ID ' || p.patient_id || ')' AS patient,
                b.amount,
                b.due_date,
                b.status,
                b.created_at
            FROM Bill b
            JOIN Patient p ON p.patient_id = b.patient_id
            ORDER BY b.created_at DESC
            LIMIT 25
        """).fetchall()

        self.recent_card.config(text=f"Recent Bills\n{len(rows)}")

        for bill_id, patient, amount, due_date, status, created_at in rows:
            self.tree.insert("", "end", values=(
                bill_id,
                patient,
                f"{amount:.2f}" if amount is not None else "",
                due_date or "",
                status or "",
                created_at or ""
            ))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("CareFlow - Staff Billing")
    root.geometry("1100x680")
    frame = BillingFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()
