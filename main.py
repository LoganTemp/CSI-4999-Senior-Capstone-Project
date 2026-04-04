import tkinter as tk
from dashboardSandbox import DashboardFrame

# ── Colour palette (identical to all other modules) ──────────────────────────
BG_LIGHT         = "#e6f2ec"
BG_SIDEBAR       = "#5FAF90"
BG_SIDEBAR_LIGHT = "#A2DDC6"
BG_PANEL         = "#ffffff"
CARD_BG          = "#f7fff7"
ACCENT           = "#308684"
TEXT             = "#0b3d2e"
BTN_NEUTRAL      = "#95a5a6"

FONT_TITLE  = ("Helvetica", 18, "bold")
FONT_HEADER = ("Helvetica", 13, "bold")
FONT_LOGO   = ("Helvetica", 13, "bold")
FONT_SMALL  = ("Helvetica", 10)
FONT_CARD   = ("Helvetica", 13, "bold")


class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow")
        self.geometry("1200x720")
        self.minsize(900, 560)
        self.configure(bg=BG_LIGHT)
        self._build_ui()

    def _build_ui(self):
        for w in self.winfo_children():
            w.destroy()
        outer = tk.Frame(self, bg=BG_LIGHT)
        outer.pack(fill="both", expand=True, padx=20, pady=20)

        self._build_sidebar(outer)
        self._build_main(outer)

    # ── Sidebar — matches staff_management.py exactly ─────────────────────────
    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=BG_SIDEBAR, width=170)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo_box = tk.Frame(sidebar, bg=BG_SIDEBAR_LIGHT, bd=1, relief="solid")
        logo_box.pack(fill="x", padx=10, pady=(12, 10))
        tk.Label(logo_box, text="CareFlow\nAdmin Portal", bg=BG_SIDEBAR_LIGHT,
                 fg=TEXT, font=("Helvetica", 9, "bold"), justify="left",
                 padx=8, pady=8).pack(anchor="w")

        for item in ["Dashboard", "Patient", "Staff", "Clinic", "Records", "Billing"]:
            tk.Label(sidebar, text=item, bg=BG_SIDEBAR, fg=TEXT,
                     font=FONT_SMALL, anchor="w",
                     padx=10, pady=6).pack(fill="x", padx=10, pady=2)

    # ── Main content area ─────────────────────────────────────────────────────
    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG_LIGHT)
        main.pack(side="left", fill="both", expand=True, padx=(12, 0))

        # White header — same as every other page
        header = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        header.pack(fill="x")
        tk.Label(header, text="Welcome to CareFlow", font=FONT_TITLE,
                 bg=BG_PANEL, fg=TEXT).pack(side="left", padx=14, pady=14)
        tk.Label(header, text="Healthcare Administration System",
                 bg=BG_PANEL, fg=BTN_NEUTRAL,
                 font=("Helvetica", 10)).pack(side="left", pady=14)

        # White body panel
        body = tk.Frame(main, bg=BG_PANEL, bd=1, relief="solid")
        body.pack(fill="both", expand=True, pady=(10, 0))

        # Centered role selection
        center = tk.Frame(body, bg=BG_PANEL)
        center.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(center, text="Select your role to continue",
                 bg=BG_PANEL, fg=TEXT, font=("Helvetica", 15, "bold")).pack(pady=(0, 4))
        tk.Label(center, text="Choose the portal that matches your account type.",
                 bg=BG_PANEL, fg=BTN_NEUTRAL, font=FONT_SMALL).pack(pady=(0, 28))

        card_row = tk.Frame(center, bg=BG_PANEL)
        card_row.pack()

        self._make_role_card(card_row, "👤", "Staff Portal",
                             ["Patient records & scheduling",
                              "Billing & payments",
                              "Medical records"],
                             command=lambda: self._show_dashboard("Staff"))

        tk.Frame(card_row, bg=BG_PANEL, width=32).pack(side="left")

        self._make_role_card(card_row, "🛡", "Admin Portal",
                             ["Full system access",
                              "Staff accounts & roles",
                              "All modules & configuration"],
                             command=lambda: self._show_dashboard("Admin"))

    # ── Role card ─────────────────────────────────────────────────────────────
    def _show_dashboard(self, role):
        for w in self.winfo_children():
            w.destroy()
        frame = DashboardFrame(self, role=role, back_cmd=self._build_ui)
        frame.pack(fill="both", expand=True)

    # ── Role card ─────────────────────────────────────────────────────────────
    def _make_role_card(self, parent, icon, role, lines, command=None):
        card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid",
                        width=260, height=210, cursor="hand2")
        card.pack(side="left")
        card.pack_propagate(False)

        strip = tk.Frame(card, bg=BG_SIDEBAR_LIGHT, height=5)
        strip.pack(fill="x")

        icon_lbl = tk.Label(card, text=icon, bg=CARD_BG, fg=TEXT,
                            font=("Helvetica", 38))
        icon_lbl.pack(pady=(18, 6))

        role_lbl = tk.Label(card, text=role, bg=CARD_BG, fg=TEXT, font=FONT_CARD)
        role_lbl.pack()

        tk.Frame(card, bg=BG_SIDEBAR_LIGHT, height=1).pack(fill="x", padx=24, pady=(6, 8))

        line_labels = []
        for line in lines:
            lbl = tk.Label(card, text=line, bg=CARD_BG, fg=TEXT,
                           font=("Helvetica", 9), justify="center")
            lbl.pack()
            line_labels.append(lbl)

        hover = [card, icon_lbl, role_lbl] + line_labels

        def on_enter(_):
            card.configure(bg=BG_SIDEBAR_LIGHT)
            for w in hover[1:]:
                w.configure(bg=BG_SIDEBAR_LIGHT)

        def on_leave(_):
            card.configure(bg=CARD_BG)
            for w in hover[1:]:
                w.configure(bg=CARD_BG)

        for w in hover:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            if command:
                w.bind("<Button-1>", lambda _, cmd=command: cmd())


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
