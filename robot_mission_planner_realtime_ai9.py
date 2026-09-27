"""
robot_mission_planner_realtime.py
=========================================================
เวอร์ชันเรียลไทม์ของ robot_mission_planner.py

การเปลี่ยนแปลงหลักจากเวอร์ชันเดิม (ที่อ่านภาพนิ่ง img/map.png):

  1) เปิดกล้อง webcam index 1 (CAMERA_INDEX = 1) ด้วย cv2.VideoCapture
     แทนการ cv2.imread ไฟล์ภาพ

  2) มี 2 ลูปทำงานคู่ขนานผ่าน root.after():
        - video_loop()      : ดึงเฟรมจากกล้อง + อัปเดตภาพพื้นหลังบนแคนวาส
                               ให้สดตลอดเวลา (ค่าเริ่มต้น ~20 fps)
        - detection_loop()  : รันตรวจจับวงกลม/ก้อนหินซ้ำเป็นระยะ (ค่าเริ่มต้น
                               ทุก 400 ms) แล้วอัปเดตตัวแปร circles / stones

  3) เนื่องจากภาพเปลี่ยนทุกเฟรม หินแต่ละก้อนที่ตรวจพบใหม่จะถูก "จับคู่"
     (match_stones) กับหินก้อนเดิมโดยดูจาก สี + ระยะห่างตำแหน่งที่ใกล้สุด
     เพื่อคง id และสถานะ picked ไว้ ไม่ให้ id ของหินกระโดดเปลี่ยนทุกเฟรม

  4) ระหว่างที่ "ภารกิจอัตโนมัติ" กำลังทำงานอยู่ (mission_running = True)
     detection_loop จะหยุดอัปเดตตำแหน่งวงกลม/หินชั่วคราว (วิดีโอยังสดอยู่)
     เพื่อไม่ให้เส้นทางที่คำนวณไว้แล้วคลาดเคลื่อนระหว่างที่รถ (จำลอง) กำลัง
     เคลื่อนที่ตามแผน แล้วจะกลับมาตรวจจับต่อทันทีที่ภารกิจเสร็จ

ส่วนตรรกะ A* / การวางแผนหยิบ-วางหิน / การจำลองรถ ยังเหมือนเดิมทุกประการ
=========================================================
"""

import math
import heapq
import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk


# ============================================================
# SETTINGS
# ============================================================

CAMERA_INDEX = 2              # <-- ใช้เว็บแคม index 1 ตามที่ต้องการ
CAMERA_REQUEST_WIDTH = 1280
CAMERA_REQUEST_HEIGHT = 720

FRAME_INTERVAL_MS = 50        # ความถี่รีเฟรชภาพวิดีโอ (~20 fps)
DETECT_INTERVAL_MS = 400      # ความถี่รันตรวจจับสี/วงกลม/หินซ้ำ
STONE_MATCH_MAX_DIST = 25     # ระยะสูงสุด (px) ที่ถือว่าเป็นหินก้อนเดิม

ROBOT_WIDTH = 35
ROBOT_LENGTH = 55
ROBOT_MARGIN = 8          # ระยะเผื่อรอบวงกลม
STONE_MARGIN = 6          # ระยะเผื่อรอบก้อนหิน

DEFAULT_CIRCLE_RADIUS = 40

PATH_GRID = 5
PATH_COLOR = "#ff00ff"
PICKUP_PATH_COLOR = "#00ffaa"

STEP_DELAY_MS = 1000      # หินก้อนละ 1 วินาที (ทยอยแสดงผล)

MIN_STONE_AREA = 20
MAX_STONE_AREA = 4500


DIRECTIONS = ["UP", "RIGHT", "DOWN", "LEFT"]

DIRECTION_ARROWS = {"UP": "↑", "RIGHT": "→", "DOWN": "↓", "LEFT": "←"}

DIRECTION_VECTOR = {
    "UP": (0, -1),
    "RIGHT": (1, 0),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
}

COLORS = {
    "GREEN": "#00cc44",
    "BLUE": "#2277ff",
    "RED": "#ff3333",
    "PURPLE": "#aa44dd",
    "CYAN": "#00bbbb",
    "ORANGE": "#ff8800",
}


# ============================================================
# สี HSV สำหรับตรวจ "วงกลม" (มาจาก ai.py)
# ============================================================

CIRCLE_COLOR_RANGES = {
    "GREEN":  ((35, 40, 40), (85, 255, 255)),
    "BLUE":   ((88, 160, 50), (105, 255, 230)),
    "RED":    ((0, 60, 40), (10, 255, 255)),
    "PURPLE": ((130, 40, 40), (170, 255, 255)),
    "CYAN":   ((80, 20, 120), (100, 155, 255)),
    "ORANGE": ((10, 60, 40), (25, 255, 255)),
}


# ============================================================
# สี HSV สำหรับตรวจ "ก้อนหิน" (มาจาก ai3.py)
# ============================================================

STONE_COLOR_RANGES = {
    "GREEN":  ((56, 50, 135), (88, 255, 255)),
    "BLUE":   ((85, 165, 100), (110, 255, 255)),
    "CYAN":   ((85, 100, 190), (110, 170, 255)),
    "RED":    ((0, 70, 120), (5, 255, 255)),
    "PURPLE": ((108, 74, 0), (164, 255, 255)),
    "ORANGE": ((5, 40, 120), (25, 255, 255)),
}


# ============================================================
# ค่า default กรณีตรวจไม่เจอวงกลมสีนั้นในเฟรมปัจจุบัน (มาจาก ai5.py)
# ============================================================

DEFAULT_CIRCLE_POSITIONS = {
    "GREEN":  (69, 197),
    "BLUE":   (294, 111),
    "RED":    (534, 88),
    "PURPLE": (78, 393),
    "CYAN":   (266, 502),
    "ORANGE": (517, 488),
}


# ============================================================
# ตรวจจับวงกลม (ย่อมาจาก ai.py)
# ============================================================

def detect_circles(image_bgr):
    """คืนค่า list ของ dict: color, x, y, radius"""

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    kernel = np.ones((5, 5), np.uint8)

    found = []

    for color_name, (lower, upper) in CIRCLE_COLOR_RANGES.items():

        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        best = None

        for contour in contours:

            area = cv2.contourArea(contour)
            if area < 3000:
                continue

            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            circularity = 4 * math.pi * area / (perimeter * perimeter)
            if circularity < 0.75:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            ratio = w / h
            if ratio < 0.8 or ratio > 1.2:
                continue

            # เลือกวงกลมที่พื้นที่ใหญ่สุดของสีนั้น ถ้าเจอมากกว่า 1
            if best is None or area > best["area"]:
                best = {
                    "color": color_name,
                    "x": x + w // 2,
                    "y": y + h // 2,
                    "radius": max(w, h) / 2,
                    "area": area,
                }

        if best is not None:
            del best["area"]
            found.append(best)

    return found


# ============================================================
# ตรวจจับก้อนหิน (ย่อมาจาก ai3.py)
# ============================================================

def detect_stones(image_bgr, circles_list):
    """คืนค่า list ของ dict: color, x, y, radius (ยังไม่มี id / picked
    เพราะจะถูกเติมทีหลังโดย match_stones เพื่อคง identity ข้ามเฟรม)"""

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    kernel = np.ones((3, 3), np.uint8)

    detected = []

    for color_name, (lower, upper) in STONE_COLOR_RANGES.items():

        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # ลบพื้นที่วงกลมทั้งหมดออกจาก mask ก่อน เพื่อไม่ให้นับวงกลมเป็นหิน
        for circle in circles_list:
            cv2.circle(
                mask,
                (int(circle["x"]), int(circle["y"])),
                int(circle["radius"]) + 5,
                0,
                -1,
            )

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        for contour in contours:

            area = cv2.contourArea(contour)
            x, y, w, h = cv2.boundingRect(contour)

            if area < MIN_STONE_AREA or area > MAX_STONE_AREA:
                continue
            if w < 5 or h < 5:
                continue
            if w > 100 or h > 100:
                continue

            ratio = w / h
            if ratio < 0.4 or ratio > 2.5:
                continue

            detected.append({
                "color": color_name,
                "x": x + w // 2,
                "y": y + h // 2,
                "radius": max(w, h) / 2,
            })

    return detected


# ============================================================
# กล้อง (real-time capture)
# ============================================================

cap = None
current_frame_bgr = None
camera_error = None

IMAGE_WIDTH = 800
IMAGE_HEIGHT = 600


def init_camera():
    """เปิดเว็บแคมตาม CAMERA_INDEX แล้วอ่านเฟรมแรกเพื่อรู้ขนาดภาพจริง"""
    global cap, IMAGE_WIDTH, IMAGE_HEIGHT, camera_error, current_frame_bgr

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        camera_error = f"ไม่สามารถเปิดกล้อง index {CAMERA_INDEX} ได้"
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_REQUEST_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_REQUEST_HEIGHT)

    ok, frame = cap.read()
    if not ok or frame is None:
        camera_error = f"เปิดกล้อง index {CAMERA_INDEX} ได้ แต่อ่านภาพไม่สำเร็จ"
        return False

    IMAGE_HEIGHT, IMAGE_WIDTH = frame.shape[:2]
    current_frame_bgr = frame
    return True


camera_ok = init_camera()


# วงกลม / หิน เริ่มต้นว่าง — จะถูกเติมโดย detection_loop() แบบเรียลไทม์
circles = []
stones = []
circles_by_color = {}
next_stone_id = 0


def match_stones(old_stones, new_stones_raw):
    """จับคู่หินที่ตรวจพบใหม่ในเฟรมนี้ กับหินก้อนเดิมจากเฟรมก่อนหน้า
    (ดูจากสีเดียวกัน + ตำแหน่งใกล้สุดภายในระยะ STONE_MATCH_MAX_DIST)
    เพื่อคง id และสถานะ picked ไว้ข้ามเฟรม ไม่ให้กระพริบ/สลับ id"""

    global next_stone_id

    used_old_indices = set()
    matched = []

    for raw in new_stones_raw:
        best_idx = None
        best_dist = STONE_MATCH_MAX_DIST

        for i, old in enumerate(old_stones):
            if i in used_old_indices:
                continue
            if old["color"] != raw["color"]:
                continue
            d = math.hypot(raw["x"] - old["x"], raw["y"] - old["y"])
            if d < best_dist:
                best_dist = d
                best_idx = i

        if best_idx is not None:
            used_old_indices.add(best_idx)
            old = old_stones[best_idx]
            raw["id"] = old["id"]
            raw["picked"] = old["picked"]
        else:
            raw["id"] = next_stone_id
            next_stone_id += 1
            raw["picked"] = False

        matched.append(raw)

    return matched


def run_detection():
    """รันตรวจจับวงกลม + หินจากเฟรมล่าสุด แล้วอัปเดต circles / stones /
    circles_by_color ให้เป็นข้อมูลปัจจุบัน"""

    global circles, stones, circles_by_color

    if current_frame_bgr is None:
        return

    detected_circles = detect_circles(current_frame_bgr)
    found_colors = {c["color"] for c in detected_circles}

    for color_name, (dx, dy) in DEFAULT_CIRCLE_POSITIONS.items():
        if color_name not in found_colors:
            detected_circles.append({
                "color": color_name,
                "x": dx,
                "y": dy,
                "radius": DEFAULT_CIRCLE_RADIUS,
            })

    detected_stones_raw = detect_stones(current_frame_bgr, detected_circles)

    circles = detected_circles
    stones = match_stones(stones, detected_stones_raw)
    circles_by_color = {c["color"]: c for c in circles}


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()
root.title("Robot Mission Planner — เรียลไทม์จากกล้อง (webcam index 1)")
root.attributes("-fullscreen", True)
root.configure(bg="#202020")

root.bind("<Escape>", lambda e: root.attributes("-fullscreen", False))


# ============================================================
# STATE
# ============================================================

robot_x = IMAGE_WIDTH - 150
robot_y = IMAGE_HEIGHT - 80
robot_direction = "LEFT"

robot_exists = False
placing_robot = False
dragging_robot = False

route_path = []            # เส้นทางที่กำลังวาด (leg ปัจจุบัน)
missions = []               # ผลลัพธ์ทั้งหมดหลังคำนวณ
mission_running = False

target_stone_id = None      # id หินก้อนที่กำลังถูกหยิบอยู่ตอนนี้ (ทำกรอบไฮไลท์)
collected_count = {}        # {color: จำนวนที่วางแล้ว}
total_by_color = {}         # {color: จำนวนหินทั้งหมดของสีนั้น}

scale = 1.0
offset_x = 0
offset_y = 0
tk_image = None


# ============================================================
# LAYOUT
# ============================================================

main_frame = tk.Frame(root, bg="#202020")
main_frame.pack(fill=tk.BOTH, expand=True)

map_frame = tk.Frame(main_frame, bg="#151515")
map_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

canvas = tk.Canvas(map_frame, bg="#151515", highlightthickness=0)
canvas.pack(fill=tk.BOTH, expand=True)

panel = tk.Frame(main_frame, bg="#252525", width=380)
panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
panel.pack_propagate(False)

tk.Label(
    panel, text="🤖 ROBOT MISSION PLANNER (LIVE)",
    font=("Arial", 18, "bold"), fg="white", bg="#252525",
).pack(pady=(20, 0))

tk.Label(
    panel, text="หยิบหินทุกก้อน → วางวงกลมให้ตรงสี (กล้องเรียลไทม์)",
    font=("Arial", 10), fg="#aaaaaa", bg="#252525",
).pack(pady=(0, 15))

status_label = tk.Label(
    panel, text="พร้อมใช้งาน",
    font=("Arial", 11, "bold"), fg="#00ff88", bg="#252525",
    wraplength=340, justify=tk.CENTER,
)
status_label.pack(fill=tk.X, padx=15, pady=8)

if not camera_ok:
    status_label.config(
        text=f"⚠ เปิดกล้องไม่สำเร็จ: {camera_error}\n"
             f"ใช้ตำแหน่งวงกลม default แทน / จะไม่มีการตรวจจับหินแบบสด",
        fg="#ffaa00",
    )


# ---- 1. จุดเริ่มต้น -------------------------------------------------

start_box = tk.LabelFrame(
    panel, text=" 1. จุดเริ่มต้นรถ ", font=("Arial", 11, "bold"),
    fg="white", bg="#252525", padx=10, pady=10,
)
start_box.pack(fill=tk.X, padx=15, pady=8)

start_position_label = tk.Label(
    start_box, text="ยังไม่ได้กำหนด", font=("Arial", 11),
    fg="white", bg="#252525",
)
start_position_label.pack(pady=5)


def enable_start():
    global placing_robot, dragging_robot, route_path, missions, mission_running
    placing_robot = True
    dragging_robot = False
    route_path = []
    missions = []
    mission_running = False
    status_label.config(text="📍 คลิกบนแผนที่\nเพื่อกำหนดจุดเริ่มต้น", fg="#00ff88")


tk.Button(
    start_box, text="📍 กำหนดจุดเริ่มต้น", command=enable_start,
    font=("Arial", 11, "bold"), height=2,
).pack(fill=tk.X, pady=5)

tk.Label(
    start_box, text="ทิศทางปัจจุบัน", font=("Arial", 10, "bold"),
    fg="#cccccc", bg="#252525",
).pack(anchor="w", pady=(10, 3))

direction_label = tk.Label(
    start_box, text="← LEFT", font=("Arial", 20, "bold"),
    fg="#00ddff", bg="#252525",
)
direction_label.pack(pady=5)

rotate_frame = tk.Frame(start_box, bg="#252525")
rotate_frame.pack(fill=tk.X, pady=5)


def update_direction():
    direction_label.config(text=DIRECTION_ARROWS[robot_direction] + " " + robot_direction)


def rotate_left():
    global robot_direction
    idx = DIRECTIONS.index(robot_direction)
    robot_direction = DIRECTIONS[(idx - 1) % 4]
    update_direction()
    redraw()


def rotate_right():
    global robot_direction
    idx = DIRECTIONS.index(robot_direction)
    robot_direction = DIRECTIONS[(idx + 1) % 4]
    update_direction()
    redraw()


tk.Button(
    rotate_frame, text="↶ หมุนซ้าย 90°", command=rotate_left,
    font=("Arial", 10, "bold"), height=2,
).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

tk.Button(
    rotate_frame, text="↷ หมุนขวา 90°", command=rotate_right,
    font=("Arial", 10, "bold"), height=2,
).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))


# ---- 2. ภารกิจอัตโนมัติ ---------------------------------------------

mission_box = tk.LabelFrame(
    panel, text=" 2. ภารกิจหยิบ-วางหินทั้งหมด ", font=("Arial", 11, "bold"),
    fg="white", bg="#252525", padx=10, pady=10,
)
mission_box.pack(fill=tk.X, padx=15, pady=8)

detect_info_label = tk.Label(
    mission_box,
    text="กำลังรอข้อมูลจากกล้อง...",
    font=("Arial", 10), fg="#cccccc", bg="#252525",
)
detect_info_label.pack(pady=(0, 6))


def run_full_mission():
    global mission_running, collected_count, total_by_color, target_stone_id

    if not robot_exists:
        messagebox.showwarning("ยังไม่มีรถ", "กรุณากำหนดจุดเริ่มต้นก่อน")
        return

    if mission_running:
        return

    # ดึงข้อมูลตำแหน่งหิน/วงกลมล่าสุดจากกล้อง ณ ขณะนี้ ก่อนเริ่มวางแผน
    # (หลังจากนี้ detection_loop จะหยุดอัปเดตชั่วคราวจนกว่าภารกิจจะเสร็จ
    # เพื่อไม่ให้เส้นทางที่วางแผนไว้คลาดเคลื่อนกลางทาง)
    run_detection()

    for s in stones:
        s["picked"] = False

    target_stone_id = None
    collected_count = {c: 0 for c in circles_by_color}
    total_by_color = {}
    for s in stones:
        total_by_color[s["color"]] = total_by_color.get(s["color"], 0) + 1

    status_label.config(text="🔎 กำลังวางแผนภารกิจทั้งหมด...", fg="#00ff88")
    root.update_idletasks()

    plan = plan_full_mission()

    if not plan:
        status_label.config(text="❌ ไม่พบหินที่หาเส้นทางได้เลย", fg="#ff5555")
        return

    result_text.delete("1.0", tk.END)
    result_text.insert(
        tk.END,
        f"พบแผนทั้งหมด {len(plan)} / {len(stones)} ก้อน\n"
        f"(ก้อนที่หาเส้นทางไม่ได้จะถูกข้าม)\n\n",
    )

    mission_running = True
    redraw()
    reveal_mission_step(plan, 0)


tk.Button(
    mission_box, text="🚀 เริ่มภารกิจอัตโนมัติ", command=run_full_mission,
    font=("Arial", 13, "bold"), bg="#00a85a", fg="white",
    activebackground="#00cc70", height=2,
).pack(fill=tk.X, pady=5)


def clear_mission():
    global route_path, missions, mission_running
    route_path = []
    missions = []
    mission_running = False
    for s in stones:
        s["picked"] = False
    status_label.config(text="ล้างภารกิจแล้ว", fg="#00ff88")
    redraw()


tk.Button(
    mission_box, text="✖ ล้างภารกิจ", command=clear_mission, font=("Arial", 10),
).pack(fill=tk.X, pady=3)


# ---- 3. ผลลัพธ์ -------------------------------------------------------

result_box = tk.LabelFrame(
    panel, text=" 3. ลำดับคำสั่ง ", font=("Arial", 11, "bold"),
    fg="white", bg="#252525", padx=8, pady=8,
)
result_box.pack(fill=tk.BOTH, expand=True, padx=15, pady=8)

result_text = tk.Text(
    result_box, bg="#171717", fg="#eeeeee", font=("Consolas", 10),
    wrap=tk.WORD,
)
result_scroll = tk.Scrollbar(result_box, command=result_text.yview)
result_text.configure(yscrollcommand=result_scroll.set)
result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
result_text.pack(fill=tk.BOTH, expand=True)

tk.Button(
    panel, text="ESC = ออกจาก Fullscreen",
    command=lambda: root.attributes("-fullscreen", False),
    font=("Arial", 9), fg="#bbbbbb", bg="#252525", relief=tk.FLAT,
).pack(pady=8)


# ============================================================
# IMAGE / COORDINATE HELPERS
# ============================================================

def update_video_frame(frame_bgr):
    """แปลงเฟรมกล้องปัจจุบันเป็นภาพที่แสดงบนแคนวาส (คำนวณ scale/offset ใหม่
    ทุกครั้งเผื่อขนาดหน้าต่างเปลี่ยน)"""

    global scale, offset_x, offset_y, tk_image

    canvas.update_idletasks()
    available_width = canvas.winfo_width()
    available_height = canvas.winfo_height()

    if available_width <= 10 or available_height <= 10:
        return

    padding = 20
    usable_width = available_width - padding * 2
    usable_height = available_height - padding * 2

    scale_x = usable_width / IMAGE_WIDTH
    scale_y = usable_height / IMAGE_HEIGHT
    scale = min(scale_x, scale_y, 1.5)

    new_width = max(1, int(IMAGE_WIDTH * scale))
    new_height = max(1, int(IMAGE_HEIGHT * scale))

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(frame_rgb).resize(
        (new_width, new_height), Image.Resampling.LANCZOS
    )
    tk_image = ImageTk.PhotoImage(pil_img)

    offset_x = (available_width - new_width) // 2
    offset_y = (available_height - new_height) // 2


def world_to_canvas(x, y):
    return offset_x + x * scale, offset_y + y * scale


def canvas_to_world(x, y):
    if scale == 0:
        return x, y
    return (x - offset_x) / scale, (y - offset_y) / scale


# ============================================================
# DRAWING
# ============================================================

def draw_map():
    if tk_image is not None:
        canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=tk_image)
    else:
        x1, y1 = world_to_canvas(0, 0)
        x2, y2 = world_to_canvas(IMAGE_WIDTH, IMAGE_HEIGHT)
        canvas.create_rectangle(x1, y1, x2, y2, outline="#444444")


def draw_circles():
    for circle in circles:
        cx, cy, r = circle["x"], circle["y"], circle["radius"]
        x1, y1 = world_to_canvas(cx - r, cy - r)
        x2, y2 = world_to_canvas(cx + r, cy + r)
        color = COLORS.get(circle["color"], "white")
        canvas.create_oval(x1, y1, x2, y2, outline=color, width=3)
        tx, ty = world_to_canvas(cx, cy)
        canvas.create_text(tx, ty, text=circle["color"], fill="white",
                            font=("Arial", 9, "bold"))

        # ---- จำนวนหินที่เก็บ/วางแล้วของสีนี้ ----
        collected = collected_count.get(circle["color"], 0)
        total = total_by_color.get(circle["color"], 0)

        count_x, count_y = world_to_canvas(cx, cy + r + 16)
        canvas.create_text(
            count_x, count_y,
            text=f"เก็บแล้ว {collected}/{total}",
            fill="#00ff88" if total and collected >= total else "#ffff00",
            font=("Arial", 9, "bold"),
        )


def draw_stones():
    for stone in stones:
        cx, cy, r = stone["x"], stone["y"], stone["radius"]
        x1, y1 = world_to_canvas(cx - r, cy - r)
        x2, y2 = world_to_canvas(cx + r, cy + r)

        if stone.get("picked"):
            # ---- เก็บแล้ว: ถมดำเป็นเครื่องหมาย ----
            canvas.create_oval(x1, y1, x2, y2, outline="#555555", fill="#111111", width=1)
        else:
            color = COLORS.get(stone["color"], "white")
            canvas.create_oval(x1, y1, x2, y2, outline=color, fill=color, width=1)

        # ---- กรอบไฮไลท์ก้อนที่กำลังถูกหยิบอยู่ตอนนี้ ----
        if stone["id"] == target_stone_id:
            pad = 8
            bx1, by1 = world_to_canvas(cx - r - pad, cy - r - pad)
            bx2, by2 = world_to_canvas(cx + r + pad, cy + r + pad)
            canvas.create_rectangle(
                bx1, by1, bx2, by2, outline="#ffff00", width=3, dash=(4, 2)
            )
            tx, ty = world_to_canvas(cx, cy - r - pad - 10)
            canvas.create_text(
                tx, ty, text=f"🎯 {stone['color']}", fill="#ffff00",
                font=("Arial", 9, "bold"),
            )


def rotate_point(px, py, angle):
    rad = math.radians(angle)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    return px * cos_a - py * sin_a, px * sin_a + py * cos_a


def draw_robot(x, y, direction, outline="#00ffff", fill="#33ccff"):
    width, length = ROBOT_WIDTH, ROBOT_LENGTH
    corners = [
        (-width / 2, -length / 2), (width / 2, -length / 2),
        (width / 2, length / 2), (-width / 2, length / 2),
    ]
    angles = {"UP": 0, "RIGHT": 90, "DOWN": 180, "LEFT": 270}
    angle = angles[direction]

    points = []
    for px, py in corners:
        rx, ry = rotate_point(px, py, angle)
        cx, cy = world_to_canvas(x + rx, y + ry)
        points.extend([cx, cy])

    canvas.create_polygon(points, fill=fill, outline=outline, width=3)

    cx, cy = world_to_canvas(x, y)
    r = 4
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="red", outline="red")

    dx, dy = DIRECTION_VECTOR[direction]
    front_distance = length / 2 + 15
    fx, fy = world_to_canvas(x + dx * front_distance, y + dy * front_distance)
    canvas.create_line(cx, cy, fx, fy, fill="red", width=4, arrow=tk.LAST)


def draw_route():
    if not route_path:
        return
    for i in range(len(route_path) - 1):
        x1, y1 = route_path[i]
        x2, y2 = route_path[i + 1]
        cx1, cy1 = world_to_canvas(x1, y1)
        cx2, cy2 = world_to_canvas(x2, y2)
        canvas.create_line(cx1, cy1, cx2, cy2, fill=PATH_COLOR,
                            width=max(3, int(5 * scale)))


def redraw():
    canvas.delete("all")
    draw_map()
    draw_route()
    draw_stones()
    draw_circles()
    if robot_exists:
        draw_robot(robot_x, robot_y, robot_direction)


# ============================================================
# COLLISION / PATHFINDING (ดัดแปลงจาก ai5.py)
# ห้ามทับวงกลม + ห้ามเหยียบหิน (ยกเว้นก้อนที่ระบุ ignore_id
# ซึ่งหมายถึงก้อนที่รถกำลังจะเข้าไปหยิบ/กำลังถืออยู่)
# ============================================================

def robot_bounding_radius():
    return math.sqrt((ROBOT_WIDTH / 2) ** 2 + (ROBOT_LENGTH / 2) ** 2)


def is_blocked(x, y, ignore_stone_id=None, extra_ignore_ids=None):
    robot_radius = robot_bounding_radius()

    if x < robot_radius or y < robot_radius:
        return True
    if x > IMAGE_WIDTH - robot_radius or y > IMAGE_HEIGHT - robot_radius:
        return True

    # ห้ามทับวงกลม (เสมอ ไม่มีข้อยกเว้น)
    for circle in circles:
        safe = circle["radius"] + robot_radius + ROBOT_MARGIN
        dx = x - circle["x"]
        dy = y - circle["y"]
        if math.hypot(dx, dy) < safe:
            return True

    # ห้ามเหยียบหิน (ยกเว้นก้อนที่ถูก ignore / เก็บไปแล้วจริง ๆ /
    # หรือถูกวางแผนไว้แล้วว่าจะเก็บก่อนหน้านี้ใน mission เดียวกัน)
    for stone in stones:
        if stone.get("picked"):
            continue
        if stone["id"] == ignore_stone_id:
            continue
        if extra_ignore_ids and stone["id"] in extra_ignore_ids:
            continue
        safe = stone["radius"] + robot_radius + STONE_MARGIN
        dx = x - stone["x"]
        dy = y - stone["y"]
        if math.hypot(dx, dy) < safe:
            return True

    return False


def snap_point(point):
    x, y = point
    return (
        int(round(x / PATH_GRID)) * PATH_GRID,
        int(round(y / PATH_GRID)) * PATH_GRID,
    )


def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar(start, goal, ignore_stone_id=None, extra_ignore_ids=None):
    start = snap_point(start)
    goal = snap_point(goal)

    if is_blocked(*start, ignore_stone_id=ignore_stone_id, extra_ignore_ids=extra_ignore_ids):
        return None
    if is_blocked(*goal, ignore_stone_id=ignore_stone_id, extra_ignore_ids=extra_ignore_ids):
        return None

    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}

    neighbors = [(PATH_GRID, 0), (-PATH_GRID, 0), (0, PATH_GRID), (0, -PATH_GRID)]
    closed = set()

    while open_set:
        _, current = heapq.heappop(open_set)

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for dx, dy in neighbors:
            nx, ny = current[0] + dx, current[1] + dy

            if nx < 0 or nx > IMAGE_WIDTH or ny < 0 or ny > IMAGE_HEIGHT:
                continue
            if is_blocked(nx, ny, ignore_stone_id=ignore_stone_id, extra_ignore_ids=extra_ignore_ids):
                continue

            neighbor = (nx, ny)
            if neighbor in closed:
                continue

            tentative_g = g_score[current] + PATH_GRID

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score, neighbor))

    return None


def simplify_path(path):
    if len(path) <= 2:
        return path

    result = [path[0]]
    previous_direction = None

    for i in range(1, len(path)):
        x1, y1 = path[i - 1]
        x2, y2 = path[i]
        dx, dy = x2 - x1, y2 - y1

        if dx > 0:
            direction = "RIGHT"
        elif dx < 0:
            direction = "LEFT"
        elif dy > 0:
            direction = "DOWN"
        else:
            direction = "UP"

        if previous_direction is not None and direction != previous_direction:
            result.append(path[i - 1])

        previous_direction = direction

    result.append(path[-1])
    return result


def get_move_direction(p1, p2):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    if dx > 0:
        return "RIGHT"
    if dx < 0:
        return "LEFT"
    if dy > 0:
        return "DOWN"
    return "UP"


def turn_command(current, target):
    current_index = DIRECTIONS.index(current)
    target_index = DIRECTIONS.index(target)
    diff = (target_index - current_index) % 4

    if diff == 0:
        return []
    if diff == 1:
        return ["หมุนขวา 90°"]
    if diff == 2:
        return ["หมุนขวา 90°", "หมุนขวา 90°"]
    return ["หมุนซ้าย 90°"]


def path_to_commands(path, start_direction, final_direction):
    if not path:
        return []

    commands = []
    current_direction = start_direction

    for i in range(len(path) - 1):
        direction = get_move_direction(path[i], path[i + 1])
        current_index = DIRECTIONS.index(current_direction)
        target_index = DIRECTIONS.index(direction)
        diff = (target_index - current_index) % 4

        if diff == 0:
            commands.append("เดินหน้า")
        elif diff == 2:
            commands.append("ถอยหลัง")
        elif diff == 1:
            commands.append("หมุนขวา 90°")
            commands.append("เดินหน้า")
            current_direction = direction
        elif diff == 3:
            commands.append("หมุนซ้าย 90°")
            commands.append("เดินหน้า")
            current_direction = direction

    final_turns = turn_command(current_direction, final_direction)
    commands.extend(final_turns)
    return commands


# ============================================================
# PARKING CANDIDATES (ใช้ได้ทั้งกับวงกลม และ ก้อนหิน)
# ============================================================

def get_parking_candidates(cx, cy, obstacle_radius):
    robot_radius = robot_bounding_radius()
    distance = obstacle_radius + robot_radius + ROBOT_MARGIN

    return [
        {"side": "TOP", "x": cx, "y": cy - distance, "direction": "DOWN"},
        {"side": "RIGHT", "x": cx + distance, "y": cy, "direction": "LEFT"},
        {"side": "BOTTOM", "x": cx, "y": cy + distance, "direction": "UP"},
        {"side": "LEFT", "x": cx - distance, "y": cy, "direction": "RIGHT"},
    ]


def get_preferred_side(from_x, from_y, target_x, target_y):
    dx = from_x - target_x
    dy = from_y - target_y

    if abs(dx) >= abs(dy):
        return "RIGHT" if dx >= 0 else "LEFT"
    return "BOTTOM" if dy >= 0 else "TOP"


def order_by_preferred(candidates, preferred):
    ordered = [c for c in candidates if c["side"] == preferred]
    ordered += [c for c in candidates if c["side"] != preferred]
    return ordered


# ============================================================
# วางแผนภารกิจทั้งหมดแบบต่อเนื่อง (nearest-neighbor, chained)
# ============================================================

def plan_full_mission():
    """
    ไล่หาหินก้อนที่ใกล้ตำแหน่งปัจจุบันที่สุดทีละก้อน (เฉพาะก้อนที่มีวงกลม
    สีเดียวกันรออยู่) → หาเส้นทางไปหยิบ → หาเส้นทางไปวางที่วงกลม →
    ใช้ตำแหน่งวางเป็นจุดเริ่มของก้อนถัดไป ทำซ้ำจนกว่าหินจะหมดหรือหา
    เส้นทางต่อไม่ได้แล้ว

    คืนค่า list ของ mission dict:
      order, stone, pickup_path, pickup_commands, pickup_park,
      place_path, place_commands, place_park, circle
    """

    cx, cy = robot_x, robot_y
    cdir = robot_direction

    pending = [s for s in stones if not s["picked"] and s["color"] in circles_by_color]

    # ใช้ set นี้เก็บ id ของก้อนที่ "วางแผนไว้แล้วว่าจะเก็บก่อนหน้า" ใน mission
    # เดียวกัน (ไม่แตะ stone["picked"] จริง เพราะ field นั้นสงวนไว้สำหรับ
    # สถานะแสดงผลจริงตอนรันแอนิเมชันเท่านั้น ไม่ใช่ตอนวางแผน)
    planned_ids = set()

    result = []
    order = 1

    while pending:

        pending.sort(key=lambda s: math.hypot(s["x"] - cx, s["y"] - cy))

        picked_this_round = False

        for stone in pending:

            # ---------- ขา 1: ไปหยิบหิน ----------

            stone_parks = get_parking_candidates(
                stone["x"], stone["y"], stone["radius"] + STONE_MARGIN
            )
            preferred = get_preferred_side(cx, cy, stone["x"], stone["y"])
            ordered_parks = order_by_preferred(stone_parks, preferred)

            pickup_path = None
            pickup_park = None

            for park in ordered_parks:
                path = astar(
                    (cx, cy), (park["x"], park["y"]),
                    ignore_stone_id=stone["id"], extra_ignore_ids=planned_ids,
                )
                if path is not None:
                    pickup_path = path
                    pickup_park = park
                    break

            if pickup_path is None:
                continue  # ก้อนนี้ไปไม่ถึง ลองก้อนถัดไปที่ใกล้รองลงมา

            # ---------- ขา 2: จากจุดหยิบไปวางที่วงกลม ----------

            circle = circles_by_color[stone["color"]]
            circle_parks = get_parking_candidates(circle["x"], circle["y"], circle["radius"])
            preferred2 = get_preferred_side(pickup_park["x"], pickup_park["y"], circle["x"], circle["y"])
            ordered_circle_parks = order_by_preferred(circle_parks, preferred2)

            place_path = None
            place_park = None

            for park in ordered_circle_parks:
                # หินก้อนนี้ถูก "หยิบขึ้นรถ" แล้ว จึงไม่ใช่สิ่งกีดขวางอีกต่อไป
                path = astar(
                    (pickup_park["x"], pickup_park["y"]),
                    (park["x"], park["y"]),
                    ignore_stone_id=stone["id"], extra_ignore_ids=planned_ids,
                )
                if path is not None:
                    place_path = path
                    place_park = park
                    break

            if place_path is None:
                continue  # วางไม่ได้ ลองก้อนถัดไป

            # ---------- สำเร็จ: บันทึก mission นี้ ----------

            simplified_pickup = simplify_path(pickup_path)
            pickup_commands = path_to_commands(simplified_pickup, cdir, pickup_park["direction"])

            simplified_place = simplify_path(place_path)
            place_commands = path_to_commands(
                simplified_place, pickup_park["direction"], place_park["direction"]
            )

            result.append({
                "order": order,
                "stone": stone,
                "pickup_path": simplified_pickup,
                "pickup_commands": pickup_commands,
                "pickup_park": pickup_park,
                "place_path": simplified_place,
                "place_commands": place_commands,
                "place_park": place_park,
                "circle": circle,
            })

            order += 1
            cx, cy = place_park["x"], place_park["y"]
            cdir = place_park["direction"]

            # หมายเหตุ: ไม่ตั้ง stone["picked"] ตรงนี้ — จะตั้งค่าจริงตอน
            # แอนิเมชันรันถึงก้อนนี้เท่านั้น (ดู reveal_mission_step) เพื่อให้
            # การถมดำบนแผนที่ตรงกับสถานะจริงที่รถเก็บไปแล้วเท่านั้น
            planned_ids.add(stone["id"])
            pending.remove(stone)
            picked_this_round = True
            break

        if not picked_this_round:
            # เหลือหินที่หาเส้นทางไม่ได้เลยสักก้อน → หยุด
            break

    return result


# ============================================================
# แสดงผลทีละก้อน ห่างกันก้อนละ 1 วินาที (STEP_DELAY_MS)
# ============================================================

def animate_along_path(path, end_direction, duration_ms, on_complete):
    """
    เคลื่อนหุ่นยนต์ไปตาม path (จุดเลี้ยวแบบ simplify_path) อย่างต่อเนื่อง
    ทีละเฟรม แทนที่จะ 'กระโดด' ไปจุดหมายทันที เพื่อให้เห็นว่ารถเดินทาง
    ต่อจากจุดล่าสุดไปหาจุดหมายจริง ๆ
    """
    global robot_x, robot_y, robot_direction, route_path

    route_path = path
    redraw()

    if not path or len(path) < 2:
        robot_direction = end_direction
        update_direction()
        redraw()
        root.after(50, on_complete)
        return

    segment_lengths = []
    total_length = 0.0
    for i in range(len(path) - 1):
        x1, y1 = path[i]
        x2, y2 = path[i + 1]
        length = math.hypot(x2 - x1, y2 - y1)
        segment_lengths.append(length)
        total_length += length

    if total_length == 0:
        robot_x, robot_y = path[-1]
        robot_direction = end_direction
        update_direction()
        redraw()
        root.after(50, on_complete)
        return

    steps = max(8, min(40, int(total_length / 12)))
    frame_delay = max(10, duration_ms // steps)

    def step(frame_index):
        global robot_x, robot_y, robot_direction

        if frame_index >= steps:
            robot_x, robot_y = path[-1]
            robot_direction = end_direction
            update_direction()
            redraw()
            on_complete()
            return

        target_dist = total_length * (frame_index + 1) / steps

        accumulated = 0.0
        px, py = path[0]
        seg_dir = robot_direction

        for i, seg_len in enumerate(segment_lengths):
            if accumulated + seg_len >= target_dist or i == len(segment_lengths) - 1:
                x1, y1 = path[i]
                x2, y2 = path[i + 1]
                if seg_len == 0:
                    px, py = x2, y2
                else:
                    remain = target_dist - accumulated
                    ratio = min(1.0, remain / seg_len)
                    px = x1 + (x2 - x1) * ratio
                    py = y1 + (y2 - y1) * ratio
                seg_dir = get_move_direction((x1, y1), (x2, y2))
                break
            accumulated += seg_len

        robot_x, robot_y = px, py
        robot_direction = seg_dir
        update_direction()
        redraw()

        root.after(frame_delay, step, frame_index + 1)

    step(0)


def reveal_mission_step(plan, index):
    global mission_running, target_stone_id

    if index >= len(plan):
        mission_running = False
        target_stone_id = None
        status_label.config(
            text=f"✅ ภารกิจเสร็จสิ้น ({len(plan)} ก้อน)", fg="#00ff88"
        )
        redraw()
        return

    mission = plan[index]
    stone = mission["stone"]
    circle = mission["circle"]

    target_stone_id = stone["id"]

    header = f"=== หินก้อนที่ {mission['order']} (สี {stone['color']}) ==="
    pickup_header = f"[ไปหยิบหิน] จอดด้าน {mission['pickup_park']['side']}"
    pickup_lines = [f"  {i:02d}. {c}" for i, c in enumerate(mission["pickup_commands"], 1)]

    print(header)
    print(pickup_header)
    for line in pickup_lines:
        print(line)

    result_text.insert(tk.END, header + "\n" + pickup_header + "\n")
    for line in pickup_lines:
        result_text.insert(tk.END, line + "\n")
    result_text.see(tk.END)

    status_label.config(
        text=f"🤖 กำลังไปหยิบก้อนที่ {mission['order']}/{len(plan)} ({stone['color']})",
        fg="#00ff88",
    )

    redraw()

    def after_pickup():
        # ถึงจุดหยิบแล้ว -> ทำเครื่องหมายว่าเก็บแล้ว (ถมดำที่ตำแหน่งเดิม)
        stone["picked"] = True

        pick_line = "  >> 🤏 หยิบหิน"
        print(pick_line)
        result_text.insert(tk.END, pick_line + "\n")
        result_text.see(tk.END)
        redraw()

        place_header = f"[ไปวางที่วงกลม {circle['color']}] จอดด้าน {mission['place_park']['side']}"
        place_lines = [f"  {i:02d}. {c}" for i, c in enumerate(mission["place_commands"], 1)]

        print(place_header)
        for line in place_lines:
            print(line)

        result_text.insert(tk.END, place_header + "\n")
        for line in place_lines:
            result_text.insert(tk.END, line + "\n")
        result_text.see(tk.END)

        status_label.config(
            text=f"🤖 กำลังไปวางก้อนที่ {mission['order']}/{len(plan)} ({stone['color']})",
            fg="#00ff88",
        )

        def after_place():
            global target_stone_id
            collected_count[stone["color"]] = collected_count.get(stone["color"], 0) + 1
            target_stone_id = None

            place_line = "  >> 📦 วางหิน\n"
            print(place_line)
            result_text.insert(tk.END, "  >> 📦 วางหิน\n\n")
            result_text.see(tk.END)
            redraw()

            root.after(max(150, STEP_DELAY_MS // 3), reveal_mission_step, plan, index + 1)

        animate_along_path(
            mission["place_path"], mission["place_park"]["direction"],
            STEP_DELAY_MS, after_place,
        )

    animate_along_path(
        mission["pickup_path"], mission["pickup_park"]["direction"],
        STEP_DELAY_MS, after_pickup,
    )


# ============================================================
# MOUSE EVENTS
# ============================================================

def mouse_down(event):
    global placing_robot, dragging_robot, robot_x, robot_y, robot_exists
    global route_path, missions

    x, y = canvas_to_world(event.x, event.y)

    if placing_robot:
        robot_x, robot_y = x, y
        robot_exists = True
        placing_robot = False
        route_path = []
        missions = []

        start_position_label.config(text=f"X = {x:.0f}\nY = {y:.0f}")
        status_label.config(text="✅ กำหนดรถแล้ว\nลากรถเพื่อขยับได้", fg="#00ff88")
        redraw()
        return

    # คลิกโดนรถ -> ลากขยับ
    dx = x - robot_x
    dy = y - robot_y
    if robot_exists and math.hypot(dx, dy) <= robot_bounding_radius():
        dragging_robot = True


def mouse_drag(event):
    global robot_x, robot_y, route_path, missions

    if not dragging_robot:
        return

    x, y = canvas_to_world(event.x, event.y)
    robot_x, robot_y = x, y
    route_path = []
    missions = []
    start_position_label.config(text=f"X = {x:.0f}\nY = {y:.0f}")
    redraw()


def mouse_up(event):
    global dragging_robot
    dragging_robot = False


canvas.bind("<ButtonPress-1>", mouse_down)
canvas.bind("<B1-Motion>", mouse_drag)
canvas.bind("<ButtonRelease-1>", mouse_up)

root.bind("<Left>", lambda e: rotate_left())
root.bind("<Right>", lambda e: rotate_right())


def on_resize(event):
    if current_frame_bgr is not None:
        update_video_frame(current_frame_bgr)
    redraw()


root.bind("<Configure>", on_resize)


# ============================================================
# REAL-TIME LOOPS: วิดีโอ (เร็ว) + ตรวจจับสี/วงกลม/หิน (ช้ากว่า)
# ============================================================

def video_loop():
    """ดึงเฟรมจากกล้องแล้วอัปเดตภาพพื้นหลังบนแคนวาสให้สดตลอดเวลา"""
    global current_frame_bgr

    if cap is not None and cap.isOpened():
        ok, frame = cap.read()
        if ok and frame is not None:
            current_frame_bgr = frame
            update_video_frame(frame)
            redraw()

    root.after(FRAME_INTERVAL_MS, video_loop)


def detection_loop():
    """รันตรวจจับวงกลม/หินซ้ำเป็นระยะ — หยุดชั่วคราวระหว่างที่ภารกิจ
    กำลังทำงานอยู่ เพื่อไม่ให้ตำแหน่งเป้าหมายขยับกลางทาง"""

    if not mission_running:
        run_detection()
        detect_info_label.config(
            text=f"ตรวจพบหิน {len(stones)} ก้อน / วงกลม {len(circles)} จุด (สด)"
        )
        redraw()

    root.after(DETECT_INTERVAL_MS, detection_loop)


def on_close():
    global cap
    if cap is not None:
        cap.release()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)


# ============================================================
# START
# ============================================================

update_direction()
root.after(100, video_loop)
root.after(300, detection_loop)

root.mainloop()