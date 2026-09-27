import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox
import urllib.request
import urllib.error
import threading
import math
import time


# =====================================================
# CONFIG
# =====================================================

ARUCO_ID = 67

ESP_IP = ""

camera_index = 1

flip_mode = 0

target_mode = False

camera = None

running = False

frame_width = 0
frame_height = 0

roi_x1 = 0
roi_y1 = 0
roi_x2 = 0
roi_y2 = 0

selecting_roi = False
roi_start = None


# =====================================================
# ARUCO
# =====================================================

aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

aruco_parameters = cv2.aruco.DetectorParameters()

aruco_detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    aruco_parameters
)


# =====================================================
# ESP CONNECT
# =====================================================

def check_esp(ip):

    try:

        url = f"http://{ip}/"

        with urllib.request.urlopen(
            url,
            timeout=2
        ) as response:

            data = response.read().decode()

            if "ESP32 ROBOT OK" in data:

                return True

    except Exception:

        return False

    return False


# =====================================================
# SEND ANGLE
# =====================================================

def send_angle(angle):

    global ESP_IP

    try:

        url = (
            f"http://{ESP_IP}/turn"
            f"?angle={angle:.2f}"
        )

        with urllib.request.urlopen(
            url,
            timeout=3
        ) as response:

            result = response.read().decode()

            print(
                f"ESP RESPONSE: {result}"
            )

        return True

    except Exception as e:

        print(
            "ESP ERROR:",
            e
        )

        return False


# =====================================================
# CONNECT WINDOW
# =====================================================

def connect_window():

    global ESP_IP

    root = tk.Tk()

    root.title("ESP32 Robot Connect")

    root.geometry("500x300")

    root.resizable(False, False)


    title = tk.Label(
        root,
        text="ESP32 ROBOT",
        font=("Arial", 24, "bold")
    )

    title.pack(
        pady=30
    )


    label = tk.Label(
        root,
        text="ESP32 IP Address",
        font=("Arial", 14)
    )

    label.pack()


    ip_entry = tk.Entry(
        root,
        font=("Arial", 16),
        justify="center"
    )

    ip_entry.pack(
        pady=10,
        ipadx=30
    )

    ip_entry.insert(
        0,
        "192.168.1.50"
    )


    status = tk.Label(
        root,
        text="Not Connected",
        font=("Arial", 13)
    )

    status.pack(
        pady=10
    )


    def connect():

        global ESP_IP

        ip = ip_entry.get().strip()

        if ip == "":

            status.config(
                text="Please enter IP"
            )

            return


        status.config(
            text="Connecting..."
        )

        root.update()


        if check_esp(ip):

            ESP_IP = ip

            status.config(
                text="CONNECTED",
            )

            root.update()

            time.sleep(0.5)

            root.destroy()

            open_camera_window()

        else:

            status.config(
                text="Connection failed"
            )

            messagebox.showerror(
                "ESP32",
                "ไม่สามารถเชื่อมต่อ ESP32 ได้"
            )


    connect_button = tk.Button(
        root,
        text="CONNECT",
        font=("Arial", 15, "bold"),
        width=15,
        height=2,
        command=connect
    )

    connect_button.pack(
        pady=10
    )


    root.mainloop()


# =====================================================
# FIND ARUCO
# =====================================================

def detect_aruco(frame):

    corners, ids, rejected = \
        aruco_detector.detectMarkers(frame)

    marker = None

    if ids is not None:

        for i, marker_id in enumerate(ids.flatten()):

            if marker_id == ARUCO_ID:

                marker = corners[i][0]

                break


    return marker


# =====================================================
# CALCULATE ROBOT ANGLE
# =====================================================

def calculate_angle(marker, target):

    # -----------------------------------------
    # ArUco corners
    #
    # 0 ---- 1
    # |      |
    # 3 ---- 2
    # -----------------------------------------

    p0 = marker[0]
    p1 = marker[1]

    center = np.mean(
        marker,
        axis=0
    )

    # -----------------------------------------
    # Marker direction
    #
    # ใช้เส้นจาก corner 0 -> corner 1
    # เป็นด้านบนของ marker
    # -----------------------------------------

    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]

    marker_angle = math.atan2(
        dy,
        dx
    )

    # -----------------------------------------
    # Vector robot -> target
    # -----------------------------------------

    tx = target[0] - center[0]
    ty = target[1] - center[1]

    target_angle = math.atan2(
        ty,
        tx
    )

    # -----------------------------------------
    # Difference
    # -----------------------------------------

    angle = (
        target_angle -
        marker_angle
    )

    angle = math.degrees(angle)

    # -----------------------------------------
    # Normalize -180 to +180
    # -----------------------------------------

    while angle > 180:

        angle -= 360

    while angle < -180:

        angle += 360


    return angle, center, marker_angle


# =====================================================
# CAMERA WINDOW
# =====================================================

def open_camera_window():

    global camera
    global running
    global camera_index
    global flip_mode

    running = True


    # -----------------------------------------
    # Create UI
    # -----------------------------------------

    root = tk.Tk()

    root.title(
        "Robot ArUco Target Control"
    )

    root.geometry(
        "1200x800"
    )


    # -----------------------------------------
    # TOP CONTROL
    # -----------------------------------------

    control = tk.Frame(
        root
    )

    control.pack(
        side=tk.TOP,
        fill=tk.X,
        pady=5
    )


    tk.Label(
        control,
        text="Camera:"
    ).pack(
        side=tk.LEFT,
        padx=5
    )


    camera_var = tk.StringVar(
        value="0"
    )

    camera_menu = tk.OptionMenu(
        control,
        camera_var,
        "0",
        "1",
        "2",
        "3"
    )

    camera_menu.pack(
        side=tk.LEFT
    )


    def change_camera():

        global camera

        index = int(
            camera_var.get()
        )

        if camera is not None:

            camera.release()

        camera = cv2.VideoCapture(
            index
        )

        camera.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            1280
        )

        camera.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            720
        )


    tk.Button(
        control,
        text="OPEN CAMERA",
        command=change_camera
    ).pack(
        side=tk.LEFT,
        padx=10
    )


    # -----------------------------------------
    # FLIP
    # -----------------------------------------

    flip_var = tk.IntVar(
        value=0
    )


    def change_flip():

        global flip_mode

        flip_mode = flip_var.get()


    tk.Checkbutton(
        control,
        text="FLIP",
        variable=flip_var,
        command=change_flip
    ).pack(
        side=tk.LEFT,
        padx=10
    )


    # -----------------------------------------
    # ROI
    # -----------------------------------------

    roi_var = tk.BooleanVar(
        value=False
    )


    def toggle_roi():

        global selecting_roi

        selecting_roi = False


    tk.Checkbutton(
        control,
        text="ROI",
        variable=roi_var,
        command=toggle_roi
    ).pack(
        side=tk.LEFT,
        padx=10
    )


    # -----------------------------------------
    # TARGET MODE
    # -----------------------------------------

    target_button = tk.Button(
        control,
        text="START TARGET",
        font=("Arial", 12, "bold")
    )

    target_button.pack(
        side=tk.LEFT,
        padx=20
    )


    status_label = tk.Label(
        control,
        text="TARGET OFF",
        font=("Arial", 12, "bold")
    )

    status_label.pack(
        side=tk.LEFT,
        padx=10
    )


    def start_target():

        global target_mode

        target_mode = True

        status_label.config(
            text="TARGET ON"
        )

        target_button.config(
            text="TARGET ACTIVE"
        )


    target_button.config(
        command=start_target
    )


    # -----------------------------------------
    # CLEAR ROI
    # -----------------------------------------

    def clear_roi():

        global roi_x1
        global roi_y1
        global roi_x2
        global roi_y2

        roi_x1 = 0
        roi_y1 = 0
        roi_x2 = 0
        roi_y2 = 0


    tk.Button(
        control,
        text="CLEAR ROI",
        command=clear_roi
    ).pack(
        side=tk.LEFT,
        padx=5
    )


    # -----------------------------------------
    # CAMERA WINDOW
    # -----------------------------------------

    window_name = "CAMERA"

    cv2.namedWindow(
        window_name
    )


    # =================================================
    # MOUSE
    # =================================================

    def mouse_callback(
        event,
        x,
        y,
        flags,
        param
    ):

        global roi_x1
        global roi_y1
        global roi_x2
        global roi_y2

        global selecting_roi
        global roi_start

        # -----------------------------------------
        # ROI
        # -----------------------------------------

        if roi_var.get():

            if event == cv2.EVENT_LBUTTONDOWN:

                selecting_roi = True

                roi_start = (
                    x,
                    y
                )

                roi_x1 = x
                roi_y1 = y
                roi_x2 = x
                roi_y2 = y


            elif (
                event == cv2.EVENT_MOUSEMOVE
                and selecting_roi
            ):

                roi_x2 = x
                roi_y2 = y


            elif (
                event == cv2.EVENT_LBUTTONUP
                and selecting_roi
            ):

                selecting_roi = False

                roi_x2 = x
                roi_y2 = y

            return


        # -----------------------------------------
        # TARGET CLICK
        # -----------------------------------------

        if (
            event ==
            cv2.EVENT_LBUTTONDOWN
            and target_mode
        ):

            if latest_marker is None:

                print(
                    "ArUco 67 not detected"
                )

                return


            target = (
                x,
                y
            )


            try:

                angle, center, marker_angle = \
                    calculate_angle(
                        latest_marker,
                        target
                    )


                print()
                print(
                    "======================"
                )

                print(
                    "TARGET:",
                    target
                )

                print(
                    "ANGLE:",
                    round(angle, 2)
                )

                print(
                    "======================"
                )


                # ---------------------------------
                # SEND TO ESP
                # ---------------------------------

                success = send_angle(
                    angle
                )


                if success:

                    print(
                        "ANGLE SENT TO ESP32"
                    )

                else:

                    print(
                        "FAILED TO SEND"
                    )


            except Exception as e:

                print(
                    "ANGLE ERROR:",
                    e
                )


    cv2.setMouseCallback(
        window_name,
        mouse_callback
    )


    # =================================================
    # CAMERA
    # =================================================

    camera = cv2.VideoCapture(
        camera_index
    )

    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        1280
    )

    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        720
    )


    # latest marker
    global latest_marker

    latest_marker = None


    # =================================================
    # LOOP
    # =================================================

    while running:

        ret, frame = camera.read()

        if not ret:

            print(
                "Cannot read camera"
            )

            break


        # -----------------------------------------
        # Flip
        # -----------------------------------------

        if flip_mode == 1:

            frame = cv2.flip(
                frame,
                1
            )


        # -----------------------------------------
        # Store dimensions
        # -----------------------------------------

        frame_height, frame_width = \
            frame.shape[:2]


        # -----------------------------------------
        # ROI
        # -----------------------------------------

        if roi_var.get():

            x1 = min(
                roi_x1,
                roi_x2
            )

            x2 = max(
                roi_x1,
                roi_x2
            )

            y1 = min(
                roi_y1,
                roi_y2
            )

            y2 = max(
                roi_y1,
                roi_y2
            )


            if (
                x2 > x1
                and y2 > y1
            ):

                roi_frame = frame[
                    y1:y2,
                    x1:x2
                ]

            else:

                roi_frame = frame

        else:

            roi_frame = frame


        # -----------------------------------------
        # ArUco
        # -----------------------------------------

        marker = detect_aruco(
            roi_frame
        )


        latest_marker = None


        if marker is not None:

            # -------------------------------------
            # Convert ROI coordinates
            # back to full image
            # -------------------------------------

            if roi_var.get():

                marker = marker.copy()

                marker[:, 0] += min(
                    roi_x1,
                    roi_x2
                )

                marker[:, 1] += min(
                    roi_y1,
                    roi_y2
                )


            latest_marker = marker


            # -------------------------------------
            # Draw marker
            # -------------------------------------

            pts = marker.astype(
                np.int32
            )

            cv2.polylines(
                frame,
                [pts],
                True,
                (0, 255, 0),
                3
            )


            # -------------------------------------
            # Center
            # -------------------------------------

            center = np.mean(
                marker,
                axis=0
            ).astype(int)


            cv2.circle(
                frame,
                tuple(center),
                7,
                (0, 0, 255),
                -1
            )


            # -------------------------------------
            # Direction
            # -------------------------------------

            p0 = marker[0]
            p1 = marker[1]

            dx = p1[0] - p0[0]
            dy = p1[1] - p0[1]

            length = math.sqrt(
                dx * dx +
                dy * dy
            )


            if length > 0:

                ux = dx / length
                uy = dy / length

                arrow_length = 100

                end = (
                    int(
                        center[0]
                        + ux
                        * arrow_length
                    ),
                    int(
                        center[1]
                        + uy
                        * arrow_length
                    )
                )


                cv2.arrowedLine(
                    frame,
                    tuple(center),
                    end,
                    (255, 0, 0),
                    5,
                    tipLength=0.2
                )


            # -------------------------------------
            # ID
            # -------------------------------------

            cv2.putText(
                frame,
                "ArUco ID 67",
                (
                    int(center[0] - 70),
                    int(center[1] - 30)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


        # -----------------------------------------
        # Draw ROI
        # -----------------------------------------

        if roi_var.get():

            x1 = min(
                roi_x1,
                roi_x2
            )

            x2 = max(
                roi_x1,
                roi_x2
            )

            y1 = min(
                roi_y1,
                roi_y2
            )

            y2 = max(
                roi_y1,
                roi_y2
            )


            if (
                x2 > x1
                and y2 > y1
            ):

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (255, 255, 0),
                    2
                )


        # -----------------------------------------
        # Status
        # -----------------------------------------

        cv2.putText(
            frame,
            f"ESP: {ESP_IP}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            f"Camera: {camera_index}",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        if target_mode:

            cv2.putText(
                frame,
                "TARGET MODE: ON",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

        else:

            cv2.putText(
                frame,
                "TARGET MODE: OFF",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )


        # -----------------------------------------
        # Show
        # -----------------------------------------

        cv2.imshow(
            window_name,
            frame
        )


        key = cv2.waitKey(1) & 0xFF


        if key == 27 or key == ord('q'):

            running = False

            break


    # =================================================
    # CLEANUP
    # =================================================

    if camera is not None:

        camera.release()

    cv2.destroyAllWindows()

    root.destroy()


# =====================================================
# START
# =====================================================

if __name__ == "__main__":

    connect_window()