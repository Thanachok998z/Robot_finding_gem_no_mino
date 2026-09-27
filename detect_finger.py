from pathlib import Path

import cv2
import math
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# =========================================================
# SETTINGS
# =========================================================

MODEL_PATH = Path(__file__).with_name("hand_landmarker.task")

WINDOW_NAME = "Robot Gesture Control"

NUM_HANDS = 2


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
# COMMAND
# =========================================================

def robot_command(command):

    print("COMMAND:", command)

    # =====================================================
    # ใส่คำสั่งหุ่นยนต์จริงตรงนี้
    # =====================================================

    if command == "LEFT":

        # robot_left()
        pass

    elif command == "RIGHT":

        # robot_right()
        pass

    elif command == "FORWARD":

        # robot_forward()
        pass

    elif command == "BACKWARD":

        # robot_backward()
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
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # CHECK MODEL
    # -----------------------------------------------------

    if not MODEL_PATH.is_file():

        raise FileNotFoundError(
            f"ไม่พบไฟล์โมเดล: {MODEL_PATH}\n"
            "โปรดวาง hand_landmarker.task "
            "ไว้โฟลเดอร์เดียวกับไฟล์ Python"
        )


    # -----------------------------------------------------
    # MEDIAPIPE
    # -----------------------------------------------------

    options = vision.HandLandmarkerOptions(

        base_options=python.BaseOptions(
            model_asset_path=str(MODEL_PATH)
        ),

        running_mode=vision.RunningMode.IMAGE,

        num_hands=NUM_HANDS,

        min_hand_detection_confidence=0.7,

        min_hand_presence_confidence=0.7,

        min_tracking_confidence=0.7
    )


    detector = (
        vision.HandLandmarker
        .create_from_options(options)
    )


    # -----------------------------------------------------
    # CAMERA
    # -----------------------------------------------------

    cap = cv2.VideoCapture(0)


    if not cap.isOpened():

        detector.close()

        raise RuntimeError(
            "ไม่สามารถเปิดกล้องได้"
        )


    # -----------------------------------------------------
    # CONNECTIONS
    # -----------------------------------------------------

    connections = [

        (
            connection.start,
            connection.end
        )

        for connection
        in vision.HandLandmarksConnections.HAND_CONNECTIONS
    ]


    # =====================================================
    # LAST COMMAND
    # =====================================================

    last_command = None


    try:

        while True:

            # =============================================
            # READ CAMERA
            # =============================================

            ret, frame = cap.read()


            if not ret:

                robot_command("STOP")

                break


            # =============================================
            # MIRROR
            # =============================================

            frame = cv2.flip(
                frame,
                1
            )


            # =============================================
            # RGB
            # =============================================

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )


            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb
            )


            # =============================================
            # DETECT
            # =============================================

            result = detector.detect(
                mp_image
            )


            # =============================================
            # RESET
            # =============================================

            left_fingers = None
            right_fingers = None

            left_command = "STOP"
            right_command = "STOP"


            # =============================================
            # PROCESS HANDS
            # =============================================

            for landmarks, handednesses in zip(

                result.hand_landmarks,

                result.handedness
            ):

                # -----------------------------------------
                # DRAW
                # -----------------------------------------

                draw_hand(
                    frame,
                    landmarks,
                    connections
                )


                # -----------------------------------------
                # MEDIAPIPE HAND
                # -----------------------------------------

                mp_hand = (
                    handednesses[0].category_name
                )


                # =================================================
                # IMPORTANT
                #
                # ภาพถูก flip แบบ mirror
                # ดังนั้นต้องสลับ Left / Right
                # เพื่อให้ตรงกับมือจริงของผู้ใช้
                # =================================================

                if mp_hand == "Left":

                    real_hand = "Right"

                else:

                    real_hand = "Left"


                # -----------------------------------------
                # COUNT
                # -----------------------------------------

                fingers = count_fingers(
                    landmarks,
                    real_hand
                )


                # =============================================
                # RIGHT HAND
                # =============================================

                if real_hand == "Right":

                    right_fingers = fingers

                    right_command = (
                        right_hand_command(
                            fingers
                        )
                    )


                # =============================================
                # LEFT HAND
                # =============================================

                elif real_hand == "Left":

                    left_fingers = fingers

                    left_command = (
                        left_hand_command(
                            fingers
                        )
                    )


                # =============================================
                # LABEL
                # =============================================

                wrist = landmarks[0]

                x = int(
                    wrist.x * frame.shape[1]
                )

                y = int(
                    wrist.y * frame.shape[0]
                )


                cv2.putText(
                    frame,
                    f"{real_hand}: {fingers}",
                    (
                        x - 70,
                        y - 30
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )


            # =====================================================
            # COMMAND PRIORITY
            # =====================================================

            # ---------------------------------------------
            # ไม่มีมือ = STOP
            # ---------------------------------------------

            if (
                left_fingers is None
                and
                right_fingers is None
            ):

                command = "STOP"


            # ---------------------------------------------
            # มีมือขวา
            # ---------------------------------------------

            elif right_fingers is not None:

                command = right_command


            # ---------------------------------------------
            # มีแต่มือซ้าย
            # ---------------------------------------------

            elif left_fingers is not None:

                command = left_command


            else:

                command = "STOP"


            # =====================================================
            # SEND COMMAND
            # =====================================================

            if command != last_command:

                robot_command(command)

                last_command = command


            # =====================================================
            # DISPLAY
            # =====================================================

            cv2.rectangle(
                frame,
                (20, 20),
                (500, 180),
                (0, 0, 0),
                -1
            )


            # ---------------------------------------------
            # RIGHT HAND
            # ---------------------------------------------

            if right_fingers is not None:

                right_text = (
                    f"RIGHT: {right_fingers} "
                    f"-> {right_command}"
                )

            else:

                right_text = "RIGHT: -"


            cv2.putText(
                frame,
                right_text,
                (40, 65),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )


            # ---------------------------------------------
            # LEFT HAND
            # ---------------------------------------------

            if left_fingers is not None:

                left_text = (
                    f"LEFT: {left_fingers} "
                    f"-> {left_command}"
                )

            else:

                left_text = "LEFT: -"


            cv2.putText(
                frame,
                left_text,
                (40, 105),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )


            # ---------------------------------------------
            # CURRENT COMMAND
            # ---------------------------------------------

            cv2.putText(
                frame,
                f"COMMAND: {command}",
                (40, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            # =============================================
            # SHOW
            # =============================================

            cv2.imshow(
                WINDOW_NAME,
                frame
            )


            # =============================================
            # QUIT
            # =============================================

            if cv2.waitKey(1) & 0xFF == ord("q"):

                robot_command("STOP")

                break


    finally:

        robot_command("STOP")

        cap.release()

        detector.close()

        cv2.destroyAllWindows()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()
