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



class PatientManagementFrame(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, bg=BG_COLOR)
        self._selected_patient_id = None
        self._build_ui()
        self._load_patients()

    # ---------------- UI ----------------
    def _build_ui(self):
        left = tk.Frame(self, bg=BG_COLOR)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        tk.Label(left, text="Patients", font=FONT_LARGE, bg=BG_COLOR).pack(anchor="w")

        cols = ("ID", "Name", "Phone", "Email")
        self.tree = ttk.Treeview(left, columns=cols, show="headings")

        for col in cols:
            self.tree.heading(col, text=col)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- RIGHT FORM ----------
        right = tk.Frame(self, bg=CONTAINER_COLOR, padx=15, pady=15)
        right.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(right, text="Patient Details", font=FONT_LARGE, bg=CONTAINER_COLOR).grid(row=0, column=0, columnspan=2)

        self.entries = {}
        fields = [
            ("First Name", "first_name"),
            ("Last Name", "last_name"),
            ("DOB", "dob"),
            ("Sex", "sex"),
            ("Phone", "phone"),
            ("Email", "email"),
            ("Address", "address"),
            ("Allergies", "allergies"),
            ("Conditions", "conditions"),
            ("Medications", "medications"),
            ("Notes", "notes"),
            ("Emergency Contact", "emergency_contact")
        ]

        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(right, text=label, bg=CONTAINER_COLOR).grid(row=i, column=0, sticky="w")
            e = tk.Entry(right, width=25)
            e.grid(row=i, column=1, pady=2)
            self.entries[key] = e

        # Buttons
        btn_frame = tk.Frame(right, bg=CONTAINER_COLOR)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add Patient", bg=BTN_GREEN, fg="white",
                  command=self._add_patient).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Update Patient", bg=BTN_BLUE, fg="white",
                  command=self._update_patient).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Remove Patient", bg="#FF9800", fg="white",
                  command=self._remove_patient).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Delete Patient", bg=BTN_RED, fg="white",
                  command=self._delete_patient).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Clear", bg=BTN_GRAY,
                  command=self._clear_form).pack(side="left", padx=4)

    # ---------------- LOAD ----------------
    def _load_patients(self):
        conn = sqlite3.connect(DB_NAME)
        rows = conn.execute("SELECT patient_id, first_name, last_name, phone, email FROM Patient").fetchall()
        conn.close()

        self.tree.delete(*self.tree.get_children())

        for row in rows:
            pid, fn, ln, phone, email = row
            self.tree.insert("", "end", iid=str(pid),
                             values=(pid, f"{fn} {ln}", phone, email))

    # ---------------- SELECT ----------------
    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        self._selected_patient_id = int(selected[0])

        conn = sqlite3.connect(DB_NAME)
        row = conn.execute("""
            SELECT first_name, last_name, dob, sex, phone, email, address,
                   allergies, conditions, medications, notes, emergency_contact
            FROM Patient WHERE patient_id=?
        """, (self._selected_patient_id,)).fetchone()
        conn.close()

        if row:
            keys = list(self.entries.keys())
            for i, key in enumerate(keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[i] if row[i] else "")

    # ---------------- COLLECT ----------------
    def _collect(self):
        return {k: e.get().strip() for k, e in self.entries.items()}

    # ---------------- ADD ----------------
    def _add_patient(self):
        data = self._collect()

        conn = sqlite3.connect(DB_NAME)
        conn.execute("""
            INSERT INTO Patient (
                first_name, last_name, dob, sex, phone, email,
                address, allergies, conditions, medications, notes, emergency_contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tuple(data.values()))
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Patient added.")
        self._load_patients()
        self._clear_form()

    # ---------------- UPDATE ----------------
    def _update_patient(self):
        if not self._selected_patient_id:
            messagebox.showwarning("Select", "Select a patient first.")
            return

        data = self._collect()

        conn = sqlite3.connect(DB_NAME)
        conn.execute("""
            UPDATE Patient SET
                first_name=?, last_name=?, dob=?, sex=?, phone=?, email=?,
                address=?, allergies=?, conditions=?, medications=?, notes=?, emergency_contact=?
            WHERE patient_id=?
        """, (*data.values(), self._selected_patient_id))
        conn.commit()
        conn.close()

        messagebox.showinfo("Updated", "Patient updated.")
        self._load_patients()

    # ---------------- REMOVE ----------------
    def _remove_patient(self):
        if not self._selected_patient_id:
            return

        messagebox.showinfo("Info", "Soft delete not implemented (no active_flag column).")

    # ---------------- DELETE ----------------
    def _delete_patient(self):
        if not self._selected_patient_id:
            return

        if not messagebox.askyesno("Confirm", "Delete this patient?"):
            return

        conn = sqlite3.connect(DB_NAME)
        conn.execute("DELETE FROM Patient WHERE patient_id=?", (self._selected_patient_id,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Deleted", "Patient removed.")
        self._load_patients()
        self._clear_form()

    # ---------------- CLEAR ----------------
    def _clear_form(self):
        for e in self.entries.values():
            e.delete(0, tk.END)
        self._selected_patient_id = None