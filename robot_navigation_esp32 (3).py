import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
import requests
import threading
import time
import math

# ============================================================
# CONFIG
# ============================================================

DEFAULT_IP = "10.126.248.22"
CAMERA_INDEX = 0

ARUCO_ID = 67

# Calibration:
# Robot travels 30 cm using 200 / 200 for 1000 ms
CALIBRATION_DISTANCE_CM = 30.0
CALIBRATION_TIME_MS = 1000
WALK_LEFT_SPEED = 200
WALK_RIGHT_SPEED = 200

# Angle tolerance
ANGLE_TOLERANCE = 5.0

# Check target every 2 seconds
CONTROL_INTERVAL = 2.0

# After turning, wait before checking camera again
TURN_WAIT = 0.3

# ============================================================
# ARUCO
# ============================================================

aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

aruco_parameters = cv2.aruco.DetectorParameters()
aruco_detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    aruco_parameters
)


# ============================================================
# MAIN APP
# ============================================================

class RobotApp:

    def __init__(self, root):
        self.root = root
        self.root.title("Robot Target Navigation")
        self.root.geometry("1200x800")

        self.running = True

        # -----------------------------
        # ESP
        # -----------------------------
        self.ip = DEFAULT_IP
        self.esp_connected = False

        # -----------------------------
        # Camera
        # -----------------------------
        self.cap = None
        self.camera_running = False
        self.camera_index = CAMERA_INDEX
        self.flip_camera = False
        self.flip_var = tk.BooleanVar(value=False)

        # Latest frame / marker
        self.current_frame = None
        self.marker_center = None
        self.marker_corners = None
        self.marker_angle = None

        # -----------------------------
        # Calibration
        # -----------------------------
        self.calibration_done = False
        self.pixels_per_cm = None

        self.calibration_start_center = None
        self.calibration_running = False

        # -----------------------------
        # Target
        # -----------------------------
        self.target = None
        self.target_selected = False

        # -----------------------------
        # Navigation
        # -----------------------------
        self.navigation_running = False
        self.turning = False
        self.walking = False

        # -----------------------------
        # Build UI
        # -----------------------------
        self.build_ui()

        # Start automatically
        self.root.after(500, self.startup)

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
        self.ip_entry.insert(0, DEFAULT_IP)
        self.ip_entry.pack(side="left", padx=5)

        self.connect_button = tk.Button(
            top,
            text="CONNECT ESP",
            command=self.connect_esp_manual,
            width=14
        )
        self.connect_button.pack(side="left", padx=5)

        self.camera_button = tk.Button(
            top,
            text="START CAMERA",
            command=self.toggle_camera,
            width=14,
            state="normal"
        )
        self.camera_button.pack(side="left", padx=5)

        # Camera selector 0-3
        tk.Label(top, text="Camera:").pack(side="left", padx=(12, 2))
        self.camera_var = tk.StringVar(value=str(CAMERA_INDEX))
        self.camera_menu = tk.OptionMenu(
            top, self.camera_var, "0", "1", "2", "3",
            command=self.change_camera
        )
        self.camera_menu.config(width=3)
        self.camera_menu.pack(side="left", padx=3)

        # Flip button
        self.flip_button = tk.Button(
            top, text="FLIP: OFF", width=10, command=self.toggle_flip
        )
        self.flip_button.pack(side="left", padx=3)

        # Direct motor test: 200/200 for 1000 ms
        self.test_move_button = tk.Button(
            top, text="TEST 30CM", width=11, command=self.test_move, state="disabled"
        )
        self.test_move_button.pack(side="left", padx=3)

        self.target_button = tk.Button(
            top,
            text="START TARGET",
            command=self.start_target,
            width=14,
            state="disabled"
        )
        self.target_button.pack(side="left", padx=5)

        self.calibrate_button = tk.Button(
            top,
            text="CALIBRATE",
            command=self.start_calibration,
            width=12,
            state="disabled"
        )
        self.calibrate_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(
            top,
            text="STOP",
            command=self.stop_robot,
            width=10
        )
        self.stop_button.pack(side="left", padx=5)

        # -----------------------------
        # Status
        # -----------------------------

        status_frame = tk.Frame(self.root)
        status_frame.pack(fill="x", padx=10)

        self.status_label = tk.Label(
            status_frame,
            text="Starting...",
            anchor="w",
            font=("Arial", 12)
        )
        self.status_label.pack(fill="x")

        self.calibration_label = tk.Label(
            status_frame,
            text="Calibration: NOT DONE",
            anchor="w"
        )
        self.calibration_label.pack(fill="x")

        self.angle_label = tk.Label(
            status_frame,
            text="Angle: -",
            anchor="w"
        )
        self.angle_label.pack(fill="x")

        self.target_label = tk.Label(
            status_frame,
            text="Target: -",
            anchor="w"
        )
        self.target_label.pack(fill="x")

        self.distance_label = tk.Label(
            status_frame,
            text="Distance: -",
            anchor="w"
        )
        self.distance_label.pack(fill="x")

        # -----------------------------
        # Canvas
        # -----------------------------

        self.canvas = tk.Canvas(
            self.root,
            bg="black",
            cursor="crosshair"
        )
        self.canvas.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.canvas.bind(
            "<Button-1>",
            self.on_canvas_click
        )

    # ========================================================
    # STATUS
    # ========================================================

    def set_status(self, text):
        self.root.after(
            0,
            lambda: self.status_label.config(text=text)
        )

    # ========================================================
    # STARTUP
    # ========================================================

    def startup(self):
        self.set_status(
            "Connecting to ESP32... | Camera 0-3 selectable"
        )

        threading.Thread(
            target=self.connect_esp_auto,
            daemon=True
        ).start()

    # ========================================================
    # ESP CONNECTION
    # ========================================================

    def connect_esp_auto(self):

        ip = self.ip_entry.get().strip()

        if not ip:
            ip = DEFAULT_IP

        self.ip = ip

        try:
            url = f"http://{self.ip}/"

            response = requests.get(
                url,
                timeout=3
            )

            if response.status_code == 200:
                self.esp_connected = True

                self.root.after(
                    0,
                    self.on_esp_connected
                )
                return

        except Exception as e:
            print("ESP connection error:", e)

        self.esp_connected = False

        self.root.after(
            0,
            lambda: self.set_status(
                "ESP32 connection failed"
            )
        )

        self.root.after(
            0,
            lambda: self.connect_button.config(
                state="normal"
            )
        )

    def connect_esp_manual(self):

        self.ip = self.ip_entry.get().strip()

        if not self.ip:
            self.ip = DEFAULT_IP

        self.set_status("Connecting to ESP32...")

        threading.Thread(
            target=self.connect_esp_auto,
            daemon=True
        ).start()

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
            f"ESP32 CONNECTED: {self.ip} | Press CALIBRATE"
        )

        # Calibration will NOT start automatically.
        # User must press the CALIBRATE button.
        self.set_status(
            "ESP32 connected. Press CALIBRATE to start."
        )

    # ========================================================
    # DIRECT MOTOR TEST
    # ========================================================

    def test_move(self):
        """Test exactly 200/200 for 1000 ms without calibration/navigation."""
        if not self.esp_connected:
            self.set_status("ESP32 not connected")
            return

        self.test_move_button.config(state="disabled")
        self.set_status("TEST: forward 200/200 for 1000 ms...")

        def worker():
            ok = self.send_move(200, 200, 1000)
            self.root.after(0, lambda: self.finish_test_move(ok))

        threading.Thread(target=worker, daemon=True).start()

    def finish_test_move(self, ok):
        self.test_move_button.config(state="normal")
        if ok:
            self.set_status("TEST DONE: ESP32 received /move 200/200/1000")
        else:
            self.set_status("TEST FAILED: check ESP32 IP / Wi-Fi / Serial Monitor")

    # ========================================================
    # CAMERA
    # ========================================================

    def open_camera(self):

        try:
            index = int(
                self.camera_var.get()
            )
        except Exception:
            index = CAMERA_INDEX

        self.camera_index = index

        if self.cap is not None:
            self.cap.release()

        self.cap = cv2.VideoCapture(
            self.camera_index, cv2.CAP_DSHOW
        )

        # Some Windows cameras need a little time after opening.
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.cap.isOpened():
            self.cap = None

            messagebox.showerror(
                "Camera Error",
                f"Cannot open camera {self.camera_index}"
            )

            return False

        self.camera_running = True

        self.camera_button.config(
            text="STOP CAMERA"
        )

        self.update_camera()

        return True

    def change_camera(self, value=None):

        try:
            new_index = int(
                self.camera_var.get()
            )
        except Exception:
            new_index = CAMERA_INDEX

        # If the selected camera is already active, do nothing.
        if (
            self.camera_running and
            self.camera_index == new_index
        ):
            return

        self.camera_index = new_index

        # Restart camera immediately when changing camera.
        if self.camera_running:
            self.stop_camera()
            self.root.after(
                100,
                self.open_camera
            )

        else:
            self.set_status(
                f"Camera selected: {self.camera_index}"
            )

    def toggle_flip(self):

        self.flip_var.set(
            not self.flip_var.get()
        )

        if self.flip_var.get():
            self.flip_button.config(
                text="FLIP: ON"
            )
            self.set_status("Flip ON")
        else:
            self.flip_button.config(
                text="FLIP: OFF"
            )
            self.set_status("Flip OFF")

    def toggle_camera(self):

        if self.camera_running:
            self.stop_camera()
        else:
            self.open_camera()

    def stop_camera(self):

        self.camera_running = False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.marker_center = None
        self.marker_corners = None
        self.marker_angle = None

        self.camera_button.config(
            text="START CAMERA"
        )

    # ========================================================
    # CAMERA LOOP
    # ========================================================

    def update_camera(self):

        if not self.camera_running:
            return

        if self.cap is None:
            return

        ret, frame = self.cap.read()

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

        self.current_frame = frame.copy()

        self.detect_aruco(frame)

        display = frame.copy()

        # Draw ArUco ID 67 bounding box
        if self.marker_corners is not None:
            pts = self.marker_corners.astype(int).reshape((-1, 1, 2))
            cv2.polylines(display, [pts], True, (0, 255, 0), 4)

            if self.marker_center is not None:
                label_x = int(self.marker_center[0] - 30)
                label_y = int(self.marker_center[1] - 35)
                cv2.putText(
                    display, "ArUco 67", (label_x, label_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
                )

        # Draw target
        if self.target is not None:

            tx, ty = self.target

            cv2.circle(
                display,
                (int(tx), int(ty)),
                10,
                (0, 0, 255),
                -1
            )

            cv2.circle(
                display,
                (int(tx), int(ty)),
                18,
                (255, 255, 255),
                2
            )

            cv2.putText(
                display,
                "TARGET",
                (int(tx) + 15, int(ty)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        # Draw robot
        if self.marker_center is not None:

            cx, cy = self.marker_center

            cv2.circle(
                display,
                (int(cx), int(cy)),
                6,
                (0, 255, 0),
                -1
            )

            # Heading line
            if self.marker_corners is not None:

                p0 = self.marker_corners[0]
                p1 = self.marker_corners[1]

                front_x = int(
                    (p0[0] + p1[0]) / 2
                )
                front_y = int(
                    (p0[1] + p1[1]) / 2
                )

                cv2.line(
                    display,
                    (int(cx), int(cy)),
                    (front_x, front_y),
                    (255, 0, 0),
                    4
                )

        self.show_frame(display)

        self.root.after(
            30,
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

        corners, ids, _ = aruco_detector.detectMarkers(
            gray
        )

        self.marker_center = None
        self.marker_corners = None
        self.marker_angle = None

        if ids is None:
            self.angle_label.config(
                text="Angle: ArUco not found"
            )
            return

        ids_flat = ids.flatten()

        for i, marker_id in enumerate(ids_flat):

            if int(marker_id) != ARUCO_ID:
                continue

            pts = corners[i][0]

            # Center
            center_x = np.mean(
                pts[:, 0]
            )

            center_y = np.mean(
                pts[:, 1]
            )

            self.marker_center = (
                float(center_x),
                float(center_y)
            )

            # Keep first two corners as front edge
            p0 = pts[0]
            p1 = pts[1]

            self.marker_corners = pts.copy()

            # Draw ArUco bounding box + ID on the live image.
            # This is drawn later again in update_camera() using the
            # stored corners, so the box remains visible on every frame.

            # Direction vector from marker center
            # toward midpoint of corner 0 and 1
            front_x = (
                p0[0] + p1[0]
            ) / 2.0

            front_y = (
                p0[1] + p1[1]
            ) / 2.0

            dx = front_x - center_x
            dy = front_y - center_y

            # Image coordinate:
            # x right
            # y down
            #
            # Heading angle:
            # 0 = right
            # clockwise positive
            heading = math.degrees(
                math.atan2(
                    dy,
                    dx
                )
            )

            heading %= 360.0

            self.marker_angle = heading

            self.angle_label.config(
                text=f"Robot heading: {heading:.1f}°"
            )

            break

    # ========================================================
    # DISPLAY FRAME
    # ========================================================

    def show_frame(self, frame):

        # Resize to fit canvas
        canvas_w = max(
            self.canvas.winfo_width(),
            1
        )

        canvas_h = max(
            self.canvas.winfo_height(),
            1
        )

        h, w = frame.shape[:2]

        scale = min(
            canvas_w / w,
            canvas_h / h
        )

        new_w = max(
            1,
            int(w * scale)
        )

        new_h = max(
            1,
            int(h * scale)
        )

        resized = cv2.resize(
            frame,
            (new_w, new_h)
        )

        rgb = cv2.cvtColor(
            resized,
            cv2.COLOR_BGR2RGB
        )

        from PIL import Image, ImageTk

        image = Image.fromarray(
            rgb
        )

        self.tk_image = ImageTk.PhotoImage(
            image=image
        )

        self.canvas.delete("all")

        self.canvas.create_image(
            canvas_w / 2,
            canvas_h / 2,
            image=self.tk_image,
            anchor="center"
        )

        # Save mapping for mouse click
        self.display_scale = scale
        self.display_width = new_w
        self.display_height = new_h
        self.frame_width = w
        self.frame_height = h
        self.canvas_width = canvas_w
        self.canvas_height = canvas_h

    # ========================================================
    # CALIBRATION
    # ========================================================

    def start_calibration(self):

        if not self.esp_connected:
            self.set_status(
                "ESP32 not connected"
            )
            return

        if self.calibration_running:
            return

        if not self.camera_running:

            if not self.open_camera():
                return

        self.navigation_running = False
        self.turning = False
        self.walking = False
        self.target = None
        self.target_selected = False

        self.calibration_running = True
        self.calibration_done = False
        self.pixels_per_cm = None
        self.calibration_start_center = None

        self.calibrate_button.config(
            state="disabled"
        )

        self.target_button.config(
            state="disabled"
        )

        self.calibration_label.config(
            text="Calibration: WAITING FOR ARUCO"
        )

        self.set_status(
            "Calibration: place robot, waiting for ArUco..."
        )

        self.root.after(
            200,
            self.calibration_wait_marker
        )

    def calibration_wait_marker(self):

        if not self.calibration_running:
            return

        if self.marker_center is None:

            self.set_status(
                "Calibration: searching ArUco ID 67..."
            )

            self.root.after(
                100,
                self.calibration_wait_marker
            )

            return

        self.calibration_start_center = (
            self.marker_center
        )

        self.calibration_label.config(
            text="Calibration: STARTING 30 cm movement"
        )

        self.set_status(
            "Calibration: walking 1000 ms..."
        )

        threading.Thread(
            target=self.calibration_move,
            daemon=True
        ).start()

    def calibration_move(self):

        ok = self.send_move(
            WALK_LEFT_SPEED,
            WALK_RIGHT_SPEED,
            CALIBRATION_TIME_MS
        )

        if not ok:

            self.root.after(
                0,
                self.calibration_failed
            )

            return

        # Give camera a little time to update
        time.sleep(0.3)

        self.root.after(
            0,
            self.finish_calibration
        )

    def finish_calibration(self):

        if not self.calibration_running:
            return

        if self.marker_center is None:

            self.set_status(
                "Calibration: ArUco lost, retrying measurement..."
            )

            self.root.after(
                300,
                self.finish_calibration
            )

            return

        x0, y0 = (
            self.calibration_start_center
        )

        x1, y1 = (
            self.marker_center
        )

        pixel_movement = math.hypot(
            x1 - x0,
            y1 - y0
        )

        if pixel_movement < 5:

            self.calibration_label.config(
                text="Calibration: movement too small"
            )

            self.set_status(
                "Calibration failed: pixel movement too small"
            )

            self.calibration_running = False

            return

        self.pixels_per_cm = (
            pixel_movement /
            CALIBRATION_DISTANCE_CM
        )

        self.calibration_done = True
        self.calibration_running = False

        self.calibrate_button.config(
            state="normal"
        )

        self.calibration_label.config(
            text=(
                f"Calibration: DONE | "
                f"{pixel_movement:.1f} px / "
                f"{CALIBRATION_DISTANCE_CM:.1f} cm | "
                f"{self.pixels_per_cm:.2f} px/cm"
            )
        )

        self.target_button.config(
            state="normal"
        )

        self.set_status(
            "Calibration complete. Select START TARGET."
        )

    def calibration_failed(self):

        self.calibration_running = False

        self.calibrate_button.config(
            state="normal"
        )

        self.calibration_label.config(
            text="Calibration: FAILED"
        )

        self.set_status(
            "Calibration movement failed"
        )

        messagebox.showerror(
            "Calibration",
            "ESP32 /move failed."
        )

    # ========================================================
    # CANVAS CLICK
    # ========================================================

    def on_canvas_click(self, event):

        if not self.calibration_done:
            return

        if not self.camera_running:
            return

        if self.current_frame is None:
            return

        if not hasattr(
            self,
            "display_scale"
        ):
            return

        # Image position on canvas
        offset_x = (
            self.canvas_width -
            self.display_width
        ) / 2

        offset_y = (
            self.canvas_height -
            self.display_height
        ) / 2

        px = (
            event.x -
            offset_x
        )

        py = (
            event.y -
            offset_y
        )

        # Outside image
        if (
            px < 0 or
            py < 0 or
            px >= self.display_width or
            py >= self.display_height
        ):
            return

        # Convert canvas pixel to camera pixel
        x = px / self.display_scale
        y = py / self.display_scale

        self.target = (
            float(x),
            float(y)
        )

        self.target_selected = True

        self.target_label.config(
            text=(
                f"Target: "
                f"({x:.0f}, {y:.0f})"
            )
        )

        self.set_status(
            "Target selected. Calculating direction..."
        )

        self.navigation_running = True

        self.root.after(
            100,
            self.auto_target_check
        )

    # ========================================================
    # START TARGET
    # ========================================================

    def start_target(self):

        if not self.calibration_done:

            messagebox.showwarning(
                "Calibration",
                "Please finish calibration first."
            )

            return

        if self.marker_center is None:

            messagebox.showwarning(
                "ArUco",
                "Cannot find ArUco ID 67."
            )

            return

        self.target = None
        self.target_selected = False
        self.navigation_running = False

        self.target_label.config(
            text="Target: Click a point on the camera image"
        )

        self.set_status(
            "Click destination on camera image."
        )

    # ========================================================
    # ANGLE CALCULATION
    # ========================================================

    def calculate_angle_to_target(self):

        if (
            self.marker_center is None or
            self.target is None or
            self.marker_angle is None
        ):
            return None

        cx, cy = self.marker_center
        tx, ty = self.target

        dx = tx - cx
        dy = ty - cy

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.0

        # Direction from robot to target
        target_direction = math.degrees(
            math.atan2(
                dy,
                dx
            )
        ) % 360.0

        # Robot heading is also clockwise-positive
        angle = (
            target_direction -
            self.marker_angle
        ) % 360.0

        return angle

    # ========================================================
    # CONVERT 0-360 ANGLE TO ESP32 SIGNED ANGLE
    # ========================================================

    def angle_for_esp32(self, angle):

        angle %= 360.0

        # 0 -> 0
        if angle < 0.01:
            return 0.0

        # Clockwise <= 180
        if angle <= 180.0:
            return angle

        # Counter-clockwise
        return -(360.0 - angle)

    # ========================================================
    # AUTO TARGET CHECK
    # ========================================================

    def auto_target_check(self):

        if not self.navigation_running:
            return

        if self.target is None:
            return

        if self.turning or self.walking:
            return

        if self.marker_center is None:

            self.set_status(
                "Waiting for ArUco..."
            )

            self.root.after(
                200,
                self.auto_target_check
            )

            return

        angle = self.calculate_angle_to_target()

        if angle is None:

            self.root.after(
                200,
                self.auto_target_check
            )

            return

        # Circular error
        error = min(
            angle,
            360.0 - angle
        )

        self.angle_label.config(
            text=(
                f"Required rotation: "
                f"{angle:.1f}° | "
                f"error: {error:.1f}°"
            )
        )

        # Already facing target
        if error <= ANGLE_TOLERANCE:

            self.set_status(
                "Direction OK. Walking straight..."
            )

            self.root.after(
                300,
                self.start_straight_walk
            )

            return

        # Need to turn
        esp_angle = self.angle_for_esp32(
            angle
        )

        self.turning = True

        self.set_status(
            f"Turning: {esp_angle:+.1f}°"
        )

        threading.Thread(
            target=self.turn_worker,
            args=(esp_angle,),
            daemon=True
        ).start()

    # ========================================================
    # TURN WORKER
    # ========================================================

    def turn_worker(self, angle):

        ok = self.send_turn(angle)

        time.sleep(TURN_WAIT)

        self.root.after(
            0,
            lambda: self.finish_turn(ok)
        )

    def finish_turn(self, ok):

        self.turning = False

        if not ok:

            self.navigation_running = False

            self.set_status(
                "Turn failed"
            )

            return

        self.set_status(
            "Turn complete. Rechecking direction..."
        )

        self.root.after(
            100,
            self.auto_target_check
        )

    # ========================================================
    # STRAIGHT WALK
    # ========================================================

    def start_straight_walk(self):

        if not self.navigation_running:
            return

        if self.target is None:
            return

        if self.walking:
            return

        if self.marker_center is None:
            self.set_status(
                "Cannot walk: ArUco lost"
            )

            return

        # Calculate current pixel distance
        cx, cy = self.marker_center
        tx, ty = self.target

        distance_px = math.hypot(
            tx - cx,
            ty - cy
        )

        distance_cm = (
            distance_px /
            self.pixels_per_cm
        )

        # 30 cm = 1000 ms
        walk_time_ms = (
            distance_cm /
            CALIBRATION_DISTANCE_CM
        ) * CALIBRATION_TIME_MS

        walk_time_ms = int(
            max(
                0,
                round(walk_time_ms)
            )
        )

        self.distance_label.config(
            text=(
                f"Distance: "
                f"{distance_px:.1f} px ≈ "
                f"{distance_cm:.1f} cm | "
                f"Walk: {walk_time_ms} ms"
            )
        )

        # Already close
        if distance_cm <= 3.0:

            self.navigation_running = False

            self.set_status(
                "TARGET REACHED"
            )

            return

        self.walking = True

        self.set_status(
            f"Walking straight {distance_cm:.1f} cm "
            f"for {walk_time_ms} ms..."
        )

        threading.Thread(
            target=self.walk_worker,
            args=(walk_time_ms,),
            daemon=True
        ).start()

    def walk_worker(self, duration_ms):

        ok = self.send_move(
            WALK_LEFT_SPEED,
            WALK_RIGHT_SPEED,
            duration_ms
        )

        time.sleep(0.3)

        self.root.after(
            0,
            lambda: self.finish_walk(ok)
        )

    def finish_walk(self, ok):

        self.walking = False

        if not ok:

            self.navigation_running = False

            self.set_status(
                "Walking failed"
            )

            return

        self.set_status(
            "Walk complete. Checking target..."
        )

        # Check actual remaining distance
        self.root.after(
            300,
            self.verify_position
        )

    # ========================================================
    # VERIFY POSITION
    # ========================================================

    def verify_position(self):

        if (
            self.marker_center is None or
            self.target is None
        ):
            self.set_status(
                "ArUco lost after walking"
            )
            return

        cx, cy = self.marker_center
        tx, ty = self.target

        distance_px = math.hypot(
            tx - cx,
            ty - cy
        )

        distance_cm = (
            distance_px /
            self.pixels_per_cm
        )

        self.distance_label.config(
            text=(
                f"Remaining: "
                f"{distance_px:.1f} px ≈ "
                f"{distance_cm:.1f} cm"
            )
        )

        if distance_cm <= 3.0:

            self.navigation_running = False

            self.set_status(
                "TARGET REACHED"
            )

            return

        # Not there yet.
        # Recalculate direction first.
        self.set_status(
            f"{distance_cm:.1f} cm remaining. Rechecking direction..."
        )

        self.root.after(
            200,
            self.auto_target_check
        )

    # ========================================================
    # HTTP: TURN
    # ========================================================

    def send_turn(self, angle):

        try:

            url = (
                f"http://{self.ip}"
                f"/turn"
            )

            response = requests.get(
                url,
                params={
                    "angle": angle
                },
                timeout=15
            )

            print(
                "TURN:",
                response.url,
                response.status_code,
                response.text
            )

            return (
                response.status_code == 200
            )

        except Exception as e:

            print(
                "TURN ERROR:",
                e
            )

            return False

    # ========================================================
    # HTTP: MOVE
    # ========================================================

    def send_move(
        self,
        left,
        right,
        duration
    ):

        try:

            url = (
                f"http://{self.ip}"
                f"/move"
            )

            response = requests.get(
                url,
                params={
                    "left": int(left),
                    "right": int(right),
                    "duration": int(duration)
                },
                timeout=max(
                    5,
                    duration / 1000.0 + 5
                )
            )

            print(
                "MOVE:",
                response.url,
                response.status_code,
                response.text
            )

            return (
                response.status_code == 200
            )

        except Exception as e:

            print(
                "MOVE ERROR:",
                e
            )

            return False

    # ========================================================
    # STOP
    # ========================================================

    def stop_robot(self):

        self.navigation_running = False
        self.turning = False
        self.walking = False

        if not self.esp_connected:
            self.set_status(
                "STOP"
            )
            return

        threading.Thread(
            target=self.send_stop,
            daemon=True
        ).start()

        self.set_status(
            "ROBOT STOP"
        )

    def send_stop(self):

        try:

            requests.get(
                f"http://{self.ip}/turn",
                params={
                    "angle": 0
                },
                timeout=3
            )

        except Exception as e:

            print(
                "STOP ERROR:",
                e
            )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self.running = False
        self.navigation_running = False

        try:
            self.send_stop()
        except Exception:
            pass

        self.stop_camera()

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
