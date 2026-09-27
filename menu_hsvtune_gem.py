import cv2
import numpy as np
import math
import tkinter as tk
from PIL import Image, ImageTk

from hsv_config import (
    load_colors,
    load_gem_colors,
    save_gem_colors
)


# =========================================================
# CONFIG
# =========================================================

colors = load_gem_colors()

circle_colors = load_colors()


color_names = [
    "GREEN",
    "ORANGE",
    "CYAN",
    "BLUE",
    "PURPLE",
    "RED"
]


# =========================================================
# BUTTON COLORS
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
# DRAW COLORS
# =========================================================

draw_colors = {
    "GREEN": (0, 255, 0),
    "ORANGE": (0, 165, 255),
    "CYAN": (255, 255, 0),
    "BLUE": (255, 0, 0),
    "PURPLE": (255, 0, 255),
    "RED": (0, 0, 255)
}


# =========================================================
# UI COLORS
# =========================================================

BG = "#F3F6FA"
CARD = "#FFFFFF"
VIDEO_BG = "#111827"
HEADER_DARK = "#1F2937"
TEXT = "#1F2937"
MUTED = "#6B7280"
BORDER = "#D7DEE8"
BLUE = "#2563EB"
BLUE_DARK = "#1D4ED8"
GREEN = "#22C55E"
RED = "#EF4444"

FONT = "Arial"


# =========================================================
# VARIABLES
# =========================================================

selected_color = "GREEN"

confirmed_colors = set()

cap = None

camera_index = 0

slider_vars = {}

slider_value_labels = {}

image_labels = {}

color_buttons = {}

status_label = None

count_label = None


# =========================================================
# ROOT
# =========================================================

root = tk.Tk()

root.title(
    "Gem Color Detection"
)

root.state("zoomed")

root.configure(
    bg=BG
)


# =========================================================
# HOVER
# =========================================================

def add_hover(
    button,
    normal,
    hover
):

    def on_enter(event):

        button.configure(
            bg=hover
        )

    def on_leave(event):

        button.configure(
            bg=normal
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
# LOAD COLOR
# =========================================================

def load_color_to_slider():

    data = colors.get(
        selected_color
    )

    if not data:
        return

    lower = data.get(
        "lower",
        [0, 0, 0]
    )

    upper = data.get(
        "upper",
        [179, 255, 255]
    )

    slider_vars["h_min"].set(
        lower[0]
    )

    slider_vars["s_min"].set(
        lower[1]
    )

    slider_vars["v_min"].set(
        lower[2]
    )

    slider_vars["h_max"].set(
        upper[0]
    )

    slider_vars["s_max"].set(
        upper[1]
    )

    slider_vars["v_max"].set(
        upper[2]
    )

    update_slider_labels()


# =========================================================
# UPDATE SLIDER LABEL
# =========================================================

def update_slider_labels():

    for name, variable in slider_vars.items():

        if name in slider_value_labels:

            slider_value_labels[
                name
            ].configure(
                text=str(
                    variable.get()
                )
            )


# =========================================================
# SELECT COLOR
# =========================================================

def select_color(color):

    global selected_color

    selected_color = color

    for name, button in color_buttons.items():

        if name == selected_color:

            button.configure(
                relief="sunken",
                bd=4,
                highlightbackground="#111827",
                highlightthickness=2
            )

        else:

            button.configure(
                relief="flat",
                bd=0,
                highlightthickness=0
            )

    load_color_to_slider()


# =========================================================
# CLEAR
# =========================================================

def clear_current_color():

    global colors

    colors = load_gem_colors()

    load_color_to_slider()

    status_label.configure(
        text=(
            f"โหลดค่า {selected_color} "
            f"จาก gem_config.json แล้ว"
        ),
        fg=BLUE
    )


# =========================================================
# SAVE GEM HSV
# =========================================================

def save_hsv():

    global colors

    h_min = slider_vars[
        "h_min"
    ].get()

    h_max = slider_vars[
        "h_max"
    ].get()

    s_min = slider_vars[
        "s_min"
    ].get()

    s_max = slider_vars[
        "s_max"
    ].get()

    v_min = slider_vars[
        "v_min"
    ].get()

    v_max = slider_vars[
        "v_max"
    ].get()

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

    success = save_gem_colors(
        colors
    )

    if success:

        status_label.configure(
            text=(
                f"บันทึก {selected_color} "
                f"ลง gem_config.json สำเร็จ"
            ),
            fg=GREEN
        )

    else:

        status_label.configure(
            text=(
                "บันทึก gem_config.json ไม่สำเร็จ"
            ),
            fg=RED
        )


# =========================================================
# CONFIRM
# =========================================================

def confirm_color():

    save_hsv()

    confirmed_colors.add(
        selected_color
    )

    update_status()


# =========================================================
# STATUS
# =========================================================

def update_status():

    confirmed = len(
        confirmed_colors
    )

    status_label.configure(
        text=(
            f"ยืนยันไปแล้ว "
            f"{confirmed} / 6 สี"
        ),
        fg=(
            GREEN
            if confirmed == 6
            else TEXT
        )
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


# =========================================================
# BACK TO AUTO
# =========================================================

def back_to_auto():

    close_program()


# =========================================================
# CAMERA
# =========================================================

def change_camera(value):

    global cap
    global camera_index

    try:

        camera_index = int(value)

    except:

        camera_index = 0

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
# CV -> TK
# แก้ปัญหาภาพขยายจนล้นกรอบ
# =========================================================

def cv_to_tk(frame, label):

    if frame is None:
        return None

    # BGR -> RGB
    frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB
    )

    image = Image.fromarray(
        frame
    )

    # -----------------------------------------------------
    # ขนาดพื้นที่จริงของ Label
    # -----------------------------------------------------

    width = label.winfo_width()

    height = label.winfo_height()

    # Tkinter อาจยังไม่คำนวณขนาด
    if width <= 20:
        width = 500

    if height <= 20:
        height = 300

    # -----------------------------------------------------
    # ขนาดภาพต้นฉบับ
    # -----------------------------------------------------

    image_width, image_height = image.size

    # -----------------------------------------------------
    # คำนวณ scale
    # ใช้ค่าที่เล็กกว่าเพื่อให้ภาพไม่ล้น
    # -----------------------------------------------------

    scale_w = width / image_width

    scale_h = height / image_height

    scale = min(
        scale_w,
        scale_h
    )

    new_width = max(
        1,
        int(image_width * scale)
    )

    new_height = max(
        1,
        int(image_height * scale)
    )

    # -----------------------------------------------------
    # Resize แบบรักษา Aspect Ratio
    # -----------------------------------------------------

    image = image.resize(
        (
            new_width,
            new_height
        ),
        Image.Resampling.LANCZOS
    )

    return ImageTk.PhotoImage(
        image
    )


# =========================================================
# GET GEM HSV
# =========================================================

def get_gem_hsv(color_name):

    data = colors.get(
        color_name
    )

    if not data:
        return None, None

    lower = np.array(
        data["lower"],
        dtype=np.uint8
    )

    upper = np.array(
        data["upper"],
        dtype=np.uint8
    )

    return lower, upper


# =========================================================
# GET CIRCLE HSV
# =========================================================

def get_circle_hsv(color_name):

    data = circle_colors.get(
        color_name
    )

    if not data:
        return None, None

    lower = np.array(
        data["lower"],
        dtype=np.uint8
    )

    upper = np.array(
        data["upper"],
        dtype=np.uint8
    )

    return lower, upper


# =========================================================
# FIND BIG CIRCLES
# =========================================================

def find_big_circles(hsv):

    big_circles = []

    for color_name in color_names:

        lower, upper = get_circle_hsv(
            color_name
        )

        if lower is None:
            continue

        mask = cv2.inRange(
            hsv,
            lower,
            upper
        )

        kernel = np.ones(
            (5, 5),
            np.uint8
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel
        )

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:

            area = cv2.contourArea(
                contour
            )

            if area < 3000:
                continue

            perimeter = cv2.arcLength(
                contour,
                True
            )

            if perimeter == 0:
                continue

            circularity = (
                4
                * math.pi
                * area
                /
                (
                    perimeter
                    * perimeter
                )
            )

            if circularity < 0.75:
                continue

            x, y, w, h = cv2.boundingRect(
                contour
            )

            ratio = w / h

            if ratio < 0.8 or ratio > 1.2:
                continue

            center_x = (
                x + w // 2
            )

            center_y = (
                y + h // 2
            )

            radius = int(
                (w + h) / 4
            )

            big_circles.append({

                "color": color_name,

                "center": (
                    center_x,
                    center_y
                ),

                "radius": radius,

                "box": (
                    x,
                    y,
                    w,
                    h
                )
            })

    return big_circles


# =========================================================
# REMOVE BIG CIRCLES
# =========================================================

def remove_big_circles(
    mask,
    big_circles
):

    result = mask.copy()

    for circle in big_circles:

        cx, cy = circle[
            "center"
        ]

        radius = circle[
            "radius"
        ]

        cv2.circle(
            result,
            (
                cx,
                cy
            ),
            radius + 5,
            0,
            -1
        )

    return result


# =========================================================
# DRAW BIG CIRCLES
# =========================================================

def draw_big_circles(
    image,
    big_circles
):

    result = image.copy()

    for circle in big_circles:

        color_name = circle[
            "color"
        ]

        cx, cy = circle[
            "center"
        ]

        radius = circle[
            "radius"
        ]

        draw_color = draw_colors[
            color_name
        ]

        cv2.circle(
            result,
            (
                cx,
                cy
            ),
            radius,
            draw_color,
            3
        )

        cv2.circle(
            result,
            (
                cx,
                cy
            ),
            5,
            draw_color,
            -1
        )

        cv2.putText(
            result,
            f"CIRCLE {color_name}",
            (
                cx - radius,
                max(
                    20,
                    cy - radius - 10
                )
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            draw_color,
            2,
            cv2.LINE_AA
        )

    cv2.putText(
        result,
        f"Big Circles: {len(big_circles)}",
        (
            15,
            30
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    return result


# =========================================================
# DETECT GEMS
# =========================================================

def detect_gems(
    hsv,
    original,
    big_circles
):

    detect_image = original.copy()

    separated_image = np.zeros_like(
        original
    )

    all_gems = []

    for color_name in color_names:

        # -------------------------------------------------
        # HSV อัญมณี
        # -------------------------------------------------

        lower, upper = get_gem_hsv(
            color_name
        )

        if lower is None:
            continue

        # -------------------------------------------------
        # MASK
        # -------------------------------------------------

        mask = cv2.inRange(
            hsv,
            lower,
            upper
        )

        # -------------------------------------------------
        # MORPH OPEN
        # -------------------------------------------------

        kernel = np.ones(
            (3, 3),
            np.uint8
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel
        )

        # -------------------------------------------------
        # MORPH CLOSE
        # -------------------------------------------------

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_CLOSE,
            kernel
        )

        # -------------------------------------------------
        # ลบพื้นที่วงกลมใหญ่
        # -------------------------------------------------

        mask = remove_big_circles(
            mask,
            big_circles
        )

        # -------------------------------------------------
        # SEPARATED
        # -------------------------------------------------

        draw_color = draw_colors[
            color_name
        ]

        separated_image[
            mask > 0
        ] = draw_color

        # -------------------------------------------------
        # CONTOURS
        # -------------------------------------------------

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        gem_number = 0

        for contour in contours:

            area = cv2.contourArea(
                contour
            )

            if area < 20:
                continue

            if area > 4500:
                continue

            x, y, w, h = cv2.boundingRect(
                contour
            )

            if w < 5 or h < 5:
                continue

            if w > 100 or h > 100:
                continue

            ratio = w / h

            if ratio < 0.4 or ratio > 2.5:
                continue

            center_x = (
                x + w // 2
            )

            center_y = (
                y + h // 2
            )

            gem_number += 1

            all_gems.append({

                "color": color_name,

                "center": (
                    center_x,
                    center_y
                ),

                "box": (
                    x,
                    y,
                    w,
                    h
                ),

                "area": area
            })

            # -------------------------------------------------
            # กรอบ
            # -------------------------------------------------

            cv2.rectangle(
                detect_image,
                (
                    x,
                    y
                ),
                (
                    x + w,
                    y + h
                ),
                draw_color,
                2
            )

            # -------------------------------------------------
            # CENTER
            # -------------------------------------------------

            cv2.circle(
                detect_image,
                (
                    center_x,
                    center_y
                ),
                5,
                (255, 255, 255),
                -1
            )

            cv2.circle(
                detect_image,
                (
                    center_x,
                    center_y
                ),
                2,
                draw_color,
                -1
            )

            # -------------------------------------------------
            # NAME
            # -------------------------------------------------

            cv2.putText(
                detect_image,
                f"{color_name} #{gem_number}",
                (
                    x,
                    max(
                        18,
                        y - 7
                    )
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                draw_color,
                2,
                cv2.LINE_AA
            )

            # -------------------------------------------------
            # COORDINATE
            # -------------------------------------------------

            cv2.putText(
                detect_image,
                f"({center_x},{center_y})",
                (
                    x,
                    y + h + 18
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

    # =====================================================
    # TOTAL
    # =====================================================

    cv2.putText(
        detect_image,
        f"Gems: {len(all_gems)}",
        (
            15,
            30
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    # =====================================================
    # COUNT EACH COLOR
    # =====================================================

    count_by_color = {
        color: 0
        for color in color_names
    }

    for gem in all_gems:

        count_by_color[
            gem["color"]
        ] += 1

    y_text = 60

    for color_name in color_names:

        count = count_by_color[
            color_name
        ]

        draw_color = draw_colors[
            color_name
        ]

        cv2.putText(
            detect_image,
            f"{color_name}: {count}",
            (
                15,
                y_text
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            draw_color,
            2,
            cv2.LINE_AA
        )

        y_text += 23

    return (
        detect_image,
        separated_image,
        all_gems
    )


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

    if not ret or frame is None:

        root.after(
            30,
            update_camera
        )

        return

    # -----------------------------------------------------
    # MIRROR
    # -----------------------------------------------------

    frame = cv2.flip(
        frame,
        1
    )

    original = frame.copy()

    # -----------------------------------------------------
    # HSV
    # -----------------------------------------------------

    hsv = cv2.cvtColor(
        original,
        cv2.COLOR_BGR2HSV
    )

    # -----------------------------------------------------
    # BIG CIRCLE
    # -----------------------------------------------------

    big_circles = find_big_circles(
        hsv
    )

    # -----------------------------------------------------
    # MARK
    # -----------------------------------------------------

    mark = draw_big_circles(
        original,
        big_circles
    )

    # -----------------------------------------------------
    # GEMS
    # -----------------------------------------------------

    (
        detect_image,
        separated_image,
        gems
    ) = detect_gems(
        hsv,
        original,
        big_circles
    )

    # -----------------------------------------------------
    # DISPLAY
    # -----------------------------------------------------

    images = {

        "original":
        original,

        "mark":
        mark,

        "separated":
        separated_image,

        "detect":
        detect_image
    }

    for name, image in images.items():

        label = image_labels.get(
            name
        )

        if label is None:
            continue

        tk_image = cv_to_tk(
            image,
            label
        )

        if tk_image is not None:

            label.configure(
                image=tk_image
            )

            label.image = tk_image

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    if count_label is not None:

        count_label.configure(
            text=(
                f"วงกลมใหญ่  "
                f"{len(big_circles)}"
                f"   |   "
                f"อัญมณี  "
                f"{len(gems)}"
            )
        )

    root.after(
        30,
        update_camera
    )


# =========================================================
# TOP COLOR BAR
# =========================================================

top_card = tk.Frame(
    root,
    bg=CARD,
    highlightbackground=BORDER,
    highlightthickness=1
)

top_card.pack(
    fill="x",
    padx=18,
    pady=(15, 8)
)


tk.Label(
    top_card,
    text="GEM COLOR",
    bg=CARD,
    fg=TEXT,
    font=(
        FONT,
        13,
        "bold"
    )
).pack(
    side="left",
    padx=(18, 10)
)


for color in color_names:

    button = tk.Button(

        top_card,

        text=color,

        bg=button_colors[
            color
        ],

        fg="white",

        activebackground=button_colors[
            color
        ],

        activeforeground="white",

        font=(
            FONT,
            12,
            "bold"
        ),

        relief="flat",

        bd=0,

        padx=18,

        pady=9,

        cursor="hand2",

        command=lambda c=color:
        select_color(c)
    )

    button.pack(
        side="left",
        padx=5,
        pady=10
    )

    color_buttons[
        color
    ] = button


# =========================================================
# CAMERA BAR
# =========================================================

camera_card = tk.Frame(
    root,
    bg=CARD,
    highlightbackground=BORDER,
    highlightthickness=1
)

camera_card.pack(
    fill="x",
    padx=18,
    pady=8
)


tk.Label(
    camera_card,
    text="Camera",
    bg=CARD,
    fg=TEXT,
    font=(
        FONT,
        13,
        "bold"
    )
).pack(
    side="left",
    padx=18
)


tk.Label(
    camera_card,
    text="Index",
    bg=CARD,
    fg=MUTED,
    font=(
        FONT,
        11
    )
).pack(
    side="left"
)


camera_var = tk.StringVar(
    value="0"
)


camera_menu = tk.OptionMenu(
    camera_card,
    camera_var,
    "0",
    "1",
    "2",
    "3",
    "4",
    command=change_camera
)

camera_menu.configure(
    bg="#EEF2F7",
    fg=TEXT,
    activebackground="#DCE6F5",
    activeforeground=TEXT,
    relief="flat",
    bd=0,
    font=(
        FONT,
        11,
        "bold"
    ),
    padx=10,
    pady=4
)

camera_menu["menu"].configure(
    font=(
        FONT,
        11
    )
)

camera_menu.pack(
    side="left",
    padx=8
)


# =========================================================
# BACK
# =========================================================

back_button = tk.Button(

    camera_card,

    text="← กลับหน้า Auto",

    bg="#EEF2F7",

    fg=TEXT,

    activebackground="#E2E8F0",

    activeforeground=TEXT,

    font=(
        FONT,
        11,
        "bold"
    ),

    relief="flat",

    bd=0,

    padx=18,

    pady=8,

    cursor="hand2",

    command=back_to_auto
)

back_button.pack(
    side="right",
    padx=15,
    pady=8
)

add_hover(
    back_button,
    "#EEF2F7",
    "#E2E8F0"
)


# =========================================================
# HSV CARD
# =========================================================

hsv_card = tk.Frame(
    root,
    bg=CARD,
    highlightbackground=BORDER,
    highlightthickness=1
)

hsv_card.pack(
    fill="x",
    padx=18,
    pady=8
)


# =========================================================
# SLIDER
# =========================================================

def create_slider_column(
    parent,
    name,
    minimum,
    maximum
):

    column = tk.Frame(
        parent,
        bg=CARD
    )

    column.pack(
        side="left",
        fill="x",
        expand=True,
        padx=10,
        pady=8
    )

    tk.Label(
        column,
        text=name,
        bg=CARD,
        fg=TEXT,
        font=(
            FONT,
            12,
            "bold"
        )
    ).pack(
        anchor="w"
    )

    # =====================================================
    # MIN
    # =====================================================

    row_min = tk.Frame(
        column,
        bg=CARD
    )

    row_min.pack(
        fill="x"
    )

    tk.Label(
        row_min,
        text="MIN",
        bg=CARD,
        fg=MUTED,
        width=4,
        font=(
            FONT,
            9,
            "bold"
        )
    ).pack(
        side="left"
    )

    var_min = tk.IntVar(
        value=minimum
    )

    key_min = (
        name.lower()
        + "_min"
    )

    slider_vars[
        key_min
    ] = var_min

    scale_min = tk.Scale(

        row_min,

        from_=minimum,

        to=maximum,

        orient="horizontal",

        variable=var_min,

        showvalue=False,

        bg=CARD,

        fg=TEXT,

        troughcolor="#E2E8F0",

        activebackground=BLUE,

        highlightthickness=0,

        bd=0,

        relief="flat",

        sliderlength=20,

        command=lambda x:
        update_slider_labels()
    )

    scale_min.pack(
        side="left",
        fill="x",
        expand=True
    )

    value_min = tk.Label(
        row_min,
        text=str(minimum),
        bg="#EEF2F7",
        fg=TEXT,
        width=4,
        font=(
            FONT,
            10,
            "bold"
        )
    )

    value_min.pack(
        side="right",
        padx=3
    )

    slider_value_labels[
        key_min
    ] = value_min

    # =====================================================
    # MAX
    # =====================================================

    row_max = tk.Frame(
        column,
        bg=CARD
    )

    row_max.pack(
        fill="x"
    )

    tk.Label(
        row_max,
        text="MAX",
        bg=CARD,
        fg=MUTED,
        width=4,
        font=(
            FONT,
            9,
            "bold"
        )
    ).pack(
        side="left"
    )

    var_max = tk.IntVar(
        value=maximum
    )

    key_max = (
        name.lower()
        + "_max"
    )

    slider_vars[
        key_max
    ] = var_max

    scale_max = tk.Scale(

        row_max,

        from_=minimum,

        to=maximum,

        orient="horizontal",

        variable=var_max,

        showvalue=False,

        bg=CARD,

        fg=TEXT,

        troughcolor="#E2E8F0",

        activebackground=BLUE,

        highlightthickness=0,

        bd=0,

        relief="flat",

        sliderlength=20,

        command=lambda x:
        update_slider_labels()
    )

    scale_max.pack(
        side="left",
        fill="x",
        expand=True
    )

    value_max = tk.Label(
        row_max,
        text=str(maximum),
        bg="#EEF2F7",
        fg=TEXT,
        width=4,
        font=(
            FONT,
            10,
            "bold"
        )
    )

    value_max.pack(
        side="right",
        padx=3
    )

    slider_value_labels[
        key_max
    ] = value_max


create_slider_column(
    hsv_card,
    "H",
    0,
    179
)

create_slider_column(
    hsv_card,
    "S",
    0,
    255
)

create_slider_column(
    hsv_card,
    "V",
    0,
    255
)


# =========================================================
# MAIN
# =========================================================

main_frame = tk.Frame(
    root,
    bg=BG
)

main_frame.pack(
    fill="both",
    expand=True,
    padx=18,
    pady=(8, 15)
)


# =========================================================
# VIDEO AREA
# =========================================================

video_frame = tk.Frame(
    main_frame,
    bg=BG
)

video_frame.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 8)
)


# =========================================================
# VIDEO CARD
# แก้เรื่องภาพล้น
# =========================================================

def create_video_card(
    parent,
    title,
    key
):

    card = tk.Frame(

        parent,

        bg=VIDEO_BG,

        highlightbackground="#374151",

        highlightthickness=1
    )

    # สำคัญ
    # ไม่ให้ Frame ขยายตาม child
    card.pack_propagate(False)

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    header = tk.Frame(
        card,
        bg=HEADER_DARK,
        height=38
    )

    header.pack(
        fill="x"
    )

    header.pack_propagate(
        False
    )

    tk.Label(
        header,
        text=title,
        bg=HEADER_DARK,
        fg="white",
        font=(
            FONT,
            11,
            "bold"
        )
    ).pack(
        side="left",
        padx=12,
        pady=8
    )

    # -----------------------------------------------------
    # IMAGE LABEL
    # -----------------------------------------------------

    label = tk.Label(

        card,

        bg=VIDEO_BG,

        fg="white",

        text="Camera Loading...",

        font=(
            FONT,
            12
        ),

        anchor="center",

        justify="center"
    )

    label.pack(
        fill="both",
        expand=True,
        padx=4,
        pady=4
    )

    image_labels[
        key
    ] = label

    return card


# =========================================================
# GRID
# =========================================================

row1 = tk.Frame(
    video_frame,
    bg=BG
)

row1.pack(
    fill="both",
    expand=True
)


row2 = tk.Frame(
    video_frame,
    bg=BG
)

row2.pack(
    fill="both",
    expand=True
)


# =========================================================
# ORIGINAL
# =========================================================

card_original = create_video_card(
    row1,
    "ORIGINAL",
    "original"
)

card_original.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 5),
    pady=(0, 5)
)


# =========================================================
# MARK
# =========================================================

card_mark = create_video_card(
    row1,
    "MARK — BIG CIRCLES",
    "mark"
)

card_mark.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(5, 0),
    pady=(0, 5)
)


# =========================================================
# SEPARATED
# =========================================================

card_separated = create_video_card(
    row2,
    "SEPARATED — GEMS",
    "separated"
)

card_separated.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(0, 5),
    pady=(5, 0)
)


# =========================================================
# DETECT
# =========================================================

card_detect = create_video_card(
    row2,
    "DETECT — GEM RESULT",
    "detect"
)

card_detect.pack(
    side="left",
    fill="both",
    expand=True,
    padx=(5, 0),
    pady=(5, 0)
)


# =========================================================
# RIGHT PANEL
# =========================================================

right_panel = tk.Frame(
    main_frame,
    bg=CARD,
    width=310,
    highlightbackground=BORDER,
    highlightthickness=1
)

right_panel.pack(
    side="right",
    fill="y"
)

right_panel.pack_propagate(
    False
)


# =========================================================
# STATUS
# =========================================================

tk.Label(
    right_panel,
    text="Gem Detection",
    bg=CARD,
    fg=TEXT,
    font=(
        FONT,
        16,
        "bold"
    )
).pack(
    anchor="w",
    padx=18,
    pady=(18, 3)
)


status_label = tk.Label(
    right_panel,
    text="เหลือ 6 / 6 สี",
    bg=CARD,
    fg=TEXT,
    font=(
        FONT,
        11
    ),
    anchor="w"
)

status_label.pack(
    fill="x",
    padx=18
)


count_label = tk.Label(
    right_panel,
    text="วงกลมใหญ่ 0 | อัญมณี 0",
    bg="#EEF2F7",
    fg=TEXT,
    font=(
        FONT,
        10,
        "bold"
    ),
    padx=10,
    pady=10
)

count_label.pack(
    fill="x",
    padx=18,
    pady=15
)


# =========================================================
# ACTION BUTTONS
# =========================================================

action_frame = tk.Frame(
    right_panel,
    bg=CARD
)

action_frame.pack(
    fill="x",
    padx=18
)


# =========================================================
# CLEAR
# =========================================================

clear_button = tk.Button(

    action_frame,

    text="Clear",

    bg="#EEF2F7",

    fg=TEXT,

    activebackground="#E2E8F0",

    activeforeground=TEXT,

    font=(
        FONT,
        11,
        "bold"
    ),

    relief="flat",

    bd=0,

    pady=10,

    cursor="hand2",

    command=clear_current_color
)

clear_button.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(0, 5)
)


# =========================================================
# SAVE
# =========================================================

save_button = tk.Button(

    action_frame,

    text="Save",

    bg=BLUE,

    fg="white",

    activebackground=BLUE_DARK,

    activeforeground="white",

    font=(
        FONT,
        11,
        "bold"
    ),

    relief="flat",

    bd=0,

    pady=10,

    cursor="hand2",

    command=save_hsv
)

save_button.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(5, 0)
)


add_hover(
    clear_button,
    "#EEF2F7",
    "#E2E8F0"
)

add_hover(
    save_button,
    BLUE,
    BLUE_DARK
)


# =========================================================
# CONFIRM
# =========================================================

confirm_button = tk.Button(

    right_panel,

    text="✓  Confirm Color",

    bg=GREEN,

    fg="white",

    activebackground="#16A34A",

    activeforeground="white",

    font=(
        FONT,
        13,
        "bold"
    ),

    relief="flat",

    bd=0,

    pady=13,

    cursor="hand2",

    command=confirm_color
)

confirm_button.pack(
    fill="x",
    padx=18,
    pady=15
)


add_hover(
    confirm_button,
    GREEN,
    "#16A34A"
)


# =========================================================
# INFORMATION
# =========================================================

info_frame = tk.Frame(

    right_panel,

    bg="#F8FAFC",

    highlightbackground=BORDER,

    highlightthickness=1
)

info_frame.pack(
    fill="x",
    padx=18,
    pady=5
)


tk.Label(
    info_frame,
    text="ระบบตรวจจับ",
    bg="#F8FAFC",
    fg=TEXT,
    font=(
        FONT,
        11,
        "bold"
    )
).pack(
    anchor="w",
    padx=12,
    pady=(12, 3)
)


tk.Label(
    info_frame,
    text=(
        "• วงกลมใหญ่ใช้ hsv_config.json\n"
        "• อัญมณีใช้ gem_config.json\n"
        "• ไม่ตรวจภายในวงกลมใหญ่\n"
        "• แยกอัญมณีเป็นก้อน\n"
        "• แสดงชื่อสีและพิกัด"
    ),
    bg="#F8FAFC",
    fg=MUTED,
    justify="left",
    font=(
        FONT,
        10
    )
).pack(
    anchor="w",
    padx=12,
    pady=(0, 12)
)


# =========================================================
# KEYBOARD
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
# INITIAL
# =========================================================

select_color(
    selected_color
)

change_camera(
    "0"
)


# =========================================================
# START CAMERA
# =========================================================

root.after(
    100,
    update_camera
)


# =========================================================
# CLOSE
# =========================================================

root.protocol(
    "WM_DELETE_WINDOW",
    close_program
)


# =========================================================
# RUN
# =========================================================

root.mainloop()