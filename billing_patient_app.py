import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import sqlite3
import os
import hashlib
import hmac
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "healthcare.db")

# --- Dashboard style palette ---
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
    def __init__(self, parent=None, back_command=None):
        super().__init__(parent, bg=BG_LIGHT)
        self.back_command = back_command

        self.conn = None
        self._reconnect_db()
        ensure_schema(self.conn)

        self.logged_in_patient_id = None
        self.logged_in_patient_name = ""
        self.payment_method_map = {}

        self.login_frame = None
        self.app_frame = None
        self.tree = None
        self.pm_var = tk.StringVar()
        self.patient_name_var = tk.StringVar(value="Not signed in")

        self._build_login_ui()

    def _reconnect_db(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass
        self.conn = sqlite3.connect(DB_NAME, timeout=5)

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
        fg = TEXT
        return tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=fg,
            font=FONT_BODY,
            anchor="w",
            padx=10,
            pady=6
        )

    def _build_sidebar(self, parent, active_label="Billing"):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(
            logo_box,
            text="CareFlow\nPatient Portal",
            bg=BG_SIDEBAR_LIGHT,
            fg=TEXT,
            font=("Helvetica", 9, "bold"),
            justify="left",
            padx=8,
            pady=8
        ).pack(anchor="w")

        items = ["Dashboard", "Patient", "Staff", "Clinic", "Records", "Billing"]
        for item in items:
            self._sidebar_button(sidebar, item, active=(item == active_label)).pack(fill="x", padx=10, pady=2)

        tk.Label(
            sidebar,
            text=f"Signed in as:\n{self.logged_in_patient_name or 'Patient'}",
            bg=BG_SIDEBAR,
            fg=TEXT,
            font=FONT_SMALL,
            justify="left"
        ).pack(side="bottom", anchor="w", padx=10, pady=12)

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
        tk.Label(header, text="Patient Billing Login", bg=BG_PANEL, fg=TEXT, font=FONT_TITLE).pack(
            side="left", padx=14, pady=14
        )

        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, pady=(10, 0))

        card = tk.Frame(body, bg=CARD_BG, bd=1, relief="solid")
        card.place(relx=0.5, rely=0.45, anchor="center", width=420, height=230)

        tk.Label(card, text="Login to access your bills", bg=CARD_BG, fg=TEXT, font=FONT_HEADER).pack(pady=(18, 14))

        tk.Label(card, text="Email", bg=CARD_BG, fg=TEXT, font=FONT_BODY).pack(anchor="w", padx=30)
        self.email_var = tk.StringVar()
        tk.Entry(card, textvariable=self.email_var, width=34, bd=1, relief="solid").pack(padx=30, pady=(4, 12))

        tk.Label(card, text="Password", bg=CARD_BG, fg=TEXT, font=FONT_BODY).pack(anchor="w", padx=30)
        self.password_var = tk.StringVar()
        tk.Entry(card, textvariable=self.password_var, show="*", width=34, bd=1, relief="solid").pack(
            padx=30, pady=(4, 14)
        )

        tk.Button(
            card,
            text="Login",
            bg=BG_SIDEBAR,
            fg=TEXT,
            font=FONT_BTN,
            relief="flat",
            padx=18,
            pady=8,
            command=self.login_patient
        ).pack()

    def login_patient(self):
        self._reconnect_db()

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
        tk.Label(left_header, text="Patient Billing", bg=BG_PANEL, fg=TEXT, font=FONT_TITLE).pack(anchor="w")
        tk.Label(left_header, text=self.patient_name_var.get(), bg=BG_PANEL, fg=TEXT, font=FONT_SMALL).pack(anchor="w")

        right_header = tk.Frame(header, bg=BG_PANEL)
        right_header.pack(side="right", padx=14, pady=12)
        if self.back_command:
            tk.Button(right_header, text="Back", bg="#e0e0e0", fg="#222", relief="flat", command=self.back_command).pack(
                side="left", padx=4
            )
        tk.Button(right_header, text="Refresh", bg=BG_SIDEBAR, fg=TEXT, relief="flat", command=self.refresh).pack(
            side="left", padx=4
        )
        tk.Button(right_header, text="Logout", bg=ACCENT, fg="white", relief="flat", command=self.logout).pack(
            side="left", padx=4
        )

        cards_frame = tk.Frame(main, bg=BG_LIGHT)
        cards_frame.pack(fill="x", pady=(10, 10))

        self.bill_count_card = tk.Label(
            cards_frame, text="Bills\n0", bg=CARD_BG, fg=TEXT, font=("Helvetica", 12, "bold"),
            bd=1, relief="solid", width=18, height=3, justify="left", anchor="w", padx=12
        )
        self.bill_count_card.pack(side="left", padx=(0, 10))

        self.unpaid_card = tk.Label(
            cards_frame, text="Unpaid\n$0.00", bg=CARD_BG, fg=TEXT, font=("Helvetica", 12, "bold"),
            bd=1, relief="solid", width=18, height=3, justify="left", anchor="w", padx=12
        )
        self.unpaid_card.pack(side="left", padx=(0, 10))

        self.pm_card = tk.Label(
            cards_frame, text="Payment Methods\n0", bg=CARD_BG, fg=TEXT, font=("Helvetica", 12, "bold"),
            bd=1, relief="solid", width=18, height=3, justify="left", anchor="w", padx=12
        )
        self.pm_card.pack(side="left")

        table_panel = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        table_panel.pack(fill="both", expand=True)

        tk.Label(table_panel, text="Bills", bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).pack(anchor="w", padx=12, pady=(10, 6))

        table_wrap = tk.Frame(table_panel, bg=BG_PANEL)
        table_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        cols = ("bill_id", "amount", "due_date", "status", "created_at", "paid_date", "location", "receipt_number")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", height=12)

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
            "due_date": 105,
            "status": 85,
            "created_at": 130,
            "paid_date": 130,
            "location": 160,
            "receipt_number": 160
        }

        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        action_panel = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        action_panel.pack(fill="x", pady=(10, 0))

        tk.Label(action_panel, text="Billing Actions", bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).pack(
            anchor="w", padx=12, pady=(10, 6)
        )

        controls = tk.Frame(action_panel, bg=BG_PANEL)
        controls.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(controls, text="Payment method:", bg=BG_PANEL, fg=TEXT, font=FONT_BODY).pack(side="left")
        self.pm_combo = ttk.Combobox(controls, textvariable=self.pm_var, state="readonly", width=40)
        self.pm_combo.pack(side="left", padx=8)

        tk.Button(
            controls, text="Pay Selected Bill", bg=BG_SIDEBAR, fg=TEXT,
            font=FONT_BTN, relief="flat", command=self.pay_selected
        ).pack(side="left", padx=4)

        tk.Button(
            controls, text="Download Receipt", bg=ACCENT, fg="white",
            font=FONT_BTN, relief="flat", command=self.download_receipt
        ).pack(side="left", padx=4)

        tk.Button(
            controls, text="Add Payment Method", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
            font=FONT_BTN, relief="flat", command=self.add_payment_method_dialog
        ).pack(side="left", padx=4)

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

        bill_count = 0
        unpaid_total = 0.0

        for bill_id, amount, due_date, status, created_at, paid_date, location_name, receipt_number in rows:
            bill_count += 1
            if (status or "").lower() != "paid" and amount is not None:
                unpaid_total += float(amount)

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

        self.bill_count_card.config(text=f"Bills\n{bill_count}")
        self.unpaid_card.config(text=f"Unpaid\n${unpaid_total:.2f}")
        self.pm_card.config(text=f"Payment Methods\n{len(self.payment_method_map)}")

    def refresh(self):
        self._reconnect_db()
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
        win.configure(bg=BG_LIGHT)

        panel = tk.Frame(win, bg=BG_PANEL, bd=1, relief="solid")
        panel.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(panel, text="Add Payment Method", bg=BG_PANEL, fg=TEXT, font=FONT_HEADER).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(14, 10), sticky="w"
        )

        tk.Label(panel, text="Payment Type:", bg=BG_PANEL, fg=TEXT).grid(row=1, column=0, padx=12, pady=8, sticky="w")
        type_var = tk.StringVar(value="Visa")
        type_combo = ttk.Combobox(
            panel,
            textvariable=type_var,
            state="readonly",
            values=["Visa", "MasterCard", "Discover", "Amex", "Debit"],
            width=25
        )
        type_combo.grid(row=1, column=1, padx=12, pady=8, sticky="w")

        tk.Label(panel, text="Card Number:", bg=BG_PANEL, fg=TEXT).grid(row=2, column=0, padx=12, pady=8, sticky="w")
        card_number_var = tk.StringVar()
        tk.Entry(panel, textvariable=card_number_var, width=28, bd=1, relief="solid").grid(
            row=2, column=1, padx=12, pady=8, sticky="w"
        )

        tk.Label(panel, text="Exp Month (MM):", bg=BG_PANEL, fg=TEXT).grid(row=3, column=0, padx=12, pady=8, sticky="w")
        exp_month_var = tk.StringVar()
        tk.Entry(panel, textvariable=exp_month_var, width=12, bd=1, relief="solid").grid(
            row=3, column=1, padx=12, pady=8, sticky="w"
        )

        tk.Label(panel, text="Exp Year (YYYY):", bg=BG_PANEL, fg=TEXT).grid(row=4, column=0, padx=12, pady=8, sticky="w")
        exp_year_var = tk.StringVar()
        tk.Entry(panel, textvariable=exp_year_var, width=12, bd=1, relief="solid").grid(
            row=4, column=1, padx=12, pady=8, sticky="w"
        )

        active_var = tk.IntVar(value=1)
        tk.Checkbutton(
            panel,
            text="Set as active payment method",
            variable=active_var,
            bg=BG_PANEL,
            fg=TEXT,
            selectcolor=BG_PANEL
        ).grid(row=5, column=0, columnspan=2, padx=12, pady=8, sticky="w")

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
                self._reconnect_db()
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

        tk.Button(
            panel,
            text="Save Payment Method",
            bg=BG_SIDEBAR,
            fg=TEXT,
            font=FONT_BTN,
            relief="flat",
            command=save_payment_method
        ).grid(row=6, column=0, columnspan=2, pady=16)

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

        self._reconnect_db()
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

        self._reconnect_db()
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
    root.geometry("1100x680")
    frame = BillingFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()