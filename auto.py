import tkinter as tk
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageTk

# =========================================================
# OPEN OTHER PROGRAM
# =========================================================

def open_program(filename):

    file_path = Path(__file__).with_name(
        filename
    )

    if not file_path.exists():

        print(
            f"ไม่พบไฟล์: {filename}"
        )

        return

    subprocess.Popen([
        sys.executable,
        str(file_path)
    ])


# =========================================================
# OPEN CIRCLE HSV
# =========================================================

def open_circle():

    open_program(
        "menu_hsvtune_circle.py"
    )


# =========================================================
# OPEN GEM HSV
# =========================================================

def open_gem():

    open_program(
        "menu_hsvtune_gem.py"
    )


# =========================================================
# CAMERA SETTINGS
# =========================================================

camera_index = 0

camera_flip = False

camera_border = 10

camera_border_enabled = True


# =========================================================
# CAMERA
# =========================================================

cap = None


def open_camera():

    global cap

    if cap is not None:

        cap.release()

        cap = None

    cap = cv2.VideoCapture(
        camera_index
    )

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        1280
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        720
    )


# =========================================================
# APPLY CAMERA SETTINGS
# =========================================================

def apply_camera_settings(
    new_index,
    new_flip,
    new_border_enabled,
    new_border
):

    global camera_index
    global camera_flip
    global camera_border_enabled
    global camera_border

    camera_index = new_index

    camera_flip = new_flip

    camera_border_enabled = (
        new_border_enabled
    )

    camera_border = new_border

    open_camera()


# =========================================================
# CAMERA SETTINGS WINDOW
# =========================================================

def open_camera_settings():

    # -----------------------------------------------------
    # Temporary values
    # -----------------------------------------------------

    temp_index = tk.IntVar(
        value=camera_index
    )

    temp_flip = tk.BooleanVar(
        value=camera_flip
    )

    temp_border_enabled = tk.BooleanVar(
        value=camera_border_enabled
    )

    temp_border = tk.IntVar(
        value=camera_border
    )

    # -----------------------------------------------------
    # Window
    # -----------------------------------------------------

    window = tk.Toplevel(
        root
    )

    window.title(
        "ปรับกล้อง"
    )

    window.geometry(
        "460x520"
    )

    window.resizable(
        False,
        False
    )

    window.configure(
        bg="#f8fafc"
    )

    window.transient(
        root
    )

    window.grab_set()

    # =====================================================
    # TITLE
    # =====================================================

    tk.Label(
        window,
        text="ปรับกล้อง",
        font=(
            "Tahoma",
            22,
            "bold"
        ),
        bg="#f8fafc",
        fg="#111827"
    ).pack(
        pady=(25, 20)
    )

    # =====================================================
    # CAMERA INDEX
    # =====================================================

    index_frame = tk.Frame(
        window,
        bg="#ffffff",
        highlightbackground="#d7dee8",
        highlightthickness=1
    )

    index_frame.pack(
        fill="x",
        padx=25,
        pady=8
    )

    tk.Label(
        index_frame,
        text="Camera Index",
        font=(
            "Tahoma",
            12,
            "bold"
        ),
        bg="#ffffff",
        fg="#111827"
    ).pack(
        anchor="w",
        padx=15,
        pady=(12, 5)
    )

    index_menu = tk.OptionMenu(
        index_frame,
        temp_index,
        0,
        1,
        2,
        3,
        4
    )

    index_menu.configure(
        bg="#eef2f7",
        fg="#111827",
        activebackground="#dbeafe",
        relief="flat",
        bd=0,
        font=(
            "Tahoma",
            11
        ),
        width=10
    )

    index_menu.pack(
        anchor="w",
        padx=15,
        pady=(0, 12)
    )

    # =====================================================
    # FLIP
    # =====================================================

    flip_frame = tk.Frame(
        window,
        bg="#ffffff",
        highlightbackground="#d7dee8",
        highlightthickness=1
    )

    flip_frame.pack(
        fill="x",
        padx=25,
        pady=8
    )

    flip_check = tk.Checkbutton(
        flip_frame,
        text="กลับภาพกล้อง (Flip)",
        variable=temp_flip,
        bg="#ffffff",
        fg="#111827",
        activebackground="#ffffff",
        activeforeground="#111827",
        selectcolor="#ffffff",
        font=(
            "Tahoma",
            12,
            "bold"
        ),
        anchor="w"
    )

    flip_check.pack(
        fill="x",
        padx=15,
        pady=15
    )

    # =====================================================
    # BORDER
    # =====================================================

    border_frame = tk.Frame(
        window,
        bg="#ffffff",
        highlightbackground="#d7dee8",
        highlightthickness=1
    )

    border_frame.pack(
        fill="x",
        padx=25,
        pady=8
    )

    border_check = tk.Checkbutton(
        border_frame,
        text="สร้างเส้นครอบพื้นที่ตรวจจับ",
        variable=temp_border_enabled,
        bg="#ffffff",
        fg="#111827",
        activebackground="#ffffff",
        activeforeground="#111827",
        selectcolor="#ffffff",
        font=(
            "Tahoma",
            12,
            "bold"
        ),
        anchor="w"
    )

    border_check.pack(
        fill="x",
        padx=15,
        pady=(12, 5)
    )

    # -----------------------------------------------------
    # Border slider
    # -----------------------------------------------------

    border_value_label = tk.Label(
        border_frame,
        text=f"{temp_border.get()} px",
        bg="#ffffff",
        fg="#2563eb",
        font=(
            "Tahoma",
            11,
            "bold"
        )
    )

    border_value_label.pack(
        anchor="e",
        padx=15
    )

    def update_border_label(value):

        border_value_label.configure(
            text=f"{int(float(value))} px"
        )

    border_slider = tk.Scale(
        border_frame,
        from_=1,
        to=100,
        orient="horizontal",
        variable=temp_border,
        command=update_border_label,
        showvalue=False,
        bg="#ffffff",
        fg="#111827",
        troughcolor="#dbeafe",
        activebackground="#2563eb",
        highlightthickness=0,
        bd=0,
        sliderlength=22
    )

    border_slider.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    # =====================================================
    # BUTTON AREA
    # =====================================================

    button_frame = tk.Frame(
        window,
        bg="#f8fafc"
    )

    button_frame.pack(
        fill="x",
        padx=25,
        pady=20
    )

    # =====================================================
    # CANCEL
    # =====================================================

    def cancel():

        window.grab_release()

        window.destroy()

    cancel_button = tk.Button(
        button_frame,
        text="Cancel",
        command=cancel,
        bg="#e5e7eb",
        fg="#111827",
        activebackground="#d1d5db",
        font=(
            "Tahoma",
            11,
            "bold"
        ),
        relief="flat",
        bd=0,
        padx=25,
        pady=10,
        cursor="hand2"
    )

    cancel_button.pack(
        side="right",
        padx=(8, 0)
    )

    # =====================================================
    # SAVE
    # =====================================================

    def save():

        apply_camera_settings(

            int(
                temp_index.get()
            ),

            bool(
                temp_flip.get()
            ),

            bool(
                temp_border_enabled.get()
            ),

            int(
                temp_border.get()
            )
        )

        window.grab_release()

        window.destroy()

    save_button = tk.Button(
        button_frame,
        text="Save",
        command=save,
        bg="#2563eb",
        fg="white",
        activebackground="#1d4ed8",
        activeforeground="white",
        font=(
            "Tahoma",
            11,
            "bold"
        ),
        relief="flat",
        bd=0,
        padx=30,
        pady=10,
        cursor="hand2"
    )

    save_button.pack(
        side="right"
    )


# =========================================================
# MAIN WINDOW
# =========================================================

root = tk.Tk()

root.title(
    "Auto"
)

root.attributes(
    "-fullscreen",
    True
)

root.configure(
    bg="#eef1f5"
)


# =========================================================
# MENU BAR
# =========================================================

menubar = tk.Menu(
    root
)


# =========================================================
# HSV MENU
# =========================================================

hsv_menu = tk.Menu(
    menubar,
    tearoff=0
)

hsv_menu.add_command(
    label="ปรับจุดมาร์กหรือวงกลม",
    command=open_circle
)

hsv_menu.add_command(
    label="ปรับสีอัญมณี",
    command=open_gem
)

menubar.add_cascade(
    label="ปรับสี HSV",
    menu=hsv_menu
)


# =========================================================
# CAMERA MENU
# =========================================================

menubar.add_command(
    label="ปรับกล้อง",
    command=open_camera_settings
)


# =========================================================
# APPLY MENU
# =========================================================

root.config(
    menu=menubar
)


# =========================================================
# MAIN CONTENT
# =========================================================

main_frame = tk.Frame(
    root,
    bg="#eef1f5"
)

main_frame.pack(
    fill="both",
    expand=True,
    padx=30,
    pady=30
)


# =========================================================
# LEFT VIDEO AREA
# =========================================================

left_frame = tk.Frame(
    main_frame,
    bg="#111827",
    highlightbackground="#374151",
    highlightthickness=1
)

left_frame.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 15)
)


# =========================================================
# VIDEO HEADER
# =========================================================

video_header = tk.Frame(
    left_frame,
    bg="#1f2937",
    height=45
)

video_header.pack(
    fill="x"
)

video_header.pack_propagate(
    False
)


tk.Label(
    video_header,
    text="CAMERA",
    font=(
        "Tahoma",
        13,
        "bold"
    ),
    bg="#1f2937",
    fg="white"
).pack(
    side="left",
    padx=15
)


camera_status_label = tk.Label(
    video_header,
    text="Camera 0",
    font=(
        "Tahoma",
        10
    ),
    bg="#1f2937",
    fg="#9ca3af"
)

camera_status_label.pack(
    side="right",
    padx=15
)


# =========================================================
# VIDEO LABEL
# =========================================================

video_label = tk.Label(
    left_frame,
    bg="#111827",
    text="Camera Loading...",
    fg="white",
    font=(
        "Tahoma",
        15
    ),
    anchor="center"
)

video_label.pack(
    fill="both",
    expand=True,
    padx=8,
    pady=8
)


# =========================================================
# RIGHT COMMAND AREA
# =========================================================

right_frame = tk.Frame(
    main_frame,
    bg="#ffffff",
    width=360,
    highlightbackground="#d7dee8",
    highlightthickness=1
)

right_frame.pack(
    side="right",
    fill="y"
)

right_frame.pack_propagate(
    False
)


# =========================================================
# RIGHT TITLE
# =========================================================

tk.Label(
    right_frame,
    text="COMMAND",
    font=(
        "Tahoma",
        18,
        "bold"
    ),
    bg="#ffffff",
    fg="#111827"
).pack(
    pady=(30, 10)
)


tk.Label(
    right_frame,
    text="พื้นที่สำหรับคำสั่งในอนาคต",
    font=(
        "Tahoma",
        11
    ),
    bg="#ffffff",
    fg="#9ca3af"
).pack()


# =========================================================
# ROI PROCESSING
# =========================================================

def process_camera_frame(frame):

    # -----------------------------------------------------
    # Flip
    # -----------------------------------------------------

    if camera_flip:

        frame = cv2.flip(
            frame,
            1
        )

    # -----------------------------------------------------
    # Yellow border
    # -----------------------------------------------------

    if camera_border_enabled:

        h, w = frame.shape[:2]

        border = int(
            camera_border
        )

        # ---------------------------------------------
        # ป้องกัน border เกินขนาดภาพ
        # ---------------------------------------------

        border = min(
            border,
            w // 2 - 1,
            h // 2 - 1
        )

        # ---------------------------------------------
        # วาดกรอบสีเหลือง
        # ---------------------------------------------

        cv2.rectangle(
            frame,
            (
                border,
                border
            ),
            (
                w - border - 1,
                h - border - 1
            ),
            (0, 255, 255),
            3
        )

        # ---------------------------------------------
        # ทำ mask เฉพาะพื้นที่ด้านใน
        # ---------------------------------------------

        mask = np.zeros(
            (h, w),
            dtype=np.uint8
        )

        cv2.rectangle(
            mask,
            (
                border,
                border
            ),
            (
                w - border - 1,
                h - border - 1
            ),
            255,
            -1
        )

        # ---------------------------------------------
        # ตัดพื้นที่นอกกรอบ
        # ---------------------------------------------

        detect_frame = cv2.bitwise_and(
            frame,
            frame,
            mask=mask
        )

        return frame, detect_frame

    else:

        return frame, frame.copy()


# =========================================================
# DISPLAY VIDEO
# =========================================================

def display_video(frame):

    if frame is None:

        return

    # -----------------------------------------------------
    # Get label size
    # -----------------------------------------------------

    label_width = video_label.winfo_width()

    label_height = video_label.winfo_height()

    if label_width <= 20:

        label_width = 800

    if label_height <= 20:

        label_height = 500

    # -----------------------------------------------------
    # BGR -> RGB
    # -----------------------------------------------------

    frame_rgb = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    image = Image.fromarray(
        frame_rgb
    )

    # -----------------------------------------------------
    # Maintain aspect ratio
    # -----------------------------------------------------

    image.thumbnail(
        (
            label_width - 10,
            label_height - 10
        ),
        Image.Resampling.LANCZOS
    )

    photo = ImageTk.PhotoImage(
        image
    )

    video_label.configure(
        image=photo,
        text=""
    )

    video_label.image = photo


# =========================================================
# CAMERA LOOP
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

        camera_status_label.configure(
            text=(
                f"Camera {camera_index} "
                f"ไม่พบภาพ"
            ),
            fg="#ef4444"
        )

        root.after(
            100,
            update_camera
        )

        return

    # -----------------------------------------------------
    # Process
    # -----------------------------------------------------

    display_frame, detect_frame = process_camera_frame(
        frame
    )

    # -----------------------------------------------------
    # ตอนนี้แสดง display_frame
    #
    # detect_frame จะส่งต่อให้ระบบ
    # ตรวจจับวงกลม / อัญมณีในภายหลัง
    # -----------------------------------------------------

    display_video(
        display_frame
    )

    camera_status_label.configure(
        text=(
            f"Camera {camera_index}"
        ),
        fg="#9ca3af"
    )

    root.after(
        30,
        update_camera
    )


# =========================================================
# ESC
# =========================================================

def exit_fullscreen(event=None):

    root.attributes(
        "-fullscreen",
        False
    )


root.bind(
    "<Escape>",
    exit_fullscreen
)


# =========================================================
# CLOSE
# =========================================================

def close_program():

    global cap

    if cap is not None:

        cap.release()

        cap = None

    root.destroy()


root.protocol(
    "WM_DELETE_WINDOW",
    close_program
)


# =========================================================
# START CAMERA
# =========================================================

open_camera()

root.after(
    100,
    update_camera
)


# =========================================================
# RUN
# =========================================================

root.mainloop()