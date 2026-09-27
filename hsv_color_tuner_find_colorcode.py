import cv2
import numpy as np


# =========================
# เปิดกล้อง index 2
# =========================

cap = cv2.VideoCapture(2)

if not cap.isOpened():
    print("ไม่สามารถเปิดกล้อง index 2 ได้")
    exit()


def nothing(x):
    pass


# =========================
# Window
# =========================

cv2.namedWindow(
    "HSV Tuner",
    cv2.WINDOW_NORMAL
)

# เปิดเต็มจอ
cv2.setWindowProperty(
    "HSV Tuner",
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)


# =========================
# Slider
# =========================

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


# =========================
# Real-time
# =========================

while True:

    # =========================
    # อ่านภาพจากกล้อง
    # =========================

    ret, img = cap.read()

    if not ret:
        print("ไม่สามารถอ่านภาพจากกล้องได้")
        break


    # =========================
    # แปลง BGR -> HSV
    # =========================

    hsv = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2HSV
    )


    # =========================
    # อ่านค่า Slider
    # =========================

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


    # =========================
    # HSV Mask
    # =========================

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


    # =========================
    # Result
    # =========================

    result = cv2.bitwise_and(
        img,
        img,
        mask=mask
    )


    # =========================
    # ใส่ค่า HSV บนภาพ
    # =========================

    display = img.copy()

    text = (
        f"H:{h_min}-{h_max}  "
        f"S:{s_min}-{s_max}  "
        f"V:{v_min}-{v_max}"
    )

    cv2.putText(
        display,
        text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 0, 255),
        2
    )


    # =========================
    # Mask เป็นภาพสี
    # =========================

    mask_color = cv2.cvtColor(
        mask,
        cv2.COLOR_GRAY2BGR
    )


    # =========================
    # ลดขนาดแต่ละภาพ
    # =========================

    scale = 0.45

    display = cv2.resize(
        display,
        None,
        fx=scale,
        fy=scale
    )

    mask_color = cv2.resize(
        mask_color,
        None,
        fx=scale,
        fy=scale
    )

    result = cv2.resize(
        result,
        None,
        fx=scale,
        fy=scale
    )


    # ช่องที่ 4 เอาภาพเดิมมาแสดง
    original_small = display.copy()


    # =========================
    # 2 x 2
    # =========================

    top = cv2.hconcat([
        display,
        mask_color
    ])

    bottom = cv2.hconcat([
        result,
        original_small
    ])

    final = cv2.vconcat([
        top,
        bottom
    ])


    # =========================
    # แสดง
    # =========================

    cv2.imshow(
        "HSV Tuner",
        final
    )


    # =========================
    # Keyboard
    # =========================

    key = cv2.waitKey(1) & 0xFF


    # =========================
    # กด S
    # =========================

    if key == ord("s"):

        print("\n======================")
        print("HSV ที่เลือก:")

        print(
            f"H = {h_min} - {h_max}"
        )

        print(
            f"S = {s_min} - {s_max}"
        )

        print(
            f"V = {v_min} - {v_max}"
        )

        print("\nโค้ด:")

        print(
            f"lower = np.array([{h_min}, {s_min}, {v_min}])"
        )

        print(
            f"upper = np.array([{h_max}, {s_max}, {v_max}])"
        )

        print("======================\n")


    # =========================
    # ESC ออก
    # =========================

    if key == 27:
        break


# =========================
# ปิด
# =========================

cap.release()

cv2.destroyAllWindows()