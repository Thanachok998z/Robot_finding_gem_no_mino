import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import requests
import math
from PIL import Image, ImageTk


# =========================================================
# CONFIG
# =========================================================

DEFAULT_IP = "10.126.248.22"
DEFAULT_CAMERA = 0

ARUCO_ID = 67

# ใช้ DICT_4X4_100
ARUCO_DICT = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

ARUCO_PARAMETERS = cv2.aruco.DetectorParameters()

ARUCO_DETECTOR = cv2.aruco.ArucoDetector(
    ARUCO_DICT,
    ARUCO_PARAMETERS
)


# =========================================================
# MAIN APP
# =========================================================

class RobotControlApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Robot Target Control")
        self.root.geometry("1100x800")

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.close
        )

        # -------------------------------------------------
        # STATE
        # -------------------------------------------------

        self.cap = None

        self.connected = False
        self.camera_running = False
        self.target_mode = False

        self.flip = False

        self.frame = None
        self.display_frame = None

        self.marker_found = False
        self.marker_center = None
        self.marker_corners = None

        self.target_point = None

        self.last_angle = None

        self.photo = None

        # -------------------------------------------------
        # UI
        # -------------------------------------------------

        self.create_ui()


    # =====================================================
    # UI
    # =====================================================

    def create_ui(self):

        # -------------------------------------------------
        # TOP CONTROL BAR
        # -------------------------------------------------

        top = tk.Frame(
            self.root,
            padx=10,
            pady=10
        )

        top.pack(
            fill="x"
        )


        # IP

        tk.Label(
            top,
            text="ESP32 IP:"
        ).pack(
            side="left"
        )


        self.ip_entry = tk.Entry(
            top,
            width=18
        )

        self.ip_entry.insert(
            0,
            DEFAULT_IP
        )

        self.ip_entry.pack(
            side="left",
            padx=5
        )


        self.connect_button = tk.Button(
            top,
            text="CONNECT ESP32",
            command=self.connect_esp
        )

        self.connect_button.pack(
            side="left",
            padx=5
        )


        # Camera

        tk.Label(
            top,
            text="Camera:"
        ).pack(
            side="left",
            padx=(20, 0)
        )


        self.camera_var = tk.StringVar(
            value=str(DEFAULT_CAMERA)
        )


        self.camera_box = ttk.Combobox(
            top,
            textvariable=self.camera_var,
            values=["0", "1", "2", "3"],
            width=4,
            state="readonly"
        )

        self.camera_box.pack(
            side="left",
            padx=5
        )


        # Flip

        self.flip_var = tk.BooleanVar(
            value=False
        )


        self.flip_check = tk.Checkbutton(
            top,
            text="FLIP",
            variable=self.flip_var
        )

        self.flip_check.pack(
            side="left",
            padx=5
        )


        # Camera button

        self.camera_button = tk.Button(
            top,
            text="OPEN CAMERA",
            command=self.toggle_camera
        )

        self.camera_button.pack(
            side="left",
            padx=5
        )


        # -------------------------------------------------
        # TARGET BUTTONS
        # -------------------------------------------------

        target_bar = tk.Frame(
            self.root,
            padx=10,
            pady=5
        )

        target_bar.pack(
            fill="x"
        )


        self.start_target_button = tk.Button(
            target_bar,
            text="START TARGET",
            font=("Arial", 12, "bold"),
            width=16,
            command=self.start_target
        )

        self.start_target_button.pack(
            side="left",
            padx=5
        )


        self.clear_target_button = tk.Button(
            target_bar,
            text="CLEAR TARGET",
            width=16,
            command=self.clear_target
        )

        self.clear_target_button.pack(
            side="left",
            padx=5
        )


        self.stop_button = tk.Button(
            target_bar,
            text="STOP",
            width=12,
            command=self.stop_robot
        )

        self.stop_button.pack(
            side="left",
            padx=5
        )


        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        self.status_var = tk.StringVar(
            value="กรุณา Connect ESP32"
        )


        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Arial", 12),
            anchor="w",
            padx=15,
            pady=5
        )

        self.status_label.pack(
            fill="x"
        )


        # -------------------------------------------------
        # CANVAS
        # -------------------------------------------------

        self.canvas_frame = tk.Frame(
            self.root,
            bg="black"
        )

        self.canvas_frame.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=10
        )


        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="black",
            highlightthickness=0
        )

        self.canvas.pack(
            expand=True,
            fill="both"
        )


        # สำคัญ:
        # คลิกบน Canvas = เลือก Target

        self.canvas.bind(
            "<Button-1>",
            self.canvas_click
        )


        # -------------------------------------------------
        # INFO
        # -------------------------------------------------

        self.info_var = tk.StringVar(
            value="ArUco ID 67: ยังไม่พบ"
        )


        self.info_label = tk.Label(
            self.root,
            textvariable=self.info_var,
            font=("Arial", 11),
            anchor="w",
            padx=15
        )

        self.info_label.pack(
            fill="x"
        )


    # =====================================================
    # CONNECT ESP32
    # =====================================================

    def connect_esp(self):

        ip = self.ip_entry.get().strip()

        if ip == "":
            messagebox.showerror(
                "Error",
                "กรุณาใส่ IP ESP32"
            )
            return


        self.status_var.set(
            "กำลังเชื่อมต่อ ESP32..."
        )

        self.root.update()


        try:

            url = f"http://{ip}/"

            response = requests.get(
                url,
                timeout=3
            )


            if response.status_code == 200:

                self.connected = True

                self.status_var.set(
                    f"ESP32 CONNECTED : {ip}"
                )

                messagebox.showinfo(
                    "Connected",
                    f"เชื่อมต่อ ESP32 สำเร็จ\n\nIP: {ip}"
                )

            else:

                self.connected = False

                self.status_var.set(
                    "ESP32 ตอบกลับผิดพลาด"
                )


        except Exception as e:

            self.connected = False

            self.status_var.set(
                "เชื่อมต่อ ESP32 ไม่ได้"
            )

            messagebox.showerror(
                "ESP32 Connection Error",
                f"ไม่สามารถเชื่อมต่อ ESP32 ได้\n\n"
                f"IP: {ip}\n\n"
                f"{e}"
            )


    # =====================================================
    # CAMERA
    # =====================================================

    def toggle_camera(self):

        if self.camera_running:

            self.stop_camera()

        else:

            self.start_camera()


    # =====================================================
    # START CAMERA
    # =====================================================

    def start_camera(self):

        try:
            camera_index = int(
                self.camera_var.get()
            )

        except:

            camera_index = 0


        self.cap = cv2.VideoCapture(
            camera_index,
            cv2.CAP_DSHOW
        )


        if not self.cap.isOpened():

            # ลองเปิดแบบธรรมดาอีกครั้ง

            self.cap.release()

            self.cap = cv2.VideoCapture(
                camera_index
            )


        if not self.cap.isOpened():

            messagebox.showerror(
                "Camera Error",
                f"เปิด Camera {camera_index} ไม่ได้"
            )

            return


        # Resolution

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            960
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            720
        )


        self.camera_running = True

        self.camera_button.config(
            text="CLOSE CAMERA"
        )


        self.status_var.set(
            "Camera เปิดแล้ว"
        )


        self.update_camera()


    # =====================================================
    # STOP CAMERA
    # =====================================================

    def stop_camera(self):

        self.camera_running = False


        if self.cap is not None:

            self.cap.release()

            self.cap = None


        self.camera_button.config(
            text="OPEN CAMERA"
        )


    # =====================================================
    # UPDATE CAMERA
    # =====================================================

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


        # -------------------------------------------------
        # FLIP
        # -------------------------------------------------

        if self.flip_var.get():

            frame = cv2.flip(
                frame,
                1
            )


        self.frame = frame.copy()


        # -------------------------------------------------
        # DETECT ARUCO
        # -------------------------------------------------

        self.detect_aruco(
            frame
        )


        # -------------------------------------------------
        # DRAW TARGET
        # -------------------------------------------------

        if self.target_point is not None:

            tx, ty = self.target_point


            cv2.circle(
                frame,
                (tx, ty),
                12,
                (0, 0, 255),
                -1
            )


            cv2.circle(
                frame,
                (tx, ty),
                18,
                (255, 255, 255),
                2
            )


            cv2.putText(
                frame,
                "TARGET",
                (tx + 15, ty - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )


        # -------------------------------------------------
        # SHOW TARGET MODE
        # -------------------------------------------------

        if self.target_mode:

            cv2.putText(
                frame,
                "CLICK TO SELECT TARGET",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 255),
                2
            )


        # -------------------------------------------------
        # DISPLAY
        # -------------------------------------------------

        self.display_frame = frame.copy()

        self.show_frame(
            frame
        )


        self.root.after(
            30,
            self.update_camera
        )


    # =====================================================
    # DETECT ARUCO
    # =====================================================

    def detect_aruco(self, frame):

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )


        corners, ids, rejected = ARUCO_DETECTOR.detectMarkers(
            gray
        )


        self.marker_found = False
        self.marker_center = None
        self.marker_corners = None


        if ids is None:

            self.info_var.set(
                "ArUco ID 67: ยังไม่พบ"
            )

            return


        ids_flat = ids.flatten()


        for i, marker_id in enumerate(ids_flat):

            if marker_id != ARUCO_ID:
                continue


            pts = corners[i][0]


            # ---------------------------------------------
            # CENTER
            # ---------------------------------------------

            center_x = int(
                np.mean(pts[:, 0])
            )

            center_y = int(
                np.mean(pts[:, 1])
            )


            self.marker_center = (
                center_x,
                center_y
            )


            self.marker_corners = pts

            self.marker_found = True


            # ---------------------------------------------
            # DRAW MARKER
            # ---------------------------------------------

            cv2.polylines(
                frame,
                [pts.astype(np.int32)],
                True,
                (0, 255, 0),
                3
            )


            cv2.circle(
                frame,
                (center_x, center_y),
                8,
                (255, 0, 0),
                -1
            )


            cv2.putText(
                frame,
                "ID 67",
                (center_x + 10, center_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


            # ---------------------------------------------
            # HEADING VECTOR
            #
            # ใช้จุดกึ่งกลางของด้านบนของ Marker
            # เป็นด้านหน้า
            # ---------------------------------------------

            front_x = int(
                (pts[0][0] + pts[1][0]) / 2
            )

            front_y = int(
                (pts[0][1] + pts[1][1]) / 2
            )


            cv2.line(
                frame,
                (center_x, center_y),
                (front_x, front_y),
                (255, 0, 255),
                4
            )


            self.info_var.set(
                f"ArUco ID 67 FOUND | "
                f"Center=({center_x},{center_y})"
            )


            break


    # =====================================================
    # START TARGET
    # =====================================================

    def start_target(self):

        if not self.connected:

            messagebox.showwarning(
                "ESP32",
                "กรุณา CONNECT ESP32 ก่อน"
            )

            return


        if not self.camera_running:

            messagebox.showwarning(
                "Camera",
                "กรุณาเปิด Camera ก่อน"
            )

            return


        self.target_mode = True

        self.target_point = None

        self.status_var.set(
            "TARGET MODE: คลิกตำแหน่งเป้าหมายบนภาพ"
        )


    # =====================================================
    # CANVAS CLICK
    # =====================================================

    def canvas_click(self, event):

        # ---------------------------------------------
        # ต้องกด START TARGET ก่อน
        # ---------------------------------------------

        if not self.target_mode:

            return


        if self.display_frame is None:

            return


        # ---------------------------------------------
        # Canvas size
        # ---------------------------------------------

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()


        frame_height, frame_width = self.display_frame.shape[:2]


        # ---------------------------------------------
        # คำนวณภาพที่ถูก resize
        # ---------------------------------------------

        scale = min(
            canvas_width / frame_width,
            canvas_height / frame_height
        )


        display_width = int(
            frame_width * scale
        )

        display_height = int(
            frame_height * scale
        )


        # ---------------------------------------------
        # ภาพอยู่กลาง Canvas
        # ---------------------------------------------

        offset_x = (
            canvas_width - display_width
        ) / 2


        offset_y = (
            canvas_height - display_height
        ) / 2


        # ---------------------------------------------
        # Mouse → Frame coordinate
        # ---------------------------------------------

        x = (
            event.x - offset_x
        ) / scale


        y = (
            event.y - offset_y
        ) / scale


        # ---------------------------------------------
        # ตรวจว่า click อยู่ในภาพหรือไม่
        # ---------------------------------------------

        if (
            x < 0
            or y < 0
            or x >= frame_width
            or y >= frame_height
        ):

            return


        x = int(x)
        y = int(y)


        # ---------------------------------------------
        # SAVE TARGET
        # ---------------------------------------------

        self.target_point = (
            x,
            y
        )


        self.status_var.set(
            f"TARGET = ({x}, {y})"
        )


        # ---------------------------------------------
        # CALCULATE ANGLE
        # ---------------------------------------------

        self.calculate_and_send_angle()


    # =====================================================
    # CALCULATE ANGLE
    # =====================================================

    def calculate_and_send_angle(self):

        if self.target_point is None:
            return


        if not self.marker_found:

            messagebox.showwarning(
                "ArUco",
                "ยังไม่พบ ArUco ID 67"
            )

            return


        if self.marker_center is None:

            return


        if self.marker_corners is None:

            return


        # ---------------------------------------------
        # ROBOT CENTER
        # ---------------------------------------------

        cx, cy = self.marker_center


        # ---------------------------------------------
        # TARGET
        # ---------------------------------------------

        tx, ty = self.target_point


        # ---------------------------------------------
        # FRONT POINT
        # ---------------------------------------------

        pts = self.marker_corners


        front_x = (
            pts[0][0] + pts[1][0]
        ) / 2


        front_y = (
            pts[0][1] + pts[1][1]
        ) / 2


        # ---------------------------------------------
        # HEADING VECTOR
        # ---------------------------------------------

        hx = front_x - cx
        hy = front_y - cy


        # ---------------------------------------------
        # TARGET VECTOR
        # ---------------------------------------------

        vx = tx - cx
        vy = ty - cy


        # ---------------------------------------------
        # VECTOR LENGTH
        # ---------------------------------------------

        heading_length = math.sqrt(
            hx * hx + hy * hy
        )


        target_length = math.sqrt(
            vx * vx + vy * vy
        )


        if heading_length < 1:
            return


        if target_length < 1:
            return


        # ---------------------------------------------
        # NORMALIZE
        # ---------------------------------------------

        hx /= heading_length
        hy /= heading_length

        vx /= target_length
        vy /= target_length


        # ---------------------------------------------
        # ANGLE
        #
        # Image coordinate Y ลงด้านล่าง
        #
        # ใช้ - เพื่อให้
        # ขวา = +
        # ซ้าย = -
        # ---------------------------------------------

        cross = (
            hx * vy
            - hy * vx
        )


        dot = (
            hx * vx
            + hy * vy
        )


        angle = math.degrees(
            math.atan2(
                -cross,
                dot
            )
        )


        # ---------------------------------------------
        # ROUND
        # ---------------------------------------------

        angle = round(
            angle,
            1
        )


        self.last_angle = angle


        # ---------------------------------------------
        # DRAW ANGLE
        # ---------------------------------------------

        self.status_var.set(
            f"TARGET ({tx},{ty}) | ANGLE = {angle}°"
        )


        print()
        print("==============================")
        print("TARGET SELECTED")
        print(f"Robot: ({cx},{cy})")
        print(f"Target: ({tx},{ty})")
        print(f"Angle: {angle}")
        print("==============================")


        # ---------------------------------------------
        # SEND ESP32
        # ---------------------------------------------

        self.send_angle(
            angle
        )


    # =====================================================
    # SEND ANGLE
    # =====================================================

    def send_angle(self, angle):

        ip = self.ip_entry.get().strip()


        if ip == "":
            return


        try:

            url = f"http://{ip}/turn"


            response = requests.get(
                url,
                params={
                    "angle": angle
                },
                timeout=10
            )


            if response.status_code == 200:

                self.status_var.set(
                    f"SENT ANGLE = {angle}° | ESP32 OK"
                )

            else:

                self.status_var.set(
                    f"ESP32 ERROR: HTTP {response.status_code}"
                )


        except Exception as e:

            self.status_var.set(
                "ส่งคำสั่งไป ESP32 ไม่สำเร็จ"
            )

            print(
                "ESP32 ERROR:",
                e
            )


    # =====================================================
    # CLEAR TARGET
    # =====================================================

    def clear_target(self):

        self.target_point = None

        self.status_var.set(
            "Target cleared"
        )


    # =====================================================
    # STOP ROBOT
    # =====================================================

    def stop_robot(self):

        ip = self.ip_entry.get().strip()


        if ip == "":
            return


        try:

            # angle = 0
            # ESP32 จะ stop motor

            requests.get(
                f"http://{ip}/turn",
                params={
                    "angle": 0
                },
                timeout=3
            )


            self.status_var.set(
                "ROBOT STOP"
            )


        except Exception as e:

            print(
                "STOP ERROR:",
                e
            )


    # =====================================================
    # SHOW FRAME
    # =====================================================

    def show_frame(self, frame):

        # BGR → RGB

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        image = Image.fromarray(
            rgb
        )


        # ---------------------------------------------
        # Canvas size
        # ---------------------------------------------

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()


        if canvas_width <= 1:
            canvas_width = 960


        if canvas_height <= 1:
            canvas_height = 600


        # ---------------------------------------------
        # FIT IMAGE
        # ---------------------------------------------

        image.thumbnail(
            (
                canvas_width,
                canvas_height
            ),
            Image.Resampling.LANCZOS
        )


        self.photo = ImageTk.PhotoImage(
            image
        )


        # ---------------------------------------------
        # CLEAR
        # ---------------------------------------------

        self.canvas.delete(
            "all"
        )


        # ---------------------------------------------
        # CENTER IMAGE
        # ---------------------------------------------

        x = canvas_width // 2
        y = canvas_height // 2


        self.canvas.create_image(
            x,
            y,
            image=self.photo,
            anchor="center"
        )


    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        try:

            self.stop_robot()

        except:
            pass


        self.stop_camera()


        self.root.destroy()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = RobotControlApp(
        root
    )

    root.mainloop()