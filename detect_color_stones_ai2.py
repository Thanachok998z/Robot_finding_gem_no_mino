import cv2
import numpy as np


# ==============================
# เปิดภาพ
# ==============================

img = cv2.imread("img/map.png")

if img is None:
    print("ไม่พบไฟล์ img/map.png")
    exit()

hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


# ==============================
# สี
# ==============================

colors = {

    "GREEN": (
        #np.array([20, 40, 0]),
        #np.array([90, 255, 255])
        np.array([56, 50, 135]),
        np.array([88, 255, 255])
    ),

    "BLUE": (
        #np.array([85, 100, 30]),
        #np.array([110, 255, 255])
        np.array([85, 165, 100]),
        np.array([110, 255, 255])
    ),

    "CYAN": (
        #np.array([80, 20, 80]),
        #np.array([100, 170, 255])
        np.array([85, 100, 190]),
        np.array([110, 170, 255])
    ),

    "RED": (
        #np.array([0, 50, 30]),
        #np.array([10, 255, 255])
        np.array([0, 70, 120]),
        np.array([5, 255, 255])
    ),

    "PURPLE": (
        #np.array([125, 30, 30]),
        #np.array([170, 255, 255])
        np.array([108, 74, 0]),
        np.array([164, 255, 255])
    ),

    "ORANGE": (
        #np.array([10, 50, 30]),
        #np.array([30, 255, 255])
        np.array([5, 40, 120]),
        np.array([25, 255, 255])
    )
}
# ==============================
# สีกรอบ
# ==============================

draw_colors = {

    "GREEN":  (0, 255, 0),
    "BLUE":   (255, 0, 0),
    "CYAN":   (255, 255, 0),
    "RED":    (0, 0, 255),
    "PURPLE": (255, 0, 255),
    "ORANGE": (0, 165, 255)
}


# ==============================
# ตรวจทีละสี
# ==============================

for color_name, (lower, upper) in colors.items():

    result = img.copy()

    # --------------------------
    # Mask
    # --------------------------

    mask = cv2.inRange(
        hsv,
        lower,
        upper
    )

    # --------------------------
    # ลด noise
    # --------------------------

    kernel = np.ones((3, 3), np.uint8)

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

    # --------------------------
    # หา contour
    # --------------------------

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    count = 0

    # --------------------------
    # วาดกรอบ
    # --------------------------

    for contour in contours:

        area = cv2.contourArea(contour)

        x, y, w, h = cv2.boundingRect(contour)

        if area < 20:
            continue

        if area > 4500:
            continue

        if w < 5 or h < 5:
            continue

        if w > 100 or h > 100:
            continue

        ratio = w / h

        if ratio < 0.4 or ratio > 2.5:
            continue
        # วาดกรอบ
        cv2.rectangle(
            result,
            (x, y),
            (x + w, y + h),
            draw_colors[color_name],
            2
        )

        count += 1

    print(color_name, "found:", count)

    # --------------------------
    # แสดง
    # --------------------------

    cv2.imshow(
        "Stone Detection",
        result
    )

    # 10 วินาที
    key = cv2.waitKey(2000)

    # ESC
    if key == 27:
        break


cv2.destroyAllWindows()