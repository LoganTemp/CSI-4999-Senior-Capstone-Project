import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

DB_NAME = "healthcare.db"

BILLING_TEMPLATES = {
    "Checkup": 75.00,
    "Follow-up": 50.00,
    "Lab work": 120.00,
    "Vaccination": 40.00,
    "Other (custom)": None,
}


def is_valid_date_yyyy_mm_dd(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


class BillingStaffApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow - Staff Billing (Create Bill)")
        self.geometry("760x520")

        self.conn = None
        self.patient_map = {}   # display -> patient_id
        self.location_map = {}  # display -> location_id

        self._build_ui()
        self._load_locations()
        self._load_patients()

    def _db(self):
        if self.conn is None:
            self.conn = sqlite3.connect(DB_NAME)
        return self.conn

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        form = ttk.LabelFrame(root, text="Create Bill", padding=10)
        form.pack(fill="x")

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

        btns = ttk.Frame(root, padding=(0, 10))
        btns.pack(fill="x")

        ttk.Button(btns, text="Create Bill", command=self.create_bill).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=8)

        # Recent bills
        recent = ttk.LabelFrame(root, text="Recent Bills (latest 25)", padding=10)
        recent.pack(fill="both", expand=True)

        cols = ("bill_id", "patient", "amount", "due_date", "status", "created_at")
        self.tree = ttk.Treeview(recent, columns=cols, show="headings", height=10)
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
        self._load_recent_bills()

    def _load_patients(self):
        try:
            cur = self._db().cursor()
            cur.execute("""
                SELECT patient_id, first_name, last_name, email, location_id
                FROM Patient
                ORDER BY last_name, first_name
            """)
            rows = cur.fetchall()

            self.patient_map.clear()
            display = []
            for pid, fn, ln, email, loc_id in rows:
                label = f"{ln}, {fn}  (ID {pid})" + (f"  <{email}>" if email else "")
                self.patient_map[label] = pid
                display.append(label)

            self.patient_combo["values"] = display
            if display:
                self.patient_combo.current(0)
                self._auto_location_from_patient()
            else:
                self.patient_combo.set("No patients found")
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def _load_locations(self):
        try:
            cur = self._db().cursor()
            cur.execute("SELECT location_id, name, status FROM ClinicLocation ORDER BY name")
            rows = cur.fetchall()

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

    def _auto_location_from_patient(self):
        label = self.patient_var.get().strip()
        if not label or label not in self.patient_map:
            return
        pid = self.patient_map[label]

        try:
            cur = self._db().cursor()
            cur.execute("SELECT location_id FROM Patient WHERE patient_id = ?", (pid,))
            row = cur.fetchone()
            if not row:
                return
            loc_id = row[0]
        except sqlite3.Error:
            return

        # Select matching location in dropdown
        if loc_id is None:
            return

        for disp, mapped_id in self.location_map.items():
            if mapped_id == loc_id:
                self.loc_combo.set(disp)
                break

    def _apply_template(self):
        name = self.template_var.get().strip() or self.template_combo.get().strip()
        amt = BILLING_TEMPLATES.get(name)

        if amt is None:
            self.amount_entry.configure(state="normal")
            if self.amount_var.get().strip() == "":
                self.amount_var.set("")
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

        amount_str = self.amount_var.get().strip()
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid amount", "Amount must be a positive number (e.g., 75.00).")
            return

        if not messagebox.askyesno("Confirm", f"Create bill for {patient_label} for ${amount:.2f} due {due}?"):
            return

        try:
            cur = self._db().cursor()
            cur.execute("""
                INSERT INTO Bill (patient_id, location_id, amount, due_date, status)
                VALUES (?, ?, ?, ?, 'unpaid')
            """, (patient_id, location_id, amount, due))
            self._db().commit()
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))
            return

        messagebox.showinfo("Success", "Bill created.")
        self._load_recent_bills()

    def _load_recent_bills(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            cur = self._db().cursor()
            cur.execute("""
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
            """)
            rows = cur.fetchall()

            for bill_id, patient, amount, due_date, status, created_at in rows:
                self.tree.insert("", "end", values=(
                    bill_id,
                    patient,
                    f"{amount:.2f}" if amount is not None else "",
                    due_date or "",
                    status or "",
                    created_at or ""
                ))
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", str(e))

    def on_close(self):
        try:
            if self.conn:
                self.conn.close()
        finally:
            self.destroy()


if __name__ == "__main__":
    app = BillingStaffApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()