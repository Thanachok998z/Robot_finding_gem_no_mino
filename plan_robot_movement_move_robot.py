import cv2
import math
import heapq

from ai import detect_circles


# ==================================================
# ตั้งค่า
# ==================================================

IMAGE_PATH = "img/map.png"


# จุดเริ่มต้นของรถ
START = (745, 515)


# ทิศเริ่มต้น
START_DIRECTION = "LEFT"


# ==================================================
# ขนาดรถ
# ==================================================

# ปรับตามขนาดรถจริง
ROBOT_WIDTH = 50
ROBOT_HEIGHT = 50


# ระยะเผื่อความปลอดภัย
SAFETY_MARGIN = 10


# ==================================================
# ความละเอียดของ Grid
# ==================================================

# ยิ่งน้อย = แม่นขึ้น แต่คำนวณช้าลง
GRID_STEP = 5


# ==================================================
# ทิศทาง
# ==================================================

DIRECTIONS = [
    "UP",
    "RIGHT",
    "DOWN",
    "LEFT"
]


VECTOR = {

    "UP": (0, -1),

    "RIGHT": (1, 0),

    "DOWN": (0, 1),

    "LEFT": (-1, 0)
}


# ==================================================
# เปลี่ยนทิศ
# ==================================================

def turn_right(direction):

    index = DIRECTIONS.index(direction)

    return DIRECTIONS[
        (index + 1) % 4
    ]


def turn_left(direction):

    index = DIRECTIONS.index(direction)

    return DIRECTIONS[
        (index - 1) % 4
    ]


# ==================================================
# คำนวณจำนวนครั้งที่ต้องหมุน
# ==================================================

def turn_commands(current, target):

    commands = []

    current_index = DIRECTIONS.index(current)
    target_index = DIRECTIONS.index(target)

    diff = (
        target_index
        - current_index
    ) % 4


    # ขวา
    if diff == 1:

        commands.append(
            "หมุนขวา 90°"
        )


    # ขวา 180
    elif diff == 2:

        commands.append(
            "หมุนขวา 90°"
        )

        commands.append(
            "หมุนขวา 90°"
        )


    # ซ้าย
    elif diff == 3:

        commands.append(
            "หมุนซ้าย 90°"
        )


    return commands


# ==================================================
# ระยะทาง Manhattan
# ==================================================

def heuristic(a, b):

    return (
        abs(a[0] - b[0])
        +
        abs(a[1] - b[1])
    )


# ==================================================
# ตรวจว่าจุดชนวงกลมหรือไม่
# ==================================================

def collision(point, circles):

    x, y = point


    # รัศมีตัวรถแบบ conservative
    robot_radius = math.sqrt(
        (ROBOT_WIDTH / 2) ** 2
        +
        (ROBOT_HEIGHT / 2) ** 2
    )


    for circle in circles:

        cx, cy = circle["center"]

        radius = circle["radius"]


        # เพิ่มพื้นที่สำหรับตัวรถ
        safe_radius = (
            radius
            +
            robot_radius
            +
            SAFETY_MARGIN
        )


        distance = math.sqrt(

            (x - cx) ** 2
            +
            (y - cy) ** 2
        )


        if distance <= safe_radius:

            return True


    return False


# ==================================================
# ตรวจจุดว่าอยู่ในภาพหรือไม่
# ==================================================

def inside_image(x, y, width, height):

    return (
        0 <= x < width
        and
        0 <= y < height
    )


# ==================================================
# A* หาเส้นทาง
# ==================================================

def astar(
    start,
    goal,
    circles,
    image_width,
    image_height
):

    # ปัดให้เข้ากับ Grid
    start = (
        round(start[0] / GRID_STEP),
        round(start[1] / GRID_STEP)
    )

    goal = (
        round(goal[0] / GRID_STEP),
        round(goal[1] / GRID_STEP)
    )


    # จำนวนช่อง Grid
    grid_width = (
        image_width // GRID_STEP
    )

    grid_height = (
        image_height // GRID_STEP
    )


    # ------------------------------------------------
    # แปลง grid → pixel
    # ------------------------------------------------

    def grid_to_pixel(node):

        return (
            node[0] * GRID_STEP,
            node[1] * GRID_STEP
        )


    # ------------------------------------------------
    # ตรวจ collision
    # ------------------------------------------------

    def blocked(node):

        x, y = grid_to_pixel(node)

        return collision(
            (x, y),
            circles
        )


    # ------------------------------------------------
    # ถ้า A หรือ B อยู่ในสิ่งกีดขวาง
    # ------------------------------------------------
    # ==================================================
    # หา B จุดที่ใกล้ที่สุดที่รถสามารถอยู่ได้
    # ==================================================

    def find_nearest_valid_point(
        goal,
        circles,
        image_width,
        image_height
    ):

        # ถ้า B เดิมใช้ได้อยู่แล้ว
        if not collision(goal, circles):
            return goal


        best_point = None
        best_distance = float("inf")


        # ค้นหารอบ ๆ B
        search_step = 5
        search_radius = 300


        for dy in range(
            -search_radius,
            search_radius + 1,
            search_step
        ):

            for dx in range(
                -search_radius,
                search_radius + 1,
                search_step
            ):

                x = goal[0] + dx
                y = goal[1] + dy


                # อยู่นอกภาพ
                if not inside_image(
                    x,
                    y,
                    image_width,
                    image_height
                ):
                    continue


                point = (x, y)


                # ต้องไม่ชนวงกลม
                if collision(point, circles):
                    continue


                # ระยะจาก B เดิม
                distance = math.sqrt(
                    dx * dx +
                    dy * dy
                )


                # เอาจุดที่ใกล้ที่สุด
                if distance < best_distance:

                    best_distance = distance
                    best_point = point


        return best_point

    if blocked(start):

        print("❌ จุด A อยู่ใกล้วงกลมเกินไป")

        return None


    if blocked(goal):
        print("⚠️ จุด B เดิมอยู่ใกล้วงกลมเกินไป")
        print("กำลังหาจุดที่ใกล้ B ที่สุดที่รถสามารถอยู่ได้...")


        original_goal = grid_to_pixel(goal)


        new_goal = find_nearest_valid_point(
            original_goal,
            circles,
            image_width,
            image_height
        )


        if new_goal is None:

            print("❌ หา B จุดใหม่ไม่ได้")

            return None


        print(
            f"เปลี่ยน B จาก "
            f"{original_goal} → {new_goal}"
        )


        goal = (
            round(new_goal[0] / GRID_STEP),
            round(new_goal[1] / GRID_STEP)
        )


    # ------------------------------------------------
    # Priority Queue
    # ------------------------------------------------

    open_set = []

    heapq.heappush(
        open_set,
        (
            0,
            start
        )
    )


    # ------------------------------------------------
    # เก็บ parent
    # ------------------------------------------------

    came_from = {}


    # ------------------------------------------------
    # cost
    # ------------------------------------------------

    g_score = {

        start: 0
    }


    # ------------------------------------------------
    # A*
    # ------------------------------------------------

    while open_set:

        _, current = heapq.heappop(
            open_set
        )


        # ถึงเป้าหมาย
        if current == goal:

            path = []

            while current in came_from:

                path.append(current)

                current = came_from[current]


            path.append(start)

            path.reverse()


            # แปลงเป็น pixel
            return [
                grid_to_pixel(p)
                for p in path
            ]


        # ------------------------------------------------
        # เดิน 4 ทิศ
        # ------------------------------------------------

        for dx, dy in [

            (1, 0),

            (-1, 0),

            (0, 1),

            (0, -1)

        ]:

            neighbor = (

                current[0] + dx,

                current[1] + dy

            )


            # อยู่นอกภาพ
            if not (

                0 <= neighbor[0]
                < grid_width

                and

                0 <= neighbor[1]
                < grid_height

            ):

                continue


            # ชนวงกลม
            if blocked(neighbor):

                continue


            tentative_g = (
                g_score[current]
                + 1
            )


            if (

                neighbor not in g_score

                or

                tentative_g
                < g_score[neighbor]

            ):

                came_from[
                    neighbor
                ] = current


                g_score[
                    neighbor
                ] = tentative_g


                f_score = (

                    tentative_g

                    +

                    heuristic(
                        neighbor,
                        goal
                    )

                )


                heapq.heappush(

                    open_set,

                    (
                        f_score,
                        neighbor
                    )

                )


    return None


# ==================================================
# ลดจำนวนจุดของเส้นทาง
# ==================================================

def simplify_path(path):

    if path is None:

        return None


    if len(path) <= 2:

        return path


    result = [

        path[0]

    ]


    previous_direction = None


    for i in range(
        1,
        len(path)
    ):

        x1, y1 = path[i - 1]

        x2, y2 = path[i]


        dx = x2 - x1

        dy = y2 - y1


        if dx > 0:

            direction = "RIGHT"

        elif dx < 0:

            direction = "LEFT"

        elif dy > 0:

            direction = "DOWN"

        else:

            direction = "UP"


        if (

            previous_direction is not None

            and

            direction
            != previous_direction

        ):

            result.append(
                path[i - 1]
            )


        previous_direction = direction


    result.append(
        path[-1]
    )


    return result


# ==================================================
# แปลงเส้นทางเป็นคำสั่งรถ
# ==================================================

def path_to_commands(
    path,
    start_direction,
    final_direction
):

    commands = []


    current_direction = (
        start_direction
    )


    total_distance = 0


    # ------------------------------------------------
    # เดินตามแต่ละ segment
    # ------------------------------------------------

    for i in range(
        1,
        len(path)
    ):

        x1, y1 = path[i - 1]

        x2, y2 = path[i]


        dx = x2 - x1

        dy = y2 - y1


        # --------------------------------------------
        # หา direction ของเส้นทาง
        # --------------------------------------------

        if dx > 0:

            movement_direction = "RIGHT"

            distance = abs(dx)


        elif dx < 0:

            movement_direction = "LEFT"

            distance = abs(dx)


        elif dy > 0:

            movement_direction = "DOWN"

            distance = abs(dy)


        else:

            movement_direction = "UP"

            distance = abs(dy)


        # --------------------------------------------
        # ตรวจว่าควรเดินหน้าหรือถอยหลัง
        # --------------------------------------------

        opposite = {

            "UP": "DOWN",

            "DOWN": "UP",

            "LEFT": "RIGHT",

            "RIGHT": "LEFT"

        }


        # ถ้า movement เป็นทิศตรงข้าม
        # ใช้ถอยหลังได้เลย
        if movement_direction == opposite[
            current_direction
        ]:

            commands.append(

                f"ถอยหลัง {distance} px"

            )

            total_distance += distance


        else:

            # ----------------------------------------
            # ต้องหมุนให้หันไปทาง movement
            # ----------------------------------------

            turns = turn_commands(

                current_direction,

                movement_direction

            )


            commands.extend(turns)


            # ----------------------------------------
            # เดินหน้า
            # ----------------------------------------

            commands.append(

                f"เดินหน้า {distance} px"

            )


            total_distance += distance


            current_direction = (
                movement_direction
            )


    # =================================================
    # เมื่อถึง B แล้ว หมุนให้ตรง final direction
    # =================================================

    turns = turn_commands(

        current_direction,

        final_direction

    )


    commands.extend(turns)


    return commands, total_distance


# ==================================================
# วาดเส้นทาง
# ==================================================

def draw_result(
    image_path,
    circles,
    path,
    start,
    goal,
    final_direction
):

    img = cv2.imread(
        image_path
    )


    # ------------------------------------------------
    # วาดวงกลม obstacle
    # ------------------------------------------------

    robot_radius = math.sqrt(

        (ROBOT_WIDTH / 2) ** 2

        +

        (ROBOT_HEIGHT / 2) ** 2

    )


    for circle in circles:

        cx, cy = circle["center"]

        radius = circle["radius"]


        # วงกลมจริง
        cv2.circle(

            img,

            (cx, cy),

            int(radius),

            (0, 0, 255),

            2

        )


        # เขตปลอดภัย
        safe_radius = int(

            radius
            +
            robot_radius
            +
            SAFETY_MARGIN

        )


        cv2.circle(

            img,

            (cx, cy),

            safe_radius,

            (0, 165, 255),

            1

        )


        cv2.putText(

            img,

            circle["color"],

            (cx - 30, cy),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.5,

            (0, 0, 0),

            1

        )


    # ------------------------------------------------
    # วาดเส้นทาง
    # ------------------------------------------------

    if path is not None:

        for i in range(
            1,
            len(path)
        ):

            p1 = path[i - 1]

            p2 = path[i]


            cv2.line(

                img,

                p1,

                p2,

                (255, 0, 255),

                4

            )


            # ลูกศร
            cv2.arrowedLine(

                img,

                p1,

                p2,

                (255, 0, 255),

                3,

                tipLength=0.3

            )


    # ------------------------------------------------
    # จุด A
    # ------------------------------------------------

    cv2.circle(

        img,

        start,

        8,

        (0, 255, 0),

        -1

    )


    cv2.putText(

        img,

        "A",

        (
            start[0] + 10,
            start[1]
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (0, 255, 0),

        2

    )


    # ------------------------------------------------
    # จุด B
    # ------------------------------------------------

    cv2.circle(

        img,

        goal,

        8,

        (255, 0, 0),

        -1

    )


    cv2.putText(

        img,

        "B",

        (
            goal[0] + 10,
            goal[1]
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (255, 0, 0),

        2

    )


    # ------------------------------------------------
    # แสดง final direction
    # ------------------------------------------------

    dx, dy = VECTOR[
        final_direction
    ]


    arrow_length = 50


    end_point = (

        goal[0] + dx * arrow_length,

        goal[1] + dy * arrow_length

    )


    cv2.arrowedLine(

        img,

        goal,

        end_point,

        (0, 255, 255),

        5,

        tipLength=0.3

    )


    cv2.putText(

        img,

        final_direction,

        (
            goal[0] + 10,
            goal[1] + 30
        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.6,

        (0, 0, 0),

        2

    )


    return img


# ==================================================
# MAIN
# ==================================================

def main():

    print()
    print("==============================")
    print("      ROBOT PATH PLANNER")
    print("==============================")
    print()


    # =================================================
    # ตรวจวงกลมจาก ai.py
    # =================================================

    print("กำลังตรวจจับวงกลม...")

    circles = detect_circles(

        IMAGE_PATH,

        show_result=False

    )


    print()
    print(
        f"พบวงกลมทั้งหมด {len(circles)} วง"
    )


    for circle in circles:

        print(

            f"{circle['color']} : "

            f"{circle['center']} "

            f"radius={circle['radius']:.1f}"

        )


    # =================================================
    # อ่านรูป
    # =================================================

    image = cv2.imread(
        IMAGE_PATH
    )


    if image is None:

        print(
            "❌ ไม่พบรูป"
        )

        return


    height, width = image.shape[:2]


    print()
    print(
        f"Image size = {width} x {height}"
    )


    # =================================================
    # จุด A
    # =================================================

    start = START


    print()
    print(
        f"A = {start}"
    )

    print(
        f"ทิศเริ่มต้น = {START_DIRECTION}"
    )


    # =================================================
    # รับ B
    # =================================================

    print()
    print("------------------------------")
    print("กรอกตำแหน่ง B")
    print("ระบบพิกัด: (0,0) ซ้ายบน")
    print("------------------------------")


    bx = int(
        input("B X = ")
    )

    by = int(
        input("B Y = ")
    )


    goal = (
        bx,
        by
    )


    # =================================================
    # รับ final direction
    # =================================================

    print()
    print("ทิศสุดท้ายเลือก:")

    print("1 = UP")
    print("2 = RIGHT")
    print("3 = DOWN")
    print("4 = LEFT")


    direction_number = int(
        input("เลือก = ")
    )


    direction_map = {

        1: "UP",

        2: "RIGHT",

        3: "DOWN",

        4: "LEFT"

    }


    if direction_number not in direction_map:

        print(
            "❌ เลือกทิศไม่ถูกต้อง"
        )

        return


    final_direction = direction_map[
        direction_number
    ]


    print()
    print(
        f"B = {goal}"
    )

    print(
        f"Final direction = "
        f"{final_direction}"
    )


    # =================================================
    # ตรวจ B อยู่นอกภาพหรือไม่
    # =================================================

    if not inside_image(

        bx,
        by,
        width,
        height

    ):

        print(
            "❌ B อยู่นอกภาพ"
        )

        return


    # =================================================
    # หาเส้นทาง
    # =================================================

    print()
    print("กำลังคำนวณเส้นทาง...")
    print("กรุณารอสักครู่")


    path = astar(

        start,

        goal,

        circles,

        width,

        height

    )


    # =================================================
    # หาเส้นทางไม่ได้
    # =================================================

    if path is None:

        print()
        print(
            "❌ ไม่สามารถหาเส้นทางได้"
        )

        print(
            "ลองเปลี่ยนตำแหน่ง B "
            "หรือปรับ ROBOT_WIDTH / HEIGHT"
        )

        return


    # =================================================
    # ลดจุด
    # =================================================

    path = simplify_path(
        path
    )


    # =================================================
    # สร้างคำสั่ง
    # =================================================

    commands, total_distance = (

        path_to_commands(

            path,

            START_DIRECTION,

            final_direction

        )

    )


    # =================================================
    # แสดงคำสั่ง
    # =================================================

    print()
    print("==============================")
    print("          RESULT")
    print("==============================")

    print()

    print(
        f"Start : {start}"
    )

    print(
        f"Goal  : {goal}"
    )

    print(
        f"Start direction : "
        f"{START_DIRECTION}"
    )

    print(
        f"Final direction : "
        f"{final_direction}"
    )

    print()

    print(
        f"ระยะทางรวมประมาณ "
        f"{total_distance} px"
    )

    print()

    print("คำสั่ง:")

    for i, command in enumerate(
        commands,
        start=1
    ):

        print(
            f"{i}. {command}"
        )


    # =================================================
    # วาดผล
    # =================================================

    result = draw_result(

        IMAGE_PATH,

        circles,

        path,

        start,

        goal,

        final_direction

    )


    # =================================================
    # แสดง
    # =================================================

    cv2.imshow(
        "Robot Path",
        result
    )


    print()
    print(
        "กดปุ่มใดก็ได้เพื่อปิด"
    )


    cv2.waitKey(0)

    cv2.destroyAllWindows()


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    main()