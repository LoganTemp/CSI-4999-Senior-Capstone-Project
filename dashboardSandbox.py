#!/usr/bin/env python3
"""
careflow_dashboard.py

Includes:
 - Left sidebar with navigation buttons (functional placeholders that print actions)
 - Top header with title, user label, and simple avatar button
 - Four overview "cards" showing counts (clickable placeholders)
 - Section table area with headers and a simple sample row
 - Responsive-ish layout using grid; minimal dependencies (only stdlib Tkinter)
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# ---------- Configuration / Styles ----------
BG_LIGHT = "#e6f2ec"
BG_SIDEBAR = "#95ecdf"
BG_PANEL = "#ffffff"
ACCENT = "#308684"
CARD_BG = "#f7fff7"
TEXT = "#0b3d2e"
SIDEBAR_WIDTH = 800
FONT_HEADER = ("Helvetica", 16, "bold")
FONT_TITLE = ("Helvetica", 20, "bold")
FONT_CARD_NUM = ("Helvetica", 16, "bold")
FONT_CARD_LABEL = ("Helvetica", 10)
FONT_TABLE = ("Helvetica", 10)

# ---------- Helper functions (placeholders) ----------
def on_nav(name):
    print(f"[NAV] {name} clicked")

def on_card_click(name):
    print(f"[CARD] {name} clicked")
    messagebox.showinfo("Card Clicked", f"You clicked: {name}")

def on_action_view(row_id):
    print(f"[ACTION] View row {row_id}")
    messagebox.showinfo("View", f"View details for ID: {row_id}")

def on_action_edit(row_id):
    print(f"[ACTION] Edit row {row_id}")
    messagebox.showinfo("Edit", f"Edit details for ID: {row_id}")

# ---------- UI Building ----------
class CareFlowDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CareFlow Admin Portal - Dashboard")
        self.geometry("1100x680")
        self.configure(bg=BG_LIGHT)
        self._create_widgets()

    def _create_widgets(self):
        # Sidebar frame
        sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=SIDEBAR_WIDTH, relief="flat")
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")
        sidebar.grid_propagate(False)

        # Logo / App name
        logo_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        logo_frame.pack(fill="x", padx=12, pady=(12, 8))
        logo_lbl = tk.Label(logo_frame, text="CareFlow", bg=BG_SIDEBAR,
                            fg=TEXT, font=("Helvetica", 12, "bold"), justify="left")
        logo_lbl.pack(anchor="w")

        # Sidebar buttons
        nav_items = [("Dashboard", lambda: on_nav("Dashboard")),
                     ("Patient", lambda: on_nav("Patient")),
                     ("Staff", lambda: on_nav("Staff")),
                     ("Clinic", lambda: on_nav("Clinic")),
                     ("Records", lambda: on_nav("Records")),
                     ("Billing", lambda: on_nav("Billing"))]

        for label, cmd in nav_items:
            b = tk.Button(sidebar, text=label, anchor="w", command=cmd,
                          relief="flat", bg=BG_SIDEBAR, fg=TEXT, padx=12)
            b.pack(fill="x", pady=4, padx=8)

        # Main area frames
        header = tk.Frame(self, bg=BG_PANEL, height=80, relief="flat")
        header.grid(row=0, column=1, sticky="new", padx=(12,12), pady=(12,0))
        header.grid_columnconfigure(0, weight=1)

        content = tk.Frame(self, bg=BG_LIGHT)
        content.grid(row=1, column=1, sticky="nsew", padx=(12,12), pady=(8,12))
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Header contents
        header_left = tk.Frame(header, bg=BG_PANEL)
        header_left.grid(row=0, column=0, sticky="w", padx=12, pady=12)
        title = tk.Label(header_left, text="Dashboard Overview", bg=BG_PANEL, fg=TEXT, font=FONT_TITLE)
        title.pack(anchor="w")

        header_right = tk.Frame(header, bg=BG_PANEL)
        header_right.grid(row=0, column=1, sticky="e", padx=12, pady=12)
        signed_lbl = tk.Label(header_right, text="Signed in as\nAdministrators Name", bg=BG_PANEL, fg=TEXT, justify="right")
        signed_lbl.pack(anchor="e")
        avatar_btn = tk.Button(header_right, text="♡", bg=ACCENT, fg="white", width=3, command=lambda: on_nav("Profile"))
        avatar_btn.pack(anchor="e", pady=(6,0))

        # Overview cards
        cards_frame = tk.Frame(content, bg=BG_LIGHT)
        cards_frame.pack(fill="x", padx=6, pady=(0,12))

        card_infos = [
            ("Active Clinics", "12"),
            ("Total Patients", "234"),
            ("Active Staff", "27"),
            ("Unpaid Billing", "$1,540")
        ]

        for i, (label, value) in enumerate(card_infos):
            card = tk.Frame(cards_frame, bg=CARD_BG, bd=1, relief="raised", width=200, height=70)
            card.pack(side="left", padx=8, pady=6)
            card.pack_propagate(False)
            val_lbl = tk.Label(card, text=value, bg=CARD_BG, fg=TEXT, font=FONT_CARD_NUM)
            val_lbl.pack(anchor="nw", padx=10, pady=(8,0))
            label_lbl = tk.Button(card, text=label, bg=CARD_BG, fg=TEXT, font=FONT_CARD_LABEL,
                                  relief="flat", command=lambda l=label: on_card_click(l))
            label_lbl.pack(anchor="nw", padx=10, pady=(0,8))

        # Section title
        section_lbl = tk.Label(content, text="Section Title", bg=BG_LIGHT, fg=TEXT, font=FONT_HEADER)
        section_lbl.pack(anchor="w", padx=8, pady=(6,4))

        # Table area
        table_container = tk.Frame(content, bg=BG_PANEL, bd=1, relief="solid")
        table_container.pack(fill="both", expand=True, padx=8, pady=(0,8))

        # Table headers (ID, CLINIC NAME, ADDRESS, CITY, PHONE, STATUS, ACTION)
        headers = ["ID", "CLINIC NAME", "ADDRESS", "CITY", "PHONE", "STATUS", "ACTION"]
        header_frame = tk.Frame(table_container, bg="#f0f0f0")
        header_frame.pack(fill="x")
        for h in headers:
            w = 10 if h == "ID" else 20
            lbl = tk.Label(header_frame, text=h, bg="#f0f0f0", font=FONT_TABLE, borderwidth=1, relief="flat")
            lbl.pack(side="left", padx=6, pady=6)

        # Scrollable body
        body_frame = tk.Frame(table_container, bg=BG_PANEL)
        body_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(body_frame, bg=BG_PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg=BG_PANEL)

        scrollable.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate sample rows
        sample_rows = [
            {"id": "1", "clinic": "Northside Health", "address": "123 Maple St", "city": "Springfield", "phone": "555-0123", "status": "Active"},
            {"id": "2", "clinic": "River Clinic", "address": "98 River Rd", "city": "Lakeview", "phone": "555-0789", "status": "Inactive"},
            # Add a few blank sample lines to show scrolling space
        ]
        for r in sample_rows:
            self._add_table_row(scrollable, r)

        # Fill with empty rows for aesthetic similar to screenshot
        for i in range(8):
            self._add_table_row(scrollable, {"id": "", "clinic": "", "address": "", "city": "", "phone": "", "status": ""})

    def _add_table_row(self, parent, row):
        row_frame = tk.Frame(parent, bg=BG_PANEL, pady=6)
        row_frame.pack(fill="x", padx=4)

        lbl_id = tk.Label(row_frame, text=row.get("id", ""), bg=BG_PANEL, font=FONT_TABLE, width=6, anchor="w")
        lbl_id.pack(side="left", padx=6)

        lbl_clinic = tk.Label(row_frame, text=row.get("clinic", ""), bg=BG_PANEL, font=FONT_TABLE, width=24, anchor="w")
        lbl_clinic.pack(side="left", padx=6)

        lbl_address = tk.Label(row_frame, text=row.get("address", ""), bg=BG_PANEL, font=FONT_TABLE, width=30, anchor="w")
        lbl_address.pack(side="left", padx=6)

        lbl_city = tk.Label(row_frame, text=row.get("city", ""), bg=BG_PANEL, font=FONT_TABLE, width=18, anchor="w")
        lbl_city.pack(side="left", padx=6)

        lbl_phone = tk.Label(row_frame, text=row.get("phone", ""), bg=BG_PANEL, font=FONT_TABLE, width=14, anchor="w")
        lbl_phone.pack(side="left", padx=6)

        lbl_status = tk.Label(row_frame, text=row.get("status", ""), bg=BG_PANEL, font=FONT_TABLE, width=12, anchor="w")
        lbl_status.pack(side="left", padx=6)

        action_frame = tk.Frame(row_frame, bg=BG_PANEL, width=120)
        action_frame.pack(side="left", padx=6)
        # Only add buttons if id exists
        if str(row.get("id", "")).strip():
            vid = row["id"]
            btn_view = tk.Button(action_frame, text="View", command=lambda i=vid: on_action_view(i))
            btn_edit = tk.Button(action_frame, text="Edit", command=lambda i=vid: on_action_edit(i))
            btn_view.pack(side="left", padx=4)
            btn_edit.pack(side="left", padx=4)

# ---------- Main ----------
if __name__ == "__main__":
    app = CareFlowDashboard()
    app.mainloop()
