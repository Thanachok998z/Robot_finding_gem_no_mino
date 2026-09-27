import cv2
import math
import time

# =========================================================
# CAMERA
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Cannot open camera")
    exit()


# =========================================================
# WINDOW
# =========================================================

WINDOW_NAME = "Robot Gesture Control"

cv2.namedWindow(
    WINDOW_NAME,
    cv2.WINDOW_NORMAL
)

cv2.setWindowProperty(
    WINDOW_NAME,
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)


# =========================================================
# SCREEN SIZE
# =========================================================

SCREEN_W = 1280
SCREEN_H = 720


# =========================================================
# CONTROL CENTER
# =========================================================

CENTER_X = SCREEN_W // 2
CENTER_Y = SCREEN_H // 2 + 50


# =========================================================
# DIRECTION SETTINGS
# =========================================================

DEAD_ZONE = 70

# =========================================================
# TOP BUTTON SETTINGS
# =========================================================

BUTTON_W = 220
BUTTON_H = 90

BUTTON_Y = 60

buttons = {

    "GRAB": (
        CENTER_X - 350,
        BUTTON_Y,
        CENTER_X - 130,
        BUTTON_Y + BUTTON_H
    ),

    "DROP": (
        CENTER_X - 110,
        BUTTON_Y,
        CENTER_X + 110,
        BUTTON_Y + BUTTON_H
    ),

    "STOP": (
        CENTER_X + 130,
        BUTTON_Y,
        CENTER_X + 350,
        BUTTON_Y + BUTTON_H
    )
}


# =========================================================
# BUTTON PRESS
# =========================================================

current_button = None
pressed_button = None

hover_start_time = 0

PRESS_TIME = 0.5


# =========================================================
# FIND BUTTON
# =========================================================

def find_button(x, y):

    for name, (bx1, by1, bx2, by2) in buttons.items():

        if bx1 <= x <= bx2 and by1 <= y <= by2:
            return name

    return None


# =========================================================
# FIND FINGERTIP
# =========================================================

def find_fingertip(contour):

    moments = cv2.moments(contour)

    if moments["m00"] == 0:
        return None

    cx = int(
        moments["m10"] /
        moments["m00"]
    )

    cy = int(
        moments["m01"] /
        moments["m00"]
    )

    center = (cx, cy)

    fingertip = None
    max_distance = 0

    for point in contour:

        px = int(point[0][0])
        py = int(point[0][1])

        distance = math.sqrt(
            (px - cx) ** 2 +
            (py - cy) ** 2
        )

        if distance > max_distance:

            max_distance = distance

            fingertip = (
                px,
                py
            )

    return center, fingertip


# =========================================================
# FIND DIRECTION
# =========================================================

def get_direction(center, fingertip):

    cx, cy = center
    fx, fy = fingertip

    dx = fx - cx
    dy = fy - cy

    distance = math.sqrt(
        dx * dx +
        dy * dy
    )

    # -----------------------------------------
    # DEAD ZONE
    # -----------------------------------------

    if distance < DEAD_ZONE:
        return "STOP"

    # -----------------------------------------
    # COMPARE X AND Y
    # -----------------------------------------

    if abs(dx) > abs(dy):

        if dx > 0:
            return "RIGHT"

        else:
            return "LEFT"

    else:

        if dy > 0:
            return "BACKWARD"

        else:
            return "FORWARD"


# =========================================================
# SEND ROBOT COMMAND
# =========================================================

def robot_command(command):

    print("COMMAND:", command)

    # =====================================================
    # ใส่คำสั่งควบคุมรถของคุณตรงนี้
    # =====================================================

    if command == "FORWARD":

        # robot_forward()
        pass

    elif command == "BACKWARD":

        # robot_backward()
        pass

    elif command == "LEFT":

        # robot_left()
        pass

    elif command == "RIGHT":

        # robot_right()
        pass

    elif command == "GRAB":

        # robot_grab()
        pass

    elif command == "DROP":

        # robot_drop()
        pass

    elif command == "STOP":

        # robot_stop()
        pass


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    # =====================================================
    # READ CAMERA
    # =====================================================

    ret, frame = cap.read()

    if not ret:

        print("Cannot read camera")
        break


    # =====================================================
    # MIRROR IMAGE
    # =====================================================

    frame = cv2.flip(
        frame,
        1
    )


    # =====================================================
    # RESIZE
    # =====================================================

    frame = cv2.resize(
        frame,
        (
            SCREEN_W,
            SCREEN_H
        )
    )


    # =====================================================
    # SKIN DETECTION
    # =====================================================

    hsv = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2HSV
    )

    lower_skin = (
        0,
        20,
        70
    )

    upper_skin = (
        20,
        255,
        255
    )

    mask = cv2.inRange(
        hsv,
        lower_skin,
        upper_skin
    )


    # =====================================================
    # MORPHOLOGY
    # =====================================================

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (7, 7)
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )


    # =====================================================
    # FIND CONTOURS
    # =====================================================

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )


    fingertip = None
    center = None

    detected_button = None
    direction = "STOP"


    # =====================================================
    # FIND HAND
    # =====================================================

    if len(contours) > 0:

        contour = max(
            contours,
            key=cv2.contourArea
        )

        area = cv2.contourArea(
            contour
        )


        if area > 5000:

            # ---------------------------------------------
            # DRAW HAND
            # ---------------------------------------------

            cv2.drawContours(
                frame,
                [contour],
                -1,
                (255, 0, 0),
                3
            )


            # ---------------------------------------------
            # FIND FINGERTIP
            # ---------------------------------------------

            result = find_fingertip(
                contour
            )


            if result is not None:

                center, fingertip = result


                # -----------------------------------------
                # FIND DIRECTION
                # -----------------------------------------

                direction = get_direction(
                    center,
                    fingertip
                )


                # -----------------------------------------
                # FIND BUTTON
                # -----------------------------------------

                detected_button = find_button(
                    fingertip[0],
                    fingertip[1]
                )


                # =========================================
                # DRAW CENTER
                # =========================================

                cv2.circle(
                    frame,
                    center,
                    10,
                    (255, 255, 0),
                    -1
                )


                # =========================================
                # DRAW FINGERTIP
                # =========================================

                cv2.circle(
                    frame,
                    fingertip,
                    15,
                    (0, 255, 0),
                    -1
                )


                # =========================================
                # DRAW DIRECTION LINE
                # =========================================

                cv2.line(
                    frame,
                    center,
                    fingertip,
                    (0, 255, 255),
                    4
                )


                # =========================================
                # DRAW DIRECTION ARROW
                # =========================================

                cv2.arrowedLine(
                    frame,
                    center,
                    fingertip,
                    (0, 255, 255),
                    5,
                    tipLength=0.2
                )


    # =====================================================
    # BUTTON LOGIC
    # =====================================================

    if detected_button != current_button:

        current_button = detected_button

        hover_start_time = time.time()

        pressed_button = None


    else:

        if current_button is not None:

            elapsed = (
                time.time()
                -
                hover_start_time
            )


            if elapsed >= PRESS_TIME:

                if pressed_button != current_button:

                    pressed_button = current_button

                    robot_command(
                        current_button
                    )


    # =====================================================
    # DIRECTION COMMAND
    # =====================================================

    # ถ้าไม่ได้กำลังจิ้มปุ่ม
    # ให้ใช้การหมุนนิ้วควบคุมทิศทาง

    if detected_button is None:

        robot_command(
            direction
        )


    # =====================================================
    # DRAW DIRECTION CENTER
    # =====================================================

    cv2.circle(
        frame,
        (
            CENTER_X,
            CENTER_Y
        ),
        DEAD_ZONE,
        (100, 100, 100),
        3
    )


    # =====================================================
    # DRAW TOP BUTTONS
    # =====================================================

    for name, (
        bx1,
        by1,
        bx2,
        by2
    ) in buttons.items():

        # ---------------------------------------------
        # HIGHLIGHT BUTTON
        # ---------------------------------------------

        if name == current_button:

            color = (
                0,
                255,
                255
            )

            thickness = 6

        else:

            color = (
                255,
                255,
                255
            )

            thickness = 4


        # ---------------------------------------------
        # RECTANGLE
        # ---------------------------------------------

        cv2.rectangle(
            frame,
            (bx1, by1),
            (bx2, by2),
            color,
            thickness
        )


        # ---------------------------------------------
        # TEXT SIZE
        # ---------------------------------------------

        text_size = cv2.getTextSize(
            name,
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            3
        )[0]


        text_x = (
            bx1
            +
            (
                bx2
                -
                bx1
                -
                text_size[0]
            ) // 2
        )


        text_y = (
            by1
            +
            (
                by2
                -
                by1
                +
                text_size[1]
            ) // 2
        )


        # ---------------------------------------------
        # DRAW TEXT
        # ---------------------------------------------

        cv2.putText(
            frame,
            name,
            (
                text_x,
                text_y
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            color,
            3
        )


    # =====================================================
    # STATUS
    # =====================================================

    if current_button is not None:

        status = (
            "BUTTON: "
            + current_button
        )

    else:

        status = (
            "DIRECTION: "
            + direction
        )


    cv2.putText(
        frame,
        status,
        (40, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 255),
        3
    )


    # =====================================================
    # FINGERTIP COORDINATE
    # =====================================================

    if fingertip is not None:

        coordinate_text = (
            f"X: {fingertip[0]}   "
            f"Y: {fingertip[1]}"
        )

        cv2.putText(
            frame,
            coordinate_text,
            (40, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )


    # =====================================================
    # SHOW
    # =====================================================

    cv2.imshow(
        WINDOW_NAME,
        frame
    )


    # =====================================================
    # KEYBOARD
    # =====================================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break


# =========================================================
# CLEANUP
# =========================================================

cap.release()

cv2.destroyAllWindows()