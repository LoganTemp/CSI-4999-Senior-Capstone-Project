#!/usr/bin/env python3
"""
careflow_records.py

CareFlow Medical Records page with the dashboard's sidebar, color scheme,
and visual style integrated.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# ==============================
# Config / Styles (from dashboard)
# ==============================
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

DB_NAME   = "healthcare.db"
DIRECTORY = "record_files"

if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)


# ==============================
# DB Helpers (unchanged logic)
# ==============================
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_records_table_exists() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            record_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id  INTEGER NOT NULL,
            staff_id    INTEGER,
            filename    TEXT NOT NULL,
            filepath    TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patient(patient_id),
            FOREIGN KEY (staff_id)   REFERENCES Staff(staff_id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_records_patient_id ON records(patient_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_records_staff_id   ON records(staff_id)")
    conn.commit()
    conn.close()


def load_clinics() -> Tuple[Dict[str, int], List[str]]:
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT location_id, name, city, state, status
        FROM ClinicLocation
        ORDER BY name, city, state
    """)
    rows = cur.fetchall()
    conn.close()

    clinic_map: Dict[str, int] = {}
    display:    List[str]      = []
    for loc_id, name, city, state, status in rows:
        label = f"{name} ({city}, {state}) [ID {loc_id}]"
        if status:
            label += f" [{status}]"
        clinic_map[label] = loc_id
        display.append(label)
    return clinic_map, display


def load_patients_for_clinic(location_id: int) -> Tuple[Dict[str, int], List[str]]:
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT patient_id, first_name, last_name, email
        FROM Patient
        WHERE location_id = ?
        ORDER BY last_name, first_name
    """, (location_id,))
    rows = cur.fetchall()
    conn.close()

    patient_map: Dict[str, int] = {}
    display:     List[str]      = []
    for pid, fn, ln, email in rows:
        label = f"{ln}, {fn} (ID {pid})"
        if email:
            label += f"  <{email}>"
        patient_map[label] = pid
        display.append(label)
    return patient_map, display


def unique_dest_path(dest_dir: str, filename: str) -> Tuple[str, str]:
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
# Nav helper
# ==============================
def on_nav(name: str):
    print(f"[NAV] {name} clicked")


# ==============================
# Main Window
# ==============================
class CareFlowRecords(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow Admin Portal - Records")
        self.geometry("1150x700")
        self.configure(bg=BG_LIGHT)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        ensure_records_table_exists()
        self._build_sidebar()
        self._build_header()
        self._build_content()

    # ------------------------------------------------------------------
    # Sidebar  (matches dashboard exactly)
    # ------------------------------------------------------------------
    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH, relief="flat")
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        sidebar.grid_propagate(False)

        logo_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        logo_frame.pack(fill="x", padx=12, pady=(14, 8))
        tk.Label(logo_frame, text="CareFlow", bg=BG_SIDEBAR,
                 fg=TEXT, font=FONT_LOGO).pack(anchor="w")

        nav_items = [
            ("Dashboard", lambda: on_nav("Dashboard")),
            ("Patient",   lambda: on_nav("Patient")),
            ("Staff",     lambda: on_nav("Staff")),
            ("Clinic",    lambda: on_nav("Clinic")),
            ("Records",   lambda: on_nav("Records")),   # active page
            ("Billing",   lambda: on_nav("Billing")),
        ]

        for label, cmd in nav_items:
            is_active = label == "Records"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR
            fg = TEXT
            b = tk.Button(
                sidebar, text=label, anchor="w", command=cmd,
                relief="flat", bg=bg, fg=fg,
                font=FONT_NAV, padx=14, pady=6,
                activebackground=ACCENT, activeforeground="white",
            )
            b.pack(fill="x", pady=2, padx=8)

    # ------------------------------------------------------------------
    # Header  (matches dashboard style)
    # ------------------------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self, bg=BG_PANEL, height=90, relief="flat")
        header.grid(row=0, column=1, sticky="new", padx=(12, 12), pady=(12, 0))
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        left = tk.Frame(header, bg=BG_PANEL)
        left.grid(row=0, column=0, sticky="w", padx=14, pady=14)
        tk.Label(left, text="Medical Records", bg=BG_PANEL,
                 fg=TEXT, font=FONT_TITLE).pack(anchor="w")

        right = tk.Frame(header, bg=BG_PANEL)
        right.grid(row=0, column=1, sticky="e", padx=14, pady=14)
        tk.Label(right, text="Signed in as\nAdministrators Name",
                 bg=BG_PANEL, fg=TEXT, justify="right").pack(anchor="e")
        tk.Button(right, text="♡", bg=BG_SIDEBAR, fg=TEXT, width=3,
                  relief="flat", command=lambda: on_nav("Profile")).pack(anchor="e", pady=(4, 0))

    # ------------------------------------------------------------------
    # Main content area
    # ------------------------------------------------------------------
    def _build_content(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.grid(row=1, column=1, sticky="nsew", padx=(12, 12), pady=(8, 12))
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self._build_filter_bar(outer)
        self._build_table(outer)
        self._build_action_bar(outer)

        # initial load
        self.clinic_map, clinics = load_clinics()
        self.patient_map: Dict[str, int] = {}
        self.clinic_combo["values"] = clinics
        if clinics:
            self.clinic_combo.current(0)
            self._on_clinic_selected()
        else:
            self.clinic_combo.set("No clinics found")

    # ------------------------------------------------------------------
    # Filter bar (clinic / patient / search)
    # ------------------------------------------------------------------
    def _build_filter_bar(self, parent):
        panel = tk.Frame(parent, bg=BG_PANEL, relief="flat", bd=0)
        panel.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        panel.grid_columnconfigure(1, weight=1)

        # Style for ttk widgets to match theme
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=CARD_BG, background=BG_PANEL,
                        foreground=TEXT, selectbackground=ACCENT)
        style.configure("TEntry",
                        fieldbackground=CARD_BG, foreground=TEXT)

        def lbl(text, row):
            tk.Label(panel, text=text, bg=BG_PANEL, fg=TEXT,
                     font=("Helvetica", 10, "bold")).grid(
                row=row, column=0, sticky="w", padx=(14, 6), pady=6)

        def reload_btn(text, cmd, row):
            tk.Button(panel, text=text, bg=BG_SIDEBAR, fg=TEXT,
                      relief="flat", padx=10, pady=3,
                      activebackground=BG_SIDEBAR_LIGHT, activeforeground=TEXT,
                      command=cmd).grid(row=row, column=2, padx=10, pady=6, sticky="w")

        # Row 0 – Clinic
        lbl("Clinic Location:", 0)
        self.clinic_var   = tk.StringVar()
        self.clinic_combo = ttk.Combobox(panel, textvariable=self.clinic_var,
                                         state="readonly", width=52)
        self.clinic_combo.grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=6)
        self.clinic_combo.bind("<<ComboboxSelected>>", lambda e: self._on_clinic_selected())
        reload_btn("Reload Clinics", self._reload_clinics, 0)

        # Row 1 – Patient
        lbl("Patient:", 1)
        self.patient_var   = tk.StringVar()
        self.patient_combo = ttk.Combobox(panel, textvariable=self.patient_var,
                                          state="readonly", width=52)
        self.patient_combo.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=6)
        self.patient_combo.bind("<<ComboboxSelected>>", lambda e: self._update_file_list())
        reload_btn("Reload Patients", self._reload_patients, 1)

        # Row 2 – Search
        lbl("Search filename:", 2)
        self.search_var = tk.StringVar()
        se = ttk.Entry(panel, textvariable=self.search_var, width=54)
        se.grid(row=2, column=1, sticky="ew", padx=(0, 6), pady=6)
        se.bind("<KeyRelease>", self._update_file_list)
        reload_btn("Refresh", self._update_file_list, 2)

    # ------------------------------------------------------------------
    # Records table
    # ------------------------------------------------------------------
    def _build_table(self, parent):
        container = tk.Frame(parent, bg=BG_PANEL, bd=1, relief="solid")
        container.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Section label inside the panel
        lbl_frame = tk.Frame(container, bg=BG_PANEL)
        lbl_frame.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(lbl_frame, text="Records", bg=BG_PANEL,
                 fg=TEXT, font=FONT_HEADER).pack(anchor="w")

        # Treeview styled to match dashboard palette
        style = ttk.Style()
        style.configure("CareFlow.Treeview",
                        background=CARD_BG, fieldbackground=CARD_BG,
                        foreground=TEXT, rowheight=28,
                        font=FONT_TABLE)
        style.configure("CareFlow.Treeview.Heading",
                        background=BG_SIDEBAR_LIGHT, foreground=TEXT,
                        font=("Helvetica", 10, "bold"), relief="flat")
        style.map("CareFlow.Treeview",
                  background=[("selected", BG_SIDEBAR)],
                  foreground=[("selected", TEXT)])
        style.map("CareFlow.Treeview.Heading",
                  background=[("active", BG_SIDEBAR)],
                  foreground=[("active", TEXT)])

        tree_frame = tk.Frame(container, bg=BG_PANEL)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=8)

        cols = ("record_id", "patient", "filename", "upload_date")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 style="CareFlow.Treeview", height=14)

        headings = {
            "record_id":   ("Record ID",   80,  "center"),
            "patient":     ("Patient",     230, "w"),
            "filename":    ("Filename",    290, "w"),
            "upload_date": ("Upload Date", 175, "center"),
        }
        for col, (text, width, anchor) in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    # ------------------------------------------------------------------
    # Action buttons bar
    # ------------------------------------------------------------------
    def _build_action_bar(self, parent):
        bar = tk.Frame(parent, bg=BG_LIGHT)
        bar.grid(row=2, column=0, sticky="ew")

        btn_cfg = dict(relief="flat", fg="white", padx=16, pady=8,
                       font=("Helvetica", 10, "bold"),
                       activeforeground="white", cursor="hand2")

        tk.Button(bar, text="⬆  Upload",   bg=BTN_SAFE,   activebackground=TEXT,
                  command=self._upload_file,   **btn_cfg).pack(side="left", padx=(0, 8))
        tk.Button(bar, text="⬇  Download", bg=BTN_INFO,   activebackground="#1a5276",
                  command=self._download_file, **btn_cfg).pack(side="left", padx=(0, 8))
        tk.Button(bar, text="✕  Delete",   bg=BTN_DANGER, activebackground="#922b21",
                  command=self._delete_file,   **btn_cfg).pack(side="left")

        tk.Label(bar,
                 text="Records are grouped by clinic and stored per patient.",
                 bg=BG_LIGHT, fg="#5a8a76", font=("Helvetica", 9)).pack(side="right")

    # ------------------------------------------------------------------
    # Event / data methods  (unchanged logic, new variable names)
    # ------------------------------------------------------------------
    def _get_clinic_id(self) -> Optional[int]:
        return self.clinic_map.get(self.clinic_var.get().strip())

    def _get_patient_id(self) -> Optional[int]:
        return self.patient_map.get(self.patient_var.get().strip())

    def _reload_clinics(self):
        self.clinic_map, clinics = load_clinics()
        self.clinic_combo["values"] = clinics
        if clinics:
            self.clinic_combo.current(0)
            self._on_clinic_selected()
        else:
            self.clinic_combo.set("No clinics found")
            self.patient_combo.set("")
            self.patient_combo["values"] = []
            self._clear_tree()

    def _reload_patients(self):
        self._on_clinic_selected()

    def _on_clinic_selected(self):
        clinic_id = self._get_clinic_id()
        if not clinic_id:
            self.patient_combo.set("")
            self.patient_combo["values"] = []
            self._clear_tree()
            return
        self.patient_map, patients = load_patients_for_clinic(clinic_id)
        self.patient_combo["values"] = patients
        if patients:
            self.patient_combo.current(0)
        else:
            self.patient_combo.set("No patients in this clinic")
        self._update_file_list()

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _get_selected_record(self) -> Optional[Tuple[int, str]]:
        sel = self.tree.selection()
        if not sel:
            return None
        v = self.tree.item(sel[0], "values")
        return (int(v[0]), v[2]) if v else None

    def _update_file_list(self, event=None):
        clinic_id = self._get_clinic_id()
        if not clinic_id:
            self._clear_tree()
            return
        patient_id  = self._get_patient_id()
        search_term = self.search_var.get().strip().lower()
        self._clear_tree()
        try:
            conn = get_conn()
            cur  = conn.cursor()
            if patient_id:
                cur.execute("""
                    SELECT r.record_id,
                           p.last_name || ', ' || p.first_name || ' (ID ' || p.patient_id || ')' AS patient_name,
                           r.filename, r.upload_date
                    FROM records r
                    JOIN Patient p ON p.patient_id = r.patient_id
                    WHERE p.location_id = ? AND r.patient_id = ?
                    ORDER BY r.upload_date DESC
                """, (clinic_id, patient_id))
            else:
                cur.execute("""
                    SELECT r.record_id,
                           p.last_name || ', ' || p.first_name || ' (ID ' || p.patient_id || ')' AS patient_name,
                           r.filename, r.upload_date
                    FROM records r
                    JOIN Patient p ON p.patient_id = r.patient_id
                    WHERE p.location_id = ?
                    ORDER BY r.upload_date DESC
                """, (clinic_id,))
            for record_id, patient_name, filename, upload_date in cur.fetchall():
                if search_term and search_term not in (filename or "").lower():
                    continue
                self.tree.insert("", "end", values=(record_id, patient_name, filename, upload_date))
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))

    def _upload_file(self):
        if not self._get_clinic_id():
            messagebox.showwarning("Clinic Required", "Please select a clinic first.")
            return
        patient_id = self._get_patient_id()
        if not patient_id:
            messagebox.showwarning("Patient Required", "Please select a patient before uploading.")
            return
        file_path = filedialog.askopenfilename()
        if not file_path:
            return
        original_filename      = os.path.basename(file_path)
        final_filename, dest   = unique_dest_path(DIRECTORY, original_filename)
        try:
            shutil.copy(file_path, dest)
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_conn()
            cur  = conn.cursor()
            cur.execute(
                "INSERT INTO records (patient_id, staff_id, filename, filepath, upload_date) VALUES (?,?,?,?,?)",
                (patient_id, None, final_filename, dest, upload_date)
            )
            conn.commit()
            conn.close()
            self._update_file_list()
            messagebox.showinfo("Success", f"{final_filename} uploaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _download_file(self):
        selected = self._get_selected_record()
        if not selected:
            messagebox.showwarning("Select a file", "Please select a record to download.")
            return
        record_id, filename = selected
        try:
            conn = get_conn()
            cur  = conn.cursor()
            cur.execute("SELECT filepath FROM records WHERE record_id = ?", (record_id,))
            row  = cur.fetchone()
            conn.close()
            if not row:
                messagebox.showerror("Not found", "Record not found in database.")
                return
            source = row[0]
            if not os.path.exists(source):
                messagebox.showerror("Missing file", "Stored file path does not exist on disk.")
                return
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if not save_path:
                return
            shutil.copy(source, save_path)
            messagebox.showinfo("Success", f"{filename} downloaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_file(self):
        selected = self._get_selected_record()
        if not selected:
            messagebox.showwarning("Select a file", "Please select a record to delete.")
            return
        record_id, filename = selected
        if not messagebox.askyesno("Confirm Delete", f"Delete '{filename}'?"):
            return
        try:
            conn = get_conn()
            cur  = conn.cursor()
            cur.execute("SELECT filepath FROM records WHERE record_id = ?", (record_id,))
            row  = cur.fetchone()
            if row and row[0] and os.path.exists(row[0]):
                os.remove(row[0])
            cur.execute("DELETE FROM records WHERE record_id = ?", (record_id,))
            conn.commit()
            conn.close()
            self._update_file_list()
            messagebox.showinfo("Success", f"{filename} deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ── Embeddable frame used by main.py portal ──────────────────────────
class RecordsFrame(tk.Frame):
    def __init__(self, parent, controller=None, role="Admin"):
        super().__init__(parent, bg=BG_LIGHT)
        self.controller = controller
        self.role = role

        ensure_records_table_exists()
        self._build_ui()

        self.clinic_map, clinics = load_clinics()
        self.patient_map: Dict[str, int] = {}
        self.clinic_combo["values"] = clinics
        if clinics:
            self.clinic_combo.current(0)
            self._on_clinic_selected()
        else:
            self.clinic_combo.set("No clinics found")

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer)

        main = tk.Frame(outer, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x")
        tk.Label(header, text="Medical Records", bg=BG_PANEL,
                 fg=TEXT, font=FONT_TITLE).pack(side="left", padx=14, pady=14)
        try:
            from PIL import Image, ImageTk
            _fimg = Image.open("img/folder_img.png").resize((45, 45), Image.LANCZOS)
            self._rec_icon = ImageTk.PhotoImage(_fimg)
            tk.Label(header, image=self._rec_icon, bg=BG_PANEL).pack(side="right", padx=(0, 14), pady=6)
        except Exception:
            pass
        signed_in = "Staff" if self.role == "Staff" else "Administrator"
        tk.Label(header, text=f"Signed in as: {signed_in}", bg=BG_PANEL,
                 fg=TEXT, font=("Helvetica", 10)).pack(side="right", padx=14)

        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, pady=(10, 0))
        body.grid_rowconfigure(1, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._build_filter_bar(body)
        self._build_table(body)
        self._build_action_bar(body)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        portal_label = "Staff Portal" if self.role == "Staff" else "Admin Portal"
        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text=f"CareFlow\n{portal_label}", bg=BG_SIDEBAR_LIGHT, fg=TEXT,
                 font=("Helvetica", 9, "bold"), justify="left",
                 padx=8, pady=8).pack(anchor="w")

        if self.role == "Staff":
            nav_map = {
                "Dashboard": "HomePage",
                "Patient":   "PatientMenuPage",
                "Records":   None,
                "Billing":   "BillingMenuPage",
            }
        else:
            nav_map = {
                "Dashboard": "HomePage",
                "Patient":   "PatientMenuPage",
                "Staff":     "StaffMenuPage",
                "Clinic":    "LocationMenuPage",
                "Records":   None,
                "Billing":   "BillingMenuPage",
            }
        def load_icon(path, size=(18, 20)):
            try:
                from PIL import Image, ImageTk
                img = Image.open(path).resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception:
                return None

        self._rec_nav_icons = {
            "Dashboard": load_icon("icons/dashboard_icon.png"),
            "Patient":   load_icon("icons/patient_icon.png"),
            "Staff":     load_icon("icons/staff_icon.png"),
            "Clinic":    load_icon("icons/clinic_icon.png"),
            "Records":   load_icon("icons/folder_icon.png"),
            "Billing":   load_icon("icons/credit_icon.png"),
        }

        for item, page in nav_map.items():
            is_active = item == "Records"
            bg = BG_SIDEBAR_LIGHT if is_active else BG_SIDEBAR
            icon = self._rec_nav_icons.get(item)

            def make_cmd(p=page):
                if p and self.controller:
                    return lambda: self.controller.show_frame(p)
                return None

            cmd = make_cmd()
            kw = dict(image=icon, compound="left") if icon else {}
            if cmd:
                tk.Button(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_NAV,
                          anchor="w", padx=10, pady=6, relief="flat",
                          activebackground=BG_SIDEBAR_LIGHT, cursor="hand2",
                          command=cmd, **kw).pack(fill="x", padx=10, pady=2)
            else:
                tk.Label(sidebar, text=item, bg=bg, fg=TEXT, font=FONT_NAV,
                         anchor="w", padx=10, pady=6, **kw).pack(fill="x", padx=10, pady=2)

        if self.controller:
            tk.Button(sidebar, text="← Dashboard", bg=BG_SIDEBAR, fg=TEXT,
                      font=FONT_NAV, relief="flat", anchor="w",
                      padx=12, pady=6, cursor="hand2",
                      command=lambda: self.controller.show_frame("HomePage")
                      ).pack(side="bottom", fill="x", padx=10, pady=(0, 12))


# Copy data/event methods from CareFlowRecords onto RecordsFrame
_SKIP = {"_build_sidebar", "_build_header", "_build_content", "_build_ui"}
for _n, _v in vars(CareFlowRecords).items():
    if not _n.startswith("__") and callable(_v) and _n not in _SKIP:
        setattr(RecordsFrame, _n, _v)


# ==============================
# Main
# ==============================
if __name__ == "__main__":
    app = CareFlowRecords()
    app.mainloop()