import cv2
import math
import requests
import tkinter as tk
from tkinter import messagebox
import threading
import time


# =========================================================
# SETTINGS
# =========================================================

CAMERA_INDEX = 1

ARUCO_ID = 67

ESP32_IP = "10.126.248.22"
ROBOT_CODE = "1234"

ESP32_URL = f"http://{ESP32_IP}/command"

HTTP_TIMEOUT = 0.3

# ---------------------------------------------------------
# ระยะ
# 261 pixel = 21 cm
# ---------------------------------------------------------

PIXEL_TO_CM = 21.0 / 261.0

# ถือว่าถึง Target เมื่อห่างไม่เกิน 21 cm
STOP_DISTANCE_CM = 21.0

# ---------------------------------------------------------
# มุม
# ---------------------------------------------------------

ANGLE_TOLERANCE = 10.0

# ---------------------------------------------------------
# ความเร็ว
# ---------------------------------------------------------

MOTOR_SPEED = 255


# =========================================================
# GLOBAL
# =========================================================

cap = None

camera_running = False

connected = False

target = None

robot_x = None
robot_y = None
robot_angle = None

current_command = "STOP"

last_command = ""

last_send_time = 0

COMMAND_INTERVAL = 0.1


# =========================================================
# ARUCO
# =========================================================

aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

aruco_parameters = cv2.aruco.DetectorParameters()

aruco_detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    aruco_parameters
)


# =========================================================
# NORMALIZE ANGLE
# =========================================================

def normalize_angle(angle):

    while angle > 180:
        angle -= 360

    while angle < -180:
        angle += 360

    return angle


# =========================================================
# CALCULATE ROBOT ANGLE
# =========================================================

def calculate_robot_angle(corners):

    top_left = corners[0]
    top_right = corners[1]

    dx = top_right[0] - top_left[0]
    dy = top_right[1] - top_left[1]

    angle = math.degrees(
        math.atan2(dy, dx)
    )

    return angle


# =========================================================
# CALCULATE COMMAND
# =========================================================

def calculate_command():

    if (
        robot_x is None or
        robot_y is None or
        robot_angle is None or
        target is None
    ):
        return "STOP", 0, 0, 0


    tx, ty = target


    # -----------------------------------------------------
    # Vector จาก Robot -> Target
    # -----------------------------------------------------

    dx = tx - robot_x
    dy = ty - robot_y


    # -----------------------------------------------------
    # Distance
    # -----------------------------------------------------

    distance_px = math.sqrt(
        dx * dx +
        dy * dy
    )

    distance_cm = (
        distance_px *
        PIXEL_TO_CM
    )


    # -----------------------------------------------------
    # ถึง Target แล้ว
    # -----------------------------------------------------

    if distance_cm <= STOP_DISTANCE_CM:

        return "STOP", distance_px, distance_cm, 0


    # -----------------------------------------------------
    # มุมที่ต้องหันไปหา Target
    # -----------------------------------------------------

    target_angle = math.degrees(
        math.atan2(dy, dx)
    )


    # -----------------------------------------------------
    # ความต่างของมุม
    # -----------------------------------------------------

    angle_error = normalize_angle(
        target_angle - robot_angle
    )


    # -----------------------------------------------------
    # ถ้ามุมยังไม่ตรง
    # -----------------------------------------------------

    if angle_error < -ANGLE_TOLERANCE:

        return (
            "LEFT",
            distance_px,
            distance_cm,
            angle_error
        )


    if angle_error > ANGLE_TOLERANCE:

        return (
            "RIGHT",
            distance_px,
            distance_cm,
            angle_error
        )


    # -----------------------------------------------------
    # มุมตรงแล้ว -> เดินหน้า
    # -----------------------------------------------------

    return (
        "FORWARD",
        distance_px,
        distance_cm,
        angle_error
    )


# =========================================================
# SEND COMMAND TO ESP32
# =========================================================

def send_command(command):

    global last_command
    global last_send_time


    current_time = time.time()


    # ไม่ต้องส่งซ้ำเร็วเกินไป
    if current_time - last_send_time < COMMAND_INTERVAL:
        return


    # ถ้าคำสั่งเดิม ไม่ต้องส่งซ้ำ
    if command == last_command:
        return


    last_command = command

    last_send_time = current_time


    params = {

        "code": ROBOT_CODE,

        "command": command,

        "speed": MOTOR_SPEED

    }


    try:

        response = requests.get(
            ESP32_URL,
            params=params,
            timeout=HTTP_TIMEOUT
        )


        print(
            "SEND:",
            command,
            "|",
            response.status_code,
            "|",
            response.text
        )


    except Exception as e:

        print(
            "SEND ERROR:",
            e
        )


# =========================================================
# MOUSE
# =========================================================

def mouse_callback(event, x, y, flags, param):

    global target

    if event == cv2.EVENT_LBUTTONDOWN:

        target = (x, y)

        print()
        print("==============================")
        print("TARGET SET")
        print("X:", x)
        print("Y:", y)
        print("==============================")


# =========================================================
# CAMERA
# =========================================================

def update_camera():

    global cap
    global camera_running
    global robot_x
    global robot_y
    global robot_angle
    global current_command
    global target


    if not camera_running:
        return


    if cap is None:
        return


    ret, frame = cap.read()


    if not ret:

        print("Camera read error")

        root.after(
            30,
            update_camera
        )

        return


    # =====================================================
    # ARUCO
    # =====================================================

    corners, ids, rejected = aruco_detector.detectMarkers(
        frame
    )


    robot_found = False


    if ids is not None and len(ids) > 0:

        ids_flat = ids.flatten()


        for i in range(len(ids_flat)):

            marker_id = int(
                ids_flat[i]
            )


            if marker_id != ARUCO_ID:
                continue


            marker_corners = corners[i][0]


            # -------------------------------------------------
            # Center
            # -------------------------------------------------

            robot_x = int(
                sum(
                    point[0]
                    for point in marker_corners
                ) / 4
            )


            robot_y = int(
                sum(
                    point[1]
                    for point in marker_corners
                ) / 4
            )


            # -------------------------------------------------
            # Angle
            # -------------------------------------------------

            robot_angle = calculate_robot_angle(
                marker_corners
            )


            robot_found = True


            # -------------------------------------------------
            # Draw marker
            # -------------------------------------------------

            cv2.polylines(
                frame,
                [
                    marker_corners.astype(
                        "int32"
                    )
                ],
                True,
                (0, 255, 0),
                3
            )


            # -------------------------------------------------
            # Center
            # -------------------------------------------------

            cv2.circle(
                frame,
                (robot_x, robot_y),
                6,
                (0, 255, 0),
                -1
            )


            # -------------------------------------------------
            # Direction
            # -------------------------------------------------

            length = 60

            angle_rad = math.radians(
                robot_angle
            )


            end_x = int(
                robot_x +
                math.cos(angle_rad) *
                length
            )


            end_y = int(
                robot_y +
                math.sin(angle_rad) *
                length
            )


            cv2.arrowedLine(
                frame,
                (robot_x, robot_y),
                (end_x, end_y),
                (0, 255, 0),
                3,
                tipLength=0.25
            )


            # -------------------------------------------------
            # Robot info
            # -------------------------------------------------

            cv2.putText(
                frame,
                f"ROBOT ID: {marker_id}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            cv2.putText(
                frame,
                f"X: {robot_x}",
                (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )


            cv2.putText(
                frame,
                f"Y: {robot_y}",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )


            cv2.putText(
                frame,
                f"ANGLE: {robot_angle:.1f}",
                (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )


            break


    # =====================================================
    # CALCULATE COMMAND
    # =====================================================

    if robot_found and target is not None:

        (
            command,
            distance_px,
            distance_cm,
            angle_error
        ) = calculate_command()


        current_command = command


        # -------------------------------------------------
        # Send command
        # -------------------------------------------------

        send_command(
            command
        )


        tx, ty = target


        # -------------------------------------------------
        # Target
        # -------------------------------------------------

        cv2.circle(
            frame,
            (tx, ty),
            10,
            (0, 0, 255),
            -1
        )


        cv2.circle(
            frame,
            (tx, ty),
            18,
            (0, 0, 255),
            2
        )


        # -------------------------------------------------
        # Line
        # -------------------------------------------------

        cv2.line(
            frame,
            (robot_x, robot_y),
            (tx, ty),
            (255, 0, 0),
            2
        )


        # -------------------------------------------------
        # Distance
        # -------------------------------------------------

        cv2.putText(
            frame,
            f"DIST: {distance_px:.1f}px",
            (20, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            f"DIST: {distance_cm:.1f}cm",
            (20, 200),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # -------------------------------------------------
        # Target angle
        # -------------------------------------------------

        target_angle = math.degrees(
            math.atan2(
                ty - robot_y,
                tx - robot_x
            )
        )


        cv2.putText(
            frame,
            f"TARGET ANGLE: {target_angle:.1f}",
            (20, 235),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )


        # -------------------------------------------------
        # Angle error
        # -------------------------------------------------

        cv2.putText(
            frame,
            f"ANGLE ERROR: {angle_error:.1f}",
            (20, 265),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )


        # -------------------------------------------------
        # Command
        # -------------------------------------------------

        cv2.putText(
            frame,
            f"COMMAND: {command}",
            (20, 305),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2
        )


    else:

        current_command = "STOP"

        send_command(
            "STOP"
        )


        cv2.putText(
            frame,
            "CLICK TO SET TARGET",
            (20, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )


    # =====================================================
    # ESP32 STATUS
    # =====================================================

    if connected:

        cv2.putText(
            frame,
            "ESP32: CONNECTED",
            (20, frame.shape[0] - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )


    # =====================================================
    # SHOW
    # =====================================================

    cv2.imshow(
        "Robot Camera",
        frame
    )


    cv2.setMouseCallback(
        "Robot Camera",
        mouse_callback
    )


    # =====================================================
    # KEYBOARD
    # =====================================================

    key = cv2.waitKey(1) & 0xFF


    if key == ord("r"):

        target = None

        current_command = "STOP"

        send_command(
            "STOP"
        )

        print(
            "TARGET CLEARED"
        )


    if key == 27:

        disconnect_camera()

        return


    root.after(
        10,
        update_camera
    )


# =========================================================
# CONNECT ESP32
# =========================================================

def connect_esp32():

    global connected
    global camera_running
    global cap
    global target
    global robot_x
    global robot_y
    global robot_angle
    global last_command


    try:

        status_label.config(
            text="CONNECTING...",
            fg="orange"
        )

        root.update()


        url = f"http://{ESP32_IP}/"


        print()
        print("==============================")
        print("CONNECTING ESP32")
        print("==============================")


        response = requests.get(
            url,
            timeout=5
        )


        print(
            "STATUS:",
            response.status_code
        )


        print(
            "RESPONSE:",
            response.text
        )


        if response.status_code != 200:

            raise Exception(
                f"HTTP {response.status_code}"
            )


        connected = True


        status_label.config(
            text="ESP32 CONNECTED",
            fg="green"
        )


        print(
            "ESP32 CONNECTED"
        )


        # =================================================
        # CAMERA
        # =================================================

        cap = cv2.VideoCapture(
            CAMERA_INDEX
        )


        if not cap.isOpened():

            connected = False

            raise Exception(
                "เปิดกล้องไม่ได้"
            )


        cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            1280
        )

        cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            720
        )


        # =================================================
        # RESET
        # =================================================

        target = None

        robot_x = None
        robot_y = None
        robot_angle = None

        last_command = ""


        # =================================================
        # START
        # =================================================

        camera_running = True


        update_camera()


    except Exception as e:

        connected = False

        camera_running = False


        status_label.config(
            text="ERROR",
            fg="red"
        )


        print()
        print("==============================")
        print("ERROR")
        print("==============================")

        print(e)


        messagebox.showerror(
            "Error",
            str(e)
        )


# =========================================================
# DISCONNECT
# =========================================================

def disconnect_camera():

    global camera_running
    global connected
    global cap
    global target
    global last_command


    # -----------------------------------------------------
    # STOP ROBOT
    # -----------------------------------------------------

    if connected:

        try:

            requests.get(
                ESP32_URL,
                params={
                    "code": ROBOT_CODE,
                    "command": "STOP",
                    "speed": 0
                },
                timeout=1
            )

        except:
            pass


    camera_running = False

    connected = False

    target = None

    last_command = ""


    if cap is not None:

        cap.release()

        cap = None


    cv2.destroyAllWindows()


    status_label.config(
        text="DISCONNECTED",
        fg="red"
    )


# =========================================================
# CLEAR TARGET
# =========================================================

def clear_target():

    global target
    global last_command


    target = None

    last_command = ""


    send_command(
        "STOP"
    )


    print(
        "TARGET CLEARED"
    )


# =========================================================
# CLOSE
# =========================================================

def close_program():

    disconnect_camera()

    root.destroy()


# =========================================================
# GUI
# =========================================================

root = tk.Tk()

root.title(
    "Robot Control"
)

root.geometry(
    "500x350"
)

root.resizable(
    False,
    False
)


title_label = tk.Label(
    root,
    text="ROBOT CONTROL",
    font=("Arial", 24, "bold")
)

title_label.pack(
    pady=25
)


ip_label = tk.Label(
    root,
    text=f"ESP32 IP: {ESP32_IP}",
    font=("Arial", 12)
)

ip_label.pack(
    pady=5
)


status_label = tk.Label(
    root,
    text="DISCONNECTED",
    fg="red",
    font=("Arial", 14, "bold")
)

status_label.pack(
    pady=15
)


connect_button = tk.Button(
    root,
    text="CONNECT ESP32",
    font=("Arial", 14, "bold"),
    width=20,
    height=2,
    command=connect_esp32
)

connect_button.pack(
    pady=10
)


clear_button = tk.Button(
    root,
    text="CLEAR TARGET",
    font=("Arial", 12),
    width=20,
    command=clear_target
)

clear_button.pack(
    pady=5
)


info_label = tk.Label(
    root,
    text=(
        "1. Connect ESP32\n"
        "2. Camera detects ArUco ID 67\n"
        "3. Click target\n"
        "4. Python calculates direction\n"
        "5. ESP32 moves\n"
        "6. Python checks position again\n"
        "7. STOP when target is reached"
    ),
    font=("Arial", 10),
    justify="left"
)

info_label.pack(
    pady=15
)


root.protocol(
    "WM_DELETE_WINDOW",
    close_program
)


root.mainloop()