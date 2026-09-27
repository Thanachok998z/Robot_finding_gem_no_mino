import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

import math
import heapq


# ============================================================
# SETTINGS
# ============================================================

IMAGE_PATH = "img/map.png"

ROBOT_WIDTH = 35
ROBOT_LENGTH = 55

ROBOT_MARGIN = 8

CIRCLE_RADIUS = 40

PATH_GRID = 5

PATH_COLOR = "#ff00ff"


# ============================================================
# DIRECTIONS
# ============================================================

DIRECTIONS = [
    "UP",
    "RIGHT",
    "DOWN",
    "LEFT"
]


DIRECTION_ARROWS = {
    "UP": "↑",
    "RIGHT": "→",
    "DOWN": "↓",
    "LEFT": "←"
}


# dx, dy
DIRECTION_VECTOR = {
    "UP": (0, -1),
    "RIGHT": (1, 0),
    "DOWN": (0, 1),
    "LEFT": (-1, 0)
}


# ============================================================
# COLORS
# ============================================================

COLORS = {
    "GREEN": "#00cc44",
    "BLUE": "#2277ff",
    "RED": "#ff3333",
    "PURPLE": "#aa44dd",
    "CYAN": "#00bbbb",
    "ORANGE": "#ff8800"
}


# ============================================================
# DEFAULT CIRCLES
# ============================================================
# ตำแหน่งวงกลมจากแผนที่เดิม
# สามารถลากเปลี่ยนตำแหน่งได้ในโปรแกรม
#
# ถ้าตำแหน่งจริงใน map.jpg แตกต่าง
# สามารถลากแก้ได้เลย
# ============================================================

circles = [

    {
        "color": "GREEN",
        "x": 69,
        "y": 197
    },

    {
        "color": "BLUE",
        "x": 294,
        "y": 111
    },

    {
        "color": "RED",
        "x": 534,
        "y": 88
    },

    {
        "color": "PURPLE",
        "x": 78,
        "y": 393
    },

    {
        "color": "CYAN",
        "x": 266,
        "y": 502
    },

    {
        "color": "ORANGE",
        "x": 517,
        "y": 488
    }

]


# ============================================================
# LOAD IMAGE
# ============================================================

try:

    original_image = Image.open(
        IMAGE_PATH
    ).convert("RGB")

except Exception as e:

    messagebox.showerror(
        "Error",
        f"ไม่พบไฟล์ {IMAGE_PATH}\n\n{e}"
    )

    raise SystemExit


IMAGE_WIDTH = original_image.width
IMAGE_HEIGHT = original_image.height


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()

root.title(
    "Robot Path Planner"
)

# Python เต็มจอ
root.attributes(
    "-fullscreen",
    True
)

root.configure(
    bg="#202020"
)


# กด ESC ออกจาก Fullscreen
root.bind(
    "<Escape>",
    lambda event: root.attributes(
        "-fullscreen",
        False
    )
)


# ============================================================
# VARIABLES
# ============================================================

robot_x = IMAGE_WIDTH - 150
robot_y = IMAGE_HEIGHT - 80

robot_direction = "LEFT"

robot_exists = False

placing_robot = False

dragging_robot = False

dragging_circle = False

selected_circle = None

adding_circle = False

route_path = []

parking_position = None

parking_direction = None


# ============================================================
# SCALE
# ============================================================

scale = 1.0

offset_x = 0

offset_y = 0

display_image = None

tk_image = None


# ============================================================
# MAIN LAYOUT
# ============================================================

main_frame = tk.Frame(

    root,

    bg="#202020"

)

main_frame.pack(

    fill=tk.BOTH,

    expand=True
)


# ============================================================
# LEFT MAP AREA
# ============================================================

map_frame = tk.Frame(

    main_frame,

    bg="#151515"

)

map_frame.pack(

    side=tk.LEFT,

    fill=tk.BOTH,

    expand=True,

    padx=10,

    pady=10
)


canvas = tk.Canvas(

    map_frame,

    bg="#151515",

    highlightthickness=0

)

canvas.pack(

    fill=tk.BOTH,

    expand=True
)


# ============================================================
# RIGHT CONTROL PANEL
# ============================================================

panel = tk.Frame(

    main_frame,

    bg="#252525",

    width=350

)

panel.pack(

    side=tk.RIGHT,

    fill=tk.Y,

    padx=(0, 10),

    pady=10
)

panel.pack_propagate(
    False
)


# ============================================================
# TITLE
# ============================================================

tk.Label(

    panel,

    text="🤖 ROBOT PATH",

    font=("Arial", 22, "bold"),

    fg="white",

    bg="#252525"

).pack(

    pady=(20, 0)
)


tk.Label(

    panel,

    text="PATH PLANNER",

    font=("Arial", 11),

    fg="#aaaaaa",

    bg="#252525"

).pack(

    pady=(0, 20)
)


# ============================================================
# STATUS
# ============================================================

status_label = tk.Label(

    panel,

    text="พร้อมใช้งาน",

    font=("Arial", 11, "bold"),

    fg="#00ff88",

    bg="#252525",

    wraplength=300,

    justify=tk.CENTER

)

status_label.pack(

    fill=tk.X,

    padx=15,

    pady=10
)


# ============================================================
# START CONTROL
# ============================================================

start_box = tk.LabelFrame(

    panel,

    text=" 1. จุดเริ่มต้นรถ ",

    font=("Arial", 11, "bold"),

    fg="white",

    bg="#252525",

    padx=10,

    pady=10

)

start_box.pack(

    fill=tk.X,

    padx=15,

    pady=8
)


start_position_label = tk.Label(

    start_box,

    text="ยังไม่ได้กำหนด",

    font=("Arial", 11),

    fg="white",

    bg="#252525"

)

start_position_label.pack(

    pady=5
)


def enable_start():

    global placing_robot

    global dragging_robot

    global adding_circle

    global selected_circle

    global route_path

    global parking_position

    global parking_direction

    global robot_exists

    global status_label

    global canvas

    global root

    global circles

    global dragging_circle

    global robot_x
    global robot_y
    global robot_direction

    placing_robot = True

    dragging_robot = False

    dragging_circle = False

    adding_circle = False

    selected_circle = None

    route_path = []

    parking_position = None

    parking_direction = None

    status_label.config(

        text="📍 คลิกบนแผนที่\nเพื่อกำหนดจุดเริ่มต้น"

    )


tk.Button(

    start_box,

    text="📍 กำหนดจุดเริ่มต้น",

    command=enable_start,

    font=("Arial", 11, "bold"),

    height=2

).pack(

    fill=tk.X,

    pady=5
)


# ============================================================
# ROBOT DIRECTION
# ============================================================

tk.Label(

    start_box,

    text="ทิศทางปัจจุบัน",

    font=("Arial", 10, "bold"),

    fg="#cccccc",

    bg="#252525"

).pack(

    anchor="w",

    pady=(10, 3)
)


direction_label = tk.Label(

    start_box,

    text="← LEFT",

    font=("Arial", 20, "bold"),

    fg="#00ddff",

    bg="#252525"

)

direction_label.pack(

    pady=5
)


# ============================================================
# ROTATE BUTTONS
# ============================================================

rotate_frame = tk.Frame(

    start_box,

    bg="#252525"

)

rotate_frame.pack(

    fill=tk.X,

    pady=5
)


def rotate_left():

    global robot_direction

    index = DIRECTIONS.index(

        robot_direction

    )

    robot_direction = DIRECTIONS[

        (index - 1) % 4

    ]

    update_direction()

    redraw()


def rotate_right():

    global robot_direction

    index = DIRECTIONS.index(

        robot_direction

    )

    robot_direction = DIRECTIONS[

        (index + 1) % 4

    ]

    update_direction()

    redraw()


tk.Button(

    rotate_frame,

    text="↶ หมุนซ้าย 90°",

    command=rotate_left,

    font=("Arial", 10, "bold"),

    height=2

).pack(

    side=tk.LEFT,

    fill=tk.X,

    expand=True,

    padx=(0, 4)
)


tk.Button(

    rotate_frame,

    text="↷ หมุนขวา 90°",

    command=rotate_right,

    font=("Arial", 10, "bold"),

    height=2

).pack(

    side=tk.RIGHT,

    fill=tk.X,

    expand=True,

    padx=(4, 0)
)


# ============================================================
# UPDATE DIRECTION
# ============================================================

def update_direction():

    direction_label.config(

        text=(

            DIRECTION_ARROWS[robot_direction]

            + " "

            + robot_direction

        )

    )


# ============================================================
# TARGET
# ============================================================

target_box = tk.LabelFrame(

    panel,

    text=" 2. เลือกเป้าหมาย ",

    font=("Arial", 11, "bold"),

    fg="white",

    bg="#252525",

    padx=10,

    pady=10

)

target_box.pack(

    fill=tk.X,

    padx=15,

    pady=8
)


target_var = tk.StringVar(

    value="RED"

)


target_combo = ttk.Combobox(

    target_box,

    textvariable=target_var,

    values=list(COLORS.keys()),

    state="readonly",

    font=("Arial", 11)

)

target_combo.pack(

    fill=tk.X,

    pady=5
)


# ============================================================
# CIRCLE EDIT
# ============================================================

circle_box = tk.LabelFrame(

    panel,

    text=" 3. แก้ไขวงกลม ",

    font=("Arial", 11, "bold"),

    fg="white",

    bg="#252525",

    padx=10,

    pady=10

)

circle_box.pack(

    fill=tk.X,

    padx=15,

    pady=8
)


circle_color_var = tk.StringVar(

    value="RED"

)


circle_combo = ttk.Combobox(

    circle_box,

    textvariable=circle_color_var,

    values=list(COLORS.keys()),

    state="readonly",

    font=("Arial", 10)

)

circle_combo.pack(

    fill=tk.X,

    pady=4
)


def enable_add_circle():

    global adding_circle

    global placing_robot

    global selected_circle

    global dragging_robot
    global dragging_circle

    adding_circle = True

    placing_robot = False

    dragging_robot = False

    dragging_circle = False

    selected_circle = None

    status_label.config(

        text=(

            "➕ คลิกบนแผนที่\n"

            f"เพื่อเพิ่ม {circle_color_var.get()}"

        )

    )


tk.Button(

    circle_box,

    text="➕ เพิ่มวงกลม",

    command=enable_add_circle,

    font=("Arial", 10, "bold"),

    height=1

).pack(

    fill=tk.X,

    pady=3
)


def delete_selected_circle():

    global selected_circle

    global route_path

    global parking_position
    global parking_direction

    if selected_circle is None:

        status_label.config(

            text="กรุณาคลิกเลือกวงกลมก่อน"

        )

        return

    if selected_circle in circles:

        circles.remove(

            selected_circle

        )

    selected_circle = None

    route_path = []

    parking_position = None
    parking_direction = None

    status_label.config(

        text="🗑 ลบวงกลมแล้ว"

    )

    redraw()


tk.Button(

    circle_box,

    text="🗑 ลบวงกลมที่เลือก",

    command=delete_selected_circle,

    font=("Arial", 10),

).pack(

    fill=tk.X,

    pady=3
)


# ============================================================
# PATH CONTROL
# ============================================================

path_box = tk.LabelFrame(

    panel,

    text=" 4. หาเส้นทาง ",

    font=("Arial", 11, "bold"),

    fg="white",

    bg="#252525",

    padx=10,

    pady=10

)

path_box.pack(

    fill=tk.X,

    padx=15,

    pady=8
)


def start_path():

    global route_path
    global parking_position
    global parking_direction

    if not robot_exists:

        messagebox.showwarning(

            "ยังไม่มีรถ",

            "กรุณากำหนดจุดเริ่มต้นก่อน"

        )

        return


    target_color = target_var.get()


    target = None


    for circle in circles:

        if circle["color"] == target_color:

            target = circle

            break


    if target is None:

        messagebox.showwarning(

            "ไม่พบเป้าหมาย",

            f"ไม่พบวงกลม {target_color}"

        )

        return


    status_label.config(

        text="🔎 กำลังหาเส้นทาง..."

    )


    root.update_idletasks()


    # --------------------------------------------------------
    # หา parking position
    # --------------------------------------------------------

    parking_candidates = get_parking_candidates(

        target

    )


    # --------------------------------------------------------
    # เลือกด้านที่เหมาะที่สุด
    # --------------------------------------------------------

    preferred = get_preferred_side(

        target

    )


    ordered_candidates = []


    # ใส่ preferred ก่อน

    for candidate in parking_candidates:

        if candidate["side"] == preferred:

            ordered_candidates.append(

                candidate

            )


    # แล้วค่อยด้านอื่น

    for candidate in parking_candidates:

        if candidate["side"] != preferred:

            ordered_candidates.append(

                candidate

            )


    best_path = None

    best_candidate = None


    # --------------------------------------------------------
    # ทดลองหา path ไปแต่ละ parking position
    # --------------------------------------------------------

    for candidate in ordered_candidates:

        path = astar(

            (

                robot_x,

                robot_y

            ),

            (

                candidate["x"],

                candidate["y"]

            )

        )


        if path is not None:

            best_path = path

            best_candidate = candidate

            break


    if best_path is None:

        route_path = []

        parking_position = None

        parking_direction = None

        redraw()

        status_label.config(

            text="❌ หาเส้นทางไม่เจอ"

        )

        return


    route_path = simplify_path(

        best_path

    )


    parking_position = (

        best_candidate["x"],

        best_candidate["y"]

    )


    parking_direction = best_candidate["direction"]


    redraw()


    # --------------------------------------------------------
    # แสดงผล
    # --------------------------------------------------------

    commands = path_to_commands(

        best_path,

        robot_direction,

        parking_direction

    )


    show_commands(

        commands,

        target_color,

        best_candidate["side"]

    )


tk.Button(

    path_box,

    text="🚀 เริ่มหาเส้นทาง",

    command=start_path,

    font=("Arial", 13, "bold"),

    bg="#00a85a",

    fg="white",

    activebackground="#00cc70",

    height=2

).pack(

    fill=tk.X,

    pady=5
)


def clear_path():

    global route_path

    global parking_position
    global parking_direction

    route_path = []

    parking_position = None

    parking_direction = None

    status_label.config(

        text="ล้างเส้นทางแล้ว"

    )

    redraw()


tk.Button(

    path_box,

    text="✖ ล้างเส้นทาง",

    command=clear_path,

    font=("Arial", 10)

).pack(

    fill=tk.X,

    pady=3
)


# ============================================================
# RESULT
# ============================================================

result_box = tk.LabelFrame(

    panel,

    text=" 5. ผลลัพธ์ ",

    font=("Arial", 11, "bold"),

    fg="white",

    bg="#252525",

    padx=8,

    pady=8

)

result_box.pack(

    fill=tk.BOTH,

    expand=True,

    padx=15,

    pady=8
)


result_text = tk.Text(

    result_box,

    bg="#171717",

    fg="#eeeeee",

    font=("Consolas", 10),

    wrap=tk.WORD,

    height=12

)

result_text.pack(

    fill=tk.BOTH,

    expand=True
)


# ============================================================
# COMMAND RESULT
# ============================================================

def show_commands(

    commands,

    target_color,

    side

):

    result_text.delete(

        "1.0",

        tk.END

    )


    result_text.insert(

        tk.END,

        f"🎯 เป้าหมาย: {target_color}\n"

    )


    result_text.insert(

        tk.END,

        f"📍 จอดด้าน: {side}\n\n"

    )


    if len(commands) == 0:

        result_text.insert(

            tk.END,

            "ไม่มีคำสั่ง"

        )

        return


    for i, command in enumerate(

        commands,

        1

    ):

        result_text.insert(

            tk.END,

            f"{i:02d}. {command}\n"

        )


    status_label.config(

        text=(

            f"✅ พบเส้นทางแล้ว\n"

            f"{len(commands)} คำสั่ง"

        )

    )


# ============================================================
# EXIT
# ============================================================

tk.Button(

    panel,

    text="ESC = ออกจาก Fullscreen",

    command=lambda: root.attributes(

        "-fullscreen",

        False

    ),

    font=("Arial", 9),

    fg="#bbbbbb",

    bg="#252525",

    relief=tk.FLAT

).pack(

    pady=8
)


# ============================================================
# IMAGE DISPLAY
# ============================================================

def update_image():

    global scale

    global offset_x

    global offset_y

    global display_image

    global tk_image


    canvas.update_idletasks()


    available_width = canvas.winfo_width()

    available_height = canvas.winfo_height()


    if available_width <= 10:

        return

    if available_height <= 10:

        return


    # --------------------------------------------
    # เว้นขอบ
    # --------------------------------------------

    padding = 20


    usable_width = available_width - padding * 2

    usable_height = available_height - padding * 2


    # --------------------------------------------
    # scale ให้รูปพอดีกับพื้นที่
    # --------------------------------------------

    scale_x = usable_width / IMAGE_WIDTH

    scale_y = usable_height / IMAGE_HEIGHT


    scale = min(

        scale_x,

        scale_y,

        1.5

    )


    new_width = int(

        IMAGE_WIDTH * scale

    )


    new_height = int(

        IMAGE_HEIGHT * scale

    )


    display_image = original_image.resize(

        (

            new_width,

            new_height

        ),

        Image.Resampling.LANCZOS

    )


    tk_image = ImageTk.PhotoImage(

        display_image

    )


    offset_x = (

        available_width - new_width

    ) // 2


    offset_y = (

        available_height - new_height

    ) // 2


    redraw()


# ============================================================
# WORLD -> CANVAS
# ============================================================

def world_to_canvas(

    x,

    y

):

    return (

        offset_x + x * scale,

        offset_y + y * scale

    )


# ============================================================
# CANVAS -> WORLD
# ============================================================

def canvas_to_world(

    x,

    y

):

    if scale == 0:

        return x, y


    return (

        (x - offset_x) / scale,

        (y - offset_y) / scale

    )


# ============================================================
# DRAW MAP
# ============================================================

def draw_map():

    if tk_image is None:

        return


    canvas.create_image(

        offset_x,

        offset_y,

        anchor=tk.NW,

        image=tk_image

    )


# ============================================================
# DRAW CIRCLES
# ============================================================

def draw_circles():

    for circle in circles:

        cx = circle["x"]

        cy = circle["y"]


        x1, y1 = world_to_canvas(

            cx - CIRCLE_RADIUS,

            cy - CIRCLE_RADIUS

        )


        x2, y2 = world_to_canvas(

            cx + CIRCLE_RADIUS,

            cy + CIRCLE_RADIUS

        )


        color = COLORS.get(

            circle["color"],

            "white"

        )


        width = 3


        if circle == selected_circle:

            width = 7


        canvas.create_oval(

            x1,

            y1,

            x2,

            y2,

            outline=color,

            width=width

        )


        tx, ty = world_to_canvas(

            cx,

            cy

        )


        canvas.create_text(

            tx,

            ty,

            text=circle["color"],

            fill="white",

            font=("Arial", 9, "bold")

        )


# ============================================================
# ROTATE POINT
# ============================================================

def rotate_point(

    px,

    py,

    angle

):

    rad = math.radians(

        angle

    )


    cos_a = math.cos(rad)

    sin_a = math.sin(rad)


    return (

        px * cos_a - py * sin_a,

        px * sin_a + py * cos_a

    )


# ============================================================
# DRAW ROBOT
# ============================================================

def draw_robot(

    x,

    y,

    direction,

    outline="#00ffff",

    fill="#33ccff",

    dashed=False

):

    width = ROBOT_WIDTH

    length = ROBOT_LENGTH


    corners = [

        (-width / 2, -length / 2),

        (width / 2, -length / 2),

        (width / 2, length / 2),

        (-width / 2, length / 2)

    ]


    angles = {

        "UP": 0,

        "RIGHT": 90,

        "DOWN": 180,

        "LEFT": 270

    }


    angle = angles[direction]


    points = []


    for px, py in corners:

        rx, ry = rotate_point(

            px,

            py,

            angle

        )


        cx, cy = world_to_canvas(

            x + rx,

            y + ry

        )


        points.extend(

            [cx, cy]

        )


    canvas.create_polygon(

        points,

        fill=fill,

        outline=outline,

        width=3

    )


    # --------------------------------------------------------
    # จุดกลาง
    # --------------------------------------------------------

    cx, cy = world_to_canvas(

        x,

        y

    )


    r = 4


    canvas.create_oval(

        cx - r,

        cy - r,

        cx + r,

        cy + r,

        fill="red",

        outline="red"

    )


    # --------------------------------------------------------
    # ลูกศรด้านหน้า
    # --------------------------------------------------------

    dx, dy = DIRECTION_VECTOR[

        direction

    ]


    front_distance = length / 2 + 15


    fx, fy = world_to_canvas(

        x + dx * front_distance,

        y + dy * front_distance

    )


    canvas.create_line(

        cx,

        cy,

        fx,

        fy,

        fill="red",

        width=4,

        arrow=tk.LAST

    )


# ============================================================
# DRAW ROUTE
# ============================================================

def draw_route():

    if not route_path:

        return


    # --------------------------------------------------------
    # วาดเส้นทีละช่วง
    # ไม่มี arrow
    # ไม่มีเส้นเฉียง
    # --------------------------------------------------------

    for i in range(

        len(route_path) - 1

    ):

        x1, y1 = route_path[i]

        x2, y2 = route_path[i + 1]


        cx1, cy1 = world_to_canvas(

            x1,

            y1

        )


        cx2, cy2 = world_to_canvas(

            x2,

            y2

        )


        canvas.create_line(

            cx1,

            cy1,

            cx2,

            cy2,

            fill=PATH_COLOR,

            width=max(

                3,

                int(5 * scale)

            )

        )


    # --------------------------------------------------------
    # จุดเลี้ยว
    # --------------------------------------------------------

    for i in range(

        1,

        len(route_path) - 1

    ):

        prev_x, prev_y = route_path[i - 1]

        x, y = route_path[i]

        next_x, next_y = route_path[i + 1]


        direction1 = (

            x - prev_x,

            y - prev_y

        )


        direction2 = (

            next_x - x,

            next_y - y

        )


        if direction1 != direction2:

            cx, cy = world_to_canvas(

                x,

                y

            )


            r = 5


            canvas.create_oval(

                cx - r,

                cy - r,

                cx + r,

                cy + r,

                fill=PATH_COLOR,

                outline="white"

            )


# ============================================================
# REDRAW
# ============================================================

def redraw():

    canvas.delete(

        "all"

    )


    draw_map()

    draw_route()

    draw_circles()


    if robot_exists:

        draw_robot(

            robot_x,

            robot_y,

            robot_direction,

            outline="#00ffff",

            fill="#33ccff"

        )


    # --------------------------------------------------------
    # รถปลายทาง
    # --------------------------------------------------------

    if (

        parking_position is not None

        and

        parking_direction is not None

    ):

        px, py = parking_position


        draw_robot(

            px,

            py,

            parking_direction,

            outline="#ffff00",

            fill="#ffff99"

        )


        cx, cy = world_to_canvas(

            px,

            py

        )


        canvas.create_text(

            cx,

            cy - 50,

            text="PARK",

            fill="yellow",

            font=("Arial", 10, "bold")

        )


# ============================================================
# FIND CIRCLE
# ============================================================

def find_circle(

    x,

    y

):

    for circle in reversed(circles):

        dx = x - circle["x"]

        dy = y - circle["y"]


        distance = math.sqrt(

            dx * dx +

            dy * dy

        )


        if distance <= CIRCLE_RADIUS:

            return circle


    return None


# ============================================================
# ROBOT HIT TEST
# ============================================================

def robot_hit_test(

    x,

    y

):

    if not robot_exists:

        return False


    dx = x - robot_x

    dy = y - robot_y


    # ใช้ bounding radius
    radius = math.sqrt(

        (ROBOT_WIDTH / 2) ** 2

        +

        (ROBOT_LENGTH / 2) ** 2

    )


    return (

        dx * dx +

        dy * dy

    ) <= radius ** 2


# ============================================================
# MOUSE DOWN
# ============================================================

def mouse_down(event):

    global placing_robot

    global adding_circle

    global dragging_robot

    global dragging_circle

    global selected_circle

    global robot_x

    global robot_y

    global robot_exists

    global route_path

    global parking_position

    global parking_direction


    x, y = canvas_to_world(

        event.x,

        event.y

    )


    # ---------------------------------------------
    # SET START
    # ---------------------------------------------

    if placing_robot:

        robot_x = x

        robot_y = y

        robot_exists = True

        placing_robot = False


        route_path = []

        parking_position = None

        parking_direction = None


        start_position_label.config(

            text=(

                f"X = {x:.0f}\n"

                f"Y = {y:.0f}"

            )

        )


        status_label.config(

            text="✅ กำหนดรถแล้ว\nลากรถเพื่อขยับได้"

        )


        redraw()

        return


    # ---------------------------------------------
    # ADD CIRCLE
    # ---------------------------------------------

    if adding_circle:

        new_circle = {

            "color": circle_color_var.get(),

            "x": x,

            "y": y

        }


        circles.append(

            new_circle

        )


        selected_circle = new_circle

        adding_circle = False


        status_label.config(

            text=(

                f"➕ เพิ่ม "

                f"{new_circle['color']} แล้ว"

            )

        )


        redraw()

        return


    # ---------------------------------------------
    # CLICK ROBOT
    # ---------------------------------------------

    if robot_hit_test(

        x,

        y

    ):

        dragging_robot = True

        selected_circle = None

        return


    # ---------------------------------------------
    # CLICK CIRCLE
    # ---------------------------------------------

    circle = find_circle(

        x,

        y

    )


    if circle is not None:

        selected_circle = circle

        dragging_circle = True


        status_label.config(

            text=(

                f"เลือก {circle['color']}\n"

                "ลากเพื่อเปลี่ยนตำแหน่ง"

            )

        )


        redraw()


# ============================================================
# MOUSE DRAG
# ============================================================

def mouse_drag(event):

    global robot_x

    global robot_y

    global dragging_robot

    global dragging_circle

    global route_path

    global parking_position

    global parking_direction


    x, y = canvas_to_world(

        event.x,

        event.y

    )


    # ---------------------------------------------
    # DRAG ROBOT
    # ---------------------------------------------

    if dragging_robot:

        robot_x = x

        robot_y = y


        route_path = []

        parking_position = None

        parking_direction = None


        start_position_label.config(

            text=(

                f"X = {x:.0f}\n"

                f"Y = {y:.0f}"

            )

        )


        redraw()


    # ---------------------------------------------
    # DRAG CIRCLE
    # ---------------------------------------------

    elif dragging_circle:

        if selected_circle is not None:

            selected_circle["x"] = x

            selected_circle["y"] = y


            route_path = []

            parking_position = None

            parking_direction = None


            redraw()


# ============================================================
# MOUSE UP
# ============================================================

def mouse_up(event):

    global dragging_robot

    global dragging_circle

    dragging_robot = False

    dragging_circle = False


# ============================================================
# KEYBOARD ROTATION
# ============================================================

root.bind(

    "<Left>",

    lambda event: rotate_left()

)

root.bind(

    "<Right>",

    lambda event: rotate_right()

)


# ============================================================
# PARKING CANDIDATES
# ============================================================

def get_parking_candidates(

    target

):

    cx = target["x"]

    cy = target["y"]


    robot_radius = math.sqrt(

        (ROBOT_WIDTH / 2) ** 2

        +

        (ROBOT_LENGTH / 2) ** 2

    )


    distance = (

        CIRCLE_RADIUS

        +

        robot_radius

        +

        ROBOT_MARGIN

    )


    candidates = [

        {

            "side": "TOP",

            "x": cx,

            "y": cy - distance,

            "direction": "DOWN"

        },

        {

            "side": "RIGHT",

            "x": cx + distance,

            "y": cy,

            "direction": "LEFT"

        },

        {

            "side": "BOTTOM",

            "x": cx,

            "y": cy + distance,

            "direction": "UP"

        },

        {

            "side": "LEFT",

            "x": cx - distance,

            "y": cy,

            "direction": "RIGHT"

        }

    ]


    return candidates


# ============================================================
# PREFERRED SIDE
# ============================================================

def get_preferred_side(

    target

):

    dx = robot_x - target["x"]

    dy = robot_y - target["y"]


    if abs(dx) >= abs(dy):

        if dx >= 0:

            return "RIGHT"

        else:

            return "LEFT"

    else:

        if dy >= 0:

            return "BOTTOM"

        else:

            return "TOP"


# ============================================================
# COLLISION
# ============================================================

def is_blocked(

    x,

    y

):

    # ---------------------------------------------
    # ขอบแผนที่
    # ---------------------------------------------

    robot_radius = math.sqrt(

        (ROBOT_WIDTH / 2) ** 2

        +

        (ROBOT_LENGTH / 2) ** 2

    )


    if x < robot_radius:

        return True


    if y < robot_radius:

        return True


    if x > IMAGE_WIDTH - robot_radius:

        return True


    if y > IMAGE_HEIGHT - robot_radius:

        return True


    # ---------------------------------------------
    # ชนวงกลม
    # ---------------------------------------------

    safe_distance = (

        CIRCLE_RADIUS

        +

        robot_radius

        +

        ROBOT_MARGIN

    )


    for circle in circles:

        dx = x - circle["x"]

        dy = y - circle["y"]


        distance = math.sqrt(

            dx * dx +

            dy * dy

        )


        if distance < safe_distance:

            return True


    return False


# ============================================================
# GRID POINT
# ============================================================

def snap_point(

    point

):

    x, y = point


    return (

        int(round(x / PATH_GRID))

        * PATH_GRID,

        int(round(y / PATH_GRID))

        * PATH_GRID

    )


# ============================================================
# HEURISTIC
# ============================================================

def heuristic(

    a,

    b

):

    return (

        abs(a[0] - b[0])

        +

        abs(a[1] - b[1])

    )


# ============================================================
# ASTAR
# ============================================================

def astar(

    start,

    goal

):

    start = snap_point(start)

    goal = snap_point(goal)


    # --------------------------------------------------------
    # ตรวจว่าจุดเริ่มหรือเป้าหมายติด obstacle หรือไม่
    # --------------------------------------------------------

    if is_blocked(

        start[0],

        start[1]

    ):

        return None


    if is_blocked(

        goal[0],

        goal[1]

    ):

        return None


    # --------------------------------------------------------
    # Open set
    # --------------------------------------------------------

    open_set = []


    heapq.heappush(

        open_set,

        (

            0,

            start

        )

    )


    came_from = {}


    g_score = {

        start: 0

    }


    # --------------------------------------------------------
    # 4 directions เท่านั้น
    # --------------------------------------------------------

    neighbors = [

        (PATH_GRID, 0),

        (-PATH_GRID, 0),

        (0, PATH_GRID),

        (0, -PATH_GRID)

    ]


    closed = set()


    while open_set:

        _, current = heapq.heappop(

            open_set

        )


        if current in closed:

            continue


        closed.add(current)


        # ----------------------------------------------------
        # ถึงเป้าหมาย
        # ----------------------------------------------------

        if current == goal:

            path = [

                current

            ]


            while current in came_from:

                current = came_from[current]

                path.append(current)


            path.reverse()


            return path


        # ----------------------------------------------------
        # สำรวจ 4 ทิศ
        # ----------------------------------------------------

        for dx, dy in neighbors:

            nx = current[0] + dx

            ny = current[1] + dy


            # -----------------------------------------------
            # ขอบ
            # -----------------------------------------------

            if nx < 0 or nx > IMAGE_WIDTH:

                continue


            if ny < 0 or ny > IMAGE_HEIGHT:

                continue


            # -----------------------------------------------
            # obstacle
            # -----------------------------------------------

            if is_blocked(

                nx,

                ny

            ):

                continue


            neighbor = (

                nx,

                ny

            )


            if neighbor in closed:

                continue


            tentative_g = (

                g_score[current]

                + PATH_GRID

            )


            if (

                neighbor not in g_score

                or

                tentative_g < g_score[neighbor]

            ):

                came_from[neighbor] = current

                g_score[neighbor] = tentative_g


                f_score = (

                    tentative_g

                    +

                    heuristic(

                        neighbor,

                        goal

                    )

                )


                heapq.heappush(

                    open_set,

                    (

                        f_score,

                        neighbor

                    )

                )


    return None


# ============================================================
# SIMPLIFY PATH
# ============================================================

def simplify_path(

    path

):

    if len(path) <= 2:

        return path


    result = [

        path[0]

    ]


    previous_direction = None


    for i in range(

        1,

        len(path)

    ):

        x1, y1 = path[i - 1]

        x2, y2 = path[i]


        dx = x2 - x1

        dy = y2 - y1


        if dx > 0:

            direction = "RIGHT"

        elif dx < 0:

            direction = "LEFT"

        elif dy > 0:

            direction = "DOWN"

        else:

            direction = "UP"


        if (

            previous_direction is not None

            and

            direction != previous_direction

        ):

            result.append(

                path[i - 1]

            )


        previous_direction = direction


    result.append(

        path[-1]

    )


    return result


# ============================================================
# GET MOVEMENT DIRECTION
# ============================================================

def get_move_direction(

    p1,

    p2

):

    dx = p2[0] - p1[0]

    dy = p2[1] - p1[1]


    if dx > 0:

        return "RIGHT"

    if dx < 0:

        return "LEFT"

    if dy > 0:

        return "DOWN"

    return "UP"


# ============================================================
# TURN COMMAND
# ============================================================

def turn_command(

    current,

    target

):

    current_index = DIRECTIONS.index(

        current

    )


    target_index = DIRECTIONS.index(

        target

    )


    diff = (

        target_index - current_index

    ) % 4


    if diff == 0:

        return []


    if diff == 1:

        return [

            "หมุนขวา 90°"

        ]


    if diff == 2:

        return [

            "หมุนขวา 90°",

            "หมุนขวา 90°"

        ]


    return [

        "หมุนซ้าย 90°"

    ]


# ============================================================
# PATH -> COMMANDS
# ============================================================

def path_to_commands(

    path,

    start_direction,

    final_direction

):

    if not path:

        return []


    commands = []


    current_direction = start_direction


    # --------------------------------------------------------
    # เดินแต่ละช่วง
    # --------------------------------------------------------

    for i in range(

        len(path) - 1

    ):

        direction = get_move_direction(

            path[i],

            path[i + 1]

        )


        current_index = DIRECTIONS.index(

            current_direction

        )


        target_index = DIRECTIONS.index(

            direction

        )


        diff = (

            target_index - current_index

        ) % 4


        # ---------------------------------------------
        # ไปข้างหน้า
        # ---------------------------------------------

        if diff == 0:

            commands.append(

                "เดินหน้า"

            )


        # ---------------------------------------------
        # กลับหลัง
        # ---------------------------------------------

        elif diff == 2:

            commands.append(

                "ถอยหลัง"

            )


        # ---------------------------------------------
        # ขวา
        # ---------------------------------------------

        elif diff == 1:

            commands.append(

                "หมุนขวา 90°"

            )

            commands.append(

                "เดินหน้า"

            )


            current_direction = direction


        # ---------------------------------------------
        # ซ้าย
        # ---------------------------------------------

        elif diff == 3:

            commands.append(

                "หมุนซ้าย 90°"

            )

            commands.append(

                "เดินหน้า"

            )


            current_direction = direction


    # --------------------------------------------------------
    # หมุนรถเข้าหาวงกลมตอนจบ
    # --------------------------------------------------------

    final_turns = turn_command(

        current_direction,

        final_direction

    )


    commands.extend(

        final_turns

    )


    return commands


# ============================================================
# RESIZE EVENT
# ============================================================

def on_resize(event):

    update_image()


root.bind(

    "<Configure>",

    on_resize

)


# ============================================================
# MOUSE EVENTS
# ============================================================

canvas.bind(

    "<ButtonPress-1>",

    mouse_down

)

canvas.bind(

    "<B1-Motion>",

    mouse_drag

)

canvas.bind(

    "<ButtonRelease-1>",

    mouse_up

)


# ============================================================
# INITIAL
# ============================================================

update_direction()

root.after(

    100,

    update_image

)


# ============================================================
# RUN
# ============================================================

root.mainloop()