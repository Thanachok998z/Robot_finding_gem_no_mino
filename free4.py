from pathlib import Path
import cv2
import math
import mediapipe as mp
import tkinter as tk
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PIL import Image, ImageTk
import requests
import threading
import time


MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")

CAMERA_INDEX = 0
NUM_HANDS = 1

WINDOW_W = 1280
WINDOW_H = 720

ESP32_IP = "10.126.248.22"
ESP_PORT = 80

ROBOT_CODE = "1234"

FORWARD_LEFT = 177
FORWARD_RIGHT = 180

BACKWARD_LEFT = 177
BACKWARD_RIGHT = 180

LEFT_TURN_LEFT = 80
LEFT_TURN_RIGHT = 180

RIGHT_TURN_LEFT = 180
RIGHT_TURN_RIGHT = 80

SERVO_GRAB_ANGLE = 20
SERVO_DROP_ANGLE = 160
ARM_ACTION_TIME_MS = 1500

HOVER_TIME = 0.25
ARM_HOVER_TIME = 0.70

SMOOTHING = 0.35

REQUEST_TIMEOUT = 2.0

CMD_STOP = 0
CMD_LEFT = 1
CMD_RIGHT = 2
CMD_FORWARD = 3
CMD_BACKWARD = 4
CMD_GRAB = 5
CMD_DROP = 6

MOVE_COMMANDS = (
    CMD_LEFT,
    CMD_RIGHT,
    CMD_FORWARD,
    CMD_BACKWARD
)

ARM_COMMANDS = (
    CMD_GRAB,
    CMD_DROP
)


class RobotApp:

    def __init__(self, root):

        self.root = root

        self.root.title("ROBOT CONTROL")

        self.root.geometry(
            f"{WINDOW_W}x{WINDOW_H}"
        )

        self.root.configure(
            bg="#0b0f16"
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

        self.running = True

        self.cap = cv2.VideoCapture(
            CAMERA_INDEX
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            WINDOW_W
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            WINDOW_H
        )

        self.current_command = CMD_STOP

        self.finger_x = None
        self.finger_y = None

        self.smooth_x = None
        self.smooth_y = None

        self.hover_button = None
        self.hover_start = 0

        self.arm_hover_triggered = False
        self.arm_grabbed = False

        # --- FIX: กันไม่ให้ยิง HTTP request ซ้อนกันหลายเธรดพร้อมกัน ---
        # ถ้ามี request ค้างอยู่ (command_in_flight) จะไม่ยิงคำสั่งใหม่
        # ซ้ำ จนกว่าอันเดิมจะตอบกลับมาก่อน
        self.command_in_flight = False

        self.ESP32_IP = tk.StringVar(
            value=ESP32_IP
        )

        self.robot_code = tk.StringVar(
            value=ROBOT_CODE
        )

        self.status_var = tk.StringVar(
            value="ESP32 DISCONNECTED"
        )

        self.command_var = tk.StringVar(
            value="STOP"
        )

        self.arm_var = tk.StringVar(
            value="RELEASED"
        )

        self.video_label = None
        self.settings_window = None

        self.create_ui()
        self.create_landmarker()

        self.update_camera()

        self.root.after(
            500,
            self.test_connection
        )

    def create_ui(self):

        self.video_label = tk.Label(
            self.root,
            bg="#0b0f16"
        )

        self.video_label.pack(
            fill="both",
            expand=True
        )

    def create_landmarker(self):

        base_options = python.BaseOptions(
            model_asset_path=str(
                MODEL_PATH
            )
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_hands=NUM_HANDS,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7
        )

        self.landmarker = (
            vision.HandLandmarker
            .create_from_options(
                options
            )
        )

    def build_params(self, cmd):

        params = {
            "code": self.robot_code.get(),
            "cmd": cmd
        }

        if cmd == CMD_FORWARD:

            params["left"] = FORWARD_LEFT
            params["right"] = FORWARD_RIGHT

        elif cmd == CMD_BACKWARD:

            params["left"] = BACKWARD_LEFT
            params["right"] = BACKWARD_RIGHT

        elif cmd == CMD_LEFT:

            params["left"] = LEFT_TURN_LEFT
            params["right"] = LEFT_TURN_RIGHT

        elif cmd == CMD_RIGHT:

            params["left"] = RIGHT_TURN_LEFT
            params["right"] = RIGHT_TURN_RIGHT

        elif cmd == CMD_GRAB:

            params["angle"] = SERVO_GRAB_ANGLE
            params["duration"] = ARM_ACTION_TIME_MS

        elif cmd == CMD_DROP:

            params["angle"] = SERVO_DROP_ANGLE
            params["duration"] = ARM_ACTION_TIME_MS

        return params

    def send_command(self, cmd):

        # หมายเหตุ: ฟังก์ชันนี้เป็น blocking call (requests.get รอ
        # network response) — ห้ามเรียกตรง ๆ จาก main thread อีกต่อไป
        # ต้องเรียกผ่าน _dispatch_command() ที่รันใน background thread
        # เท่านั้น ไม่งั้นกล้อง/UI จะค้างเหมือนเดิม

        try:

            url = (
                f"http://{self.ESP32_IP.get()}"
                f":{ESP_PORT}/command"
            )

            params = self.build_params(
                cmd
            )

            response = requests.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT
            )

            return response.status_code == 200

        except Exception:

            return False

    def robot_command(self, cmd):

        if cmd == self.current_command:
            return

        # --- FIX: ไม่ยิงคำสั่งซ้อนถ้ามี request ค้างอยู่ ---
        if self.command_in_flight:
            return

        self.command_in_flight = True

        # --- FIX: ยิง HTTP request ใน background thread แทนที่จะ
        # เรียกตรง ๆ บน main thread เพื่อไม่ให้กล้อง/UI ค้างระหว่างรอ
        # response (โดยเฉพาะตอน ESP32 หลุดหรือช้า จะค้างเต็ม
        # REQUEST_TIMEOUT วินาทีทุกครั้งถ้าไม่ทำแบบนี้)
        threading.Thread(
            target=self._send_command_worker,
            args=(cmd,),
            daemon=True
        ).start()

    def _send_command_worker(self, cmd):

        success = self.send_command(
            cmd
        )

        # อัปเดต UI ต้องกลับไปทำบน main thread เท่านั้น ผ่าน root.after
        self.root.after(
            0,
            lambda: self._on_command_result(
                cmd,
                success
            )
        )

    def _on_command_result(self, cmd, success):

        self.command_in_flight = False

        if success:

            self.current_command = cmd

            names = {
                CMD_STOP: "STOP",
                CMD_LEFT: "LEFT",
                CMD_RIGHT: "RIGHT",
                CMD_FORWARD: "FORWARD",
                CMD_BACKWARD: "BACKWARD",
                CMD_GRAB: "GRAB",
                CMD_DROP: "DROP"
            }

            self.command_var.set(
                names[cmd]
            )

            self.status_var.set(
                "ESP32 CONNECTED"
            )

        else:

            self.status_var.set(
                "ESP32 ERROR"
            )

            if cmd == CMD_GRAB:

                self.arm_grabbed = False

                self.arm_var.set(
                    "RELEASED"
                )

            elif cmd == CMD_DROP:

                self.arm_grabbed = True

                self.arm_var.set(
                    "GRABBED"
                )

    def distance(self, a, b):

        return math.sqrt(
            (a.x - b.x) ** 2 +
            (a.y - b.y) ** 2 +
            (a.z - b.z) ** 2
        )

    def get_fingertip(self, frame):

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        result = self.landmarker.detect(
            mp_image
        )

        if not result.hand_landmarks:
            return None

        landmarks = result.hand_landmarks[0]

        fingertip = landmarks[8]

        h, w = frame.shape[:2]

        x = int(
            fingertip.x * w
        )

        y = int(
            fingertip.y * h
        )

        return x, y, landmarks

    def get_buttons(self):

        return {

            "FORWARD": {
                "rect": (
                    520,
                    155,
                    760,
                    235
                ),
                "cmd": CMD_FORWARD
            },

            "LEFT": {
                "rect": (
                    400,
                    250,
                    560,
                    330
                ),
                "cmd": CMD_LEFT
            },

            "STOP": {
                "rect": (
                    560,
                    250,
                    720,
                    330
                ),
                "cmd": CMD_STOP
            },

            "RIGHT": {
                "rect": (
                    720,
                    250,
                    880,
                    330
                ),
                "cmd": CMD_RIGHT
            },

            "BACKWARD": {
                "rect": (
                    520,
                    345,
                    760,
                    425
                ),
                "cmd": CMD_BACKWARD
            },

            "GRAB": {
                "rect": (
                    400,
                    480,
                    560,
                    555
                ),
                "cmd": CMD_GRAB
            },

            "DROP": {
                "rect": (
                    560,
                    480,
                    720,
                    555
                ),
                "cmd": CMD_DROP
            },

            "SETTINGS": {
                "rect": (
                    720,
                    480,
                    880,
                    555
                ),
                "cmd": None
            }
        }

    def inside_button(
        self,
        x,
        y,
        rect
    ):

        x1, y1, x2, y2 = rect

        return (
            x1 <= x <= x2
            and
            y1 <= y <= y2
        )

    def process_hover(
        self,
        x,
        y
    ):

        buttons = self.get_buttons()

        current = None

        for name, data in buttons.items():

            if self.inside_button(
                x,
                y,
                data["rect"]
            ):

                current = name
                break

        now = time.time()

        if current != self.hover_button:

            self.hover_button = current
            self.hover_start = now
            self.arm_hover_triggered = False

            if current is None:

                self.robot_command(
                    CMD_STOP
                )

            return

        if current is None:
            return

        elapsed = (
            now -
            self.hover_start
        )

        if current == "SETTINGS":

            if elapsed >= HOVER_TIME:

                self.open_settings()

                self.hover_button = None
                self.hover_start = now
                self.arm_hover_triggered = False

            return

        if current in (
            "FORWARD",
            "BACKWARD",
            "LEFT",
            "RIGHT",
            "STOP"
        ):

            if elapsed >= HOVER_TIME:

                cmd = buttons[
                    current
                ]["cmd"]

                self.robot_command(
                    cmd
                )

        elif current == "GRAB":

            if (
                elapsed >= ARM_HOVER_TIME
                and
                not self.arm_hover_triggered
            ):

                if not self.arm_grabbed:

                    self.arm_hover_triggered = True

                    self.arm_grabbed = True

                    self.arm_var.set(
                        "GRABBED"
                    )

                    self.robot_command(
                        CMD_GRAB
                    )

        elif current == "DROP":

            if (
                elapsed >= ARM_HOVER_TIME
                and
                not self.arm_hover_triggered
            ):

                if self.arm_grabbed:

                    self.arm_hover_triggered = True

                    self.arm_grabbed = False

                    self.arm_var.set(
                        "RELEASED"
                    )

                    self.robot_command(
                        CMD_DROP
                    )

    def draw_button(
        self,
        frame,
        name,
        rect,
        active
    ):

        x1, y1, x2, y2 = rect

        if active:

            fill = (
                35,
                130,
                220
            )

            border = (
                100,
                220,
                255
            )

        else:

            fill = (
                30,
                38,
                52
            )

            border = (
                90,
                105,
                125
            )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            fill,
            -1
        )

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            border,
            2
        )

        cx = (
            x1 + x2
        ) // 2

        cy = (
            y1 + y2
        ) // 2

        icons = {

            "FORWARD": "F",

            "BACKWARD": "B",

            "LEFT": "L",

            "RIGHT": "R",

            "STOP": "S",

            "GRAB": "GRAB",

            "DROP": "DROP",

            "SETTINGS": "SET"
        }

        text = icons[name]

        if name in (
            "FORWARD",
            "BACKWARD",
            "LEFT",
            "RIGHT",
            "STOP"
        ):

            cv2.putText(
                frame,
                text,
                (
                    cx - 18,
                    cy + 10
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        else:

            cv2.putText(
                frame,
                text,
                (
                    cx - 32,
                    cy + 8
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

    def draw_ui(
        self,
        frame
    ):

        buttons = self.get_buttons()

        overlay = frame.copy()

        panel_x1 = 290
        panel_x2 = 990

        cv2.rectangle(
            overlay,
            (panel_x1, 0),
            (panel_x2, WINDOW_H),
            (10, 15, 23),
            -1
        )

        frame = cv2.addWeighted(
            overlay,
            0.88,
            frame,
            0.12,
            0
        )

        cv2.putText(
            frame,
            "ROBOT CONTROL",
            (475, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            self.status_var.get(),
            (475, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (80, 220, 120),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            "COMMAND",
            (475, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (140, 150, 165),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            self.command_var.get(),
            (575, 128),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (90, 190, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            "ARM",
            (690, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (140, 150, 165),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            self.arm_var.get(),
            (735, 128),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (90, 220, 140),
            1,
            cv2.LINE_AA
        )

        for name, data in buttons.items():

            self.draw_button(
                frame,
                name,
                data["rect"],
                name == self.hover_button
            )

        cv2.putText(
            frame,
            "MOVE FINGERTIP TO CONTROL",
            (440, 625),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (150, 160, 175),
            1,
            cv2.LINE_AA
        )

        return frame

    def open_settings(self):

        if self.settings_window is not None:

            try:

                if self.settings_window.winfo_exists():

                    self.settings_window.lift()
                    self.settings_window.focus_force()

                    return

            except:
                pass

        win = tk.Toplevel(
            self.root
        )

        self.settings_window = win

        win.title(
            "ROBOT SETTINGS"
        )

        win.geometry(
            "500x780"
        )

        win.resizable(
            False,
            False
        )

        win.configure(
            bg="#0b0f16"
        )

        def close_settings():

            self.settings_window = None

            win.destroy()

        win.protocol(
            "WM_DELETE_WINDOW",
            close_settings
        )

        title = tk.Label(
            win,
            text="ROBOT SETTINGS",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#0b0f16"
        )

        title.pack(
            pady=(15, 10)
        )

        frame = tk.Frame(
            win,
            bg="#0b0f16"
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=25
        )

        entries = {}

        fields = [

            ("ESP32 IP", self.ESP32_IP.get()),
            ("Robot Code", self.robot_code.get()),

            ("Forward Left", str(FORWARD_LEFT)),
            ("Forward Right", str(FORWARD_RIGHT)),

            ("Backward Left", str(BACKWARD_LEFT)),
            ("Backward Right", str(BACKWARD_RIGHT)),

            ("Left Turn Left", str(LEFT_TURN_LEFT)),
            ("Left Turn Right", str(LEFT_TURN_RIGHT)),

            ("Right Turn Left", str(RIGHT_TURN_LEFT)),
            ("Right Turn Right", str(RIGHT_TURN_RIGHT)),

            ("Grab Angle", str(SERVO_GRAB_ANGLE)),
            ("Drop Angle", str(SERVO_DROP_ANGLE)),

            ("Arm Action Time (ms)",
             str(ARM_ACTION_TIME_MS)),

            ("Hover Time (s)",
             str(HOVER_TIME)),

            ("Arm Hover Time (s)",
             str(ARM_HOVER_TIME)),

            ("Smoothing",
             str(SMOOTHING)),

            ("Request Timeout (s)",
             str(REQUEST_TIMEOUT))
        ]

        for i, (label_text, value) in enumerate(fields):

            tk.Label(
                frame,
                text=label_text,
                font=("Arial", 10),
                fg="#dce3ec",
                bg="#0b0f16",
                anchor="w"
            ).grid(
                row=i,
                column=0,
                sticky="w",
                pady=4
            )

            entry = tk.Entry(
                frame,
                font=("Arial", 10),
                bg="#1b2430",
                fg="white",
                insertbackground="white",
                relief="flat",
                width=18
            )

            entry.insert(
                0,
                value
            )

            entry.grid(
                row=i,
                column=1,
                sticky="e",
                pady=4,
                ipady=3
            )

            entries[label_text] = entry

        status = tk.Label(
            win,
            text="",
            font=("Arial", 10),
            fg="#70dc98",
            bg="#0b0f16"
        )

        status.pack(
            pady=(4, 6)
        )

        def save_settings():

            global FORWARD_LEFT
            global FORWARD_RIGHT
            global BACKWARD_LEFT
            global BACKWARD_RIGHT
            global LEFT_TURN_LEFT
            global LEFT_TURN_RIGHT
            global RIGHT_TURN_LEFT
            global RIGHT_TURN_RIGHT

            global SERVO_GRAB_ANGLE
            global SERVO_DROP_ANGLE
            global ARM_ACTION_TIME_MS
            global HOVER_TIME
            global ARM_HOVER_TIME
            global SMOOTHING
            global REQUEST_TIMEOUT

            try:

                new_ip = entries[
                    "ESP32 IP"
                ].get().strip()

                new_code = entries[
                    "Robot Code"
                ].get().strip()

                forward_left = int(
                    entries[
                        "Forward Left"
                    ].get()
                )

                forward_right = int(
                    entries[
                        "Forward Right"
                    ].get()
                )

                backward_left = int(
                    entries[
                        "Backward Left"
                    ].get()
                )

                backward_right = int(
                    entries[
                        "Backward Right"
                    ].get()
                )

                left_turn_left = int(
                    entries[
                        "Left Turn Left"
                    ].get()
                )

                left_turn_right = int(
                    entries[
                        "Left Turn Right"
                    ].get()
                )

                right_turn_left = int(
                    entries[
                        "Right Turn Left"
                    ].get()
                )

                right_turn_right = int(
                    entries[
                        "Right Turn Right"
                    ].get()
                )

                grab = int(
                    entries[
                        "Grab Angle"
                    ].get()
                )

                drop = int(
                    entries[
                        "Drop Angle"
                    ].get()
                )

                arm_time = int(
                    entries[
                        "Arm Action Time (ms)"
                    ].get()
                )

                hover = float(
                    entries[
                        "Hover Time (s)"
                    ].get()
                )

                arm_hover = float(
                    entries[
                        "Arm Hover Time (s)"
                    ].get()
                )

                smoothing = float(
                    entries[
                        "Smoothing"
                    ].get()
                )

                timeout = float(
                    entries[
                        "Request Timeout (s)"
                    ].get()
                )

                if not new_ip:

                    raise ValueError(
                        "ESP32 IP is empty"
                    )

                if not new_code:

                    raise ValueError(
                        "Robot Code is empty"
                    )

                speeds = [
                    forward_left,
                    forward_right,
                    backward_left,
                    backward_right,
                    left_turn_left,
                    left_turn_right,
                    right_turn_left,
                    right_turn_right
                ]

                for speed in speeds:

                    if not 0 <= speed <= 255:

                        raise ValueError(
                            "Motor speed must be 0-255"
                        )

                if not 0 <= grab <= 180:

                    raise ValueError(
                        "Grab Angle must be 0-180"
                    )

                if not 0 <= drop <= 180:

                    raise ValueError(
                        "Drop Angle must be 0-180"
                    )

                if arm_time <= 0:

                    raise ValueError(
                        "Arm Action Time must be greater than 0"
                    )

                if hover < 0:

                    raise ValueError(
                        "Hover Time cannot be negative"
                    )

                if arm_hover < 0:

                    raise ValueError(
                        "Arm Hover Time cannot be negative"
                    )

                if not 0 <= smoothing <= 1:

                    raise ValueError(
                        "Smoothing must be between 0 and 1"
                    )

                if timeout <= 0:

                    raise ValueError(
                        "Request Timeout must be greater than 0"
                    )

                self.ESP32_IP.set(
                    new_ip
                )

                self.robot_code.set(
                    new_code
                )

                FORWARD_LEFT = forward_left
                FORWARD_RIGHT = forward_right

                BACKWARD_LEFT = backward_left
                BACKWARD_RIGHT = backward_right

                LEFT_TURN_LEFT = left_turn_left
                LEFT_TURN_RIGHT = left_turn_right

                RIGHT_TURN_LEFT = right_turn_left
                RIGHT_TURN_RIGHT = right_turn_right

                SERVO_GRAB_ANGLE = grab
                SERVO_DROP_ANGLE = drop

                ARM_ACTION_TIME_MS = arm_time

                HOVER_TIME = hover
                ARM_HOVER_TIME = arm_hover

                SMOOTHING = smoothing

                REQUEST_TIMEOUT = timeout

                status.config(
                    text="Settings saved",
                    fg="#70dc98"
                )

            except ValueError as e:

                status.config(
                    text=str(e),
                    fg="#ff7070"
                )

        button_frame = tk.Frame(
            win,
            bg="#0b0f16"
        )

        button_frame.pack(
            pady=(3, 15)
        )

        tk.Button(
            button_frame,
            text="SAVE",
            command=save_settings,
            font=("Arial", 11, "bold"),
            bg="#237fd4",
            fg="white",
            activebackground="#3296ee",
            activeforeground="white",
            relief="flat",
            width=12,
            height=2
        ).pack(
            side="left",
            padx=6
        )

        tk.Button(
            button_frame,
            text="CLOSE",
            command=close_settings,
            font=("Arial", 11, "bold"),
            bg="#303a48",
            fg="white",
            activebackground="#455264",
            activeforeground="white",
            relief="flat",
            width=12,
            height=2
        ).pack(
            side="left",
            padx=6
        )

    def test_connection(self):

        def worker():

            try:

                url = (
                    f"http://{self.ESP32_IP.get()}"
                    f":{ESP_PORT}/"
                )

                response = requests.get(
                    url,
                    timeout=2
                )

                if response.status_code == 200:

                    self.status_var.set(
                        "ESP32 CONNECTED"
                    )

                else:

                    self.status_var.set(
                        "ESP32 ERROR"
                    )

            except Exception:

                self.status_var.set(
                    "ESP32 DISCONNECTED"
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def update_camera(self):

        if not self.running:

            return

        ret, frame = self.cap.read()

        if not ret:

            self.root.after(
                30,
                self.update_camera
            )

            return

        frame = cv2.flip(
            frame,
            1
        )

        frame = cv2.resize(
            frame,
            (
                WINDOW_W,
                WINDOW_H
            )
        )

        fingertip = self.get_fingertip(
            frame
        )

        if fingertip is not None:

            x, y, landmarks = fingertip

            if (
                self.smooth_x is None
                or
                self.smooth_y is None
            ):

                self.smooth_x = x
                self.smooth_y = y

            else:

                self.smooth_x = (
                    self.smooth_x
                    * (1 - SMOOTHING)
                    +
                    x
                    * SMOOTHING
                )

                self.smooth_y = (
                    self.smooth_y
                    * (1 - SMOOTHING)
                    +
                    y
                    * SMOOTHING
                )

            x = int(
                self.smooth_x
            )

            y = int(
                self.smooth_y
            )

            self.finger_x = x
            self.finger_y = y

            self.process_hover(
                x,
                y
            )

            cv2.circle(
                frame,
                (x, y),
                16,
                (255, 255, 255),
                2
            )

            cv2.circle(
                frame,
                (x, y),
                7,
                (0, 220, 255),
                -1
            )

            cv2.line(
                frame,
                (x - 25, y),
                (x + 25, y),
                (0, 220, 255),
                1
            )

            cv2.line(
                frame,
                (x, y - 25),
                (x, y + 25),
                (0, 220, 255),
                1
            )

        else:

            self.finger_x = None
            self.finger_y = None

            self.smooth_x = None
            self.smooth_y = None

            self.hover_button = None
            self.hover_start = 0
            self.arm_hover_triggered = False

            self.robot_command(
                CMD_STOP
            )

        frame = self.draw_ui(
            frame
        )

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        image = Image.fromarray(
            rgb
        )

        photo = ImageTk.PhotoImage(
            image
        )

        self.video_label.configure(
            image=photo
        )

        self.video_label.image = photo

        self.root.after(
            15,
            self.update_camera
        )

    def close(self):

        self.running = False

        try:

            # ตอนปิดโปรแกรม ยอมให้ blocking ได้ เพราะปิดแอปอยู่แล้ว
            # แต่กันเวลารอไม่ให้ยาวเกินไปด้วย timeout สั้น ๆ
            requests.get(
                f"http://{self.ESP32_IP.get()}:{ESP_PORT}/command",
                params=self.build_params(CMD_STOP),
                timeout=1.0
            )

        except:
            pass

        try:

            self.cap.release()

        except:
            pass

        try:

            self.landmarker.close()

        except:
            pass

        self.root.destroy()


if __name__ == "__main__":

    root = tk.Tk()

    app = RobotApp(
        root
    )

    root.mainloop()