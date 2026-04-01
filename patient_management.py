import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional

DB_NAME = "healthcare.db"

BG_LIGHT        = "#e6f2ec"
BG_SIDEBAR      = "#5FAF90"
BG_SIDEBAR_LIGHT= "#A2DDC6"
BG_PANEL        = "#ffffff"
ACCENT          = "#308684"
CARD_BG         = "#f7fff7"
TEXT            = "#0b3d2e"
BTN_DANGER      = "#c0392b"
BTN_SAFE        = "#308684"
BTN_INFO        = "#2980b9"

SIDEBAR_WIDTH = 160
FONT_TITLE    = ("Helvetica", 18, "bold")
FONT_HEADER   = ("Helvetica", 13, "bold")
FONT_TABLE    = ("Helvetica", 10)
FONT_NAV      = ("Helvetica", 10)
FONT_LOGO     = ("Helvetica", 13, "bold")



class PatientManagementFrame(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent, bg=BG_LIGHT)
        self._selected_patient_id = None
        self._build_ui()
        self._load_patients()

    # ---------------- UI ----------------
    def _build_ui(self):
        #left = tk.Frame(self, bg=BG_COLOR)
        #left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=12, pady=12)

        left = tk.Frame(outer, bg=BG_PANEL, bd=1, relief="solid")
        left.pack(side="left", fill="both", expand=True, padx=(0,10), pady=0)

        #tk.Label(left, text="Patients", font=FONT_LARGE, bg=BG_COLOR).pack(anchor="w")

        tk.Label(left, text="Patients", font=FONT_TITLE, bg=BG_PANEL, fg=TEXT).pack(anchor="w", padx=14, pady=(10,0))


        style = ttk.Style()
        style.theme_use("clam")

        style.configure("CareFlow.Treeview",
            background=CARD_BG,
            fieldbackground=CARD_BG,
            foreground=TEXT,
            rowheight=28,
            font=FONT_TABLE
        )

        style.configure("CareFlow.Treeview.Heading",
            background="#A2DDC6",
            foreground=TEXT,
            font=("Helvetica", 10, "bold"),
            relief="flat"
        )

        style.map("CareFlow.Treeview",
            background=[("selected", "#5FAF90")],
            foreground=[("selected", TEXT)]
        )


        cols = ("ID", "Name", "Phone", "Email")
        #self.tree = ttk.Treeview(left, columns=cols, show="headings")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", style="CareFlow.Treeview")

        #for col in cols:
            #self.tree.heading(col, text=col)

        col_config = {
            "ID": ("ID", 60, "center"),
            "Name": ("Name", 180, "w"),
            "Phone": ("Phone", 120, "center"),
            "Email": ("Email", 200, "w"),
        }

        for col, (text, width, anchor) in col_config.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)

        tree_frame = tk.Frame(left, bg=BG_PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=8) 

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.tree.tag_configure("inactive", foreground="gray")

        # ---------- RIGHT FORM ----------
        #right = tk.Frame(self, bg=CONTAINER_COLOR, padx=15, pady=15)
        right = tk.Frame(outer, bg=BG_PANEL, padx=15, pady=15, bd=1, relief="solid")
        right.pack(side="left", fill="y")
        #right.pack(side="left", fill="y", padx=10, pady=10)

        #tk.Label(right, text="Patient Details", font=FONT_LARGE, bg=CONTAINER_COLOR).grid(row=0, column=0, columnspan=2)
        tk.Label(right, text="Patient Details", font=FONT_HEADER, bg=BG_PANEL, fg=TEXT).grid(row=0, column=0, columnspan=2, pady=(0,10))

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
            tk.Label(right, text=label, bg=BG_PANEL).grid(row=i, column=0, sticky="w")
            #e = tk.Entry(right, width=25)
            e = tk.Entry(right, width=25, bg=CARD_BG, fg=TEXT, relief="flat")
            e.grid(row=i, column=1, pady=4, padx=(6,0))
            self.entries[key] = e

        # Buttons
        btn_cfg = dict(
            relief="flat",
            fg="white",
            padx=12,
            pady=6,
            font=("Helvetica", 10, "bold"),
            cursor="hand2"
        )

        btn_frame = tk.Frame(right, bg=BG_PANEL)
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(12,0))

        tk.Button(btn_frame, text="Add", bg=BTN_SAFE,
                command=self._add_patient, **btn_cfg).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Update", bg=BTN_INFO,
                command=self._update_patient, **btn_cfg).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Deactivate", bg="#f39c12",
                command=self.soft_delete_patient, **btn_cfg).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Delete", bg=BTN_DANGER,
                command=self._delete_patient, **btn_cfg).pack(side="left", padx=4)

        tk.Button(btn_frame, text="Clear", bg="#95a5a6",
                command=self._clear_form, **btn_cfg).pack(side="left", padx=4)

    # ---------------- LOAD ----------------
    def _load_patients(self):
        conn = sqlite3.connect(DB_NAME)
        # rows = conn.execute("SELECT patient_id, first_name, last_name, phone, email FROM Patient").fetchall()
        rows = conn.execute("""
            SELECT patient_id, first_name, last_name, phone, email, active_flag
            FROM Patient
        """).fetchall()
        conn.close()

        self.tree.delete(*self.tree.get_children())

        #for row in rows:
        #    pid, fn, ln, phone, email = row
        #    self.tree.insert("", "end", iid=str(pid),
        #                     values=(pid, f"{fn} {ln}", phone, email))

        for row in rows:
            pid, fn, ln, phone, email, active = row

            tag = "inactive" if active == 0 else ""

            self.tree.insert(
                "",
                "end",
                iid=str(pid),
                values=(pid, f"{fn} {ln}", phone, email),
                tags=(tag,)
            )

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
    def soft_delete_patient(self):
        if not self._selected_patient_id:
            messagebox.showwarning("Select", "Select a patient first.")
            return

        if not messagebox.askyesno("Confirm", "Deactivate this patient?"):
            return

        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            cur.execute("""
                UPDATE Patient
                SET active_flag = 0
                WHERE patient_id = ?
            """, (self._selected_patient_id,))

            conn.commit()
            conn.close()

            messagebox.showinfo("Success", "Patient deactivated.")
            self._load_patients()
            self._clear_form()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete patient:\n\n{e}")

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