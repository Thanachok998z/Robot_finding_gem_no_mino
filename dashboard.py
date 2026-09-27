import tkinter as tk
import subprocess
import sys
import os


# =========================
# ฟังก์ชันเปิดโปรแกรม
# =========================

def manual_click():
    print("กำลังเปิดระบบแมนนวล...")

    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "final_manual.py"
    )

    subprocess.Popen([sys.executable, file_path])


def auto_click():
    print("กำลังเปิดระบบออโต้...")

    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "auto.py"
    )

    subprocess.Popen([sys.executable, file_path])


# =========================
# สร้างหน้าต่างหลัก
# =========================

root = tk.Tk()
root.title("โปรแกรมตรวจจับหิน")

# ขนาดหน้าต่าง
window_width = 850
window_height = 550

# หาตำแหน่งกึ่งกลางหน้าจอ
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

center_x = int((screen_width - window_width) / 2)
center_y = int((screen_height - window_height) / 2)

root.geometry(
    f"{window_width}x{window_height}+{center_x}+{center_y}"
)

root.configure(bg="#f0f2f5")


# =========================
# Frame หลัก
# =========================

main_frame = tk.Frame(
    root,
    bg="#f0f2f5"
)

main_frame.pack(expand=True)


# =========================
# หัวข้อ
# =========================

label_title = tk.Label(
    main_frame,
    text="โปรแกรมตรวจจับหิน",
    font=("Tahoma", 28, "bold"),
    bg="#f0f2f5",
    fg="#1e293b"
)

label_title.pack(pady=40)


# =========================
# Frame ปุ่ม
# =========================

button_frame = tk.Frame(
    main_frame,
    bg="#f0f2f5"
)

button_frame.pack(pady=10)


# =========================
# Hover Effect
# =========================

def on_enter_manual(event):
    btn_manual.config(bg="#d97706")


def on_leave_manual(event):
    btn_manual.config(bg="#f59e0b")


def on_enter_auto(event):
    btn_auto.config(bg="#059669")


def on_leave_auto(event):
    btn_auto.config(bg="#10b981")


# =========================
# ปุ่ม Manual
# =========================

btn_manual = tk.Button(
    button_frame,
    text="ระบบแมนนวล",
    font=("Tahoma", 16, "bold"),
    width=14,
    height=2,
    bg="#f59e0b",
    fg="white",
    activebackground="#d97706",
    activeforeground="white",
    bd=0,
    relief="flat",
    cursor="hand2",
    command=manual_click
)

btn_manual.pack(
    side=tk.LEFT,
    padx=20
)

btn_manual.bind("<Enter>", on_enter_manual)
btn_manual.bind("<Leave>", on_leave_manual)


# =========================
# ปุ่ม Auto
# =========================

btn_auto = tk.Button(
    button_frame,
    text="ระบบออโต้",
    font=("Tahoma", 16, "bold"),
    width=14,
    height=2,
    bg="#10b981",
    fg="white",
    activebackground="#059669",
    activeforeground="white",
    bd=0,
    relief="flat",
    cursor="hand2",
    command=auto_click
)

btn_auto.pack(
    side=tk.RIGHT,
    padx=20
)

btn_auto.bind("<Enter>", on_enter_auto)
btn_auto.bind("<Leave>", on_leave_auto)


# =========================
# เริ่มโปรแกรม
# =========================

root.mainloop()
