import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import requests
import threading
import math
import time

# ============================================================
# CONFIG
# ============================================================
DEFAULT_IP = "10.126.248.22"
CAMERA_INDEX = 0
ARUCO_ID = 67

# Calibration
CALIBRATION_DISTANCE_CM = 30.0
CALIBRATION_DURATION_MS = 1000
CALIBRATION_LEFT_SPEED = 200
CALIBRATION_RIGHT_SPEED = 200

# Connection test requested:
# เมื่อเชื่อม ESP32 สำเร็จ -> เดินหน้า 200/200 เป็นเวลา 300 ms
CONNECT_TEST_LEFT = 400
CONNECT_TEST_RIGHT = 400
CONNECT_TEST_DURATION_MS = 500

# Normal walking
WALK_LEFT_SPEED = 200
WALK_RIGHT_SPEED = 200

# Robot reaches target when <= 3 cm
TARGET_REACHED_CM = 3.0

# ============================================================
# ARUCO
# ============================================================
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

ARUCO_PARAMETERS = cv2.aruco.DetectorParameters()

ARUCO_DETECTOR = cv2.aruco.ArucoDetector(
    ARUCO_DICT,
    ARUCO_PARAMETERS
)


class RobotApp:

    def __init__(self, root):

        self.root = root
        self.root.title("ESP32 Robot Navigation")
        self.root.geometry("1200x800")

        # ----------------------------------------------------
        # ESP
        # ----------------------------------------------------
        self.ip = DEFAULT_IP
        self.esp_connected = False

        # ----------------------------------------------------
        # Camera
        # ----------------------------------------------------
        self.camera = None
        self.camera_running = False
        self.camera_index = CAMERA_INDEX

        self.flip_var = tk.BooleanVar(value=False)

        # ----------------------------------------------------
        # ArUco
        # ----------------------------------------------------
        self.marker_center = None
        self.marker_corners = None
        self.marker_heading = None

        # ----------------------------------------------------
        # Calibration
        # ----------------------------------------------------
        self.calibrating = False
        self.calibration_start_center = None
        self.pixels_per_cm = None

        # ----------------------------------------------------
        # Target
        # ----------------------------------------------------
        self.target_point = None
        self.target_active = False
        self.navigation_busy = False

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------
        self.build_ui()

    # ========================================================
    # UI
    # ========================================================
    def build_ui(self):

        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(
            top,
            text="ESP32 IP:"
        ).pack(side="left")

        self.ip_entry = tk.Entry(
            top,
            width=18
        )
        self.ip_entry.insert(0, self.ip)
        self.ip_entry.pack(side="left", padx=5)

        self.connect_button = tk.Button(
            top,
            text="CONNECT ESP",
            command=self.connect_esp,
            width=15
        )
        self.connect_button.pack(side="left", padx=5)

        self.camera_button = tk.Button(
            top,
            text="START CAMERA",
            command=self.toggle_camera,
            width=15
        )
        self.camera_button.pack(side="left", padx=5)

        tk.Label(
            top,
            text="Camera:"
        ).pack(side="left", padx=(15, 3))

        self.camera_var = tk.StringVar(
            value=str(CAMERA_INDEX)
        )

        self.camera_menu = ttk.Combobox(
            top,
            textvariable=self.camera_var,
            values=["0", "1", "2", "3"],
            width=4,
            state="readonly"
        )
        self.camera_menu.pack(side="left")

        self.flip_button = tk.Button(
            top,
            text="FLIP",
            command=self.toggle_flip,
            width=8
        )
        self.flip_button.pack(side="left", padx=5)

        # ----------------------------------------------------
        # Controls
        # ----------------------------------------------------
        control = tk.Frame(self.root)
        control.pack(fill="x", padx=10, pady=5)

        self.calibrate_button = tk.Button(
            control,
            text="CALIBRATE",
            command=self.start_calibration,
            width=15,
            state="disabled"
        )
        self.calibrate_button.pack(side="left", padx=5)

        self.test_move_button = tk.Button(
            control,
            text="TEST 30CM",
            command=self.test_30cm,
            width=15,
            state="disabled"
        )
        self.test_move_button.pack(side="left", padx=5)

        self.start_target_button = tk.Button(
            control,
            text="START TARGET",
            command=self.enable_target,
            width=15,
            state="disabled"
        )
        self.start_target_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(
            control,
            text="STOP",
            command=self.stop_robot,
            width=15
        )
        self.stop_button.pack(side="left", padx=5)

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------
        self.status_var = tk.StringVar(
            value="Not connected"
        )

        tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            font=("Arial", 12, "bold")
        ).pack(fill="x", padx=10, pady=5)

        # ----------------------------------------------------
        # Camera display
        # ----------------------------------------------------
        self.video_label = tk.Label(
            self.root,
            text="Camera not started",
            bg="black",
            fg="white"
        )
        self.video_label.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=10
        )

        # ----------------------------------------------------
        # Info
        # ----------------------------------------------------
        self.info_var = tk.StringVar(
            value="ArUco: -- | Heading: -- | Scale: --"
        )

        tk.Label(
            self.root,
            textvariable=self.info_var,
            anchor="w"
        ).pack(fill="x", padx=10, pady=5)

        self.video_label.bind(
            "<Button-1>",
            self.on_camera_click
        )

    # ========================================================
    # STATUS
    # ========================================================
    def set_status(self, text):

        self.root.after(
            0,
            lambda: self.status_var.set(text)
        )

    # ========================================================
    # ESP CONNECTION
    # ========================================================
    def connect_esp(self):

        ip = self.ip_entry.get().strip()

        if not ip:
            messagebox.showerror(
                "Error",
                "กรุณาใส่ IP ของ ESP32"
            )
            return

        self.ip = ip

        self.set_status(
            "Connecting to ESP32..."
        )

        self.connect_button.config(
            state="disabled"
        )

        threading.Thread(
            target=self.connect_worker,
            daemon=True
        ).start()

    def connect_worker(self):

        try:

            response = requests.get(
                f"http://{self.ip}/",
                timeout=5
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP {response.status_code}"
                )

            self.esp_connected = True

            self.root.after(
                0,
                self.on_esp_connected
            )

        except Exception as e:

            self.esp_connected = False

            self.root.after(
                0,
                lambda: self.on_esp_failed(str(e))
            )

    def on_esp_connected(self):

        self.connect_button.config(
            state="disabled"
        )

        self.camera_button.config(
            state="normal"
        )

        self.test_move_button.config(
            state="normal"
        )

        self.calibrate_button.config(
            state="normal"
        )

        self.set_status(
            f"ESP32 CONNECTED: {self.ip}"
        )

        # ----------------------------------------------------
        # One-time movement immediately after connection
        # 200 / 200 for 300 ms
        # ----------------------------------------------------
        threading.Thread(
            target=self.start_connect_move,
            daemon=True
        ).start()

    def start_connect_move(self):

        self.set_status(
            "ESP32 connected. Forward 200/200 for 300 ms..."
        )

        ok = self.send_move(
            CONNECT_TEST_LEFT,
            CONNECT_TEST_RIGHT,
            CONNECT_TEST_DURATION_MS
        )

        if ok:
            self.set_status(
                "ESP32 connected. Forward test DONE."
            )
        else:
            self.set_status(
                "ESP32 connected, but forward test FAILED."
            )

    def on_esp_failed(self, error):

        self.connect_button.config(
            state="normal"
        )

        self.set_status(
            f"ESP32 connection failed: {error}"
        )

    # ========================================================
    # HTTP
    # ========================================================
    def send_move(
        self,
        left,
        right,
        duration_ms
    ):

        if not self.esp_connected:
            return False

        try:

            response = requests.get(
                f"http://{self.ip}/move",
                params={
                    "left": int(left),
                    "right": int(right),
                    "duration": int(duration_ms)
                },
                timeout=max(
                    5,
                    duration_ms / 1000 + 5
                )
            )

            return response.status_code == 200

        except Exception as e:

            print(
                "send_move error:",
                e
            )

            return False

    def send_turn(self, angle):

        if not self.esp_connected:
            return False

        try:

            response = requests.get(
                f"http://{self.ip}/turn",
                params={
                    "angle": float(angle)
                },
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:

            print(
                "send_turn error:",
                e
            )

            return False

    def send_stop(self):

        if not self.esp_connected:
            return False

        try:

            response = requests.get(
                f"http://{self.ip}/turn",
                params={
                    "angle": 0
                },
                timeout=5
            )

            return response.status_code == 200

        except Exception as e:

            print(
                "send_stop error:",
                e
            )

            return False

    # ========================================================
    # CAMERA
    # ========================================================
    def toggle_camera(self):

        if self.camera_running:
            self.close_camera()
        else:
            self.open_camera()

    def open_camera(self):

        try:
            self.camera_index = int(
                self.camera_var.get()
            )
        except:
            self.camera_index = 0

        self.camera = cv2.VideoCapture(
            self.camera_index,
            cv2.CAP_DSHOW
        )

        self.camera.set(
            cv2.CAP_PROP_BUFFERSIZE,
            1
        )

        if not self.camera.isOpened():

            messagebox.showerror(
                "Camera Error",
                f"เปิด Camera {self.camera_index} ไม่ได้"
            )

            self.camera = None
            return

        self.camera_running = True

        self.camera_button.config(
            text="STOP CAMERA"
        )

        self.set_status(
            f"Camera {self.camera_index} started"
        )

        self.update_camera()

    def close_camera(self):

        self.camera_running = False

        if self.camera is not None:
            self.camera.release()
            self.camera = None

        self.camera_button.config(
            text="START CAMERA"
        )

        self.video_label.config(
            image="",
            text="Camera stopped"
        )

    def toggle_flip(self):

        self.flip_var.set(
            not self.flip_var.get()
        )

    # ========================================================
    # CAMERA LOOP
    # ========================================================
    def update_camera(self):

        if not self.camera_running:
            return

        if self.camera is None:
            return

        ret, frame = self.camera.read()

        if not ret:

            self.root.after(
                30,
                self.update_camera
            )

            return

        if self.flip_var.get():

            frame = cv2.flip(
                frame,
                1
            )

        self.process_camera_frame(
            frame
        )

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        # resize for GUI
        display = rgb.copy()

        h, w = display.shape[:2]

        max_w = 1100
        max_h = 620

        scale = min(
            max_w / w,
            max_h / h,
            1.0
        )

        if scale < 1.0:

            display = cv2.resize(
                display,
                (
                    int(w * scale),
                    int(h * scale)
                )
            )

        # Tkinter PhotoImage
        from PIL import Image, ImageTk

        image = Image.fromarray(
            display
        )

        photo = ImageTk.PhotoImage(
            image=image
        )

        self.video_label.config(
            image=photo,
            text=""
        )

        self.video_label.image = photo

        self.root.after(
            20,
            self.update_camera
        )

    # ========================================================
    # ARUCO DETECTION
    # ========================================================
    def detect_aruco(self, frame):

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        corners, ids, _ = ARUCO_DETECTOR.detectMarkers(
            gray
        )

        found = None

        if ids is not None:

            ids_flat = ids.flatten()

            for i, marker_id in enumerate(ids_flat):

                if marker_id != ARUCO_ID:
                    continue

                pts = corners[i][0]

                center_x = int(
                    np.mean(pts[:, 0])
                )

                center_y = int(
                    np.mean(pts[:, 1])
                )

                # ArUco corner order:
                # 0 = top-left
                # 1 = top-right
                #
                # heading vector is 0 -> 1
                dx = pts[1][0] - pts[0][0]
                dy = pts[1][1] - pts[0][1]

                heading = math.degrees(
                    math.atan2(
                        dy,
                        dx
                    )
                )

                # convert to 0..360
                heading = (
                    heading + 360
                ) % 360

                found = {
                    "center": (
                        center_x,
                        center_y
                    ),
                    "corners": pts.copy(),
                    "heading": heading
                }

                break

        return found

    # ========================================================
    # CAMERA PROCESS
    # ========================================================
    def process_camera_frame(self, frame):

        marker = self.detect_aruco(
            frame
        )

        if marker is not None:

            self.marker_center = marker[
                "center"
            ]

            self.marker_corners = marker[
                "corners"
            ]

            self.marker_heading = marker[
                "heading"
            ]

            pts = marker[
                "corners"
            ].astype(np.int32)

            cv2.polylines(
                frame,
                [pts],
                True,
                (0, 255, 0),
                3
            )

            cx, cy = marker[
                "center"
            ]

            cv2.circle(
                frame,
                (cx, cy),
                6,
                (0, 255, 0),
                -1
            )

            cv2.putText(
                frame,
                f"ArUco {ARUCO_ID}",
                (cx + 10, cy - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"Heading: {marker['heading']:.1f}",
                (cx + 10, cy + 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2
            )

            self.info_var.set(
                f"ArUco: {cx},{cy} | "
                f"Heading: {marker['heading']:.1f}° | "
                f"Scale: "
                f"{self.pixels_per_cm:.2f} px/cm"
                if self.pixels_per_cm
                else
                f"ArUco: {cx},{cy} | "
                f"Heading: {marker['heading']:.1f}° | "
                f"Scale: --"
            )

        else:

            self.info_var.set(
                "ArUco 67: NOT FOUND | "
                "Heading: -- | Scale: --"
                if self.pixels_per_cm is None
                else
                f"ArUco 67: NOT FOUND | "
                f"Heading: -- | "
                f"Scale: {self.pixels_per_cm:.2f} px/cm"
            )

        # ----------------------------------------------------
        # Calibration measurement
        # ----------------------------------------------------
        if (
            self.calibrating and
            self.calibration_start_center is not None and
            marker is not None
        ):

            sx, sy = self.calibration_start_center
            cx, cy = marker["center"]

            pixel_distance = math.hypot(
                cx - sx,
                cy - sy
            )

            if pixel_distance > 3:

                self.finish_calibration(
                    pixel_distance
                )

    # ========================================================
    # CALIBRATION
    # ========================================================
    def start_calibration(self):

        if not self.esp_connected:

            messagebox.showwarning(
                "ESP32",
                "ยังไม่ได้เชื่อม ESP32"
            )

            return

        if not self.camera_running:

            messagebox.showwarning(
                "Camera",
                "กรุณาเปิดกล้องก่อน"
            )

            return

        if self.marker_center is None:

            messagebox.showwarning(
                "ArUco",
                "ไม่พบ ArUco ID 67"
            )

            return

        if self.calibrating:
            return

        self.calibrating = True

        self.calibration_start_center = (
            self.marker_center
        )

        self.set_status(
            "Calibration: moving forward 30 cm..."
        )

        threading.Thread(
            target=self.calibration_worker,
            daemon=True
        ).start()

    def calibration_worker(self):

        ok = self.send_move(
            CALIBRATION_LEFT_SPEED,
            CALIBRATION_RIGHT_SPEED,
            CALIBRATION_DURATION_MS
        )

        if not ok:

            self.calibrating = False

            self.set_status(
                "Calibration FAILED: ESP32 move error"
            )

            return

        # ให้กล้องได้ frame หลังหยุด
        time.sleep(0.15)

        if self.calibration_start_center is None:

            self.calibrating = False
            return

        # Try current marker several times
        for _ in range(30):

            if not self.calibrating:
                return

            if self.marker_center is not None:

                sx, sy = (
                    self.calibration_start_center
                )

                cx, cy = (
                    self.marker_center
                )

                pixel_distance = math.hypot(
                    cx - sx,
                    cy - sy
                )

                if pixel_distance > 3:

                    self.finish_calibration(
                        pixel_distance
                    )

                    return

            time.sleep(0.05)

        self.calibrating = False

        self.set_status(
            "Calibration FAILED: ArUco movement too small"
        )

    def finish_calibration(
        self,
        pixel_distance
    ):

        if not self.calibrating:
            return

        self.calibrating = False

        self.pixels_per_cm = (
            pixel_distance /
            CALIBRATION_DISTANCE_CM
        )

        self.set_status(
            f"Calibration DONE: "
            f"{self.pixels_per_cm:.2f} px/cm"
        )

        self.root.after(
            0,
            lambda: self.start_target_button.config(
                state="normal"
            )
        )

    # ========================================================
    # TEST 30 CM
    # ========================================================
    def test_30cm(self):

        if not self.esp_connected:
            return

        threading.Thread(
            target=self.test_30cm_worker,
            daemon=True
        ).start()

    def test_30cm_worker(self):

        self.set_status(
            "TEST: forward 200/200 for 1000 ms"
        )

        ok = self.send_move(
            WALK_LEFT_SPEED,
            WALK_RIGHT_SPEED,
            CALIBRATION_DURATION_MS
        )

        if ok:
            self.set_status(
                "TEST DONE"
            )
        else:
            self.set_status(
                "TEST FAILED"
            )

    # ========================================================
    # TARGET
    # ========================================================
    def enable_target(self):

        if self.pixels_per_cm is None:

            messagebox.showwarning(
                "Calibration",
                "กรุณา CALIBRATE ก่อน"
            )

            return

        self.target_active = True

        self.set_status(
            "START TARGET: คลิกจุดหมายบนภาพ"
        )

    def on_camera_click(self, event):

        if not self.target_active:
            return

        if self.navigation_busy:
            return

        if self.camera is None:
            return

        # ----------------------------------------------------
        # Need map displayed size -> camera coordinates
        # ----------------------------------------------------
        ret, frame = self.camera.read()

        if not ret:
            return

        if self.flip_var.get():
            frame = cv2.flip(
                frame,
                1
            )

        h, w = frame.shape[:2]

        label_w = self.video_label.winfo_width()
        label_h = self.video_label.winfo_height()

        if label_w <= 1 or label_h <= 1:
            return

        scale = min(
            1100 / w,
            620 / h,
            1.0
        )

        display_w = int(w * scale)
        display_h = int(h * scale)

        offset_x = max(
            0,
            (label_w - display_w) // 2
        )

        offset_y = max(
            0,
            (label_h - display_h) // 2
        )

        x = int(
            (event.x - offset_x) / scale
        )

        y = int(
            (event.y - offset_y) / scale
        )

        if x < 0 or x >= w or y < 0 or y >= h:
            return

        self.target_point = (
            x,
            y
        )

        self.target_active = False
        self.navigation_busy = True

        self.set_status(
            f"Target: {x},{y}"
        )

        threading.Thread(
            target=self.navigate_to_target,
            daemon=True
        ).start()

    # ========================================================
    # ANGLE
    # ========================================================
    def calculate_target_angle(
        self,
        robot_center,
        robot_heading,
        target
    ):
        rx, ry = robot_center
        tx, ty = target

        dx = tx - rx
        dy = ty - ry

        target_direction = (
            math.degrees(
                math.atan2(
                    dy,
                    dx
                )
            ) + 360
        ) % 360

        # clockwise difference
        angle = (
            target_direction -
            robot_heading
        ) % 360

        return angle

    def convert_to_esp_turn_angle(
        self,
        angle_0_360
    ):
        angle = angle_0_360 % 360

        if angle <= 180:
            return angle

        return angle - 360

    # ========================================================
    # NAVIGATION
    # ========================================================
    def navigate_to_target(self):

        try:

            if self.marker_center is None:

                self.set_status(
                    "Navigation FAILED: ArUco not found"
                )

                return

            if self.marker_heading is None:

                self.set_status(
                    "Navigation FAILED: heading unavailable"
                )

                return

            target = self.target_point

            # ------------------------------------------------
            # 1. Calculate direction
            # ------------------------------------------------
            angle_0_360 = (
                self.calculate_target_angle(
                    self.marker_center,
                    self.marker_heading,
                    target
                )
            )

            # ------------------------------------------------
            # 2. Convert to ESP format
            # ------------------------------------------------
            turn_angle = (
                self.convert_to_esp_turn_angle(
                    angle_0_360
                )
            )

            self.set_status(
                f"Turning {turn_angle:.1f}°..."
            )

            # ------------------------------------------------
            # 3. Turn
            # ------------------------------------------------
            if abs(turn_angle) > 1.0:

                ok = self.send_turn(
                    turn_angle
                )

                if not ok:

                    self.set_status(
                        "TURN FAILED"
                    )

                    return

            time.sleep(0.15)

            # ------------------------------------------------
            # 4. Re-read robot position
            # ------------------------------------------------
            if self.marker_center is None:

                self.set_status(
                    "Navigation FAILED: ArUco lost"
                )

                return

            cx, cy = self.marker_center
            tx, ty = target

            pixel_distance = math.hypot(
                tx - cx,
                ty - cy
            )

            distance_cm = (
                pixel_distance /
                self.pixels_per_cm
            )

            if distance_cm <= TARGET_REACHED_CM:

                self.set_status(
                    f"TARGET REACHED "
                    f"({distance_cm:.2f} cm)"
                )

                return

            # ------------------------------------------------
            # 5. Calculate walking time
            #
            # 30 cm = 1000 ms
            # ------------------------------------------------
            walk_duration = int(
                distance_cm /
                CALIBRATION_DISTANCE_CM *
                CALIBRATION_DURATION_MS
            )

            walk_duration = max(
                50,
                walk_duration
            )

            self.set_status(
                f"Walking {distance_cm:.1f} cm "
                f"({walk_duration} ms)..."
            )

            ok = self.send_move(
                WALK_LEFT_SPEED,
                WALK_RIGHT_SPEED,
                walk_duration
            )

            if not ok:

                self.set_status(
                    "WALK FAILED"
                )

                return

            time.sleep(0.15)

            # ------------------------------------------------
            # 6. Verify remaining distance
            # ------------------------------------------------
            self.verify_target()

        finally:

            self.navigation_busy = False

    # ========================================================
    # VERIFY
    # ========================================================
    def verify_target(self):

        if self.marker_center is None:

            self.set_status(
                "VERIFY FAILED: ArUco not found"
            )

            return

        if self.target_point is None:

            return

        cx, cy = self.marker_center
        tx, ty = self.target_point

        pixel_distance = math.hypot(
            tx - cx,
            ty - cy
        )

        distance_cm = (
            pixel_distance /
            self.pixels_per_cm
        )

        if distance_cm <= TARGET_REACHED_CM:

            self.set_status(
                f"TARGET REACHED "
                f"({distance_cm:.2f} cm)"
            )

            return

        # ----------------------------------------------------
        # ยังไม่ถึง -> คำนวณหัวใหม่แล้วเดินอีกครั้ง
        # ----------------------------------------------------
        if self.marker_heading is None:

            self.set_status(
                "VERIFY: heading unavailable"
            )

            return

        angle_0_360 = (
            self.calculate_target_angle(
                self.marker_center,
                self.marker_heading,
                self.target_point
            )
        )

        turn_angle = (
            self.convert_to_esp_turn_angle(
                angle_0_360
            )
        )

        self.set_status(
            f"VERIFY: remaining "
            f"{distance_cm:.1f} cm, "
            f"turn {turn_angle:.1f}°"
        )

        if abs(turn_angle) > 1.0:

            if not self.send_turn(
                turn_angle
            ):

                self.set_status(
                    "VERIFY TURN FAILED"
                )

                return

            time.sleep(0.15)

        # เดินระยะที่เหลือ
        remaining_ms = int(
            distance_cm /
            CALIBRATION_DISTANCE_CM *
            CALIBRATION_DURATION_MS
        )

        remaining_ms = max(
            50,
            remaining_ms
        )

        if not self.send_move(
            WALK_LEFT_SPEED,
            WALK_RIGHT_SPEED,
            remaining_ms
        ):

            self.set_status(
                "VERIFY WALK FAILED"
            )

            return

        time.sleep(0.15)

        # ตรวจอีกครั้ง
        if self.marker_center is None:

            self.set_status(
                "VERIFY FAILED: ArUco lost"
            )

            return

        cx, cy = self.marker_center

        pixel_distance = math.hypot(
            self.target_point[0] - cx,
            self.target_point[1] - cy
        )

        distance_cm = (
            pixel_distance /
            self.pixels_per_cm
        )

        if distance_cm <= TARGET_REACHED_CM:

            self.set_status(
                f"TARGET REACHED "
                f"({distance_cm:.2f} cm)"
            )
        else:

            self.set_status(
                f"Still {distance_cm:.1f} cm "
                f"from target"
            )

    # ========================================================
    # STOP
    # ========================================================
    def stop_robot(self):

        self.calibrating = False
        self.target_active = False

        if self.esp_connected:

            threading.Thread(
                target=self.send_stop,
                daemon=True
            ).start()

        self.set_status(
            "STOP"
        )

    # ========================================================
    # CLOSE
    # ========================================================
    def close(self):

        self.calibrating = False
        self.target_active = False
        self.navigation_busy = False

        if self.esp_connected:

            try:
                self.send_stop()
            except:
                pass

        self.close_camera()

        self.root.destroy()


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":

    root = tk.Tk()

    app = RobotApp(root)

    root.protocol(
        "WM_DELETE_WINDOW",
        app.close
    )

    root.mainloop()
