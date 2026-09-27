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

CAMERA_INDEX = 1
NUM_HANDS = 1

WINDOW_W = 1280
WINDOW_H = 720

# !!! ตรวจสอบ IP นี้จาก Serial Monitor ของ ESP32 ทุกครั้งที่บอร์ด
# เชื่อมต่อ WiFi ใหม่ (เพราะเป็น DHCP, IP อาจเปลี่ยนได้) !!!
ESP32_IP = "10.126.248.22"
ESP_PORT = 80

# ROBOT_CODE เป็น secret ที่ "กำหนดที่นี่" — ถ้าจะเปลี่ยน ต้องไปแก้
# ROBOT_CODE ในไฟล์ .ino ให้ตรงกันด้วย (จำเป็นต้องมี 2 ที่ เพราะ ESP32
# ต้องมีสำเนาไว้ตรวจสอบเอง มิฉะนั้นใครก็สั่งงานหุ่นยนต์ได้)
ROBOT_CODE = "1234"

# --- จุดที่ขอ: ค่าควบคุมทั้งหมดกำหนด/ปรับได้จากตรงนี้ที่เดียว ---
# ฝั่ง .ino จะไม่มีค่าพวกนี้ฝังอยู่ในตัวเองแล้ว มันแค่รับค่าที่ส่งมา
# แล้วเอาไปสั่งฮาร์ดแวร์ตามนั้น เปลี่ยนพฤติกรรมหุ่นยนต์ (ความเร็ว,
# มุมแขนกล, จังหวะเวลา) ได้โดยไม่ต้องแก้/อัปโหลดโค้ด ESP32 ใหม่เลย
MOTOR_SPEED_LEFT = 177
MOTOR_SPEED_RIGHT = 180

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

MOVE_COMMANDS = (CMD_LEFT, CMD_RIGHT, CMD_FORWARD, CMD_BACKWARD)
ARM_COMMANDS = (CMD_GRAB, CMD_DROP)


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

        self.create_ui()
        self.create_landmarker()

        self.update_camera()

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

        # --- จุดที่ขอ: Python เป็นคนตัดสินใจว่าจะส่งค่าอะไรไปสั่ง
        # ESP32 บ้าง ตรงนี้คือจุดเดียวที่ "แปล" คำสั่งเป็นค่าจริง
        # (ความเร็ว/มุม/เวลา) ทั้งหมด ถ้าจะทวีค่าความเร็วหรือมุมแขนกล
        # ก็แก้ค่าคงที่ด้านบนของไฟล์นี้ที่เดียวพอ ไม่ต้องยุ่งกับ .ino

        params = {
            "code": self.robot_code.get(),
            "cmd": cmd,
        }

        if cmd in MOVE_COMMANDS:

            params["left"] = MOTOR_SPEED_LEFT
            params["right"] = MOTOR_SPEED_RIGHT

        elif cmd == CMD_GRAB:

            params["angle"] = SERVO_GRAB_ANGLE
            params["duration"] = ARM_ACTION_TIME_MS

        elif cmd == CMD_DROP:

            params["angle"] = SERVO_DROP_ANGLE
            params["duration"] = ARM_ACTION_TIME_MS

        return params

    def send_command(self, cmd):

        try:

            url = (
                f"http://{self.ESP32_IP.get()}"
                f":{ESP_PORT}/command"
            )

            params = self.build_params(cmd)

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

        success = self.send_command(
            cmd
        )

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

            # ถ้าคำสั่งแขนกลส่งไม่สำเร็จจริง ๆ ให้ rollback สถานะ UI
            # กลับ ไม่ให้ arm_grabbed/arm_var ค้างผิดสภาพ
            if cmd == CMD_GRAB:
                self.arm_grabbed = False
                self.arm_var.set("RELEASED")
            elif cmd == CMD_DROP:
                self.arm_grabbed = True
                self.arm_var.set("GRABBED")

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
                    1010,
                    155,
                    1170,
                    245
                ),
                "cmd": CMD_FORWARD
            },

            "LEFT": {
                "rect": (
                    825,
                    265,
                    985,
                    355
                ),
                "cmd": CMD_LEFT
            },

            "STOP": {
                "rect": (
                    1010,
                    265,
                    1170,
                    355
                ),
                "cmd": CMD_STOP
            },

            "RIGHT": {
                "rect": (
                    1190,
                    265,
                    1270,
                    355
                ),
                "cmd": CMD_RIGHT
            },

            "BACKWARD": {
                "rect": (
                    1010,
                    375,
                    1170,
                    465
                ),
                "cmd": CMD_BACKWARD
            },

            "GRAB": {
                "rect": (
                    885,
                    520,
                    1025,
                    600
                ),
                "cmd": CMD_GRAB
            },

            "DROP": {
                "rect": (
                    1045,
                    520,
                    1185,
                    600
                ),
                "cmd": CMD_DROP
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

            "FORWARD": "▲",

            "BACKWARD": "▼",

            "LEFT": "◀",

            "RIGHT": "▶",

            "STOP": "■",

            "GRAB": "GRAB",

            "DROP": "DROP"
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

        cv2.rectangle(
            overlay,
            (785, 0),
            (1280, 720),
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
            (820, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        status_color = (
            80,
            220,
            120
        )

        cv2.putText(
            frame,
            self.status_var.get(),
            (820, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            status_color,
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            "COMMAND",
            (820, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (140, 150, 165),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            self.command_var.get(),
            (920, 128),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (90, 190, 255),
            2,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            "ARM",
            (1090, 125),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (140, 150, 165),
            1,
            cv2.LINE_AA
        )

        cv2.putText(
            frame,
            self.arm_var.get(),
            (1140, 128),
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
            (850, 650),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (150, 160, 175),
            1,
            cv2.LINE_AA
        )

        return frame

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
                or self.smooth_y is None
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

    def close(self):

        self.running = False

        try:

            self.send_command(
                CMD_STOP
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