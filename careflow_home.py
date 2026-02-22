import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import sqlite3
import re
from datetime import datetime
import os
import hashlib

DB_NAME = "healthcare.db"

# ---------------- Styling constants  ----------------
BG_COLOR = "#dddede"
FG_COLOR = "#222"
BTN_GREEN = "#4CAF50"
BTN_BLUE = "#2196F3"
BTN_GRAY = "#e0e0e0"
CONTAINER_COLOR = "#f2efef"
FONT_LARGE = ("Arial", 22, "bold")
FONT_MEDIUM = ("Arial", 14)
FONT_SMALL = ("Arial", 12)
TABLET_BREAKPOINT = 800


# ------------------------ DB migration ------------------------
def ensure_patient_password_column():
    """Adds Patient.password_hash if it doesn't exist (safe to run every startup)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(Patient)")
        cols = [row[1] for row in cur.fetchall()]
        if "password_hash" not in cols:
            cur.execute("ALTER TABLE Patient ADD COLUMN password_hash TEXT")
            conn.commit()
        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Patient schema update failed:\n\n{e}")


def ensure_staff_password_column():
    """Adds Staff.password_hash if it doesn't exist (safe to run every startup)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(Staff)")
        cols = [row[1] for row in cur.fetchall()]
        if "password_hash" not in cols:
            cur.execute("ALTER TABLE Staff ADD COLUMN password_hash TEXT")
            conn.commit()
        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Staff schema update failed:\n\n{e}")


# ------------------------ Password hashing ------------------------
def hash_password(password: str, iterations: int = 200_000) -> str:
    """
    PBKDF2-HMAC-SHA256 hash. Stored as:
    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


# ------------------------ Validation helpers ------------------------
def is_valid_date_yyyy_mm_dd(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def normalize_sex(s: str) -> str:
    s = (s or "").strip().upper()
    if s in ("M", "MALE"):
        return "M"
    if s in ("F", "FEMALE"):
        return "F"
    return ""


def is_valid_phone_555_format(s: str) -> bool:
    return bool(re.fullmatch(r"\d{3}-\d{4}", (s or "").strip()))


def is_valid_email_basic(s: str) -> bool:
    s = (s or "").strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s))

# ------------------------ Clinic Location DB helpers ------------------------
def get_all_active_clinics():
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            SELECT location_id, name, city, state
            FROM ClinicLocation
            WHERE status = 'active'
        """)

        results = cur.fetchall()
        conn.close()
        return results

    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to fetch clinics:\n\n{e}")
        return []
    
    
def add_clinic_location(name, address, city, state, zip_code, phone):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO ClinicLocation (name, address, city, state, zip, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (name, address, city, state, zip_code, phone))

        conn.commit()
        conn.close()
        return True

    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to add clinic:\n\n{e}")
        return False
    
    
def remove_clinic_location(location_id):
    """
    Soft delete a clinic by setting status = 'inactive'.
    Returns True if successful, False if error.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            UPDATE ClinicLocation
            SET status = 'inactive'
            WHERE location_id = ?
        """, (location_id,))

        conn.commit()
        conn.close()
        return True

    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to remove clinic:\n\n{e}")
        return False
    
    
def update_clinic_location(location_id, name=None, address=None, city=None, state=None, zip_code=None, phone=None):
    """
    Update clinic fields. Only updates the fields that are not None.
    Returns True if successful, False if error.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        # Build the SET clause dynamically
        fields = []
        values = []

        if name is not None:
            fields.append("name = ?")
            values.append(name)
        if address is not None:
            fields.append("address = ?")
            values.append(address)
        if city is not None:
            fields.append("city = ?")
            values.append(city)
        if state is not None:
            fields.append("state = ?")
            values.append(state)
        if zip_code is not None:
            fields.append("zip = ?")
            values.append(zip_code)
        if phone is not None:
            fields.append("phone = ?")
            values.append(phone)

        if not fields:
            # Nothing to update
            conn.close()
            return False

        values.append(location_id)
        sql = f"UPDATE ClinicLocation SET {', '.join(fields)} WHERE location_id = ?"
        cur.execute(sql, values)
        conn.commit()
        conn.close()
        return True

    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to update clinic:\n\n{e}")
        return False   
    
    
def soft_delete_clinic_location(clinic_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        cur.execute("""
            UPDATE ClinicLocation
            SET status = 'inactive'
            WHERE location_id = ?
        """, (clinic_id,))

        conn.commit()
        conn.close()
        return True

    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Failed to delete clinic:\n\n{e}")
        return False

# ------------------------ App ------------------------
class CareFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CareFlow Patient Portal")
        self.geometry("520x680")
        self.configure(bg=BG_COLOR)

        # Try setting icon
        try:
            if os.path.exists("favicon.ico"):
                self.iconbitmap("favicon.ico")
        except Exception:
            pass

        # Ensure DB schema is ready BEFORE UI tries to insert
        ensure_patient_password_column()
        ensure_staff_password_column()

        self.logo_img = None
        self._load_logo()

        container = tk.Frame(self, bg=BG_COLOR)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (HomePage, PatientMenuPage, NewPatientPage, LocationMenuPage, StaffMenuPage, NewStaffPage):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("HomePage")

    def _load_logo(self):
        try:
            img = Image.open("logo.png").convert("RGBA")
            img = img.resize((250, 250))
            self.logo_img = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_img = None
            print(f"Logo load failed: {e}")

    def show_frame(self, page_name: str):
        self.frames[page_name].tkraise()


# ---------------- HOME PAGE ----------------
class HomePage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        self.root = controller

        self.content = tk.Frame(self, bg=BG_COLOR)
        self.content.pack(expand=True, fill="both")

        # Gradient header behind logo
        self.logo_canvas_height = 180
        self.logo_canvas = tk.Canvas(self.content, height=self.logo_canvas_height, highlightthickness=0, bd=0)
        self.logo_canvas.pack(fill="x", pady=(10, 10))

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        def draw_gradient(canvas, width, height):
            steps = 100
            start_color = hex_to_rgb(BTN_GREEN)
            end_color = hex_to_rgb(BTN_BLUE)
            for i in range(steps):
                r = int(start_color[0] + (end_color[0] - start_color[0]) * i / steps)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * i / steps)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * i / steps)
                color = f"#{r:02x}{g:02x}{b:02x}"
                y1 = int(i * height / steps)
                y2 = int((i + 1) * height / steps)
                canvas.create_rectangle(0, y1, width, y2, outline="", fill=color)

        def place_logo():
            self.logo_canvas.delete("logo")
            x = self.logo_canvas.winfo_width() // 2
            y = self.logo_canvas_height // 2
            if controller.logo_img:
                self.logo_canvas.create_image(x, y, image=controller.logo_img, anchor="c", tags="logo")
            else:
                self.logo_canvas.create_text(x, y, text="[Logo]", font=FONT_LARGE, tags="logo")

        def resize_gradient(event):
            self.logo_canvas.delete("all")
            draw_gradient(self.logo_canvas, event.width, self.logo_canvas_height)
            place_logo()

        self.logo_canvas.bind("<Configure>", resize_gradient)
        self.after(0, lambda: resize_gradient(type("E", (), {"width": self.logo_canvas.winfo_width()})()))

        # Title/subtitle
        tk.Label(self.content, text="Welcome to CareFlow", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack()
        tk.Label(self.content, text="Health Management Systems", font=FONT_MEDIUM, bg=BG_COLOR, fg=FG_COLOR).pack()
        tk.Label(
            self.content,
            text="Your secure medical documentation portal",
            font=FONT_SMALL, bg=BG_COLOR, fg="gray"
        ).pack(pady=(6, 22))

        # Buttons (responsive)
        self.button_frame = tk.Frame(self.content, bg=BG_COLOR)
        self.button_frame.pack(pady=20)

        self.patient_btn = tk.Button(
            self.button_frame, text="Patient",
            font=FONT_MEDIUM, bg=BTN_GREEN, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("PatientMenuPage")
        )
        self.clinic_btn = tk.Button(
            self.button_frame, text="Clinic Locations",
            font=FONT_MEDIUM, bg=BTN_GRAY, fg="black",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("LocationMenuPage")
        )
        self.clinic_btn.pack(side=tk.TOP, pady=5)
        
        self.staff_btn = tk.Button(
            self.button_frame, text="Provider",
            font=FONT_MEDIUM, bg=BTN_BLUE, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("StaffMenuPage")
        )

        self.buttons = [self.patient_btn, self.staff_btn]
        for btn in self.buttons:
            btn.pack(side=tk.TOP, pady=5)

        # Horizontal bar
        self.bar = tk.Frame(self.content, bg=BTN_GREEN, height=4)
        self.bar.pack(fill="x", padx=50, pady=(10, 0))

        # Link box
        self.link_box = tk.Frame(self.content, bg=CONTAINER_COLOR, height=50)
        self.link_box.pack(fill="x", padx=30, pady=(0, 20))

        self.link_frame = tk.Frame(self.link_box, bg=CONTAINER_COLOR)
        self.link_frame.pack(fill="both", expand=True, padx=10, pady=10)

        for text in ["Sign Up", "Sign In", "FAQs"]:
            tk.Button(
                self.link_frame,
                text=text,
                font=FONT_SMALL,
                relief="flat",
                bg=CONTAINER_COLOR,
                fg="black",
                cursor="hand2",
                command=lambda t=text: messagebox.showinfo(t, f"{t} clicked (hook later)")
            ).pack(side=tk.LEFT, expand=True)

        tk.Label(
            self.content, text="Created by the CareFlow Team, 2026",
            font=FONT_SMALL, bg=BG_COLOR, fg="gray"
        ).pack(pady=(6, 22))

        # Responsive behavior
        self.bind("<Configure>", self.adjust_buttons)
        self.root.bind("<Configure>", self.adjust_buttons)

    def adjust_buttons(self, event=None):
        width = self.root.winfo_width()

        for btn in self.buttons:
            btn.pack_forget()

        if width > TABLET_BREAKPOINT:
            for btn in self.buttons:
                btn.pack(side=tk.LEFT, padx=20, pady=0)
        else:
            for btn in self.buttons:
                btn.pack(side=tk.TOP, pady=5)

        # Bar 80% width centered
        bar_width = int(width * 0.8)
        padx_bar = max((width - bar_width) // 2, 0)
        self.bar.pack_configure(padx=padx_bar)

        # Link box 90% width centered
        box_width = int(width * 0.9)
        padx_box = max((width - box_width) // 2, 0)
        self.link_box.pack_configure(padx=padx_box)


# ---------------- PATIENT MENU ----------------
class PatientMenuPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)

        content = tk.Frame(self, bg=BG_COLOR)
        content.pack(expand=True)

        tk.Label(content, text="Patient Portal", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack(pady=(10, 10))
        tk.Label(content, text="Please choose an option:", font=FONT_SMALL, bg=BG_COLOR, fg="gray").pack(pady=(0, 24))

        tk.Button(
            content, text="Existing Patient",
            font=FONT_MEDIUM, bg=BTN_GREEN, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Existing Patient", "Existing patient login screen coming soon")
        ).pack(pady=10)

        tk.Button(
            content, text="New Patient",
            font=FONT_MEDIUM, bg=BTN_GREEN, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("NewPatientPage")
        ).pack(pady=10)

        tk.Button(
            content, text="Back",
            font=FONT_SMALL, bg=BTN_GRAY, fg="#222",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("HomePage")
        ).pack(pady=(26, 0))


# ---------------- STAFF MENU ----------------
class StaffMenuPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)

        content = tk.Frame(self, bg=BG_COLOR)
        content.pack(expand=True)

        tk.Label(content, text="Provider Portal", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack(pady=(10, 10))
        tk.Label(content, text="Please choose an option:", font=FONT_SMALL, bg=BG_COLOR, fg="gray").pack(pady=(0, 24))

        tk.Button(
            content, text="Existing Staff",
            font=FONT_MEDIUM, bg=BTN_BLUE, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Existing Staff", "Existing staff login screen coming soon")
        ).pack(pady=10)

        tk.Button(
            content, text="New Staff",
            font=FONT_MEDIUM, bg=BTN_BLUE, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("NewStaffPage")
        ).pack(pady=10)

        tk.Button(
            content, text="Back",
            font=FONT_SMALL, bg=BTN_GRAY, fg="#222",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("HomePage")
        ).pack(pady=(26, 0))


# ---------------- NEW PATIENT PAGE ----------------
class NewPatientPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        tk.Label(self, text="New Patient Registration", font=("Arial", 18, "bold"),
                 bg=BG_COLOR, fg=FG_COLOR).pack(pady=(10, 2))

        tk.Label(self, text="Required: DOB YYYY-MM-DD • Sex M/F • Phone ###-#### • Password (min 8 chars)",
                 font=("Arial", 10), bg=BG_COLOR, fg="gray").pack(pady=(0, 10))

        content = tk.Frame(self, bg=BG_COLOR)
        content.pack(expand=True)

        form_wrap = tk.Frame(content, bg=CONTAINER_COLOR)
        form_wrap.pack(padx=20, pady=10)

        form = tk.Frame(form_wrap, bg=CONTAINER_COLOR)
        form.pack(padx=14, pady=14)

        self.entries = {}

        def add_row(label, key, row, required=False, is_password=False):
            lbl = f"{label}{' *' if required else ''}"
            tk.Label(form, text=lbl, bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            e = tk.Entry(form, width=34, show="*" if is_password else "")
            e.grid(row=row, column=1, padx=10, pady=5)
            self.entries[key] = e

        r = 0
        add_row("First Name", "first_name", r, required=True); r += 1
        add_row("Last Name", "last_name", r, required=True); r += 1
        add_row("DOB (YYYY-MM-DD)", "dob", r, required=True); r += 1
        add_row("Sex (M/F)", "sex", r, required=True); r += 1
        add_row("Phone (###-####)", "phone", r, required=True); r += 1
        add_row("Email", "email", r, required=True); r += 1
        add_row("Address", "address", r, required=True); r += 1

        tk.Label(form, text="Clinic Location *", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", padx=10, pady=5
        )
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(form, textvariable=self.location_var, width=32, state="readonly")
        self.location_combo.grid(row=r, column=1, padx=10, pady=5)
        r += 1

        self.location_map = {}
        self._load_locations()

        add_row("Allergies (or None)", "allergies", r, required=True); r += 1
        add_row("Conditions (or None)", "conditions", r, required=True); r += 1
        add_row("Medications (or None)", "medications", r, required=True); r += 1
        add_row("Notes", "notes", r, required=False); r += 1
        add_row("Emergency Contact", "emergency_contact", r, required=True); r += 1
        add_row("Password", "password", r, required=True, is_password=True); r += 1
        add_row("Confirm Password", "confirm_password", r, required=True, is_password=True); r += 1

        btn_row = tk.Frame(content, bg=BG_COLOR)
        btn_row.pack(pady=(10, 0))

        tk.Button(
            btn_row, text="Submit",
            font=FONT_SMALL, bg=BTN_GREEN, fg="white",
            width=14, height=2, relief="flat",
            command=self.save_patient
        ).pack(side="left", padx=8)

        tk.Button(
            btn_row, text="Back",
            font=FONT_SMALL, bg=BTN_GRAY, fg="#222",
            width=14, height=2, relief="flat",
            command=lambda: controller.show_frame("PatientMenuPage")
        ).pack(side="left", padx=8)

    def _load_locations(self):
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("SELECT location_id, name FROM ClinicLocation ORDER BY name")
            rows = cur.fetchall()
            conn.close()

            display_names = []
            for loc_id, name in rows:
                label = str(name) if name is not None else f"Location {loc_id}"
                self.location_map[label] = loc_id
                display_names.append(label)

            self.location_combo["values"] = display_names
            if display_names:
                self.location_combo.current(0)
            else:
                self.location_combo.set("No locations found")

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not load clinic locations.\n\n{e}")

    def save_patient(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}

        required_keys = [
            "first_name", "last_name", "dob", "sex", "phone", "email", "address",
            "allergies", "conditions", "medications", "emergency_contact",
            "password", "confirm_password"
        ]
        missing = [k for k in required_keys if not data.get(k)]
        if missing:
            nice = ", ".join(m.replace("_", " ") for m in missing)
            messagebox.showerror("Missing Fields", f"Please fill in: {nice}")
            return

        selected_location = self.location_var.get().strip()
        if not selected_location or selected_location not in self.location_map:
            messagebox.showerror("Missing Clinic Location", "Please select a clinic location.")
            return
        location_id = self.location_map[selected_location]

        if not is_valid_date_yyyy_mm_dd(data["dob"]):
            messagebox.showerror("Invalid DOB", "DOB must be YYYY-MM-DD (example: 1990-05-10).")
            return

        sex_norm = normalize_sex(data["sex"])
        if sex_norm not in ("M", "F"):
            messagebox.showerror("Invalid Sex", "Sex must be M or F.")
            return
        data["sex"] = sex_norm

        if not is_valid_phone_555_format(data["phone"]):
            messagebox.showerror("Invalid Phone", "Phone must be ###-#### (example: 555-1111).")
            return

        if not is_valid_email_basic(data["email"]):
            messagebox.showerror("Invalid Email", "Please enter a valid email (example: john.doe@email.com).")
            return

        if len(data["password"]) < 8:
            messagebox.showerror("Weak Password", "Password must be at least 8 characters long.")
            return
        if data["password"] != data["confirm_password"]:
            messagebox.showerror("Password Mismatch", "Password and Confirm Password must match.")
            return

        pw_hash = hash_password(data["password"])

        for key in ("allergies", "conditions", "medications"):
            if data[key].lower() == "none":
                data[key] = "None"

        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO Patient (
                    first_name, last_name, dob, sex, phone, email, address,
                    location_id, allergies, conditions, medications,
                    notes, emergency_contact, password_hash
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                data["first_name"],
                data["last_name"],
                data["dob"],
                data["sex"],
                data["phone"],
                data["email"],
                data["address"],
                location_id,
                data["allergies"],
                data["conditions"],
                data["medications"],
                data.get("notes", ""),
                data["emergency_contact"],
                pw_hash
            ))
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not add patient.\n\n{e}")
            return

        messagebox.showinfo("Success", "Patient added successfully!")
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        if self.location_combo["values"]:
            self.location_combo.current(0)

        self.controller.show_frame("HomePage")

# ---------------- CLINIC LOCATION PAGE ----------------
class LocationMenuPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        self.content = tk.Frame(self, bg=BG_COLOR)
        self.content.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(self.content, text="Clinic Locations", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack(pady=(0, 10))

        # Treeview to show clinics
        columns = ("ID", "Name", "City", "State")
        self.tree = ttk.Treeview(self.content, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(pady=10)

        # Refresh button
        tk.Button(
            self.content,
            text="Refresh List",
            font=FONT_MEDIUM,
            bg=BTN_BLUE,
            fg="white",
            width=15,
            command=self.refresh_clinics
        ).pack(pady=5)

        # Button frame
        self.button_frame = tk.Frame(self.content, bg=BG_COLOR)
        self.button_frame.pack(pady=10)

        # Add, Update, Delete buttons
        tk.Button(
            self.button_frame, text="Add Clinic",
            font=FONT_SMALL, bg=BTN_GREEN, fg="white",
            width=12,
            command=self.add_clinic_dialog
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            self.button_frame, text="Update Clinic",
            font=FONT_SMALL, bg="#FFA500", fg="white",
            width=12,
            command=self.update_clinic_dialog
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            self.button_frame, text="Delete Clinic",
            font=FONT_SMALL, bg="#F44336", fg="white",
            width=12,
            command=self.delete_clinic_dialog
        ).pack(side=tk.LEFT, padx=5)

        # Load clinics initially
        self.refresh_clinics()

    # ------------------- REFRESH -------------------
    def refresh_clinics(self):
        # Clear current rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Load from DB
        clinics = get_all_active_clinics()
        print("DEBUG: clinics loaded:", clinics)  # optional debug
        for c in clinics:
            self.tree.insert("", "end", values=c)

    # ------------------- ADD -------------------
    def add_clinic_dialog(self):
        win = tk.Toplevel(self)
        win.title("Add Clinic")
        win.geometry("400x350")
        win.configure(bg=BG_COLOR)

        entries = {}
        fields = [("Name", ""), ("Address", ""), ("City", ""), ("State", ""), ("ZIP", ""), ("Phone", "")]
        for idx, (label_text, default) in enumerate(fields):
            tk.Label(win, text=label_text, bg=BG_COLOR, font=FONT_SMALL).grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            ent = tk.Entry(win, width=30)
            ent.insert(0, default)
            ent.grid(row=idx, column=1, padx=10, pady=5)
            entries[label_text.lower()] = ent

        def submit():
            new_name = entries["name"].get().strip()
            new_address = entries["address"].get().strip()
            new_city = entries["city"].get().strip()
            new_state = entries["state"].get().strip()
            new_zip = entries["zip"].get().strip()
            new_phone = entries["phone"].get().strip()

            if not new_name or not new_address or not new_city or not new_state or not new_zip:
                messagebox.showwarning("Input Error", "Name, Address, City, State, and ZIP are required.")
                return

            success = add_clinic_location(new_name, new_address, new_city, new_state, new_zip, new_phone)
            if success:
                win.destroy()             # close popup first
                self.refresh_clinics()    # refresh table
                messagebox.showinfo("Success", f"Clinic '{new_name}' added successfully!")
            else:
                messagebox.showerror("Error", "Failed to add clinic.")

        tk.Button(win, text="Add Clinic", bg=BTN_GREEN, fg="white", width=15, command=submit).grid(
            row=len(fields), column=0, columnspan=2, pady=15
        )

    # ------------------- UPDATE -------------------
    def update_clinic_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Clinic", "Please select a clinic to update.")
            return

        # Get all current values from the selected row
        clinic_id = self.tree.item(selected[0])["values"][0]

        # Fetch the full clinic record from DB to pre-fill all fields
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("""
            SELECT name, address, city, state, zip, phone
            FROM ClinicLocation
            WHERE location_id = ?
        """, (clinic_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Failed to fetch clinic info.")
            return

        name, address, city, state, zip_code, phone = row

        # Popup window
        win = tk.Toplevel(self)
        win.title("Update Clinic")
        win.geometry("400x350")
        win.configure(bg=BG_COLOR)

        entries = {}
        fields = [("Name", name), ("Address", address), ("City", city), ("State", state), ("ZIP", zip_code), ("Phone", phone)]
        for idx, (label_text, default) in enumerate(fields):
            tk.Label(win, text=label_text, bg=BG_COLOR, font=FONT_SMALL).grid(row=idx, column=0, sticky="w", padx=10, pady=5)
            ent = tk.Entry(win, width=30)
            ent.insert(0, default)
            ent.grid(row=idx, column=1, padx=10, pady=5)
            entries[label_text.lower()] = ent

        # Submit function
        def submit():
            new_name = entries["name"].get().strip()
            new_address = entries["address"].get().strip()
            new_city = entries["city"].get().strip()
            new_state = entries["state"].get().strip()
            new_zip = entries["zip"].get().strip()
            new_phone = entries["phone"].get().strip()

            if not new_name or not new_address or not new_city or not new_state or not new_zip:
                messagebox.showwarning("Input Error", "Name, Address, City, State, and ZIP are required.")
                return

            success = update_clinic_location(
                location_id=clinic_id,
                name=new_name,
                address=new_address,
                city=new_city,
                state=new_state,
                zip_code=new_zip,
                phone=new_phone
            )
            if success:
                win.destroy()             # close popup first
                self.refresh_clinics()    # refresh table
                messagebox.showinfo("Success", f"Clinic '{new_name}' updated successfully!")
            else:
                messagebox.showerror("Error", "Failed to update clinic.")

        tk.Button(win, text="Save Changes", bg=BTN_BLUE, fg="white", width=15, command=submit).grid(
            row=len(fields), column=0, columnspan=2, pady=15
        )

    # ------------------- DELETE -------------------
    def delete_clinic_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Clinic", "Please select a clinic to delete.")
            return

        # Get clinic ID and Name from the selected row
        clinic_id, name = self.tree.item(selected[0])["values"][0:2]

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{name}'?"):
            return

        # Call DB helper
        success = soft_delete_clinic_location(clinic_id)
        if success:
            self.refresh_clinics()  # Refresh table immediately
            messagebox.showinfo("Deleted", f"Clinic '{name}' was deleted.")
        else:
            messagebox.showerror("Error", "Failed to delete clinic.")
        
# ---------------- NEW STAFF PAGE ----------------
class NewStaffPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller

        tk.Label(self, text="New Staff Registration", font=("Arial", 18, "bold"),
                 bg=BG_COLOR, fg=FG_COLOR).pack(pady=(10, 2))

        tk.Label(self, text="Required: Email • Phone ###-#### • Role • Password (min 8 chars)",
                 font=("Arial", 10), bg=BG_COLOR, fg="gray").pack(pady=(0, 10))

        content = tk.Frame(self, bg=BG_COLOR)
        content.pack(expand=True)

        form_wrap = tk.Frame(content, bg=CONTAINER_COLOR)
        form_wrap.pack(padx=20, pady=10)

        form = tk.Frame(form_wrap, bg=CONTAINER_COLOR)
        form.pack(padx=14, pady=14)

        self.entries = {}

        def add_row(label, key, row, required=False, is_password=False):
            lbl = f"{label}{' *' if required else ''}"
            tk.Label(form, text=lbl, bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
                row=row, column=0, sticky="w", padx=10, pady=5
            )
            e = tk.Entry(form, width=34, show="*" if is_password else "")
            e.grid(row=row, column=1, padx=10, pady=5)
            self.entries[key] = e

        r = 0
        add_row("First Name", "first_name", r, required=True); r += 1
        add_row("Last Name", "last_name", r, required=True); r += 1
        add_row("Email", "email", r, required=True); r += 1
        add_row("Phone (###-####)", "phone", r, required=True); r += 1

        # Role dropdown
        tk.Label(form, text="Role *", bg=CONTAINER_COLOR, fg=FG_COLOR, anchor="w").grid(
            row=r, column=0, sticky="w", padx=10, pady=5
        )
        self.role_var = tk.StringVar()
        self.role_combo = ttk.Combobox(
            form,
            textvariable=self.role_var,
            width=32,
            state="readonly",
            values=["doctor", "billing", "records", "nurse"]
        )
        self.role_combo.grid(row=r, column=1, padx=10, pady=5)
        self.role_combo.current(0)
        r += 1

        add_row("Password", "password", r, required=True, is_password=True); r += 1
        add_row("Confirm Password", "confirm_password", r, required=True, is_password=True); r += 1
        add_row("Staff Confirmation Code", "confirmation_code", r, required=True, is_password=True); r += 1
        
        btn_row = tk.Frame(content, bg=BG_COLOR)
        btn_row.pack(pady=(10, 0))

        tk.Button(
            btn_row, text="Submit",
            font=FONT_SMALL, bg=BTN_BLUE, fg="white",
            width=14, height=2, relief="flat",
            command=self.save_staff
        ).pack(side="left", padx=8)

        tk.Button(
            btn_row, text="Back",
            font=FONT_SMALL, bg=BTN_GRAY, fg="#222",
            width=14, height=2, relief="flat",
            command=lambda: controller.show_frame("StaffMenuPage")
        ).pack(side="left", padx=8)

    def save_staff(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        role = (self.role_var.get() or "").strip()

        required_keys = ["first_name", "last_name", "email", "phone", "password", "confirm_password"]
        missing = [k for k in required_keys if not data.get(k)]
        if missing or not role:
            msg_parts = []
            if missing:
                msg_parts.append("Missing: " + ", ".join(m.replace("_", " ") for m in missing))
            if not role:
                msg_parts.append("Please select a role.")
            messagebox.showerror("Missing Fields", "\n".join(msg_parts))
            return

        if not is_valid_email_basic(data["email"]):
            messagebox.showerror("Invalid Email", "Please enter a valid email (example: alice@clinic.com).")
            return

        if not is_valid_phone_555_format(data["phone"]):
            messagebox.showerror("Invalid Phone", "Phone must be ###-#### (example: 555-5555).")
            return

        if len(data["password"]) < 8:
            messagebox.showerror("Weak Password", "Password must be at least 8 characters long.")
            return
        if data["password"] != data["confirm_password"]:
            messagebox.showerror("Password Mismatch", "Password and Confirm Password must match.")
            return
        if data.get("confirmation_code") != "1234":
            messagebox.showerror("Invalid Code", "Invalid staff confirmation code.")
            return

        pw_hash = hash_password(data["password"])

        # Insert into Staff
        try:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()

            # Keep active_flag = 1 by default
            cur.execute("""
                INSERT INTO Staff (first_name, last_name, email, phone, role, active_flag, password_hash)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (
                data["first_name"],
                data["last_name"],
                data["email"],
                data["phone"],
                role,
                pw_hash
            ))

            conn.commit()
            conn.close()

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Could not add staff.\n\n{e}")
            return

        messagebox.showinfo("Success", "Staff member added successfully!")
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.role_combo.current(0)

        self.controller.show_frame("HomePage")


if __name__ == "__main__":
    app = CareFlowApp()
    app.mainloop()