import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


class CareFlowApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("CareFlow Patient Portal")

        # Starting size (you can still maximize/resize now)
        self.geometry("520x620")
        self.configure(bg="#ffffff")

        # ---- Load logo once ----
        self.logo_img = None
        self._load_logo()

        # ---- Container for "pages" ----
        container = tk.Frame(self, bg="#ffffff")
        container.pack(fill="both", expand=True)

        # Make the grid cell expand so frames can center properly when resized
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (HomePage, PatientMenuPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("HomePage")

    def _load_logo(self):
        try:
            img = Image.open("logo.png")
            img = img.resize((200, 200))
            self.logo_img = ImageTk.PhotoImage(img)
        except Exception as e:
            self.logo_img = None
            print(f"Logo load failed: {e}")

    def show_frame(self, page_name: str):
        frame = self.frames[page_name]
        frame.tkraise()


class HomePage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg="#ffffff")
        self.controller = controller

        # Center column container (keeps everything centered even when maximized)
        content = tk.Frame(self, bg="#ffffff")
        content.pack(expand=True)  # center vertically

        # Logo (or fallback text)
        if controller.logo_img:
            tk.Label(content, image=controller.logo_img, bg="#ffffff").pack(pady=(10, 18))
        else:
            tk.Label(content, text="CareFlow", font=("Arial", 28, "bold"),
                     bg="#ffffff", fg="#222").pack(pady=(20, 18))

        tk.Label(
            content,
            text="Welcome to CareFlow",
            font=("Arial", 22, "bold"),
            bg="#ffffff",
            fg="#222"
        ).pack(pady=(0, 6))

        tk.Label(
            content,
            text="Your secure medical patient portal",
            font=("Arial", 12),
            bg="#ffffff",
            fg="gray"
        ).pack(pady=(0, 24))

        # Buttons
        tk.Button(
            content,
            text="Patient Login",
            font=("Arial", 14),
            bg="#2196F3",
            fg="white",
            width=18,
            height=2,
            relief="flat",
            command=lambda: controller.show_frame("PatientMenuPage")
        ).pack(pady=10)

        tk.Button(
            content,
            text="Staff Login",
            font=("Arial", 14),
            bg="#2196F3",
            fg="white",
            width=18,
            height=2,
            relief="flat",
            command=self.staff_login
        ).pack(pady=10)

        tk.Label(
            content,
            text="Group 2",
            font=("Arial", 10),
            bg="#ffffff",
            fg="gray"
        ).pack(pady=(18, 0))

    def staff_login(self):
        messagebox.showinfo("Staff Login", "Staff login clicked (hook this to staff screen later)")


class PatientMenuPage(tk.Frame):
    def __init__(self, parent, controller: CareFlowApp):
        super().__init__(parent, bg="#ffffff")
        self.controller = controller

        # Center column container
        content = tk.Frame(self, bg="#ffffff")
        content.pack(expand=True)

        tk.Label(
            content,
            text="Patient Portal",
            font=("Arial", 22, "bold"),
            bg="#ffffff",
            fg="#222"
        ).pack(pady=(10, 10))

        tk.Label(
            content,
            text="Please choose an option:",
            font=("Arial", 12),
            bg="#ffffff",
            fg="gray"
        ).pack(pady=(0, 24))

        tk.Button(
            content,
            text="Existing Patient",
            font=("Arial", 14),
            bg="#2196F3",
            fg="white",
            width=18,
            height=2,
            relief="flat",
            command=self.existing_patient
        ).pack(pady=10)

        tk.Button(
            content,
            text="New Patient",
            font=("Arial", 14),
            bg="#2196F3",
            fg="white",
            width=18,
            height=2,
            relief="flat",
            command=self.new_patient
        ).pack(pady=10)

        tk.Button(
            content,
            text="Back",
            font=("Arial", 12),
            bg="#ffffff",
            fg="#222",
            width=18,
            height=2,
            relief="flat",
            command=lambda: controller.show_frame("HomePage")
        ).pack(pady=(26, 0))

    def existing_patient(self):
        messagebox.showinfo("Existing Patient", "Existing patient clicked (next: login form)")

    def new_patient(self):
        messagebox.showinfo("New Patient", "New patient clicked (next: registration form)")


if __name__ == "__main__":
    app = CareFlowApp()
    app.mainloop()
