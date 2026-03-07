import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import re
from datetime import datetime

DB_NAME = "healthcare.db"


def is_valid_date_yyyy_mm_dd(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


class BillingPatientFrame(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.conn = None
        self.patient_map = {}        # display -> patient_id
        self.payment_method_map = {} # display -> payment_method_id

        self._build_ui()
        self._load_patients()

    def _db(self):
        if self.conn is None:
            self.conn = sqlite3.connect(DB_NAME)
        return self.conn

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        # Top controls
        top = ttk.LabelFrame(root, text="Patient", padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Select patient:").grid(row=0, column=0, sticky="w")
        self.patient_var = tk.StringVar()
        self.patient_combo = ttk.Combobox(top, textvariable=self.patient_var, state="readonly", width=45)
        self.patient_combo.grid(row=0, column=1, padx=8, sticky="w")
        self.patient_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(top, text="Refresh", command=self.refresh).grid(row=0, column=2, padx=6)

        # Bills table
        mid = ttk.LabelFrame(root, text="Bills", padding=10)
        mid.pack(fill="both", expand=True, pady=(10, 10))

        cols = ("bill_id", "amount", "due_date", "status", "created_at", "location")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=12)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120 if c != "created_at" else 160)
        self.tree.column("bill_id", width=70)
        self.tree.column("amount", width=90)
        self.tree.column("status", width=90)
        self.tree.column("location", width=160)

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        # Payment controls
        bottom = ttk.LabelFrame(root, text="Pay selected bill", padding=10)
        bottom.pack(fill="x")

        ttk.Label(bottom, text="Payment method:").grid(row=0, column=0, sticky="w")
        self.pm_var = tk.StringVar()
        self.pm_combo = ttk.Combobox(bottom, textvariable=self.pm_var, state="readonly", width=45)
        self.pm_combo.grid(row=0, column=1, padx=8, sticky="w")

        ttk.Button(bottom, text="Mark as PAID", command=self.pay_selected).grid(row=0, column=2, padx=6)

        ttk.Label(
            root,
            text="Note: For now this marks the bill status as 'paid'. (No card processing; demo-only.)",
            foreground="gray"
        ).pack(anchor="w")

    def _load_patients(self):
        try:
            cur = self._db().cursor()
            cur.execute("""
                SELECT patient_id, first_name, last_name, email
                FROM Patient
                ORDER BY last_name, first_name
            """)
            rows = cur.fetchall()

            self.patient_map.clear()
            display = []
            for pid, fn, ln, email in rows:
                label = f"{ln}, {fn}  (ID {pid})" + (f"  <{email}>" if email else "")
                self.patient_map[label] = pid
                display.append(label)

            self.patient_combo["values"] = display
            if display:
                self.patient_combo.current(0)
                self.refresh()
            else:
                self.patient_combo.set("No patients found")
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def _load_payment_methods(self, patient_id: int):
        try:
            cur = self._db().cursor()
            cur.execute("""
                SELECT payment_method_id, type, last4, exp_month, exp_year, active_flag
                FROM PaymentMethod
                WHERE patient_id = ?
                ORDER BY active_flag DESC, payment_method_id DESC
            """, (patient_id,))
            rows = cur.fetchall()

            self.payment_method_map.clear()
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
                self.pm_combo.set("No payment methods (ok for demo)")
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def refresh(self):
        label = self.patient_var.get().strip()
        if not label or label not in self.patient_map:
            return

        patient_id = self.patient_map[label]
        self._load_payment_methods(patient_id)
        self._load_bills(patient_id)

    def _load_bills(self, patient_id: int):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            cur = self._db().cursor()
            cur.execute("""
                SELECT
                    b.bill_id,
                    b.amount,
                    b.due_date,
                    b.status,
                    b.created_at,
                    COALESCE(cl.name, '') AS location_name
                FROM Bill b
                LEFT JOIN ClinicLocation cl ON cl.location_id = b.location_id
                WHERE b.patient_id = ?
                ORDER BY
                    CASE WHEN b.status = 'paid' THEN 1 ELSE 0 END,
                    b.due_date ASC,
                    b.created_at DESC
            """, (patient_id,))
            rows = cur.fetchall()

            for bill_id, amount, due_date, status, created_at, location_name in rows:
                self.tree.insert("", "end", values=(
                    bill_id,
                    f"{amount:.2f}" if amount is not None else "",
                    due_date or "",
                    status or "",
                    created_at or "",
                    location_name or ""
                ))
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def pay_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select a bill", "Please select a bill in the table.")
            return

        values = self.tree.item(sel[0], "values")
        bill_id = values[0]
        status = (values[3] or "").lower()

        if status == "paid":
            messagebox.showinfo("Already paid", "That bill is already marked as paid.")
            return

        # Payment method optional for demo, but we keep UI
        pm_label = self.pm_var.get().strip()
        if pm_label and "No payment methods" not in pm_label and pm_label not in self.payment_method_map:
            messagebox.showwarning("Payment method", "Please select a valid payment method (or leave it).")
            return

        if not messagebox.askyesno("Confirm payment", f"Mark bill #{bill_id} as PAID?"):
            return

        try:
            cur = self._db().cursor()
            cur.execute("UPDATE Bill SET status = 'paid' WHERE bill_id = ?", (bill_id,))
            self._db().commit()
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))
            return

        self.refresh()
        messagebox.showinfo("Success", f"Bill #{bill_id} marked as paid.")

    def on_close(self):
        try:
            if self.conn:
                self.conn.close()
        finally:
            self.destroy()


class BillingPatientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow - Patient Billing")
        self.geometry("820x520")
        frame = BillingPatientFrame(self)
        frame.pack(fill="both", expand=True)


if __name__ == "__main__":
    app = BillingPatientApp()
    app.mainloop()