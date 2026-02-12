import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# ------------------------
# Button Functions
# ------------------------
def patient_login():
    messagebox.showinfo("Patient Login", "Patient login clicked")

def staff_login():
    messagebox.showinfo("Staff Login", "Staff login clicked")

# ------------------------
# Main Window
# ------------------------
root = tk.Tk()
root.title("CareFlow Patient Portal")
root.geometry("400x500")
root.configure(bg="#ffffff")

# ------------------------
# Logo
# ------------------------
img = Image.open("logo.png")
img = img.resize((300, 300))
logo = ImageTk.PhotoImage(img)

logo_label = tk.Label(root, image=logo, bg="#ffffff")
logo_label.pack(pady=15)

# ------------------------
# Welcome Text
# ------------------------
title = tk.Label(
    root,
    text="Welcome to CareFlow",
    font=("Arial", 18, "bold"),
    bg="#ffffff"
)
title.pack(pady=5)

subtitle = tk.Label(
    root,
    text="Your secure medical patient portal",
    font=("Arial", 12),
    bg="#ffffff",
    fg="gray"
)
subtitle.pack(pady=5)

# ------------------------
# Buttons
# ------------------------
patient_btn = tk.Button(
    root,
    text="Patient Login",
    font=("Arial", 14),
    bg="#1978C5",
    fg="white",
    width=18,
    height=2,
    command=patient_login
)
patient_btn.pack(pady=20)

staff_btn = tk.Button(
    root,
    text="Staff Login",
    font=("Arial", 14),
    bg="#2196F3",
    fg="white",
    width=18,
    height=2,
    command=staff_login
)
staff_btn.pack()

# ------------------------
# Run App
# ------------------------
root.mainloop()
