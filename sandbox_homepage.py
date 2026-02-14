import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk  # optional, for logo

# ---------------- Styling constants ----------------
BG_COLOR = "#dddede"
FG_COLOR = "#222"
BTN_GREEN = "#4CAF50"
BTN_BLUE = "#2196F3"
BTN_GRAY = "#e0e0e0"
CONTAINER_COLOR = "#f2efef"  # light grey container
FONT_LARGE = ("Arial", 22, "bold")
FONT_MEDIUM = ("Arial", 14)
FONT_SMALL = ("Arial", 12)

# Breakpoints (window widths in pixels)
TABLET_BREAKPOINT = 800


# ---------------- HomePage Sandbox ----------------
class HomePage(tk.Frame):
    def __init__(self, parent, controller=None):
        super().__init__(parent, bg=BG_COLOR)
        self.root = parent

        # Content container
        self.content = tk.Frame(self, bg=BG_COLOR)
        self.content.pack(expand=True, fill="both")

        # ---------------- Gradient box behind logo ----------------
        self.logo_canvas_height = 160
        self.logo_canvas = tk.Canvas(self.content, height=self.logo_canvas_height, highlightthickness=0, bd=0)
        self.logo_canvas.pack(fill="x", pady=(10, 10))

        # Draw vertical gradient using button colors
        def draw_gradient(canvas, width, height):
            steps = 100
            # Convert hex colors to RGB tuples
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip("#")
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            start_color = hex_to_rgb(BTN_GREEN)  # green
            end_color = hex_to_rgb(BTN_BLUE)     # blue
                    
            for i in range(steps):
                r = int(start_color[0] + (end_color[0] - start_color[0]) * i / steps)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * i / steps)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * i / steps)
                color = f"#{r:02x}{g:02x}{b:02x}"
                y1 = int(i * height / steps)
                y2 = int((i + 1) * height / steps)
                canvas.create_rectangle(0, y1, width, y2, outline="", fill=color)

        # Bind resize to redraw gradient
        def resize_gradient(event):
            self.logo_canvas.delete("all")
            draw_gradient(self.logo_canvas, event.width, self.logo_canvas_height)
            # Re-place logo on top after resizing
            place_logo()

        self.logo_canvas.bind("<Configure>", resize_gradient)

        # Logo placeholder on top of gradient
        try:
            img = Image.open("logo.png")  # optional, only if you have a logo
            img = img.resize((180, 180))
            self.logo_img = ImageTk.PhotoImage(img)
        except Exception:
            self.logo_img = None

        def place_logo():
            self.logo_canvas.delete("logo")
            x = self.logo_canvas.winfo_width() // 2
            y = self.logo_canvas_height // 2
            if self.logo_img:
                self.logo_canvas.create_image(x, y, image=self.logo_img, anchor="c", tags="logo")
            else:
                self.logo_canvas.create_text(x, y, text="[Logo]", font=FONT_LARGE, tags="logo")

        place_logo()  # initial placement

        # ---------------- Title and subtitle ----------------
        tk.Label(self.content, text="Welcome to CareFlow", font=FONT_LARGE, bg=BG_COLOR, fg=FG_COLOR).pack()
        tk.Label(self.content, text="Health Management Systems", font=FONT_MEDIUM, bg=BG_COLOR, fg=FG_COLOR).pack()
        tk.Label(self.content, text="Your secure medical documentation portal", font=FONT_SMALL, bg=BG_COLOR, fg="gray").pack(pady=(6, 22))

        # ---------------- Buttons ----------------
        self.button_frame = tk.Frame(self.content, bg=BG_COLOR)
        self.button_frame.pack(pady=20)

        self.patient_btn = tk.Button(
            self.button_frame, text="Patient",
            font=FONT_MEDIUM, bg=BTN_GREEN, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Patient", "Clicked")
        )
        self.staff_btn = tk.Button(
            self.button_frame, text="Provider",
            font=FONT_MEDIUM, bg=BTN_BLUE, fg="white",
            width=18, height=2, relief="flat",
            command=lambda: messagebox.showinfo("Provider", "Clicked")
        )

        self.buttons = [self.patient_btn, self.staff_btn]

        # Initial layout: stacked vertically
        for btn in self.buttons:
            btn.pack(side=tk.TOP, pady=5)

        # ---------------- Horizontal bar ----------------
        self.bar = tk.Frame(self.content, bg=BTN_GREEN, height=4)
        self.bar.pack(fill="x", padx=50, pady=(10, 0))  # default, updated on resize

        # ---------------- Light grey container with links ----------------
        self.link_box = tk.Frame(self.content, bg=CONTAINER_COLOR, height=50)
        initial_box_width = int(self.root.winfo_width() * 0.9)
        padx_box = max((self.root.winfo_width() - initial_box_width) // 2, 0)
        self.link_box.pack(fill="x", padx=padx_box, pady=(0, 20))

        self.link_frame = tk.Frame(self.link_box, bg=CONTAINER_COLOR)
        self.link_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.links = []
        link_texts = ["Sign Up", "Sign In", "FAQs"]
        for text in link_texts:
            btn = tk.Button(
                self.link_frame,
                text=text,
                font=FONT_SMALL,
                relief="flat",
                bg=CONTAINER_COLOR,
                fg="black",
                cursor="hand2",
                command=lambda t=text: messagebox.showinfo(t, f"{t} clicked")
            )
            btn.pack(side=tk.LEFT, expand=True)
            self.links.append(btn)

        tk.Label(self.content, text="Created by the CareFlow Team, 2026", font=FONT_SMALL, bg=BG_COLOR, fg="gray").pack(pady=(6, 22))

        # ---------------- Responsive layout ----------------
        self.bind("<Configure>", self.adjust_buttons)
        self.root.bind("<Configure>", self.adjust_buttons)

    def adjust_buttons(self, event):
        """Adjust button layout and bar/link box width based on window width (responsive)."""
        width = self.root.winfo_width()

        # Clear previous button layout
        for btn in self.buttons:
            btn.pack_forget()

        if width > TABLET_BREAKPOINT:
            # Desktop: side-by-side buttons
            for btn in self.buttons:
                btn.pack(side=tk.LEFT, padx=20, pady=0)
        else:
            # Mobile/tablet: stacked buttons
            for btn in self.buttons:
                btn.pack(side=tk.TOP, pady=5)

        # Horizontal bar: 80% width, centered
        bar_width = int(width * 0.8)
        padx_bar = max((width - bar_width)//2, 0)
        self.bar.pack_configure(padx=padx_bar)

        # Link box: 90% width, centered
        box_width = int(width * 0.9)
        padx_box = max((width - box_width)//2, 0)
        self.link_box.pack_configure(padx=padx_box)


# ---------------- Runner ----------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Sandbox HomePage")
    root.geometry("520x620")  # start with mobile/tablet size
    page = HomePage(root)
    page.pack(fill="both", expand=True)
    root.mainloop()
