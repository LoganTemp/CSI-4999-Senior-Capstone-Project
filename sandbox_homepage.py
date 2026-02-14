import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk  # optional, for logo if you have one

# ---------------- Styling constants ----------------
BG_COLOR = "#f4f7fb"
FG_COLOR = "#222"
BTN_GREEN = "#4CAF50"
BTN_BLUE = "#2196F3"
BTN_GRAY = "#e0e0e0"
FONT_LARGE = ("Arial", 22, "bold")
FONT_MEDIUM = ("Arial", 14)
FONT_SMALL = ("Arial", 12)

# Breakpoints (widths in pixels)
MOBILE_BREAKPOINT = 520
TABLET_BREAKPOINT = 800
DESKTOP_BREAKPOINT = 1100


# ---------------- HomePage Sandbox ----------------
class HomePage(tk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, bg=BG_COLOR)

        self.content = tk.Frame(self, bg=BG_COLOR)
        self.content.pack(expand=True, fill="both")

        # Logo placeholder
        try:
            img = Image.open("logo.png")
            img = img.resize((180, 180))
            self.logo_img = ImageTk.PhotoImage(img)
            tk.Label(self.content, image=self.logo_img, bg=BG_COLOR).pack(pady=(10, 18))
        except Exception:
            tk.Label(self.content, text="[Logo]", bg=BG_COLOR, font=FONT_LARGE).pack(pady=(10, 18))

        # Title and subtitle
        tk.Label(self.content, text="Welcome to CareFlow", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack()
        tk.Label(self.content, text="Your secure medical patient portal", font=FONT_SMALL, bg=BG_COLOR, fg="gray").pack(pady=(6, 22))

        # Button frame
        self.button_frame = tk.Frame(self.content, bg=BG_COLOR)
        # Note: Initially pack centered, not left
        self.button_frame.pack(side=tk.BOTTOM, anchor="center", pady=20)

        # Buttons
        self.patient_btn = tk.Button(
            self.button_frame, text="Patient Login",
            font=FONT_MEDIUM, bg=BTN_GREEN, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Patient Login", "Clicked")
        )
        self.staff_btn = tk.Button(
            self.button_frame, text="Staff Login",
            font=FONT_MEDIUM, bg=BTN_BLUE, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Staff Login", "Clicked")
        )

        self.buttons = [self.patient_btn, self.staff_btn]

        # Initially stacked
        for btn in self.buttons:
            btn.pack(side=tk.TOP, pady=5)

        # Bind resize for responsive layout
        self.bind("<Configure>", self.adjust_buttons)

    def adjust_buttons(self, event):
        width = event.width

        # Remove current button packing
        for btn in self.buttons:
            btn.pack_forget()

        if width <= TABLET_BREAKPOINT:
            # Mobile/tablet: stacked buttons, frame centered
            self.button_frame.pack(side=tk.BOTTOM, anchor="center", pady=20)
            for btn in self.buttons:
                btn.pack(side=tk.TOP, pady=5)
        else:
            # Desktop: side-by-side, frame anchored lower-left
            self.button_frame.pack(side=tk.BOTTOM, anchor="w", padx=40, pady=40)
            for btn in self.buttons:
                btn.pack(side=tk.LEFT, padx=20, pady=0)


        # Optional: adjust logo size for desktop
        if hasattr(self, "logo_img"):
            if width > DESKTOP_BREAKPOINT:
                # Enlarge logo slightly
                try:
                    img = Image.open("logo.png")
                    img = img.resize((220, 220))
                    self.logo_img = ImageTk.PhotoImage(img)
                    # Replace existing logo
                    for widget in self.content.winfo_children():
                        if isinstance(widget, tk.Label) and getattr(widget, "image", None):
                            widget.configure(image=self.logo_img)
                except Exception:
                    pass


# ---------------- Runner ----------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Sandbox HomePage")
    root.geometry("520x620")  # start with mobile/tablet size
    page = HomePage(root)
    page.pack(fill="both", expand=True)
    root.mainloop()
