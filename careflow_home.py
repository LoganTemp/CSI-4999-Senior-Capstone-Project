import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import sqlite3
import re
from datetime import datetime
import os
import hashlib

DB_NAME = "healthcare.db"

# ---------------- Styling constants (from teammate sandbox) ----------------
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
    return bool(re.fullmatch(r"\d{3}-\d{4}", (s or "").strip()))


def is_valid_email_basic(s: str) -> bool:
    s = (s or "").strip()
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", s))


# ------------------------ App ------------------------
class CareFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CareFlow Patient Portal")
        self.geometry("520x680")
        self.configure(bg=BG_COLOR)

        # Try setting icon (won't crash if missing/bad .ico)
        try:
            if os.path.exists("logo.ico"):
                self.iconbitmap("logo.ico")
        except Exception:
            pass

        # Ensure DB schema is ready BEFORE UI tries to insert new patients
        ensure_patient_password_column()

        self.logo_img = None
        self._load_logo()

        container = tk.Frame(self, bg=BG_COLOR)
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
            img = Image.open("logo.png").convert("RGBA")
            img = img.resize((180, 180))
            self.logo_img = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_img = None
            print(f"Logo load failed: {e}")

    def show_frame(self, page_name: str):
        self.frames[page_name].tkraise()


# ---------------- HOME PAGE (styled like teammate sandbox) ----------------
class HomePage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg=BG_COLOR)
        self.controller = controller
        self.root = controller

        self.content = tk.Frame(self, bg=BG_COLOR)
        self.content.pack(expand=True, fill="both")

        # Gradient header behind logo
        self.logo_canvas_height = 160
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
        tk.Label(self.content, text="Your secure medical documentation portal", font=FONT_SMALL,
                 bg=BG_COLOR, fg="gray").pack(pady=(6, 22))

        # Buttons (responsive)
        self.button_frame = tk.Frame(self.content, bg=BG_COLOR)
        self.button_frame.pack(pady=20)

        self.patient_btn = tk.Button(
            self.button_frame, text="Patient",
            font=FONT_MEDIUM, bg=BTN_GREEN, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: controller.show_frame("PatientMenuPage")
        )
        self.staff_btn = tk.Button(
            self.button_frame, text="Provider",
            font=FONT_MEDIUM, bg=BTN_BLUE, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Provider", "Provider login screen coming soon")
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

        tk.Label(self.content, text="Created by the CareFlow Team, 2026",
                 font=FONT_SMALL, bg=BG_COLOR, fg="gray").pack(pady=(6, 22))

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

        # Clinic Location dropdown
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

        messagebox.showinfo("Success", f"Patient added successfully!\nAssigned Location: {selected_location}")

        for entry in self.entries.values():
            entry.delete(0, tk.END)
        if self.location_combo["values"]:
            self.location_combo.current(0)

        self.controller.show_frame("HomePage")


if __name__ == "__main__":
    app = CareFlowApp()
    app.mainloop()
