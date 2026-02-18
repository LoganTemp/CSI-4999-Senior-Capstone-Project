import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import sqlite3
import re
from datetime import datetime
import os
import hashlib

DB_NAME = "healthcare.db"


# ------------------------ DB migration ------------------------
def ensure_patient_password_column():
    """Adds Patient.password_hash if it doesn't exist (safe to run every startup)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(Patient)")
        cols = [row[1] for row in cur.fetchall()]  # row[1] = column name

        if "password_hash" not in cols:
            cur.execute("ALTER TABLE Patient ADD COLUMN password_hash TEXT")
            conn.commit()

        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror("Database Error", f"Schema update failed:\n\n{e}")


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
    # Enforce ###-#### (matches your sample data)
    return bool(re.fullmatch(r"\d{3}-\d{4}", (s or "").strip()))


def is_valid_email_basic(s: str) -> bool:
    s = (s or "").strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s))


# ------------------------ App ------------------------
class CareFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CareFlow Patient Portal")
        self.iconbitmap("favicon.ico")
        self.geometry("520x680")
        self.configure(bg="#f4f7fb")

        # Ensure DB schema is ready BEFORE UI tries to insert new patients
        ensure_patient_password_column()

        self.logo_img = None
        self._load_logo()

        container = tk.Frame(self, bg="#f4f7fb")
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (HomePage, PatientMenuPage, NewPatientPage):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("HomePage")

    def _load_logo(self):
        try:
            img = Image.open("logo.png")
            img = img.resize((180, 180))
            self.logo_img = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_img = None
            print(f"Logo load failed: {e}")

    def show_frame(self, page_name: str):
        self.frames[page_name].tkraise()


# ---------------- HOME PAGE ----------------
class HomePage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg="#f4f7fb")

        content = tk.Frame(self, bg="#f4f7fb")
        content.pack(expand=True)

        if controller.logo_img:
            tk.Label(content, image=controller.logo_img, bg="#f4f7fb").pack(pady=(10, 18))

        tk.Label(
            content,
            text="Welcome to CareFlow",
            font=("Arial", 22, "bold"),
            bg="#f4f7fb",
            fg="#222"
        ).pack()

        tk.Label(
            content,
            text="Your secure medical patient portal",
            font=("Arial", 12),
            bg="#f4f7fb",
            fg="gray"
        ).pack(pady=(6, 22))

        tk.Button(
            content, text="Patient Login",
            font=("Arial", 14), bg="#4CAF50", fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("PatientMenuPage")
        ).pack(pady=10)

        tk.Button(
            content, text="Staff Login",
            font=("Arial", 14), bg="#2196F3", fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Staff Login", "Staff login clicked (hook later)")
        ).pack(pady=10)

        tk.Label(
            content,
            text="Group 2",
            font=("Arial", 10),
            bg="#f4f7fb",
            fg="gray"
        ).pack(pady=(18, 0))


# ---------------- PATIENT MENU ----------------
class PatientMenuPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg="#f4f7fb")

        content = tk.Frame(self, bg="#f4f7fb")
        content.pack(expand=True)

        tk.Label(
            content,
            text="Patient Portal",
            font=("Arial", 22, "bold"),
            bg="#f4f7fb",
            fg="#222"
        ).pack(pady=(10, 10))

        tk.Label(
            content,
            text="Please choose an option:",
            font=("Arial", 12),
            bg="#f4f7fb",
            fg="gray"
        ).pack(pady=(0, 24))

        tk.Button(
            content, text="Existing Patient",
            font=("Arial", 14), bg="#4CAF50", fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Existing Patient", "Existing patient clicked (hook later)")
        ).pack(pady=10)

        tk.Button(
            content, text="New Patient",
            font=("Arial", 14), bg="#4CAF50", fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("NewPatientPage")
        ).pack(pady=10)

        tk.Button(
            content, text="Back",
            font=("Arial", 12), bg="#e0e0e0", fg="#222",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("HomePage")
        ).pack(pady=(26, 0))


# ---------------- NEW PATIENT PAGE ----------------
class NewPatientPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg="#f4f7fb")
        self.controller = controller

        tk.Label(
            self,
            text="New Patient Registration",
            font=("Arial", 18, "bold"),
            bg="#f4f7fb",
            fg="#222"
        ).pack(pady=(10, 2))

        tk.Label(
            self,
            text="Required: DOB YYYY-MM-DD • Sex M/F • Phone ###-#### • Password (min 8 chars)",
            font=("Arial", 10),
            bg="#f4f7fb",
            fg="gray"
        ).pack(pady=(0, 10))

        content = tk.Frame(self, bg="#f4f7fb")
        content.pack(expand=True)

        form = tk.Frame(content, bg="#f4f7fb")
        form.pack()

        self.entries = {}

        def add_row(label, key, row, required=False, is_password=False):
            lbl = f"{label}{' *' if required else ''}"
            tk.Label(form, text=lbl, bg="#f4f7fb", anchor="w").grid(
                row=row, column=0, sticky="w", padx=10, pady=4
            )
            e = tk.Entry(form, width=34, show="*" if is_password else "")
            e.grid(row=row, column=1, padx=10, pady=4)
            self.entries[key] = e

        r = 0
        add_row("First Name", "first_name", r, required=True); r += 1
        add_row("Last Name", "last_name", r, required=True); r += 1
        add_row("DOB (YYYY-MM-DD)", "dob", r, required=True); r += 1
        add_row("Sex (M/F)", "sex", r, required=True); r += 1
        add_row("Phone (###-####)", "phone", r, required=True); r += 1
        add_row("Email", "email", r, required=True); r += 1
        add_row("Address", "address", r, required=True); r += 1

        # ---- Clinic Location dropdown ----
        tk.Label(form, text="Clinic Location *", bg="#f4f7fb", anchor="w").grid(
            row=r, column=0, sticky="w", padx=10, pady=4
        )
        self.location_var = tk.StringVar()
        self.location_combo = ttk.Combobox(
            form,
            textvariable=self.location_var,
            width=32,
            state="readonly"
        )
        self.location_combo.grid(row=r, column=1, padx=10, pady=4)
        r += 1

        self.location_map = {}
        self._load_locations()

        add_row("Allergies (or None)", "allergies", r, required=True); r += 1
        add_row("Conditions (or None)", "conditions", r, required=True); r += 1
        add_row("Medications (or None)", "medications", r, required=True); r += 1
        add_row("Notes", "notes", r, required=False); r += 1
        add_row("Emergency Contact", "emergency_contact", r, required=True); r += 1

        # ---- Password fields ----
        add_row("Password", "password", r, required=True, is_password=True); r += 1
        add_row("Confirm Password", "confirm_password", r, required=True, is_password=True); r += 1

        btn_row = tk.Frame(content, bg="#f4f7fb")
        btn_row.pack(pady=(12, 0))

        tk.Button(
            btn_row, text="Submit",
            font=("Arial", 12), bg="#4CAF50", fg="white",
            width=14, height=2, relief="flat",
            command=self.save_patient
        ).pack(side="left", padx=8)

        tk.Button(
            btn_row, text="Back",
            font=("Arial", 12), bg="#e0e0e0", fg="#222",
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

        # Location required
        selected_location = self.location_var.get().strip()
        if not selected_location or selected_location not in self.location_map:
            messagebox.showerror("Missing Clinic Location", "Please select a clinic location.")
            return
        location_id = self.location_map[selected_location]

        # Formatting
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

        # Password rules
        if len(data["password"]) < 8:
            messagebox.showerror("Weak Password", "Password must be at least 8 characters long.")
            return
        if data["password"] != data["confirm_password"]:
            messagebox.showerror("Password Mismatch", "Password and Confirm Password must match.")
            return

        pw_hash = hash_password(data["password"])

        # Normalize "None"
        for key in ("allergies", "conditions", "medications"):
            if data[key].lower() == "none":
                data[key] = "None"

        # Insert into DB (including password_hash)
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

        messagebox.showinfo("Success", f"Patient added successfully!\nAssigned Location: {selected_location}")

        # Clear form
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)

        # Reset dropdown
        if self.location_combo["values"]:
            self.location_combo.current(0)

        # Go back to Home Page
        self.controller.show_frame("HomePage")

if __name__ == "__main__":
    app = CareFlowApp()
    app.mainloop()
