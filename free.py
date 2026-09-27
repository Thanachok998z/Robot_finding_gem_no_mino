from pathlib import Path

import cv2
import math
import mediapipe as mp
import tkinter as tk

from tkinter import messagebox
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from PIL import Image, ImageTk

import requests
import threading
import time
import queue


# =========================================================
# SETTINGS
# =========================================================

MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")

NUM_HANDS = 2

WINDOW_W = 1280
WINDOW_H = 720

CAMERA_INDEX = 0

# ESP32 WebServer
ESP_PORT = 80

# ต้องตรงกับ Arduino
ROBOT_CODE = "1234"


# =========================================================
# MOTOR SPEED
# =========================================================

SPEED_LEFT = 200
SPEED_RIGHT = 200

# หมุนซ้าย
TURN_LEFT_LEFT = 80
TURN_LEFT_RIGHT = 180

# หมุนขวา
TURN_RIGHT_LEFT = 180
TURN_RIGHT_RIGHT = 80


# =========================================================
# COLORS
# =========================================================

BG_COLOR = "#eef1f5"
LEFT_PANEL = "#cbd3dc"
RIGHT_PANEL = "#ffffff"
CAMERA_BG = "#536ff0"
TEXT_COLOR = "#111111"
GRAY = "#d9d9d9"
ORANGE = "#ffbd59"
GREEN = "#10b981"
RED = "#ef4444"
BLUE = "#4f6ff5"


# =========================================================
# COMMAND
# =========================================================

CMD_STOP = 0
CMD_LEFT = 1
CMD_RIGHT = 2
CMD_FORWARD = 3
CMD_BACKWARD = 4

CMD_GRAB = 5
CMD_DROP = 6

CMD_SERVO_180 = 7
CMD_SERVO_0 = 8


# =========================================================
# DISTANCE
# =========================================================

def distance(a, b):

    return math.sqrt(
        (a.x - b.x) ** 2 +
        (a.y - b.y) ** 2
    )


# =========================================================
# ANGLE
# =========================================================

def angle(a, b, c):

    ba_x = a.x - b.x
    ba_y = a.y - b.y

    bc_x = c.x - b.x
    bc_y = c.y - b.y

    dot = (
        ba_x * bc_x +
        ba_y * bc_y
    )

    mag_ba = math.sqrt(
        ba_x ** 2 +
        ba_y ** 2
    )

    mag_bc = math.sqrt(
        bc_x ** 2 +
        bc_y ** 2
    )

    if mag_ba == 0 or mag_bc == 0:
        return 0

    cos_value = dot / (
        mag_ba * mag_bc
    )

    cos_value = max(
        -1,
        min(1, cos_value)
    )

    return math.degrees(
        math.acos(cos_value)
    )


# =========================================================
# CHECK FINGER
# =========================================================

def is_finger_extended(
    landmarks,
    mcp,
    pip,
    dip,
    tip
):

    finger_angle = angle(
        landmarks[mcp],
        landmarks[pip],
        landmarks[dip]
    )

    tip_distance = distance(
        landmarks[mcp],
        landmarks[tip]
    )

    pip_distance = distance(
        landmarks[mcp],
        landmarks[pip]
    )

    return (
        finger_angle > 155
        and
        tip_distance > pip_distance * 1.15
    )


# =========================================================
# COUNT FINGERS
# =========================================================

def count_fingers(
    landmarks,
    handedness
):

    count = 0

    # =====================================================
    # THUMB
    # =====================================================

    thumb_angle = angle(
        landmarks[2],
        landmarks[3],
        landmarks[4]
    )

    thumb_length = distance(
        landmarks[2],
        landmarks[4]
    )

    thumb_base = distance(
        landmarks[2],
        landmarks[5]
    )

    if (
        thumb_angle > 145
        and
        thumb_length > thumb_base * 0.8
    ):

        count += 1


    # =====================================================
    # INDEX
    # =====================================================

    if is_finger_extended(
        landmarks,
        5,
        6,
        7,
        8
    ):

        count += 1


    # =====================================================
    # MIDDLE
    # =====================================================

    if is_finger_extended(
        landmarks,
        9,
        10,
        11,
        12
    ):

        count += 1


    # =====================================================
    # RING
    # =====================================================

    if is_finger_extended(
        landmarks,
        13,
        14,
        15,
        16
    ):

        count += 1


    # =====================================================
    # PINKY
    # =====================================================

    if is_finger_extended(
        landmarks,
        17,
        18,
        19,
        20
    ):

        count += 1

    return count


# =========================================================
# DRAW HAND
# =========================================================

def draw_hand(
    frame,
    landmarks,
    connections
):

    height, width = frame.shape[:2]

    points = [
        (
            int(landmark.x * width),
            int(landmark.y * height)
        )
        for landmark in landmarks
    ]

    # -----------------------------------------------------
    # CONNECTIONS
    # -----------------------------------------------------

    for start, end in connections:

        cv2.line(
            frame,
            points[start],
            points[end],
            (255, 0, 0),
            2
        )

    # -----------------------------------------------------
    # LANDMARKS
    # -----------------------------------------------------

    for point in points:

        cv2.circle(
            frame,
            point,
            5,
            (0, 255, 0),
            -1
        )


# =========================================================
# RIGHT HAND COMMAND
# =========================================================

def right_hand_command(fingers):

    if fingers == 1:
        return "LEFT"

    elif fingers == 2:
        return "RIGHT"

    elif fingers == 3:
        return "FORWARD"

    elif fingers == 4:
        return "BACKWARD"

    return "STOP"


# =========================================================
# LEFT HAND COMMAND
# =========================================================

def left_hand_command(fingers):

    if 0 <= fingers <= 3:
        return "GRAB"

    elif 4 <= fingers <= 5:
        return "DROP"

    return "STOP"


# =========================================================
# MAIN APP
# =========================================================

class RobotGestureApp:

    def __init__(self, root):

        self.root = root

        # -------------------------------------------------
        # RUNNING
        # -------------------------------------------------

        self.running = True

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        self.camera_index = CAMERA_INDEX

        self.cap = cv2.VideoCapture(
            self.camera_index
        )

        if not self.cap.isOpened():

            raise RuntimeError(
                "ไม่สามารถเปิดกล้องได้"
            )

        # -------------------------------------------------
        # ESP
        # -------------------------------------------------

        self.esp_ip = ""

        self.esp_connected = False

        self.http_lock = threading.Lock()

        # -------------------------------------------------
        # COMMAND
        # -------------------------------------------------

        self.current_command = None

        self.last_sent_command = None

        # -------------------------------------------------
        # QUEUE
        # -------------------------------------------------

        self.command_queue = queue.Queue(
            maxsize=1
        )

        self.command_worker = threading.Thread(
            target=self.command_worker_loop,
            daemon=True
        )

        self.command_worker.start()

        # -------------------------------------------------
        # HISTORY
        # -------------------------------------------------

        self.history = []

        # -------------------------------------------------
        # UI
        # -------------------------------------------------

        self.create_window()

        # -------------------------------------------------
        # MEDIAPIPE
        # -------------------------------------------------

        self.setup_mediapipe()

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        self.update_camera()


    # =====================================================
    # WINDOW
    # =====================================================

    def create_window(self):

        self.root.title(
            "Robot Gesture Control"
        )

        self.root.geometry(
            f"{WINDOW_W}x{WINDOW_H}"
        )

        self.root.configure(
            bg=BG_COLOR
        )

        self.root.resizable(
            False,
            False
        )

        # -------------------------------------------------
        # CENTER
        # -------------------------------------------------

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        center_x = int(
            (screen_w - WINDOW_W) / 2
        )

        center_y = int(
            (screen_h - WINDOW_H) / 2
        )

        self.root.geometry(
            f"{WINDOW_W}x{WINDOW_H}+"
            f"{center_x}+{center_y}"
        )

        # -------------------------------------------------
        # MAIN
        # -------------------------------------------------

        self.main_frame = tk.Frame(
            self.root,
            bg=BG_COLOR
        )

        self.main_frame.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=25
        )

        # -------------------------------------------------
        # LEFT
        # -------------------------------------------------

        self.left_frame = tk.Frame(
            self.main_frame,
            bg=LEFT_PANEL,
            width=700,
            height=620
        )

        self.left_frame.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.left_frame.pack_propagate(
            False
        )

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        self.camera_label = tk.Label(
            self.left_frame,
            bg=CAMERA_BG
        )

        self.camera_label.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=30
        )

        # -------------------------------------------------
        # RIGHT
        # -------------------------------------------------

        self.right_frame = tk.Frame(
            self.main_frame,
            bg=RIGHT_PANEL,
            width=480,
            height=620
        )

        self.right_frame.pack(
            side="right",
            fill="y"
        )

        self.right_frame.pack_propagate(
            False
        )

        self.create_right_panel()


    # =====================================================
    # RIGHT PANEL
    # =====================================================

    def create_right_panel(self):

        title = tk.Label(
            self.right_frame,
            text="connect ESP",
            font=("Tahoma", 25),
            bg=RIGHT_PANEL,
            fg=TEXT_COLOR,
            anchor="w"
        )

        title.pack(
            fill="x",
            padx=30,
            pady=(30, 12)
        )

        # =================================================
        # IP
        # =================================================

        self.ip_entry = tk.Entry(
            self.right_frame,
            font=("Tahoma", 15),
            bg=GRAY,
            fg="#555555",
            bd=0,
            relief="flat"
        )

        self.ip_entry.insert(
            0,
            "Input IP"
        )

        self.ip_entry.pack(
            fill="x",
            padx=30,
            ipady=9
        )

        self.ip_entry.bind(
            "<FocusIn>",
            self.clear_ip
        )

        self.ip_entry.bind(
            "<FocusOut>",
            self.restore_ip
        )

        # =================================================
        # CONNECT
        # =================================================

        self.connect_button = tk.Button(
            self.right_frame,
            text="CONNECT ESP",
            font=("Tahoma", 17, "bold"),
            bg=ORANGE,
            fg="black",
            activebackground="#e8a844",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.connect_esp
        )

        self.connect_button.pack(
            fill="x",
            padx=30,
            pady=15,
            ipady=6
        )

        # =================================================
        # SEND
        # =================================================

        self.send_button = tk.Button(
            self.right_frame,
            text="SEND : STOP",
            font=("Tahoma", 16, "bold"),
            bg=BLUE,
            fg="white",
            activebackground="#3d5de0",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.send_current_command
        )

        self.send_button.pack(
            fill="x",
            padx=30,
            pady=(0, 15),
            ipady=6
        )

        # =================================================
        # STATUS
        # =================================================

        self.status_label = tk.Label(
            self.right_frame,
            text="● DISCONNECTED",
            font=("Tahoma", 13, "bold"),
            bg=RIGHT_PANEL,
            fg=RED,
            anchor="w"
        )

        self.status_label.pack(
            fill="x",
            padx=30
        )

        # =================================================
        # CAMERA
        # =================================================

        camera_frame = tk.Frame(
            self.right_frame,
            bg=RIGHT_PANEL
        )

        camera_frame.pack(
            fill="x",
            padx=30,
            pady=(18, 5)
        )

        camera_title = tk.Label(
            camera_frame,
            text="Index Cam",
            font=("Tahoma", 19),
            bg=RIGHT_PANEL,
            fg=TEXT_COLOR
        )

        camera_title.pack(
            side="left"
        )

        minus_button = tk.Button(
            camera_frame,
            text="−",
            font=("Tahoma", 22, "bold"),
            bg=RIGHT_PANEL,
            bd=0,
            cursor="hand2",
            command=self.decrease_camera
        )

        minus_button.pack(
            side="left",
            padx=(30, 8)
        )

        self.camera_index_label = tk.Label(
            camera_frame,
            text=str(self.camera_index),
            font=("Tahoma", 16, "bold"),
            bg=GRAY,
            width=4
        )

        self.camera_index_label.pack(
            side="left"
        )

        plus_button = tk.Button(
            camera_frame,
            text="+",
            font=("Tahoma", 25, "bold"),
            bg=RIGHT_PANEL,
            bd=0,
            cursor="hand2",
            command=self.increase_camera
        )

        plus_button.pack(
            side="left",
            padx=8
        )

        # =================================================
        # COMMAND
        # =================================================

        self.command_label = tk.Label(
            self.right_frame,
            text="COMMAND: STOP",
            font=("Tahoma", 18, "bold"),
            bg=RIGHT_PANEL,
            fg=BLUE,
            anchor="w"
        )

        self.command_label.pack(
            fill="x",
            padx=30,
            pady=(10, 5)
        )

        # =================================================
        # HISTORY
        # =================================================

        history_title = tk.Label(
            self.right_frame,
            text="History",
            font=("Tahoma", 22),
            bg="#d8d8d8",
            fg=TEXT_COLOR,
            anchor="w"
        )

        history_title.pack(
            fill="x",
            padx=30,
            pady=(10, 0),
            ipady=8
        )

        self.history_box = tk.Listbox(
            self.right_frame,
            font=("Consolas", 11),
            bg="#d8d8d8",
            fg="#222222",
            bd=0,
            highlightthickness=0,
            activestyle="none"
        )

        self.history_box.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=(0, 25)
        )


    # =====================================================
    # IP
    # =====================================================

    def clear_ip(self, event):

        if self.ip_entry.get() == "Input IP":

            self.ip_entry.delete(
                0,
                tk.END
            )

            self.ip_entry.config(
                fg="black"
            )


    def restore_ip(self, event):

        if self.ip_entry.get() == "":

            self.ip_entry.insert(
                0,
                "Input IP"
            )

            self.ip_entry.config(
                fg="#555555"
            )


    # =====================================================
    # MEDIAPIPE
    # =====================================================

    def setup_mediapipe(self):

        if not MODEL_PATH.is_file():

            raise FileNotFoundError(
                f"ไม่พบไฟล์โมเดล:\n"
                f"{MODEL_PATH}"
            )

        options = vision.HandLandmarkerOptions(

            base_options=python.BaseOptions(
                model_asset_path=str(
                    MODEL_PATH
                )
            ),

            running_mode=vision.RunningMode.IMAGE,

            num_hands=NUM_HANDS,

            min_hand_detection_confidence=0.7,

            min_hand_presence_confidence=0.7,

            min_tracking_confidence=0.7
        )

        self.detector = (
            vision.HandLandmarker
            .create_from_options(
                options
            )
        )

        self.connections = [
            (
                connection.start,
                connection.end
            )
            for connection
            in vision.HandLandmarksConnections.HAND_CONNECTIONS
        ]


    # =====================================================
    # CONNECT ESP
    # =====================================================

    def connect_esp(self):

        ip = self.ip_entry.get().strip()

        if ip == "" or ip == "Input IP":

            messagebox.showwarning(
                "ESP32",
                "กรุณาใส่ IP ของ ESP32"
            )

            return

        self.esp_ip = ip

        self.connect_button.config(
            text="CONNECTING...",
            bg=ORANGE,
            state="disabled"
        )

        threading.Thread(
            target=self._connect_thread,
            daemon=True
        ).start()


    # =====================================================
    # CONNECTION THREAD
    # =====================================================

    def _connect_thread(self):

        try:

            url = (
                f"http://"
                f"{self.esp_ip}:"
                f"{ESP_PORT}/"
            )

            response = requests.get(
                url,
                timeout=3
            )

            print(
                "ESP RESPONSE:",
                response.text
            )

            if response.status_code == 200:

                self.esp_connected = True

                self.root.after(
                    0,
                    self.connection_success
                )

            else:

                raise Exception(
                    f"HTTP {response.status_code}"
                )

        except Exception as e:

            print(
                "ESP ERROR:",
                e
            )

            self.esp_connected = False

            self.root.after(
                0,
                self.connection_failed
            )


    # =====================================================
    # CONNECTION SUCCESS
    # =====================================================

    def connection_success(self):

        self.connect_button.config(
            text="CONNECTED",
            bg=GREEN,
            state="normal"
        )

        self.status_label.config(
            text="● CONNECTED",
            fg=GREEN
        )

        self.add_history(
            "ESP CONNECTED"
        )

        print(
            "ESP32 CONNECTED"
        )


    # =====================================================
    # CONNECTION FAILED
    # =====================================================

    def connection_failed(self):

        self.connect_button.config(
            text="CONNECT ESP",
            bg=ORANGE,
            state="normal"
        )

        self.status_label.config(
            text="● CONNECTION FAILED",
            fg=RED
        )

        messagebox.showerror(
            "ESP32",
            "ไม่สามารถเชื่อมต่อ ESP32 ได้\n\n"
            f"IP: {self.esp_ip}\n"
            f"PORT: {ESP_PORT}\n\n"
            "ตรวจสอบ Wi-Fi"
        )


    # =====================================================
    # COMMAND WORKER
    # =====================================================

    def command_worker_loop(self):

        while self.running:

            try:

                command = self.command_queue.get(
                    timeout=0.2
                )

            except queue.Empty:

                continue

            if command is None:

                break

            self.send_command(
                command
            )


    # =====================================================
    # QUEUE COMMAND
    # =====================================================

    def queue_command(self, command):

        # ลบ command เก่า
        try:

            while True:

                self.command_queue.get_nowait()

        except queue.Empty:

            pass

        try:

            self.command_queue.put_nowait(
                command
            )

        except queue.Full:

            pass


    # =====================================================
    # SEND COMMAND
    # =====================================================

    def send_command(self, command):

        if not self.esp_ip:

            print(
                "[ESP] ยังไม่ได้ใส่ IP"
            )

            return False

        command_map = {

            "STOP": CMD_STOP,

            "LEFT": CMD_LEFT,

            "RIGHT": CMD_RIGHT,

            "FORWARD": CMD_FORWARD,

            "BACKWARD": CMD_BACKWARD,

            "GRAB": CMD_GRAB,

            "DROP": CMD_DROP
        }

        if command not in command_map:

            print(
                "UNKNOWN COMMAND:",
                command
            )

            return False

        cmd = command_map[command]

        # =================================================
        # MOTOR SPEED
        # =================================================

        left_speed = 0
        right_speed = 0

        if command == "FORWARD":

            left_speed = SPEED_LEFT
            right_speed = SPEED_RIGHT

        elif command == "BACKWARD":

            left_speed = SPEED_LEFT
            right_speed = SPEED_RIGHT

        elif command == "LEFT":

            left_speed = TURN_LEFT_LEFT
            right_speed = TURN_LEFT_RIGHT

        elif command == "RIGHT":

            left_speed = TURN_RIGHT_LEFT
            right_speed = TURN_RIGHT_RIGHT

        elif command == "STOP":

            left_speed = 0
            right_speed = 0

        elif command == "GRAB":

            left_speed = 0
            right_speed = 0

        elif command == "DROP":

            left_speed = 0
            right_speed = 0

        # =================================================
        # URL
        # =================================================

        url = (
            f"http://"
            f"{self.esp_ip}:"
            f"{ESP_PORT}"
            f"/command"
        )

        params = {

            "code": ROBOT_CODE,

            "cmd": cmd,

            "left": left_speed,

            "right": right_speed
        }

        print(
            f"SEND: {command} "
            f"CMD:{cmd} "
            f"L:{left_speed} "
            f"R:{right_speed}"
        )

        try:

            with self.http_lock:

                response = requests.get(
                    url,
                    params=params,
                    timeout=1
                )

            print(
                "RESPONSE:",
                response.text
            )

            print(
                "HTTP:",
                response.status_code
            )

            if response.status_code == 200:

                self.esp_connected = True

                self.last_sent_command = command

                return True

            return False

        except Exception as e:

            print(
                "SEND ERROR:",
                e
            )

            self.esp_connected = False

            self.root.after(
                0,
                self.set_disconnected
            )

            return False


    # =====================================================
    # SERVO DIRECT
    # =====================================================

    def send_servo_command(self, angle):

        if not self.esp_ip:

            return False

        if angle == 180:

            cmd = CMD_SERVO_180

        else:

            cmd = CMD_SERVO_0

        url = (
            f"http://"
            f"{self.esp_ip}:"
            f"{ESP_PORT}"
            f"/command"
        )

        params = {

            "code": ROBOT_CODE,

            "cmd": cmd,

            "left": 0,

            "right": 0
        }

        try:

            response = requests.get(
                url,
                params=params,
                timeout=1
            )

            print(
                "SERVO:",
                angle,
                response.text
            )

            return response.status_code == 200

        except Exception as e:

            print(
                "SERVO ERROR:",
                e
            )

            return False


    # =====================================================
    # ROBOT COMMAND
    # =====================================================

    def robot_command(self, command):

        if command is None:

            command = "STOP"

        # ไม่ส่งซ้ำ
        if command == self.current_command:

            return

        self.current_command = command

        # -------------------------------------------------
        # UI
        # -------------------------------------------------

        self.root.after(
            0,
            lambda: self.command_label.config(
                text=f"COMMAND: {command}"
            )
        )

        self.root.after(
            0,
            lambda: self.send_button.config(
                text=f"SEND : {command}"
            )
        )

        print(
            "[GESTURE]",
            command
        )

        # -------------------------------------------------
        # QUEUE
        # -------------------------------------------------

        self.queue_command(
            command
        )


    # =====================================================
    # MANUAL SEND BUTTON
    # =====================================================

    def send_current_command(self):

        command = self.current_command

        if command is None:

            command = "STOP"

        self.queue_command(
            command
        )

        self.add_history(
            "MANUAL SEND: " + command
        )


    # =====================================================
    # HISTORY
    # =====================================================

    def add_history(self, text):

        current_time = time.strftime(
            "%H:%M:%S"
        )

        item = (
            f"[{current_time}] "
            f"{text}"
        )

        self.history.insert(
            0,
            item
        )

        if len(self.history) > 20:

            self.history.pop()

        self.history_box.delete(
            0,
            tk.END
        )

        for item in self.history:

            self.history_box.insert(
                tk.END,
                item
            )


    # =====================================================
    # DISCONNECTED
    # =====================================================

    def set_disconnected(self):

        self.esp_connected = False

        self.status_label.config(
            text="● DISCONNECTED",
            fg=RED
        )

        self.connect_button.config(
            text="CONNECT ESP",
            bg=ORANGE,
            state="normal"
        )


    # =====================================================
    # CAMERA
    # =====================================================

    def decrease_camera(self):

        if self.camera_index <= 0:

            return

        self.camera_index -= 1

        self.restart_camera()


    def increase_camera(self):

        self.camera_index += 1

        self.restart_camera()


    def restart_camera(self):

        if self.cap:

            self.cap.release()

        self.cap = cv2.VideoCapture(
            self.camera_index
        )

        self.camera_index_label.config(
            text=str(
                self.camera_index
            )
        )


    # =====================================================
    # CAMERA UPDATE
    # =====================================================

    def update_camera(self):

        if not self.running:

            return

        ret, frame = self.cap.read()

        if not ret:

            self.robot_command(
                "STOP"
            )

            self.root.after(
                30,
                self.update_camera
            )

            return

        # -------------------------------------------------
        # MIRROR
        # -------------------------------------------------

        frame = cv2.flip(
            frame,
            1
        )

        # -------------------------------------------------
        # RESIZE
        # -------------------------------------------------

        frame = cv2.resize(
            frame,
            (640, 560)
        )

        # -------------------------------------------------
        # RGB
        # -------------------------------------------------

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        # -------------------------------------------------
        # DETECT
        # -------------------------------------------------

        result = self.detector.detect(
            mp_image
        )

        left_fingers = None
        right_fingers = None

        left_command = "STOP"
        right_command = "STOP"

        # =================================================
        # HANDS
        # =================================================

        for landmarks, handednesses in zip(

            result.hand_landmarks,

            result.handedness

        ):

            draw_hand(
                frame,
                landmarks,
                self.connections
            )

            mp_hand = (
                handednesses[0]
                .category_name
            )

            # เพราะภาพ mirror
            if mp_hand == "Left":

                real_hand = "Right"

            else:

                real_hand = "Left"

            fingers = count_fingers(
                landmarks,
                real_hand
            )

            # -------------------------------------------------
            # RIGHT
            # -------------------------------------------------

            if real_hand == "Right":

                right_fingers = fingers

                right_command = (
                    right_hand_command(
                        fingers
                    )
                )

            # -------------------------------------------------
            # LEFT
            # -------------------------------------------------

            elif real_hand == "Left":

                left_fingers = fingers

                left_command = (
                    left_hand_command(
                        fingers
                    )
                )

            # -------------------------------------------------
            # LABEL
            # -------------------------------------------------

            wrist = landmarks[0]

            x = int(
                wrist.x *
                frame.shape[1]
            )

            y = int(
                wrist.y *
                frame.shape[0]
            )

            label = (
                f"{real_hand}: "
                f"{fingers}"
            )

            cv2.putText(
                frame,
                label,
                (
                    x - 50,
                    y - 20
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

        # =================================================
        # COMMAND PRIORITY
        # =================================================

        if (
            left_fingers is None
            and
            right_fingers is None
        ):

            command = "STOP"

        elif right_fingers is not None:

            command = right_command

        elif left_fingers is not None:

            command = left_command

        else:

            command = "STOP"

        # =================================================
        # SEND
        # =================================================

        self.robot_command(
            command
        )

        # =================================================
        # INFO
        # =================================================

        cv2.rectangle(
            frame,
            (15, 15),
            (410, 125),
            (20, 20, 20),
            -1
        )

        if right_fingers is not None:

            right_text = (
                f"RIGHT: "
                f"{right_fingers} "
                f"-> {right_command}"
            )

        else:

            right_text = "RIGHT: -"

        cv2.putText(
            frame,
            right_text,
            (30, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2
        )

        if left_fingers is not None:

            left_text = (
                f"LEFT: "
                f"{left_fingers} "
                f"-> {left_command}"
            )

        else:

            left_text = "LEFT: -"

        cv2.putText(
            frame,
            left_text,
            (30, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"COMMAND: {command}",
            (30, 108),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            2
        )

        # =================================================
        # TKINTER IMAGE
        # =================================================

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        image = Image.fromarray(
            frame_rgb
        )

        photo = ImageTk.PhotoImage(
            image=image
        )

        self.camera_label.config(
            image=photo
        )

        self.camera_label.image = photo

        # =================================================
        # NEXT
        # =================================================

        self.root.after(
            15,
            self.update_camera
        )


    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        self.running = False

        # -------------------------------------------------
        # STOP
        # -------------------------------------------------

        try:

            if self.esp_ip:

                url = (
                    f"http://"
                    f"{self.esp_ip}:"
                    f"{ESP_PORT}"
                    f"/command"
                )

                requests.get(
                    url,
                    params={
                        "code": ROBOT_CODE,
                        "cmd": CMD_STOP,
                        "left": 0,
                        "right": 0
                    },
                    timeout=1
                )

        except:

            pass

        # -------------------------------------------------
        # WORKER
        # -------------------------------------------------

        try:

            self.command_queue.put_nowait(
                None
            )

        except:

            pass

        # -------------------------------------------------
        # CAMERA
        # -------------------------------------------------

        try:

            self.cap.release()

        except:

            pass

        # -------------------------------------------------
        # MEDIAPIPE
        # -------------------------------------------------

        try:

            self.detector.close()

        except:

            pass

        # -------------------------------------------------
        # WINDOW
        # -------------------------------------------------

        try:

            self.root.destroy()

        except:

            pass


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    try:

        app = RobotGestureApp(
            root
        )

        root.protocol(
            "WM_DELETE_WINDOW",
            app.close
        )

        root.mainloop()

    except Exception as e:

        try:
            root.destroy()
        except:
            pass

        messagebox.showerror(
            "Error",
            str(e)
        )