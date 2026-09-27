import cv2

ARUCO_TYPE = cv2.aruco.DICT_4X4_50
CAMERA_INDEX = 1

aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_TYPE)
parameters = cv2.aruco.DetectorParameters()

detector = cv2.aruco.ArucoDetector(
    aruco_dict,
    parameters
)

cap = cv2.VideoCapture(CAMERA_INDEX)

while True:
    ret, frame = cap.read()

    if not ret:
        print("เปิดกล้องไม่ได้")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    corners, ids, rejected = detector.detectMarkers(gray)

    if ids is not None:

        for i, marker_id in enumerate(ids.flatten()):

            marker_id = int(marker_id)

            if 1 <= marker_id <= 49:

                cv2.aruco.drawDetectedMarkers(
                    frame,
                    [corners[i]],
                    ids[i:i+1]
                )

                pts = corners[i][0]

                center_x = int(pts[:, 0].mean())
                center_y = int(pts[:, 1].mean())

                cv2.circle(
                    frame,
                    (center_x, center_y),
                    5,
                    (0, 255, 0),
                    -1
                )

                cv2.putText(
                    frame,
                    f"ID: {marker_id}",
                    (center_x + 10, center_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

                print(f"เจอ ArUco ID = {marker_id}")

    cv2.imshow("ArUco 4x4_50", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()