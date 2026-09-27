import tkinter as tk


# =========================================================
# MAIN WINDOW
# =========================================================

root = tk.Tk()

root.title(
    "ปรับสี HSV"
)


# =========================================================
# FULLSCREEN
# =========================================================

root.attributes(
    "-fullscreen",
    True
)


root.configure(
    bg="#eef1f5"
)


# =========================================================
# TITLE
# =========================================================

title = tk.Label(
    root,
    text="ปรับสี HSV",
    font=("Tahoma", 36, "bold"),
    bg="#eef1f5",
    fg="#111827"
)

title.pack(
    pady=40
)


# =========================================================
# CONTENT
# =========================================================

content = tk.Frame(
    root,
    bg="#ffffff"
)

content.pack(
    fill="both",
    expand=True,
    padx=40,
    pady=(0, 40)
)


label = tk.Label(
    content,
    text="HSV TUNE",
    font=("Tahoma", 30, "bold"),
    bg="#ffffff",
    fg="#111827"
)

label.pack(
    pady=100
)


# =========================================================
# CLOSE
# =========================================================

def close_window():

    root.destroy()


close_button = tk.Button(
    content,
    text="ปิด",
    font=("Tahoma", 18, "bold"),
    bg="#ef4444",
    fg="white",
    activebackground="#dc2626",
    activeforeground="white",
    bd=0,
    cursor="hand2",
    command=close_window
)

close_button.pack(
    ipadx=50,
    ipady=15
)


# =========================================================
# ESC
# =========================================================

root.bind(
    "<Escape>",
    lambda event: root.destroy()
)


# =========================================================
# RUN
# =========================================================

root.mainloop()