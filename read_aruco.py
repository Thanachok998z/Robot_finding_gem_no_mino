import cv2

# -----------------------------
# ArUco
# -----------------------------
aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

parameters = cv2.aruco.DetectorParameters()

detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    parameters
)

# -----------------------------
# โหลดรูป
# -----------------------------
images = {
    0: cv2.imread("images/arrows.jpg"),
    67: cv2.imread("images/67.jpg")
}

# -----------------------------
# เปิดกล้อง
# -----------------------------
cap = cv2.VideoCapture(1)


while True:

    ret, frame = cap.read()

    if not ret:
        break

    corners, ids, rejected = detector.detectMarkers(frame)

    if ids is not None:

        for i, marker_id in enumerate(ids):

            marker_id = int(marker_id)

            # อ่านแค่ ID 0 กับ 67
            if marker_id not in [0, 67]:
                continue

            # -----------------------------
            # มุมของ ArUco
            # -----------------------------
            dst = corners[i][0].astype("float32")

            # จุดกลาง
            center_x = int(dst[:, 0].mean())
            center_y = int(dst[:, 1].mean())

            # -----------------------------
            # วาดกรอบ ArUco
            # -----------------------------
            cv2.polylines(
                frame,
                [dst.astype(int)],
                True,
                (0, 255, 0),
                3
            )

            # -----------------------------
            # รูปที่จะเอาไปวาง
            # -----------------------------
            img = images[marker_id]

            if img is None:
                continue

            h, w = img.shape[:2]

            # -----------------------------
            # จุดปลายทางของรูป
            # ต้องตรงกับ 4 มุม ArUco
            # -----------------------------
            src = cv2.Point2f if False else None

            src_points = __import__("numpy").array([
                [0, 0],
                [w - 1, 0],
                [w - 1, h - 1],
                [0, h - 1]
            ], dtype="float32")

            # -----------------------------
            # Perspective Transform
            # -----------------------------
            matrix = cv2.getPerspectiveTransform(
                src_points,
                dst
            )

            warped = cv2.warpPerspective(
                img,
                matrix,
                (frame.shape[1], frame.shape[0])
            )

            # -----------------------------
            # สร้าง Mask
            # -----------------------------
            mask = __import__("numpy").zeros(
                (frame.shape[0], frame.shape[1]),
                dtype=__import__("numpy").uint8
            )

            cv2.fillConvexPoly(
                mask,
                dst.astype(int),
                255
            )

            # -----------------------------
            # เอารูปไปวาง
            # -----------------------------
            mask_inv = cv2.bitwise_not(mask)

            background = cv2.bitwise_and(
                frame,
                frame,
                mask=mask_inv
            )

            foreground = cv2.bitwise_and(
                warped,
                warped,
                mask=mask
            )

            frame = cv2.add(
                background,
                foreground
            )

            # -----------------------------
            # วาดกรอบทับอีกครั้ง
            # -----------------------------
            cv2.polylines(
                frame,
                [dst.astype(int)],
                True,
                (0, 255, 0),
                3
            )

            # -----------------------------
            # จุดกลาง
            # -----------------------------
            cv2.circle(
                frame,
                (center_x, center_y),
                5,
                (0, 0, 255),
                -1
            )

            # -----------------------------
            # แสดง ID
            # -----------------------------
            cv2.putText(
                frame,
                f"ID: {marker_id}",
                (center_x - 40, center_y - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    # -----------------------------
    # แสดงกล้อง
    # -----------------------------
    cv2.imshow(
        "ArUco Reader",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


cap.release()
cv2.destroyAllWindows()