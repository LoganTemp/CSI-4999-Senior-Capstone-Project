import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import hashlib
import hmac
from datetime import datetime

DB_NAME = "healthcare.db"

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
    def __init__(self, parent=None):
        super().__init__(parent)
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

    def _build_login_ui(self):
        self._clear_root_frames()

        self.login_frame = ttk.Frame(self, padding=20)
        self.login_frame.pack(fill="both", expand=True)

        card = ttk.LabelFrame(self.login_frame, text="Staff Login", padding=16)
        card.pack(expand=True)

        ttk.Label(card, text="Email:").grid(row=0, column=0, sticky="w", pady=6)
        self.email_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.email_var, width=35).grid(row=0, column=1, pady=6)

        ttk.Label(card, text="Password:").grid(row=1, column=0, sticky="w", pady=6)
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="*", width=35).grid(row=1, column=1, pady=6)

        ttk.Button(card, text="Login", command=self.login_staff).grid(row=2, column=0, columnspan=2, pady=14)

    def login_staff(self):
        email = self.email_var.get().strip()
        password = self.password_var.get()

        if not email or not password:
            messagebox.showerror("Missing info", "Please enter email and password.")
            return

        cur = self._db().cursor()
        row = cur.execute("""
            SELECT staff_id, first_name, last_name, password_hash, active_flag, role
            FROM Staff
            WHERE LOWER(email) = LOWER(?)
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

        self.app_frame = ttk.Frame(self, padding=12)
        self.app_frame.pack(fill="both", expand=True)

        top = ttk.LabelFrame(self.app_frame, text="Staff Session", padding=10)
        top.pack(fill="x")

        ttk.Label(top, text=f"Signed in as: {self.logged_in_staff_name}").grid(row=0, column=0, sticky="w")
        ttk.Button(top, text="Logout", command=self.logout).grid(row=0, column=1, padx=8)

        form = ttk.LabelFrame(self.app_frame, text="Create Bill", padding=10)
        form.pack(fill="x", pady=(10, 10))

        r = 0
        ttk.Label(form, text="Patient:").grid(row=r, column=0, sticky="w")
        self.patient_var = tk.StringVar()
        self.patient_combo = ttk.Combobox(form, textvariable=self.patient_var, state="readonly", width=50)
        self.patient_combo.grid(row=r, column=1, padx=8, pady=4, sticky="w")
        self.patient_combo.bind("<<ComboboxSelected>>", lambda e: self._auto_location_from_patient())
        r += 1

        ttk.Label(form, text="Service template:").grid(row=r, column=0, sticky="w")
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(
            form, textvariable=self.template_var, state="readonly",
            values=list(BILLING_TEMPLATES.keys()), width=30
        )
        self.template_combo.grid(row=r, column=1, padx=8, pady=4, sticky="w")
        self.template_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_template())
        r += 1

        ttk.Label(form, text="Amount ($):").grid(row=r, column=0, sticky="w")
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(form, textvariable=self.amount_var, width=20)
        self.amount_entry.grid(row=r, column=1, padx=8, pady=4, sticky="w")
        r += 1

        ttk.Label(form, text="Due date (YYYY-MM-DD):").grid(row=r, column=0, sticky="w")
        self.due_var = tk.StringVar()
        self.due_entry = ttk.Entry(form, textvariable=self.due_var, width=20)
        self.due_entry.grid(row=r, column=1, padx=8, pady=4, sticky="w")
        r += 1

        ttk.Label(form, text="Clinic location:").grid(row=r, column=0, sticky="w")
        self.loc_var = tk.StringVar()
        self.loc_combo = ttk.Combobox(form, textvariable=self.loc_var, state="readonly", width=50)
        self.loc_combo.grid(row=r, column=1, padx=8, pady=4, sticky="w")
        r += 1

        btns = ttk.Frame(self.app_frame, padding=(0, 10))
        btns.pack(fill="x")

        ttk.Button(btns, text="Create Bill", command=self.create_bill).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=8)

        recent = ttk.LabelFrame(self.app_frame, text="Recent Bills (latest 25)", padding=10)
        recent.pack(fill="both", expand=True)

        cols = ("bill_id", "patient", "amount", "due_date", "status", "created_at")
        self.tree = ttk.Treeview(recent, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140 if c != "created_at" else 170)
        self.tree.column("bill_id", width=70)
        self.tree.column("amount", width=90)
        self.tree.column("status", width=90)

        vsb = ttk.Scrollbar(recent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        recent.grid_rowconfigure(0, weight=1)
        recent.grid_columnconfigure(0, weight=1)

        self.template_combo.set("Checkup")
        self._apply_template()

    def logout(self):
        self.logged_in_staff_id = None
        self.logged_in_staff_name = ""
        self._build_login_ui()

    def _load_patients(self):
        rows = self._db().cursor().execute("""
            SELECT patient_id, first_name, last_name, email, location_id
            FROM Patient
            ORDER BY last_name, first_name
        """).fetchall()

        self.patient_map.clear()
        display = []
        for pid, fn, ln, email, _loc_id in rows:
            label = f"{ln}, {fn}  (ID {pid})" + (f"  <{email}>" if email else "")
            self.patient_map[label] = pid
            display.append(label)

        self.patient_combo["values"] = display
        if display:
            self.patient_combo.current(0)
            self._auto_location_from_patient()

    def _load_locations(self):
        rows = self._db().cursor().execute("""
            SELECT location_id, name, status
            FROM ClinicLocation
            ORDER BY name
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
            "SELECT location_id FROM Patient WHERE patient_id = ?",
            (pid,)
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
            self.amount_entry.configure(state="normal")
        else:
            self.amount_var.set(f"{amt:.2f}")
            self.amount_entry.configure(state="disabled")

    def clear_form(self):
        if self.patient_combo["values"]:
            self.patient_combo.current(0)
        if self.loc_combo["values"]:
            self.loc_combo.current(0)
        self.template_combo.set("Checkup")
        self.amount_entry.configure(state="normal")
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
    root.geometry("820x580")
    frame = BillingFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()