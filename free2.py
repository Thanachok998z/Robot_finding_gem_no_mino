import requests

# ==========================================
# ESP32
# ==========================================

ESP32_IP = "10.126.248.22"
ROBOT_CODE = "1234"


# ==========================================
# ส่งคำสั่งไป ESP32
# ==========================================

def send_motor(left, right, duration):

    # --------------------------------------
    # แปลงทิศทาง
    # --------------------------------------

    # ซ้าย
    if left >= 0:
        left_speed = min(left, 255)
        left_direction = "FORWARD"
    else:
        left_speed = min(abs(left), 255)
        left_direction = "BACKWARD"

    # ขวา
    if right >= 0:
        right_speed = min(right, 255)
        right_direction = "FORWARD"
    else:
        right_speed = min(abs(right), 255)
        right_direction = "BACKWARD"


    print()
    print("================================")
    print("Motor Command")
    print("================================")

    print(
        f"Left  : {left_speed} {left_direction}"
    )

    print(
        f"Right : {right_speed} {right_direction}"
    )

    print(
        f"Time  : {duration} ms"
    )


    # --------------------------------------
    # ส่งแยกตามทิศทาง
    # --------------------------------------

    # ถ้าซ้ายและขวาเดินหน้า
    if left >= 0 and right >= 0:

        cmd = 3

        params = {
            "code": ROBOT_CODE,
            "cmd": cmd,
            "left": left_speed,
            "right": right_speed
        }


    # ถ้าซ้ายและขวาถอยหลัง
    elif left < 0 and right < 0:

        cmd = 4

        params = {
            "code": ROBOT_CODE,
            "cmd": cmd,
            "left": left_speed,
            "right": right_speed
        }


    # ถ้าซ้ายเดินหน้า ขวาถอยหลัง
    elif left >= 0 and right < 0:

        cmd = 2

        params = {
            "code": ROBOT_CODE,
            "cmd": cmd,
            "left": left_speed,
            "right": right_speed
        }


    # ถ้าซ้ายถอยหลัง ขวาเดินหน้า
    else:

        cmd = 1

        params = {
            "code": ROBOT_CODE,
            "cmd": cmd,
            "left": left_speed,
            "right": right_speed
        }


    # --------------------------------------
    # ส่ง HTTP
    # --------------------------------------

    try:

        url = f"http://{ESP32_IP}/command"

        response = requests.get(
            url,
            params=params,
            timeout=2
        )

        print("ESP32:", response.text)


    except Exception as e:

        print("ERROR:", e)
        return


    # --------------------------------------
    # รอเวลาที่กำหนด
    # --------------------------------------

    import time

    time.sleep(duration / 1000)


    # --------------------------------------
    # STOP
    # --------------------------------------

    try:

        requests.get(
            url,
            params={
                "code": ROBOT_CODE,
                "cmd": 0
            },
            timeout=2
        )

        print("STOP")

    except Exception as e:

        print("STOP ERROR:", e)


# ==========================================
# MAIN
# ==========================================

print("================================")
print(" ESP32 MOTOR CONTROLLER")
print("================================")
print()
print("รูปแบบ:")
print("LEFT RIGHT TIME")
print()
print("ตัวอย่าง:")
print("400 -200 3000")
print()
print("ความหมาย:")
print("ซ้าย 400 เดินหน้า")
print("ขวา 200 ถอยหลัง")
print("3000 ms")
print()
print("พิมพ์ q เพื่อออก")
print()


while True:

    try:

        user_input = input("> ").strip()

        if user_input.lower() == "q":
            break


        # ----------------------------------
        # แยกค่า
        # ----------------------------------

        values = user_input.split()

        if len(values) != 3:

            print(
                "กรุณาใส่: LEFT RIGHT TIME"
            )

            continue


        left = int(values[0])
        right = int(values[1])
        duration = int(values[2])


        # ----------------------------------
        # ตรวจสอบเวลา
        # ----------------------------------

        if duration <= 0:

            print(
                "เวลา ต้องมากกว่า 0"
            )

            continue


        # ----------------------------------
        # ส่งรถ
        # ----------------------------------

        send_motor(
            left,
            right,
            duration
        )


    except ValueError:

        print(
            "กรุณาใส่ตัวเลข เช่น:"
        )

        print(
            "400 -200 3000"
        )


    except KeyboardInterrupt:

        print()
        print("STOP")

        try:

            requests.get(
                f"http://{ESP32_IP}/command",
                params={
                    "code": ROBOT_CODE,
                    "cmd": 0
                },
                timeout=2
            )

        except:
            pass

        break