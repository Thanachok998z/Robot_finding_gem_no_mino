import cv2
import os

# เลือก Dictionary
aruco_dict = cv2.aruco.getPredefinedDictionary(
    cv2.aruco.DICT_4X4_100
)

# ID ของ Marker ที่ต้องการสร้าง
marker_id = 67
# ขนาดภาพ Marker (pixel)
size = 500

# สร้าง Marker
marker = cv2.aruco.generateImageMarker(
    aruco_dict,
    marker_id,
    size
)

# สร้างโฟลเดอร์เก็บรูป
os.makedirs("aruco_markers", exist_ok=True)

# บันทึกไฟล์
filename = f"aruco_markers/marker_{marker_id}.png"
cv2.imwrite(filename, marker)

print(f"สร้าง Marker สำเร็จ: {filename}")

# แสดงภาพ
cv2.imshow("ArUco Marker", marker)
cv2.waitKey(0)
cv2.destroyAllWindows()