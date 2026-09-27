import cv2
import numpy as np
import math


def detect_circles(img, show_result=True):

    # =========================
    # สำเนาภาพ
    # =========================

    original = img.copy()

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


    # =========================
    # กำหนดสี
    # =========================

    colors = {

        "GREEN":
            ((35, 40, 40),
             (85, 255, 255)),

        "BLUE":
            ((88, 160, 50),
             (105, 255, 230)),

        "RED":
            ((160, 15, 51),
             (179, 255, 255)),

        "PURPLE":
            ((130, 40, 40),
             (170, 255, 255)),

        "CYAN":
            ((80, 20, 120),
             (100, 155, 255)),

        "ORANGE":
            ((0, 49, 95),
            (21, 180, 255)),
    }


    # =========================
    # เก็บวงกลมทั้งหมด
    # =========================

    circles = []


    # =========================
    # ตรวจทีละสี
    # =========================

    for color_name, (lower, upper) in colors.items():

        lower = np.array(lower)
        upper = np.array(upper)


        # =========================
        # แยกสี
        # =========================

        mask = cv2.inRange(
            hsv,
            lower,
            upper
        )


        # =========================
        # ลด noise
        # =========================

        kernel = np.ones(
            (5, 5),
            np.uint8
        )

        mask = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel
        )


        # =========================
        # หา contour
        # =========================

        contours, _ = cv2.findContours(
            mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )


        # =========================
        # ตรวจ contour
        # =========================

        for contour in contours:

            area = cv2.contourArea(contour)


            # เล็กเกินไป
            if area < 3000:
                continue


            perimeter = cv2.arcLength(
                contour,
                True
            )

            if perimeter == 0:
                continue


            # =========================
            # Circularity
            # =========================

            circularity = (
                4 * math.pi * area
                / (perimeter * perimeter)
            )


            if circularity < 0.75:
                continue


            # =========================
            # Bounding box
            # =========================

            x, y, w, h = cv2.boundingRect(
                contour
            )


            # =========================
            # ตรวจสัดส่วน
            # =========================

            ratio = w / h

            if ratio < 0.8 or ratio > 1.2:
                continue


            # =========================
            # จุดกลาง
            # =========================

            center_x = x + w // 2
            center_y = y + h // 2


            # =========================
            # รัศมี
            # =========================

            radius = max(w, h) / 2


            # =========================
            # เก็บข้อมูล
            # =========================

            circle_data = {

                "color": color_name,

                "center": (
                    center_x,
                    center_y
                ),

                "radius": radius,

                "box": (
                    x,
                    y,
                    w,
                    h
                ),

                "circularity": circularity
            }


            circles.append(circle_data)


            # =========================
            # วาดผล
            # =========================

            if show_result:

                cv2.rectangle(
                    img,
                    (x, y),
                    (x + w, y + h),
                    (0, 255, 0),
                    3
                )


                cv2.circle(
                    img,
                    (center_x, center_y),
                    5,
                    (0, 0, 255),
                    -1
                )


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
                    (x + 5, y + h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1
                )


            # =========================
            # แสดงข้อมูล
            # =========================

            print(
                f"{color_name}: "
                f"Center=({center_x},{center_y}) "
                f"Radius={radius:.1f} "
                f"Circularity={circularity:.2f}"
            )


    return circles


# ==========================================
# Real-time Camera
# ==========================================

if __name__ == "__main__":

    # เปิดกล้อง index 2
    cap = cv2.VideoCapture(2)

    if not cap.isOpened():
        print("ไม่สามารถเปิดกล้อง index 2 ได้")
        exit()


    print("เปิดกล้องแล้ว")
    print("กด Q เพื่อออก")


    while True:

        # อ่านภาพจากกล้อง
        ret, frame = cap.read()

        if not ret:
            print("ไม่สามารถอ่านภาพจากกล้องได้")
            break


        # =========================
        # ตรวจจับวงกลม
        # =========================

        circles = detect_circles(
            frame,
            show_result=True
        )


        # =========================
        # แสดงภาพ
        # =========================

        cv2.imshow(
            "Real-time Circle Detection",
            frame
        )


        # =========================
        # กด Q เพื่อออก
        # =========================

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break


    # ปิดกล้อง
    cap.release()

    cv2.destroyAllWindows()