import cv2
import numpy as np
import math


# =========================================================
# 1. เปิดภาพต้นฉบับ
# =========================================================

img = cv2.imread("img/map.png")

if img is None:
    print("ไม่พบไฟล์ img/map.png")
    exit()

# สำคัญมาก!!
# original จะไม่ถูกวาดอะไรลงไปเลย
original = img.copy()

hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)


# =========================================================
# 2. สีสำหรับหา "วงกลมใหญ่"
# =========================================================

circle_colors = {

    "GREEN":  ((35, 40, 40), (85, 255, 255)),

    "BLUE":   ((88, 160, 50), (105, 255, 230)),

    "RED":    ((0, 60, 40), (10, 255, 255)),

    "PURPLE": ((130, 40, 40), (170, 255, 255)),

    "CYAN":   ((80, 20, 120), (100, 155, 255)),

    "ORANGE": ((10, 60, 40), (25, 255, 255))
}


# =========================================================
# 3. หา 6 วงกลมใหญ่
# =========================================================

big_circles = []

for color_name, (lower, upper) in circle_colors.items():

    lower = np.array(lower)
    upper = np.array(upper)

    mask = cv2.inRange(
        hsv,
        lower,
        upper
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones((5, 5), np.uint8)
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    for contour in contours:

        area = cv2.contourArea(contour)

        if area < 3000:
            continue

        perimeter = cv2.arcLength(
            contour,
            True
        )

        if perimeter == 0:
            continue

        circularity = (
            4 * math.pi * area
            / (perimeter * perimeter)
        )

        if circularity < 0.75:
            continue

        x, y, w, h = cv2.boundingRect(
            contour
        )

        ratio = w / h

        if ratio < 0.8 or ratio > 1.2:
            continue

        center_x = x + w // 2
        center_y = y + h // 2

        radius = int((w + h) / 4)

        # เก็บตำแหน่งวงกลม
        big_circles.append(
            (center_x, center_y, radius, color_name)
        )

        print(
            f"Circle {color_name}: "
            f"Center=({center_x},{center_y}) "
            f"Radius={radius}"
        )


print(
    "\nพบวงกลมใหญ่ทั้งหมด:",
    len(big_circles)
)


# =========================================================
# 4. สีสำหรับ "หิน"
# =========================================================

colors = {

    "GREEN": (
        np.array([56, 50, 135]),
        np.array([88, 255, 255])
    ),

    "BLUE": (
        np.array([85, 165, 100]),
        np.array([110, 255, 255])
    ),

    "CYAN": (
        np.array([85, 100, 190]),
        np.array([110, 170, 255])
    ),

    "RED": (
        np.array([0, 70, 120]),
        np.array([5, 255, 255])
    ),

    "PURPLE": (
        np.array([108, 74, 0]),
        np.array([164, 255, 255])
    ),

    "ORANGE": (
        np.array([5, 40, 120]),
        np.array([25, 255, 255])
    )
}


# =========================================================
# 5. สีกรอบ
# =========================================================

draw_colors = {

    "GREEN":  (0, 255, 0),
    "BLUE":   (255, 0, 0),
    "CYAN":   (255, 255, 0),
    "RED":    (0, 0, 255),
    "PURPLE": (255, 0, 255),
    "ORANGE": (0, 165, 255)
}


# =========================================================
# 6. ตรวจหาหินทีละสี
# =========================================================

for color_name, (lower, upper) in colors.items():

    # ใช้ภาพต้นฉบับ
    result = original.copy()


    # -----------------------------------------------------
    # Mask สี
    # -----------------------------------------------------

    mask = cv2.inRange(
        hsv,
        lower,
        upper
    )


    # -----------------------------------------------------
    # ลด noise
    # -----------------------------------------------------

    kernel = np.ones(
        (3, 3),
        np.uint8
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
    # 7. สำคัญมาก!!
    # ลบวงกลมใหญ่ทั้ง 6 ออกจาก Mask
    # =====================================================

    for cx, cy, radius, circle_color in big_circles:

        cv2.circle(
            mask,
            (cx, cy),
            radius + 5,
            0,
            -1
        )


    # =====================================================
    # 8. หา contour ของหิน
    # =====================================================

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )


    count = 0


    # =====================================================
    # 9. ตรวจแต่ละ contour
    # =====================================================

    for contour in contours:

        area = cv2.contourArea(
            contour
        )

        x, y, w, h = cv2.boundingRect(
            contour
        )


        # ก้อนเล็กเกินไป
        if area < 20:
            continue


        # ตอนนี้ยอมให้ใหญ่ขึ้น
        if area > 4500:
            continue


        # ขนาดขั้นต่ำ
        if w < 5 or h < 5:
            continue


        # ก้อนที่ติดกันสามารถใหญ่กว่า 50 ได้
        if w > 100 or h > 100:
            continue


        # อัตราส่วน
        ratio = w / h

        if ratio < 0.4 or ratio > 2.5:
            continue


        # =================================================
        # วาดกรอบ
        # =================================================

        cv2.rectangle(
            result,
            (x, y),
            (x + w, y + h),
            draw_colors[color_name],
            2
        )

        count += 1


    print(
        color_name,
        "found:",
        count
    )


    # =====================================================
    # 10. แสดงผล
    # =====================================================

    cv2.imshow(
        "Stone Detection",
        result
    )


    key = cv2.waitKey(2000)

    if key == 27:
        break


cv2.destroyAllWindows()