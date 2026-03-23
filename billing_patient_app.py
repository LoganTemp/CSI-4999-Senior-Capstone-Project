import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import hashlib
import hmac
from datetime import datetime

DB_NAME = "healthcare.db"


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


def ensure_patient_password_column(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(Patient)").fetchall()]
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE Patient ADD COLUMN password_hash TEXT")


def ensure_bill_payment_columns(conn):
    cols = [row[1] for row in conn.execute("PRAGMA table_info(Bill)").fetchall()]
    if "paid_date" not in cols:
        conn.execute("ALTER TABLE Bill ADD COLUMN paid_date TEXT")
    if "payment_method_id" not in cols:
        conn.execute("ALTER TABLE Bill ADD COLUMN payment_method_id INTEGER")
    if "receipt_number" not in cols:
        conn.execute("ALTER TABLE Bill ADD COLUMN receipt_number TEXT")


def ensure_schema(conn):
    ensure_patient_password_column(conn)
    ensure_bill_payment_columns(conn)
    conn.commit()


def generate_receipt_number(bill_id: int) -> str:
    return f"RCPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{bill_id}"


class BillingFrame(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = sqlite3.connect(DB_NAME)
        ensure_schema(self.conn)

        self.logged_in_patient_id = None
        self.logged_in_patient_name = ""
        self.payment_method_map = {}

        self.login_frame = None
        self.app_frame = None
        self.tree = None
        self.pm_combo = None
        self.pm_var = tk.StringVar()
        self.patient_name_var = tk.StringVar(value="Not signed in")

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

        card = ttk.LabelFrame(self.login_frame, text="Patient Login", padding=16)
        card.pack(expand=True)

        ttk.Label(card, text="Email:").grid(row=0, column=0, sticky="w", pady=6)
        self.email_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.email_var, width=35).grid(row=0, column=1, pady=6)

        ttk.Label(card, text="Password:").grid(row=1, column=0, sticky="w", pady=6)
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="*", width=35).grid(row=1, column=1, pady=6)

        ttk.Button(card, text="Login", command=self.login_patient).grid(row=2, column=0, columnspan=2, pady=14)

    def login_patient(self):
        email = self.email_var.get().strip()
        password = self.password_var.get()

        if not email or not password:
            messagebox.showerror("Missing info", "Please enter email and password.")
            return

        row = self._db().cursor().execute("""
            SELECT patient_id, first_name, last_name, password_hash
            FROM Patient
            WHERE LOWER(email) = LOWER(?)
        """, (email,)).fetchone()

        if not row:
            messagebox.showerror("Login failed", "No patient account was found with that email.")
            return

        patient_id, first_name, last_name, stored_hash = row

        if not stored_hash or not verify_password(password, stored_hash):
            messagebox.showerror("Login failed", "Incorrect password.")
            return

        self.logged_in_patient_id = patient_id
        self.logged_in_patient_name = f"{first_name} {last_name}"
        self.patient_name_var.set(f"Signed in as: {self.logged_in_patient_name} (ID {patient_id})")

        self._build_app_ui()
        self.refresh()

    def _build_app_ui(self):
        self._clear_root_frames()

        self.app_frame = ttk.Frame(self, padding=12)
        self.app_frame.pack(fill="both", expand=True)

        top = ttk.LabelFrame(self.app_frame, text="Patient Account", padding=10)
        top.pack(fill="x")

        ttk.Label(top, textvariable=self.patient_name_var).grid(row=0, column=0, sticky="w")
        ttk.Button(top, text="Refresh", command=self.refresh).grid(row=0, column=1, padx=8)
        ttk.Button(top, text="Logout", command=self.logout).grid(row=0, column=2, padx=8)

        mid = ttk.LabelFrame(self.app_frame, text="Bills", padding=10)
        mid.pack(fill="both", expand=True, pady=(10, 10))

        cols = ("bill_id", "amount", "due_date", "status", "created_at", "paid_date", "location", "receipt_number")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=14)

        headings = {
            "bill_id": "Bill ID",
            "amount": "Amount",
            "due_date": "Due Date",
            "status": "Status",
            "created_at": "Created",
            "paid_date": "Paid Date",
            "location": "Location",
            "receipt_number": "Receipt #"
        }
        widths = {
            "bill_id": 70,
            "amount": 90,
            "due_date": 110,
            "status": 90,
            "created_at": 140,
            "paid_date": 140,
            "location": 170,
            "receipt_number": 170
        }

        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c])

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        bottom = ttk.LabelFrame(self.app_frame, text="Actions", padding=10)
        bottom.pack(fill="x")

        ttk.Label(bottom, text="Payment method:").grid(row=0, column=0, sticky="w")
        self.pm_combo = ttk.Combobox(bottom, textvariable=self.pm_var, state="readonly", width=45)
        self.pm_combo.grid(row=0, column=1, padx=8, sticky="w")

        ttk.Button(bottom, text="Pay Selected Bill", command=self.pay_selected).grid(row=0, column=2, padx=8)
        ttk.Button(bottom, text="Download Receipt", command=self.download_receipt).grid(row=0, column=3, padx=8)
        ttk.Button(bottom, text="Add Payment Method", command=self.add_payment_method_dialog).grid(row=0, column=4, padx=8)

    def logout(self):
        self.logged_in_patient_id = None
        self.logged_in_patient_name = ""
        self.patient_name_var.set("Not signed in")
        self._build_login_ui()

    def _load_payment_methods(self):
        self.payment_method_map.clear()
        rows = self._db().cursor().execute("""
            SELECT payment_method_id, type, last4, exp_month, exp_year, active_flag
            FROM PaymentMethod
            WHERE patient_id = ?
            ORDER BY active_flag DESC, payment_method_id DESC
        """, (self.logged_in_patient_id,)).fetchall()

        display = []
        for pmid, typ, last4, mm, yy, active in rows:
            active_txt = "ACTIVE" if active else "inactive"
            label = f"{typ or 'method'} ****{last4 or '????'}  exp {mm}/{yy}  ({active_txt})  [PM {pmid}]"
            self.payment_method_map[label] = pmid
            display.append(label)

        self.pm_combo["values"] = display
        if display:
            self.pm_combo.current(0)
        else:
            self.pm_combo.set("No payment methods found")

    def _load_bills(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self._db().cursor().execute("""
            SELECT
                b.bill_id,
                b.amount,
                b.due_date,
                b.status,
                b.created_at,
                b.paid_date,
                COALESCE(cl.name, '') AS location_name,
                COALESCE(b.receipt_number, '')
            FROM Bill b
            LEFT JOIN ClinicLocation cl ON cl.location_id = b.location_id
            WHERE b.patient_id = ?
            ORDER BY
                CASE WHEN b.status = 'paid' THEN 1 ELSE 0 END,
                b.due_date ASC,
                b.created_at DESC
        """, (self.logged_in_patient_id,)).fetchall()

        for bill_id, amount, due_date, status, created_at, paid_date, location_name, receipt_number in rows:
            self.tree.insert("", "end", values=(
                bill_id,
                f"{amount:.2f}" if amount is not None else "",
                due_date or "",
                status or "",
                created_at or "",
                paid_date or "",
                location_name or "",
                receipt_number or ""
            ))

    def refresh(self):
        self._load_payment_methods()
        self._load_bills()

    def add_payment_method_dialog(self):
        if not self.logged_in_patient_id:
            messagebox.showerror("Not logged in", "Please log in first.")
            return

        win = tk.Toplevel(self)
        win.title("Add Payment Method")
        win.geometry("420x320")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        ttk.Label(win, text="Payment Type:").grid(row=0, column=0, padx=12, pady=10, sticky="w")
        type_var = tk.StringVar(value="Visa")
        type_combo = ttk.Combobox(
            win,
            textvariable=type_var,
            state="readonly",
            values=["Visa", "MasterCard", "Discover", "Amex", "Debit"],
            width=25
        )
        type_combo.grid(row=0, column=1, padx=12, pady=10, sticky="w")

        ttk.Label(win, text="Card Number:").grid(row=1, column=0, padx=12, pady=10, sticky="w")
        card_number_var = tk.StringVar()
        ttk.Entry(win, textvariable=card_number_var, width=28).grid(row=1, column=1, padx=12, pady=10, sticky="w")

        ttk.Label(win, text="Exp Month (MM):").grid(row=2, column=0, padx=12, pady=10, sticky="w")
        exp_month_var = tk.StringVar()
        ttk.Entry(win, textvariable=exp_month_var, width=10).grid(row=2, column=1, padx=12, pady=10, sticky="w")

        ttk.Label(win, text="Exp Year (YYYY):").grid(row=3, column=0, padx=12, pady=10, sticky="w")
        exp_year_var = tk.StringVar()
        ttk.Entry(win, textvariable=exp_year_var, width=10).grid(row=3, column=1, padx=12, pady=10, sticky="w")

        active_var = tk.IntVar(value=1)
        ttk.Checkbutton(win, text="Set as active payment method", variable=active_var).grid(
            row=4, column=0, columnspan=2, padx=12, pady=10, sticky="w"
        )

        def save_payment_method():
            pm_type = type_var.get().strip()
            card_number = card_number_var.get().strip().replace(" ", "").replace("-", "")
            exp_month = exp_month_var.get().strip()
            exp_year = exp_year_var.get().strip()
            active_flag = active_var.get()

            if not pm_type or not card_number or not exp_month or not exp_year:
                messagebox.showerror("Missing fields", "Please complete all payment method fields.")
                return

            if not card_number.isdigit() or len(card_number) < 4:
                messagebox.showerror("Invalid card", "Card number must be numeric and at least 4 digits.")
                return

            if not exp_month.isdigit() or not (1 <= int(exp_month) <= 12):
                messagebox.showerror("Invalid month", "Expiration month must be between 1 and 12.")
                return

            if not exp_year.isdigit() or len(exp_year) != 4:
                messagebox.showerror("Invalid year", "Expiration year must be 4 digits.")
                return

            last4 = card_number[-4:]
            exp_month_db = int(exp_month)
            exp_year_db = int(exp_year)

            try:
                cur = self._db().cursor()

                if active_flag == 1:
                    cur.execute("""
                        UPDATE PaymentMethod
                        SET active_flag = 0
                        WHERE patient_id = ?
                    """, (self.logged_in_patient_id,))

                cur.execute("""
                    INSERT INTO PaymentMethod (
                        patient_id, type, last4, exp_month, exp_year, active_flag
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.logged_in_patient_id,
                    pm_type,
                    last4,
                    exp_month_db,
                    exp_year_db,
                    active_flag
                ))

                self._db().commit()
            except sqlite3.Error as e:
                messagebox.showerror("Database Error", f"Could not add payment method.\n\n{e}")
                return

            win.destroy()
            self.refresh()
            messagebox.showinfo("Success", f"Payment method ending in {last4} added successfully.")

        ttk.Button(win, text="Save Payment Method", command=save_payment_method).grid(
            row=5, column=0, columnspan=2, pady=18
        )

    def pay_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a bill", "Please select a bill.")
            return

        values = self.tree.item(sel[0], "values")
        bill_id = int(values[0])
        status = (values[3] or "").lower()

        if status == "paid":
            messagebox.showinfo("Already paid", "That bill is already marked as paid.")
            return

        pm_label = self.pm_var.get().strip()
        if not pm_label or pm_label not in self.payment_method_map:
            messagebox.showwarning("Payment method", "Please select a valid payment method.")
            return

        payment_method_id = self.payment_method_map[pm_label]
        receipt_number = generate_receipt_number(bill_id)
        paid_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self._db().execute("""
            UPDATE Bill
            SET status = 'paid',
                paid_date = ?,
                payment_method_id = ?,
                receipt_number = ?
            WHERE bill_id = ?
        """, (paid_date, payment_method_id, receipt_number, bill_id))
        self._db().commit()

        self.refresh()
        messagebox.showinfo("Success", f"Bill #{bill_id} marked as paid.")

    def download_receipt(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a bill", "Please select a paid bill first.")
            return

        values = self.tree.item(sel[0], "values")
        bill_id = int(values[0])

        row = self._db().cursor().execute("""
            SELECT
                b.bill_id,
                b.amount,
                b.due_date,
                b.status,
                b.created_at,
                b.paid_date,
                COALESCE(b.receipt_number, ''),
                p.first_name,
                p.last_name,
                p.email,
                COALESCE(cl.name, '') AS clinic_name,
                COALESCE(pm.type, '') AS payment_type,
                COALESCE(pm.last4, '') AS payment_last4
            FROM Bill b
            JOIN Patient p ON p.patient_id = b.patient_id
            LEFT JOIN ClinicLocation cl ON cl.location_id = b.location_id
            LEFT JOIN PaymentMethod pm ON pm.payment_method_id = b.payment_method_id
            WHERE b.bill_id = ? AND b.patient_id = ?
        """, (bill_id, self.logged_in_patient_id)).fetchone()

        if not row:
            messagebox.showerror("Not found", "Could not load that bill.")
            return

        (
            bill_id, amount, due_date, status, created_at, paid_date, receipt_number,
            first_name, last_name, email, clinic_name, payment_type, payment_last4
        ) = row

        if (status or "").lower() != "paid":
            messagebox.showwarning("Receipt unavailable", "Only paid bills can have receipts downloaded.")
            return

        if not receipt_number:
            receipt_number = generate_receipt_number(bill_id)
            self._db().execute(
                "UPDATE Bill SET receipt_number = ? WHERE bill_id = ?",
                (receipt_number, bill_id)
            )
            self._db().commit()

        receipt_text = (
            "CareFlow Payment Receipt\n"
            "========================\n"
            f"Receipt Number: {receipt_number}\n"
            f"Bill ID: {bill_id}\n"
            f"Patient: {first_name} {last_name}\n"
            f"Email: {email or ''}\n"
            f"Clinic: {clinic_name}\n"
            f"Amount Paid: ${float(amount):.2f}\n"
            f"Due Date: {due_date or ''}\n"
            f"Created At: {created_at or ''}\n"
            f"Paid Date: {paid_date or ''}\n"
            f"Payment Method: {payment_type} ****{payment_last4}\n"
            f"Status: {status}\n"
        )

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"receipt_bill_{bill_id}.txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not save_path:
            return

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(receipt_text)

        messagebox.showinfo("Downloaded", "Receipt downloaded successfully.")
        self.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("CareFlow - Patient Billing")
    root.geometry("950x620")
    frame = BillingFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()