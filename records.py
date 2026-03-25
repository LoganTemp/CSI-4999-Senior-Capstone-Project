import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ==============================
# Config
# ==============================
DB_NAME = "healthcare.db"
DIRECTORY = "record_files"  # where files are stored locally

if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)


# ==============================
# DB Helpers
# ==============================
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_records_table_exists() -> None:
    """
    Safe guard: creates the records table if it doesn't exist.
    Schema kept the same:
      record_id, patient_id (NOT NULL), staff_id (nullable), filename, filepath, upload_date
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            staff_id INTEGER,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient(patient_id),
            FOREIGN KEY (staff_id) REFERENCES Staff(staff_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_records_patient_id ON records(patient_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_records_staff_id ON records(staff_id)")
    conn.commit()
    conn.close()


def load_clinics() -> Tuple[Dict[str, int], List[str]]:
    """
    Returns:
      clinic_map: display_label -> location_id
      display_list: list of clinic labels
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT location_id, name, city, state, status
        FROM ClinicLocation
        ORDER BY name, city, state
    """)
    rows = cur.fetchall()
    conn.close()

    clinic_map: Dict[str, int] = {}
    display: List[str] = []

    for loc_id, name, city, state, status in rows:
        label = f"{name} ({city}, {state}) [ID {loc_id}]"
        if status:
            label += f" [{status}]"
        clinic_map[label] = loc_id
        display.append(label)

    return clinic_map, display


def load_patients_for_clinic(location_id: int) -> Tuple[Dict[str, int], List[str]]:
    """
    Returns only patients assigned to the selected clinic.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT patient_id, first_name, last_name, email
        FROM Patient
        WHERE location_id = ?
        ORDER BY last_name, first_name
    """, (location_id,))
    rows = cur.fetchall()
    conn.close()

    patient_map: Dict[str, int] = {}
    display: List[str] = []

    for pid, fn, ln, email in rows:
        label = f"{ln}, {fn} (ID {pid})"
        if email:
            label += f"  <{email}>"
        patient_map[label] = pid
        display.append(label)

    return patient_map, display


def unique_dest_path(dest_dir: str, filename: str) -> Tuple[str, str]:
    """
    Prevent overwrite in record_files by renaming:
      report.pdf -> report_2.pdf, report_3.pdf, ...
    Returns (final_filename, final_dest_path)
    """
    base, ext = os.path.splitext(filename)
    candidate = filename
    dest_path = os.path.join(dest_dir, candidate)
    i = 2
    while os.path.exists(dest_path):
        candidate = f"{base}_{i}{ext}"
        dest_path = os.path.join(dest_dir, candidate)
        i += 1
    return candidate, dest_path


# ==============================
# UI App
# ==============================
class RecordsFrame(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent)

        ensure_records_table_exists()

        self.clinic_map, clinics = load_clinics()
        self.patient_map: Dict[str, int] = {}

        # ------------------------------
        # Top frame: clinic + patient + search
        # ------------------------------
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="Clinic Location:").grid(row=0, column=0, sticky="w")
        self.clinic_var = tk.StringVar()
        self.clinic_combo = ttk.Combobox(top, textvariable=self.clinic_var, state="readonly", width=45)
        self.clinic_combo.grid(row=0, column=1, padx=8, sticky="w")
        self.clinic_combo["values"] = clinics
        self.clinic_combo.bind("<<ComboboxSelected>>", lambda e: self.on_clinic_selected())

        ttk.Button(top, text="Reload Clinics", command=self.reload_clinics).grid(row=0, column=2, padx=6)

        ttk.Label(top, text="Patient:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.patient_var = tk.StringVar()
        self.patient_combo = ttk.Combobox(top, textvariable=self.patient_var, state="readonly", width=45)
        self.patient_combo.grid(row=1, column=1, padx=8, sticky="w", pady=(10, 0))
        self.patient_combo.bind("<<ComboboxSelected>>", lambda e: self.update_file_list())

        ttk.Button(top, text="Reload Patients", command=self.reload_patients_for_selected_clinic).grid(
            row=1, column=2, padx=6, pady=(10, 0)
        )

        ttk.Label(top, text="Search filename:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=48)
        search_entry.grid(row=2, column=1, padx=8, sticky="w", pady=(10, 0))
        search_entry.bind("<KeyRelease>", self.update_file_list)

        ttk.Button(top, text="Refresh", command=self.update_file_list).grid(row=2, column=2, padx=6, pady=(10, 0))

        # ------------------------------
        # Table: records list
        # ------------------------------
        mid = ttk.Frame(self, padding=(12, 0, 12, 0))
        mid.pack(fill="both", expand=True)

        cols = ("record_id", "patient", "filename", "upload_date")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=14)
        self.tree.heading("record_id", text="Record ID")
        self.tree.heading("patient", text="Patient")
        self.tree.heading("filename", text="Filename")
        self.tree.heading("upload_date", text="Upload Date")

        self.tree.column("record_id", width=90, anchor="center")
        self.tree.column("patient", width=220)
        self.tree.column("filename", width=280)
        self.tree.column("upload_date", width=180)

        vsb = ttk.Scrollbar(mid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew", pady=10)
        vsb.grid(row=0, column=1, sticky="ns", pady=10)

        mid.grid_rowconfigure(0, weight=1)
        mid.grid_columnconfigure(0, weight=1)

        # ------------------------------
        # Buttons
        # ------------------------------
        bottom = ttk.Frame(self, padding=12)
        bottom.pack(fill="x")

        tk.Button(bottom, text="Upload", bg="#4CAF50", fg="white", width=13, height=2, relief="flat", command=self.upload_file).pack(side="left")
        tk.Button(bottom, text="Download", bg="#2196F3", fg="white", width=13, height=2, relief="flat", command=self.download_file).pack(side="left", padx=8)
        tk.Button(bottom, text="Delete", bg="#e53935", fg="white", width=13, height=2, relief="flat", command=self.delete_file).pack(side="left", padx=8)

        ttk.Label(
            bottom,
            text="Records are grouped by clinic, but still stored under each patient.",
            foreground="gray"
        ).pack(side="right")

        # Default selections
        if clinics:
            self.clinic_combo.current(0)
            self.on_clinic_selected()
        else:
            self.clinic_combo.set("No clinics found")

    # ------------------------------
    # Helpers
    # ------------------------------
    def get_selected_clinic_id(self) -> Optional[int]:
        label = self.clinic_var.get().strip()
        return self.clinic_map.get(label)

    def get_selected_patient_id(self) -> Optional[int]:
        label = self.patient_var.get().strip()
        return self.patient_map.get(label)

    def reload_clinics(self):
        self.clinic_map, clinics = load_clinics()
        self.clinic_combo["values"] = clinics
        if clinics:
            self.clinic_combo.current(0)
            self.on_clinic_selected()
        else:
            self.clinic_combo.set("No clinics found")
            self.patient_combo.set("")
            self.patient_combo["values"] = []
            self.clear_tree()

    def reload_patients_for_selected_clinic(self):
        self.on_clinic_selected()

    def on_clinic_selected(self):
        clinic_id = self.get_selected_clinic_id()
        if not clinic_id:
            self.patient_combo.set("")
            self.patient_combo["values"] = []
            self.clear_tree()
            return

        self.patient_map, patients = load_patients_for_clinic(clinic_id)
        self.patient_combo["values"] = patients

        if patients:
            self.patient_combo.current(0)
        else:
            self.patient_combo.set("No patients in this clinic")

        self.update_file_list()

    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def get_selected_record(self) -> Optional[Tuple[int, str]]:
        """
        Returns (record_id, filename) for selected row.
        """
        sel = self.tree.selection()
        if not sel:
            return None
        values = self.tree.item(sel[0], "values")
        if not values:
            return None
        return int(values[0]), values[2]

    # ------------------------------
    # Refresh list from DB
    # ------------------------------
    def update_file_list(self, event=None):
        clinic_id = self.get_selected_clinic_id()
        if not clinic_id:
            self.clear_tree()
            return

        patient_id = self.get_selected_patient_id()
        search_term = self.search_var.get().strip().lower()
        self.clear_tree()

        try:
            conn = get_conn()
            cur = conn.cursor()

            if patient_id:
                cur.execute("""
                    SELECT
                        r.record_id,
                        p.last_name || ', ' || p.first_name || ' (ID ' || p.patient_id || ')' AS patient_name,
                        r.filename,
                        r.upload_date
                    FROM records r
                    JOIN Patient p ON p.patient_id = r.patient_id
                    WHERE p.location_id = ?
                      AND r.patient_id = ?
                    ORDER BY r.upload_date DESC
                """, (clinic_id, patient_id))
            else:
                cur.execute("""
                    SELECT
                        r.record_id,
                        p.last_name || ', ' || p.first_name || ' (ID ' || p.patient_id || ')' AS patient_name,
                        r.filename,
                        r.upload_date
                    FROM records r
                    JOIN Patient p ON p.patient_id = r.patient_id
                    WHERE p.location_id = ?
                    ORDER BY r.upload_date DESC
                """, (clinic_id,))

            rows = cur.fetchall()
            conn.close()

            for record_id, patient_name, filename, upload_date in rows:
                if search_term and search_term not in (filename or "").lower():
                    continue
                self.tree.insert("", "end", values=(record_id, patient_name, filename, upload_date))

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    # ------------------------------
    # Upload File
    # ------------------------------
    def upload_file(self):
        clinic_id = self.get_selected_clinic_id()
        if not clinic_id:
            messagebox.showwarning("Clinic Required", "Please select a clinic first.")
            return

        patient_id = self.get_selected_patient_id()
        if not patient_id:
            messagebox.showwarning("Patient Required", "Please select a patient in the selected clinic before uploading.")
            return

        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        original_filename = os.path.basename(file_path)
        final_filename, dest_path = unique_dest_path(DIRECTORY, original_filename)

        try:
            shutil.copy(file_path, dest_path)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            staff_id = None  # until login system exists

            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO records (patient_id, staff_id, filename, filepath, upload_date) VALUES (?, ?, ?, ?, ?)",
                (patient_id, staff_id, final_filename, dest_path, upload_date)
            )
            conn.commit()
            conn.close()

            self.update_file_list()
            messagebox.showinfo("Success", f"{final_filename} uploaded successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------------------
    # Download File
    # ------------------------------
    def download_file(self):
        selected = self.get_selected_record()
        if not selected:
            messagebox.showwarning("Select a file", "Please select a record to download.")
            return

        record_id, filename = selected

        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT filepath FROM records WHERE record_id = ?", (record_id,))
            row = cur.fetchone()
            conn.close()

            if not row:
                messagebox.showerror("Not found", "That record was not found in the database.")
                return

            source_path = row[0]
            if not os.path.exists(source_path):
                messagebox.showerror("Missing file", "The stored file path does not exist on disk.")
                return

            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if not save_path:
                return

            shutil.copy(source_path, save_path)
            messagebox.showinfo("Success", f"{filename} downloaded successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ------------------------------
    # Delete File
    # ------------------------------
    def delete_file(self):
        selected = self.get_selected_record()
        if not selected:
            messagebox.showwarning("Select a file", "Please select a record to delete.")
            return

        record_id, filename = selected

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{filename}'?")
        if not confirm:
            return

        try:
            conn = get_conn()
            cur = conn.cursor()

            cur.execute("SELECT filepath FROM records WHERE record_id = ?", (record_id,))
            row = cur.fetchone()

            if row:
                file_path = row[0]
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

            cur.execute("DELETE FROM records WHERE record_id = ?", (record_id,))
            conn.commit()
            conn.close()

            self.update_file_list()
            messagebox.showinfo("Success", f"{filename} deleted successfully.")

        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("CareFlow - Medical Records")
    root.geometry("950x560")
    frame = RecordsFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()