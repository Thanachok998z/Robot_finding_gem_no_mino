import cv2
import numpy as np
import math

img = cv2.imread("img/map.png")
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

colors = {
    "GREEN":  ((35, 40, 40), (85, 255, 255)),

    # 🔵 น้ำเงินเข้ม
    "BLUE":   ((88, 160, 50), (105, 255, 230)),

    "RED":    ((0, 60, 40), (10, 255, 255)),

    "PURPLE": ((130, 40, 40), (170, 255, 255)),

    # 🩵 ฟ้าอ่อน
    "CYAN":   ((80, 20, 120), (100, 155, 255)),

    "ORANGE": ((10, 60, 40), (25, 255, 255))
}

for color_name, (lower, upper) in colors.items():

    lower = np.array(lower)
    upper = np.array(upper)

    # แยกสี
    mask = cv2.inRange(hsv, lower, upper)

    # ลด noise
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones((5, 5), np.uint8)
    )

    # หา contour
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    for contour in contours:

        area = cv2.contourArea(contour)

        # 1. กรองของที่เล็กเกินไป
        if area < 3000:
            continue

        perimeter = cv2.arcLength(contour, True)

        if perimeter == 0:
            continue

        # 2. คำนวณความกลม
        circularity = (
            4 * math.pi * area
            / (perimeter * perimeter)
        )

        # ต้องกลมพอ
        if circularity < 0.75:
            continue

        # 3. Bounding Box
        x, y, w, h = cv2.boundingRect(contour)

        # 4. ตรวจสอบสัดส่วน
        # วงกลมควรมี width และ height ใกล้กัน
        ratio = w / h

        if ratio < 0.8 or ratio > 1.2:
            continue

        # ผ่านทุกเงื่อนไข = เป็นวงกลมที่เราต้องการ

        center_x = x + w // 2
        center_y = y + h // 2

        # วาดกรอบ
        cv2.rectangle(
            img,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            3
        )

        # จุดกึ่งกลาง
        cv2.circle(
            img,
            (center_x, center_y),
            5,
            (0, 0, 255),
            -1
        )

        # ชื่อสี
        cv2.putText(
            img,
            color_name,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 0),
            2
        )
        cv2.putText(
    img,
    f"({center_x}, {center_y})",
    (x + w - 80, y + 15),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.4,              # ขนาดตัวอักษร
    (0, 0, 0),
    1                 # ความหนา
)
        print(
            f"{color_name}: "
            f"Box=({x},{y},{w},{h}) "
            f"Center=({center_x},{center_y}) "
            f"Circularity={circularity:.2f}"
        )

cv2.imshow("Result", img)
cv2.waitKey(0)
cv2.destroyAllWindows()