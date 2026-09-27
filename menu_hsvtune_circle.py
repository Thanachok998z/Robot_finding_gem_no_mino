import cv2
import numpy as np
import math
import tkinter as tk
from PIL import Image, ImageTk

from hsv_config import load_colors, save_colors


# =========================================================
# โหลดค่า HSV จาก JSON
# =========================================================

colors = load_colors()


# =========================================================
# รายชื่อสี
# =========================================================

color_names = [
    "GREEN",
    "ORANGE",
    "CYAN",
    "BLUE",
    "PURPLE",
    "RED"
]


# =========================================================
# สีปุ่ม
# =========================================================

button_colors = {

    "GREEN": "#7ED957",
    "ORANGE": "#FF7417",
    "CYAN": "#35AEEF",
    "BLUE": "#0755A5",
    "PURPLE": "#C65BE0",
    "RED": "#FF3030"
}


# =========================================================
# Theme
# =========================================================

BG_COLOR = "#F4F7FA"

CARD_COLOR = "#FFFFFF"

TOP_COLOR = "#FFFFFF"

BORDER_COLOR = "#E1E7ED"

TEXT_COLOR = "#172033"

SUBTEXT_COLOR = "#667085"

GREEN = "#10B981"

GREEN_DARK = "#059669"

BLUE = "#35AEEF"

RED = "#EF4444"

LIGHT_GREEN = "#ECFDF5"

LIGHT_BLUE = "#EFF8FF"

LIGHT_RED = "#FEF2F2"

VIDEO_BG = "#DCE3EA"


# =========================================================
# Font
# =========================================================

FONT_NORMAL = (
    "Arial",
    15
)

FONT_BUTTON = (
    "Arial",
    18,
    "bold"
)

FONT_TITLE = (
    "Arial",
    17,
    "bold"
)

FONT_SMALL = (
    "Arial",
    12
)


# =========================================================
# ตัวแปร
# =========================================================

selected_color = "GREEN"

selected_index = 0

confirmed_colors = set()


# =========================================================
# กล้อง
# =========================================================

camera_index = 0

cap = cv2.VideoCapture(
    camera_index
)

if not cap.isOpened():

    print(
        f"ไม่สามารถเปิดกล้อง index {camera_index}"
    )

    cap = None


# =========================================================
# MAIN WINDOW
# =========================================================

root = tk.Tk()

root.title(
    "HSV Tuner"
)

# เต็มพื้นที่ แต่ไม่บัง Taskbar
root.state(
    "zoomed"
)

root.configure(
    bg=BG_COLOR
)


# =========================================================
# Utility : Hover Button
# =========================================================

def add_hover(
    button,
    normal_color,
    hover_color
):

    def on_enter(event):

        button.config(
            bg=hover_color
        )

    def on_leave(event):

        button.config(
            bg=normal_color
        )

    button.bind(
        "<Enter>",
        on_enter
    )

    button.bind(
        "<Leave>",
        on_leave
    )


# =========================================================
# เลือกสี
# =========================================================

def select_color(index):

    global selected_color
    global selected_index

    selected_index = index

    selected_color = color_names[index]

    load_color_to_slider(
        selected_color
    )

    update_color_buttons()

    update_status()


# =========================================================
# อัปเดตปุ่มสี
# =========================================================

def update_color_buttons():

    for i, name in enumerate(
        color_names
    ):

        if i == selected_index:

            color_buttons[i].config(
                relief="sunken",
                bd=4,
                highlightthickness=2,
                highlightbackground=TEXT_COLOR
            )

        else:

            color_buttons[i].config(
                relief="flat",
                bd=0,
                highlightthickness=0
            )


# =========================================================
# โหลดค่า HSV เข้า Slider
# =========================================================

def load_color_to_slider(
    color_name
):

    lower = colors[color_name]["lower"]

    upper = colors[color_name]["upper"]

    h_min_scale.set(
        lower[0]
    )

    h_max_scale.set(
        upper[0]
    )

    s_min_scale.set(
        lower[1]
    )

    s_max_scale.set(
        upper[1]
    )

    v_min_scale.set(
        lower[2]
    )

    v_max_scale.set(
        upper[2]
    )

    update_slider_labels()


# =========================================================
# อ่านค่า HSV จาก Slider
# =========================================================

def get_hsv_values():

    h_min = int(
        h_min_scale.get()
    )

    h_max = int(
        h_max_scale.get()
    )

    s_min = int(
        s_min_scale.get()
    )

    s_max = int(
        s_max_scale.get()
    )

    v_min = int(
        v_min_scale.get()
    )

    v_max = int(
        v_max_scale.get()
    )

    return (
        h_min,
        h_max,
        s_min,
        s_max,
        v_min,
        v_max
    )


# =========================================================
# อัปเดตข้อความ Slider
# =========================================================

def update_slider_labels():

    (
        h_min,
        h_max,
        s_min,
        s_max,
        v_min,
        v_max
    ) = get_hsv_values()

    h_min_label.config(
        text=f"H MIN  {h_min}"
    )

    h_max_label.config(
        text=f"H MAX  {h_max}"
    )

    s_min_label.config(
        text=f"S MIN  {s_min}"
    )

    s_max_label.config(
        text=f"S MAX  {s_max}"
    )

    v_min_label.config(
        text=f"V MIN  {v_min}"
    )

    v_max_label.config(
        text=f"V MAX  {v_max}"
    )


# =========================================================
# Slider เปลี่ยน
# =========================================================

def slider_changed(value):

    update_slider_labels()


# =========================================================
# SAVE
# =========================================================

def save_hsv():

    (
        h_min,
        h_max,
        s_min,
        s_max,
        v_min,
        v_max
    ) = get_hsv_values()


    # -----------------------------------------
    # อัปเดตค่าของสี
    # -----------------------------------------

    colors[selected_color] = {

        "lower": [
            h_min,
            s_min,
            v_min
        ],

        "upper": [
            h_max,
            s_max,
            v_max
        ]
    }


    # -----------------------------------------
    # บันทึก JSON
    # -----------------------------------------

    success = save_colors(
        colors
    )


    if success:

        print()

        print(
            "==================================="
        )

        print(
            f"สี = {selected_color}"
        )

        print(
            f"H = {h_min} - {h_max}"
        )

        print(
            f"S = {s_min} - {s_max}"
        )

        print(
            f"V = {v_min} - {v_max}"
        )

        print()

        print(
            f"lower = "
            f"[{h_min}, {s_min}, {v_min}]"
        )

        print(
            f"upper = "
            f"[{h_max}, {s_max}, {v_max}]"
        )

        print(
            "บันทึกลง hsv_config.json แล้ว"
        )

        print(
            "==================================="
        )


        status_label.config(
            text=f"บันทึก {selected_color} แล้ว",
            fg=GREEN_DARK,
            bg=LIGHT_GREEN
        )

        status_card.config(
            bg=LIGHT_GREEN
        )


# =========================================================
# Confirm Color
# =========================================================

def confirm_color():

    save_hsv()

    confirmed_colors.add(
        selected_color
    )

    update_status()


# =========================================================
# Clear
# =========================================================

def clear_current_color():

    global colors

    colors = load_colors()

    load_color_to_slider(
        selected_color
    )

    status_label.config(
        text=f"คืนค่า {selected_color} แล้ว",
        fg=RED,
        bg=LIGHT_RED
    )

    status_card.config(
        bg=LIGHT_RED
    )


# =========================================================
# Status
# =========================================================

def update_status():

    confirmed_count = len(
        confirmed_colors
    )

    remaining = (
        len(color_names)
        -
        confirmed_count
    )

    status_label.config(

        text=(
            f"เหลือ {remaining} / 6 สี\n"
            f"ยืนยันแล้ว "
            f"{confirmed_count} / 6 สี"
        )
    )


# =========================================================
# เปลี่ยนกล้อง
# =========================================================

def change_camera(
    value=None
):

    global cap
    global camera_index

    try:

        new_index = int(
            camera_var.get()
        )

    except:

        return


    if new_index == camera_index:

        return


    if cap is not None:

        cap.release()


    camera_index = new_index

    cap = cv2.VideoCapture(
        camera_index
    )


    if not cap.isOpened():

        print(
            f"ไม่สามารถเปิดกล้อง "
            f"index {camera_index}"
        )

        cap = None


# =========================================================
# กลับหน้า Auto
# =========================================================

def back_to_auto():

    close_program()


# =========================================================
# ปิด
# =========================================================

def close_program():

    global cap

    if cap is not None:

        cap.release()

        cap = None

    root.destroy()


# =========================================================
# Keyboard
# =========================================================

def keyboard(event):

    key = event.keysym.lower()

    if key == "s":

        save_hsv()

    elif key == "q":

        back_to_auto()


root.bind(
    "<Key>",
    keyboard
)


# =========================================================
# TOP BAR
# =========================================================

top_frame = tk.Frame(

    root,

    bg=TOP_COLOR,

    height=88,

    highlightbackground=BORDER_COLOR,

    highlightthickness=1
)

top_frame.pack(

    fill="x",

    padx=12,

    pady=(10, 0)
)

top_frame.pack_propagate(
    False
)


# =========================================================
# Color Buttons
# =========================================================

color_buttons = []


for i, name in enumerate(
    color_names
):

    btn = tk.Button(

        top_frame,

        text=f"Color {i + 1}",

        font=FONT_BUTTON,

        bg=button_colors[name],

        fg="white" if name in [
            "BLUE",
            "PURPLE",
            "RED"
        ] else "black",

        activeforeground="black",

        relief="flat",

        bd=0,

        cursor="hand2",

        command=lambda x=i:
        select_color(x)
    )


    btn.pack(

        side="left",

        expand=True,

        fill="both",

        padx=6,

        pady=10
    )


    color_buttons.append(
        btn
    )


# =========================================================
# CAMERA BAR
# =========================================================

camera_frame = tk.Frame(

    root,

    bg=BG_COLOR
)

camera_frame.pack(

    fill="x",

    padx=30,

    pady=(12, 5)
)


# =========================================================
# CAMERA LEFT CARD
# =========================================================

camera_left = tk.Frame(

    camera_frame,

    bg=CARD_COLOR,

    highlightbackground=BORDER_COLOR,

    highlightthickness=1
)

camera_left.pack(
    side="left"
)


camera_title = tk.Label(

    camera_left,

    text="  Camera Index  ",

    font=(
        "Arial",
        16,
        "bold"
    ),

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

camera_title.pack(

    side="left",

    pady=8
)


camera_var = tk.StringVar(

    value=str(
        camera_index
    )
)


camera_menu = tk.OptionMenu(

    camera_left,

    camera_var,

    "0",
    "1",
    "2",
    "3",
    "4",

    command=change_camera
)

camera_menu.config(

    font=(
        "Arial",
        14,
        "bold"
    ),

    width=4,

    bg="#EEF2F6",

    fg=TEXT_COLOR,

    relief="flat",

    bd=0,

    highlightthickness=0
)

camera_menu.pack(

    side="left",

    padx=8,

    pady=5
)


# =========================================================
# BACK BUTTON
# =========================================================

back_button = tk.Button(

    camera_frame,

    text="←  กลับหน้า Auto",

    font=(
        "Arial",
        14,
        "bold"
    ),

    command=back_to_auto,

    bg=CARD_COLOR,

    fg=TEXT_COLOR,

    activebackground="#E8F7F1",

    activeforeground=GREEN_DARK,

    relief="flat",

    bd=0,

    cursor="hand2",

    padx=18,

    pady=8
)

back_button.pack(

    side="right"
)

add_hover(
    back_button,
    CARD_COLOR,
    "#E8F7F1"
)


# =========================================================
# HSV SLIDER
# =========================================================

slider_card = tk.Frame(

    root,

    bg=CARD_COLOR,

    highlightbackground=BORDER_COLOR,

    highlightthickness=1
)

slider_card.pack(

    fill="x",

    padx=30,

    pady=(5, 10)
)


slider_frame = tk.Frame(

    slider_card,

    bg=CARD_COLOR
)

slider_frame.pack(

    fill="x",

    padx=20,

    pady=8
)


# =========================================================
# H
# =========================================================

h_frame = tk.Frame(

    slider_frame,

    bg=CARD_COLOR
)

h_frame.pack(

    side="left",

    expand=True,

    fill="x",

    padx=8
)


h_min_label = tk.Label(

    h_frame,

    text="H MIN  0",

    font=FONT_SMALL,

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

h_min_label.pack(
    side="left"
)


h_min_scale = tk.Scale(

    h_frame,

    from_=0,

    to=179,

    orient="horizontal",

    showvalue=False,

    command=slider_changed,

    bg=CARD_COLOR,

    highlightthickness=0,

    troughcolor="#E4EAF0",

    activebackground=GREEN
)

h_min_scale.pack(

    side="left",

    expand=True,

    fill="x"
)


h_max_label = tk.Label(

    h_frame,

    text="H MAX  179",

    font=FONT_SMALL,

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

h_max_label.pack(
    side="left"
)


h_max_scale = tk.Scale(

    h_frame,

    from_=0,

    to=179,

    orient="horizontal",

    showvalue=False,

    command=slider_changed,

    bg=CARD_COLOR,

    highlightthickness=0,

    troughcolor="#E4EAF0",

    activebackground=GREEN
)

h_max_scale.pack(

    side="left",

    expand=True,

    fill="x"
)


# =========================================================
# S
# =========================================================

s_frame = tk.Frame(

    slider_frame,

    bg=CARD_COLOR
)

s_frame.pack(

    side="left",

    expand=True,

    fill="x",

    padx=8
)


s_min_label = tk.Label(

    s_frame,

    text="S MIN  0",

    font=FONT_SMALL,

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

s_min_label.pack(
    side="left"
)


s_min_scale = tk.Scale(

    s_frame,

    from_=0,

    to=255,

    orient="horizontal",

    showvalue=False,

    command=slider_changed,

    bg=CARD_COLOR,

    highlightthickness=0,

    troughcolor="#E4EAF0",

    activebackground=GREEN
)

s_min_scale.pack(

    side="left",

    expand=True,

    fill="x"
)


s_max_label = tk.Label(

    s_frame,

    text="S MAX  255",

    font=FONT_SMALL,

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

s_max_label.pack(
    side="left"
)


s_max_scale = tk.Scale(

    s_frame,

    from_=0,

    to=255,

    orient="horizontal",

    showvalue=False,

    command=slider_changed,

    bg=CARD_COLOR,

    highlightthickness=0,

    troughcolor="#E4EAF0",

    activebackground=GREEN
)

s_max_scale.pack(

    side="left",

    expand=True,

    fill="x"
)


# =========================================================
# V
# =========================================================

v_frame = tk.Frame(

    slider_frame,

    bg=CARD_COLOR
)

v_frame.pack(

    side="left",

    expand=True,

    fill="x",

    padx=8
)


v_min_label = tk.Label(

    v_frame,

    text="V MIN  0",

    font=FONT_SMALL,

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

v_min_label.pack(
    side="left"
)


v_min_scale = tk.Scale(

    v_frame,

    from_=0,

    to=255,

    orient="horizontal",

    showvalue=False,

    command=slider_changed,

    bg=CARD_COLOR,

    highlightthickness=0,

    troughcolor="#E4EAF0",

    activebackground=GREEN
)

v_min_scale.pack(

    side="left",

    expand=True,

    fill="x"
)


v_max_label = tk.Label(

    v_frame,

    text="V MAX  255",

    font=FONT_SMALL,

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

v_max_label.pack(
    side="left"
)


v_max_scale = tk.Scale(

    v_frame,

    from_=0,

    to=255,

    orient="horizontal",

    showvalue=False,

    command=slider_changed,

    bg=CARD_COLOR,

    highlightthickness=0,

    troughcolor="#E4EAF0",

    activebackground=GREEN
)

v_max_scale.pack(

    side="left",

    expand=True,

    fill="x"
)


# =========================================================
# VIDEO AREA
# =========================================================

video_frame = tk.Frame(

    root,

    bg=BG_COLOR
)

video_frame.pack(

    fill="both",

    expand=True,

    padx=30,

    pady=5
)


# =========================================================
# VIDEO LEFT
# =========================================================

left_video = tk.Frame(

    video_frame,

    bg=VIDEO_BG,

    highlightbackground=BORDER_COLOR,

    highlightthickness=1
)

left_video.place(

    relx=0,

    rely=0,

    relwidth=0.70,

    relheight=1
)


# =========================================================
# RIGHT PANEL
# =========================================================

right_panel = tk.Frame(

    video_frame,

    bg=BG_COLOR
)

right_panel.place(

    relx=0.715,

    rely=0,

    relwidth=0.285,

    relheight=1
)


# =========================================================
# VIDEO TITLES
# =========================================================

original_title = tk.Label(

    left_video,

    text="●  Original",

    font=FONT_TITLE,

    bg=VIDEO_BG,

    fg=TEXT_COLOR,

    anchor="w"
)

original_title.place(

    relx=0.015,

    rely=0.01,

    relwidth=0.47,

    height=30
)


mark_title = tk.Label(

    left_video,

    text="●  Mark",

    font=FONT_TITLE,

    bg=VIDEO_BG,

    fg=TEXT_COLOR,

    anchor="w"
)

mark_title.place(

    relx=0.515,

    rely=0.01,

    relwidth=0.47,

    height=30
)


separated_title = tk.Label(

    left_video,

    text="●  Separated",

    font=FONT_TITLE,

    bg=VIDEO_BG,

    fg=TEXT_COLOR,

    anchor="w"
)

separated_title.place(

    relx=0.015,

    rely=0.51,

    relwidth=0.47,

    height=30
)


detect_title = tk.Label(

    left_video,

    text="●  Detect",

    font=FONT_TITLE,

    bg=VIDEO_BG,

    fg=TEXT_COLOR,

    anchor="w"
)

detect_title.place(

    relx=0.515,

    rely=0.51,

    relwidth=0.47,

    height=30
)


# =========================================================
# IMAGE
# =========================================================

original_label = tk.Label(

    left_video,

    bg="#101820"
)

original_label.place(

    relx=0.01,

    rely=0.06,

    relwidth=0.48,

    relheight=0.43
)


mark_label = tk.Label(

    left_video,

    bg="#101820"
)

mark_label.place(

    relx=0.51,

    rely=0.06,

    relwidth=0.48,

    relheight=0.43
)


separated_label = tk.Label(

    left_video,

    bg="#101820"
)

separated_label.place(

    relx=0.01,

    rely=0.57,

    relwidth=0.48,

    relheight=0.43
)


detect_label = tk.Label(

    left_video,

    bg="#101820"
)

detect_label.place(

    relx=0.51,

    rely=0.57,

    relwidth=0.48,

    relheight=0.43
)


# =========================================================
# STATUS CARD
# =========================================================

status_card = tk.Frame(

    right_panel,

    bg=LIGHT_GREEN,

    highlightbackground=BORDER_COLOR,

    highlightthickness=1
)

status_card.pack(

    fill="x",

    pady=(0, 12)
)


status_title = tk.Label(

    status_card,

    text="HSV STATUS",

    font=(
        "Arial",
        12,
        "bold"
    ),

    bg=LIGHT_GREEN,

    fg=SUBTEXT_COLOR
)

status_title.pack(

    pady=(15, 3)
)


status_label = tk.Label(

    status_card,

    text=(
        "เหลือ 6 / 6 สี\n"
        "ยืนยันแล้ว 0 / 6 สี"
    ),

    font=(
        "Arial",
        20,
        "bold"
    ),

    bg=LIGHT_GREEN,

    fg=GREEN_DARK,

    justify="center"
)

status_label.pack(

    pady=(0, 15)
)


# =========================================================
# CURRENT COLOR CARD
# =========================================================

current_card = tk.Frame(

    right_panel,

    bg=CARD_COLOR,

    highlightbackground=BORDER_COLOR,

    highlightthickness=1
)

current_card.pack(

    fill="x",

    pady=(0, 12)
)


current_title = tk.Label(

    current_card,

    text="CURRENT COLOR",

    font=(
        "Arial",
        11,
        "bold"
    ),

    bg=CARD_COLOR,

    fg=SUBTEXT_COLOR
)

current_title.pack(

    anchor="w",

    padx=15,

    pady=(12, 2)
)


current_color_label = tk.Label(

    current_card,

    textvariable=tk.StringVar(
        value=selected_color
    ),

    font=(
        "Arial",
        23,
        "bold"
    ),

    bg=CARD_COLOR,

    fg=TEXT_COLOR
)

current_color_label.pack(

    anchor="w",

    padx=15,

    pady=(0, 12)
)


# =========================================================
# UPDATE CURRENT COLOR LABEL
# =========================================================

old_select_color = select_color


def select_color(index):

    global selected_color
    global selected_index

    selected_index = index

    selected_color = color_names[index]

    load_color_to_slider(
        selected_color
    )

    update_color_buttons()

    update_status()

    current_color_label.config(
        text=selected_color
    )


# =========================================================
# BUTTON AREA
# =========================================================

button_frame = tk.Frame(

    right_panel,

    bg=BG_COLOR
)

button_frame.pack(

    fill="x",

    pady=(0, 12)
)


# =========================================================
# CLEAR
# =========================================================

clear_button = tk.Button(

    button_frame,

    text="Clear",

    font=(
        "Arial",
        19,
        "bold"
    ),

    bg="#FFE7E7",

    fg=RED,

    activebackground="#FFD0D0",

    relief="flat",

    bd=0,

    cursor="hand2",

    command=clear_current_color,

    pady=10
)

clear_button.pack(

    side="left",

    expand=True,

    fill="both",

    padx=(0, 5)
)


# =========================================================
# SAVE
# =========================================================

save_button = tk.Button(

    button_frame,

    text="Save",

    font=(
        "Arial",
        19,
        "bold"
    ),

    bg=LIGHT_BLUE,

    fg="#0875B8",

    activebackground="#D9F0FF",

    relief="flat",

    bd=0,

    cursor="hand2",

    command=save_hsv,

    pady=10
)

save_button.pack(

    side="left",

    expand=True,

    fill="both",

    padx=(5, 0)
)


add_hover(
    clear_button,
    "#FFE7E7",
    "#FFD4D4"
)

add_hover(
    save_button,
    LIGHT_BLUE,
    "#D8F0FF"
)


# =========================================================
# CONFIRM
# =========================================================

confirm_button = tk.Button(

    right_panel,

    text="✓  Confirm Color",

    font=(
        "Arial",
        19,
        "bold"
    ),

    bg=GREEN,

    fg="white",

    activebackground=GREEN_DARK,

    activeforeground="white",

    relief="flat",

    bd=0,

    cursor="hand2",

    command=confirm_color,

    pady=13
)

confirm_button.pack(

    fill="x",

    pady=(0, 10)
)


add_hover(
    confirm_button,
    GREEN,
    GREEN_DARK
)


# =========================================================
# SHORTCUT
# =========================================================

shortcut_label = tk.Label(

    right_panel,

    text="S  Save     •     Q  กลับหน้า Auto",

    font=(
        "Arial",
        10
    ),

    bg=BG_COLOR,

    fg=SUBTEXT_COLOR
)

shortcut_label.pack(
    pady=5
)


# =========================================================
# โหลด GREEN
# =========================================================

load_color_to_slider(
    "GREEN"
)

update_color_buttons()


# =========================================================
# OpenCV -> Tkinter
# =========================================================

def cv_to_tk(
    frame,
    label
):

    if frame is None:

        return


    rgb = cv2.cvtColor(

        frame,

        cv2.COLOR_BGR2RGB
    )


    width = label.winfo_width()

    height = label.winfo_height()


    if width <= 1:

        width = 500


    if height <= 1:

        height = 300


    h, w = rgb.shape[:2]


    scale = min(

        width / w,

        height / h
    )


    new_w = max(

        1,

        int(w * scale)
    )


    new_h = max(

        1,

        int(h * scale)
    )


    rgb = cv2.resize(

        rgb,

        (
            new_w,
            new_h
        )
    )


    image = Image.fromarray(
        rgb
    )


    photo = ImageTk.PhotoImage(
        image=image
    )


    label.config(
        image=photo
    )


    label.image = photo


# =========================================================
# Camera Processing
# =========================================================

def update_camera():

    global cap


    if cap is None:

        root.after(
            30,
            update_camera
        )

        return


    ret, frame = cap.read()


    if not ret:

        root.after(
            30,
            update_camera
        )

        return


    # =====================================================
    # MIRROR CAMERA
    # =====================================================

    frame = cv2.flip(
        frame,
        1
    )


    # =====================================================
    # ORIGINAL
    # =====================================================

    original = frame.copy()


    # =====================================================
    # HSV
    # =====================================================

    hsv = cv2.cvtColor(

        frame,

        cv2.COLOR_BGR2HSV
    )


    # =====================================================
    # HSV
    # =====================================================

    (
        h_min,
        h_max,
        s_min,
        s_max,
        v_min,
        v_max
    ) = get_hsv_values()


    # =====================================================
    # MASK
    # =====================================================

    lower = np.array(

        [
            h_min,
            s_min,
            v_min
        ],

        dtype=np.uint8
    )


    upper = np.array(

        [
            h_max,
            s_max,
            v_max
        ],

        dtype=np.uint8
    )


    mask = cv2.inRange(

        hsv,

        lower,

        upper
    )


    # =====================================================
    # MORPHOLOGY
    # =====================================================

    kernel = np.ones(

        (
            5,
            5
        ),

        np.uint8
    )


    mask = cv2.morphologyEx(

        mask,

        cv2.MORPH_OPEN,

        kernel
    )


    # =====================================================
    # SEPARATED
    # =====================================================

    separated = cv2.bitwise_and(

        frame,

        frame,

        mask=mask
    )


    # =====================================================
    # DETECTION
    # =====================================================

    detection = frame.copy()


    contours, _ = cv2.findContours(

        mask,

        cv2.RETR_EXTERNAL,

        cv2.CHAIN_APPROX_SIMPLE
    )


    count = 0


    for contour in contours:


        # -----------------------------------------------
        # Area
        # -----------------------------------------------

        area = cv2.contourArea(
            contour
        )


        if area < 3000:

            continue


        # -----------------------------------------------
        # Perimeter
        # -----------------------------------------------

        perimeter = cv2.arcLength(

            contour,

            True
        )


        if perimeter == 0:

            continue


        # -----------------------------------------------
        # Circularity
        # -----------------------------------------------

        circularity = (

            4 *

            math.pi *

            area

            /

            (
                perimeter *
                perimeter
            )
        )


        if circularity < 0.75:

            continue


        # -----------------------------------------------
        # Bounding Box
        # -----------------------------------------------

        x, y, w, h = cv2.boundingRect(

            contour
        )


        # -----------------------------------------------
        # Ratio
        # -----------------------------------------------

        ratio = w / h


        if ratio < 0.8 or ratio > 1.2:

            continue


        # -----------------------------------------------
        # Center
        # -----------------------------------------------

        center_x = x + w // 2

        center_y = y + h // 2


        count += 1


        # -----------------------------------------------
        # Rectangle
        # -----------------------------------------------

        cv2.rectangle(

            detection,

            (
                x,
                y
            ),

            (
                x + w,
                y + h
            ),

            (
                0,
                255,
                0
            ),

            3
        )


        # -----------------------------------------------
        # Center
        # -----------------------------------------------

        cv2.circle(

            detection,

            (
                center_x,
                center_y
            ),

            5,

            (
                0,
                0,
                255
            ),

            -1
        )


        # -----------------------------------------------
        # Color
        # -----------------------------------------------

        cv2.putText(

            detection,

            selected_color,

            (
                x,
                max(
                    20,
                    y - 10
                )
            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.7,

            (
                0,
                0,
                0
            ),

            2
        )


        # -----------------------------------------------
        # Coordinate
        # -----------------------------------------------

        cv2.putText(

            detection,

            f"({center_x},{center_y})",

            (
                x + 5,
                y + h - 10
            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.5,

            (
                0,
                0,
                0
            ),

            1
        )


    # =====================================================
    # MASK BGR
    # =====================================================

    mask_color = cv2.cvtColor(

        mask,

        cv2.COLOR_GRAY2BGR
    )


    # =====================================================
    # TEXT
    # =====================================================

    cv2.putText(

        original,

        "ORIGINAL",

        (
            20,
            35
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (
            0,
            0,
            255
        ),

        2
    )


    cv2.putText(

        mask_color,

        f"MASK - {selected_color}",

        (
            20,
            35
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (
            0,
            0,
            255
        ),

        2
    )


    cv2.putText(

        separated,

        f"SEPARATED - {selected_color}",

        (
            20,
            35
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (
            0,
            0,
            255
        ),

        2
    )


    cv2.putText(

        detection,

        "DETECTION",

        (
            20,
            35
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        1,

        (
            0,
            0,
            255
        ),

        2
    )


    cv2.putText(

        detection,

        f"Detected: {count}",

        (
            20,
            70
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.7,

        (
            0,
            0,
            255
        ),

        2
    )


    # =====================================================
    # แสดงภาพ
    # =====================================================

    cv_to_tk(

        original,

        original_label
    )


    cv_to_tk(

        mask_color,

        mark_label
    )


    cv_to_tk(

        separated,

        separated_label
    )


    cv_to_tk(

        detection,

        detect_label
    )


    # =====================================================
    # ทำต่อ
    # =====================================================

    root.after(

        30,

        update_camera
    )


# =========================================================
# ปุ่ม X
# =========================================================

root.protocol(

    "WM_DELETE_WINDOW",

    close_program
)


# =========================================================
# เริ่มกล้อง
# =========================================================

update_camera()


# =========================================================
# RUN
# =========================================================

root.mainloop()