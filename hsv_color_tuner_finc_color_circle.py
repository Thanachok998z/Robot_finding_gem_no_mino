import cv2
import numpy as np
import math


# =========================================================
# สีทั้งหมด
# =========================================================

colors = {

    "GREEN":
        ((35, 40, 40),
         (85, 255, 255)),

    "BLUE":
        ((88, 160, 50),
         (105, 255, 230)),

    "RED":
        ((0, 60, 40),
         (10, 255, 255)),

    "PURPLE":
        ((130, 40, 40),
         (170, 255, 255)),

    "CYAN":
        ((80, 20, 120),
         (100, 155, 255)),

    "ORANGE":
        ((4, 94, 95),
         (21, 180, 255))
}


color_names = list(colors.keys())


# =========================================================
# สีที่กำลังปรับ
# =========================================================

selected_color = "GREEN"

last_color_index = -1


# =========================================================
# เปิดกล้อง index 2
# =========================================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ไม่สามารถเปิดกล้อง index 2 ได้")
    exit()


# =========================================================
# Trackbar
# =========================================================

def nothing(x):
    pass


cv2.namedWindow(
    "HSV Tuner",
    cv2.WINDOW_NORMAL
)


# =========================================================
# Trackbar เลือกสี
# =========================================================

cv2.createTrackbar(
    "Color",
    "HSV Tuner",
    0,
    5,
    nothing
)


# =========================================================
# Trackbar HSV
# =========================================================

cv2.createTrackbar(
    "H Min",
    "HSV Tuner",
    0,
    179,
    nothing
)

cv2.createTrackbar(
    "H Max",
    "HSV Tuner",
    179,
    179,
    nothing
)

cv2.createTrackbar(
    "S Min",
    "HSV Tuner",
    0,
    255,
    nothing
)

cv2.createTrackbar(
    "S Max",
    "HSV Tuner",
    255,
    255,
    nothing
)

cv2.createTrackbar(
    "V Min",
    "HSV Tuner",
    0,
    255,
    nothing
)

cv2.createTrackbar(
    "V Max",
    "HSV Tuner",
    255,
    255,
    nothing
)


# =========================================================
# โหลดค่า HSV ของสีเข้า Slider
# =========================================================

def load_color_to_slider(color_name):

    lower, upper = colors[color_name]

    cv2.setTrackbarPos(
        "H Min",
        "HSV Tuner",
        lower[0]
    )

    cv2.setTrackbarPos(
        "H Max",
        "HSV Tuner",
        upper[0]
    )

    cv2.setTrackbarPos(
        "S Min",
        "HSV Tuner",
        lower[1]
    )

    cv2.setTrackbarPos(
        "S Max",
        "HSV Tuner",
        upper[1]
    )

    cv2.setTrackbarPos(
        "V Min",
        "HSV Tuner",
        lower[2]
    )

    cv2.setTrackbarPos(
        "V Max",
        "HSV Tuner",
        upper[2]
    )


# เริ่มต้น
load_color_to_slider("GREEN")


print("===================================")
print("เปิดกล้อง index 2 แล้ว")
print()
print("สีที่ใช้:")
print("GREEN")
print("BLUE")
print("RED")
print("PURPLE")
print("CYAN")
print("ORANGE")
print()
print("กด S = บันทึกค่า HSV")
print("กด Q = ออก")
print("===================================")


# =========================================================
# Real-time
# =========================================================

while True:

    # =====================================================
    # อ่านกล้อง
    # =====================================================

    ret, frame = cap.read()

    if not ret:
        print("ไม่สามารถอ่านภาพจากกล้องได้")
        break


    # เก็บภาพ Original
    original = frame.copy()


    # =====================================================
    # HSV
    # =====================================================

    hsv = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2HSV
    )


    # =====================================================
    # อ่านสีที่เลือก
    # =====================================================

    color_index = cv2.getTrackbarPos(
        "Color",
        "HSV Tuner"
    )


    # ถ้าเปลี่ยนสี
    if color_index != last_color_index:

        selected_color = color_names[color_index]

        load_color_to_slider(
            selected_color
        )

        last_color_index = color_index


    # =====================================================
    # อ่านค่า HSV
    # =====================================================

    h_min = cv2.getTrackbarPos(
        "H Min",
        "HSV Tuner"
    )

    h_max = cv2.getTrackbarPos(
        "H Max",
        "HSV Tuner"
    )

    s_min = cv2.getTrackbarPos(
        "S Min",
        "HSV Tuner"
    )

    s_max = cv2.getTrackbarPos(
        "S Max",
        "HSV Tuner"
    )

    v_min = cv2.getTrackbarPos(
        "V Min",
        "HSV Tuner"
    )

    v_max = cv2.getTrackbarPos(
        "V Max",
        "HSV Tuner"
    )


    # =====================================================
    # บันทึก HSV ของสีปัจจุบัน
    # =====================================================

    colors[selected_color] = (

        (h_min, s_min, v_min),

        (h_max, s_max, v_max)
    )


    # =====================================================
    # Mask ของสีที่เลือก
    # =====================================================

    lower = np.array([
        h_min,
        s_min,
        v_min
    ])

    upper = np.array([
        h_max,
        s_max,
        v_max
    ])


    mask = cv2.inRange(
        hsv,
        lower,
        upper
    )


    # =====================================================
    # ลด Noise
    # =====================================================

    kernel = np.ones(
        (5, 5),
        np.uint8
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )


    # =====================================================
    # ภาพแยกสี
    # =====================================================

    separated = cv2.bitwise_and(
        frame,
        frame,
        mask=mask
    )


    # =====================================================
    # ภาพสำหรับ Detection
    # =====================================================

    detection = frame.copy()


    # =====================================================
    # หา Contour
    # =====================================================

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )


    count = 0


    # =====================================================
    # ตรวจวัตถุ
    # =====================================================

    for contour in contours:

        area = cv2.contourArea(
            contour
        )


        if area < 3000:
            continue


        perimeter = cv2.arcLength(
            contour,
            True
        )

        if perimeter == 0:
            continue


        # Circularity

        circularity = (
            4 * math.pi * area
            / (perimeter * perimeter)
        )


        if circularity < 0.75:
            continue


        # Bounding Box

        x, y, w, h = cv2.boundingRect(
            contour
        )


        # Ratio

        ratio = w / h

        if ratio < 0.8 or ratio > 1.2:
            continue


        # Center

        center_x = x + w // 2
        center_y = y + h // 2


        count += 1


        # =================================================
        # กรอบ
        # =================================================

        cv2.rectangle(
            detection,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            3
        )


        # =================================================
        # จุดกลาง
        # =================================================

        cv2.circle(
            detection,
            (center_x, center_y),
            5,
            (0, 0, 255),
            -1
        )


        # =================================================
        # ชื่อสี
        # =================================================

        cv2.putText(
            detection,
            selected_color,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            2
        )


        # =================================================
        # พิกัด
        # =================================================

        cv2.putText(
            detection,
            f"({center_x},{center_y})",
            (x + 5, y + h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            1
        )


    # =====================================================
    # ข้อความด้านบน
    # =====================================================

    hsv_text = (
        f"{selected_color}  "
        f"H:{h_min}-{h_max} "
        f"S:{s_min}-{s_max} "
        f"V:{v_min}-{v_max}"
    )


    cv2.putText(
        detection,
        hsv_text,
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )


    cv2.putText(
        detection,
        f"Detected: {count}",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 255),
        2
    )


    # =====================================================
    # Mask เปลี่ยนเป็นภาพ 3 channel
    # =====================================================

    mask_color = cv2.cvtColor(
        mask,
        cv2.COLOR_GRAY2BGR
    )


    # =====================================================
    # เขียนชื่อแต่ละช่อง
    # =====================================================

    cv2.putText(
        original,
        "ORIGINAL",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )


    cv2.putText(
        mask_color,
        f"MASK - {selected_color}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )


    cv2.putText(
        separated,
        f"SEPARATED - {selected_color}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )


    cv2.putText(
        detection,
        "DETECTION",
        (20, 105),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 0, 255),
        2
    )


    # =====================================================
    # ลดขนาด
    # =====================================================

    scale = 0.45

    original_small = cv2.resize(
        original,
        None,
        fx=scale,
        fy=scale
    )

    mask_small = cv2.resize(
        mask_color,
        None,
        fx=scale,
        fy=scale
    )

    separated_small = cv2.resize(
        separated,
        None,
        fx=scale,
        fy=scale
    )

    detection_small = cv2.resize(
        detection,
        None,
        fx=scale,
        fy=scale
    )


    # =====================================================
    # 2 x 2
    # =====================================================

    top = cv2.hconcat([
        original_small,
        mask_small
    ])

    bottom = cv2.hconcat([
        separated_small,
        detection_small
    ])


    final = cv2.vconcat([
        top,
        bottom
    ])


    # =====================================================
    # แสดง
    # =====================================================

    cv2.imshow(
        "HSV Tuner",
        final
    )


    # =====================================================
    # Keyboard
    # =====================================================

    key = cv2.waitKey(1) & 0xFF


    # =====================================================
    # S = บันทึก HSV
    # =====================================================

    if key == ord("s"):

        print()
        print("==============================")

        print(
            f"สี = {selected_color}"
        )

        print(
            f"H = {h_min} - {h_max}"
        )

        print(
            f"S = {s_min} - {s_max}"
        )

        print(
            f"V = {v_min} - {v_max}"
        )

        print()

        print(
            f"lower = np.array([{h_min}, {s_min}, {v_min}])"
        )

        print(
            f"upper = np.array([{h_max}, {s_max}, {v_max}])"
        )

        print("==============================")
        print()


    # =====================================================
    # Q = ออก
    # =====================================================

    if key == ord("q"):
        break


# =========================================================
# ปิด
# =========================================================

cap.release()

cv2.destroyAllWindows()