import cv2
import math
import heapq
import numpy as np


# =========================================================
# SETTINGS
# =========================================================

IMAGE_PATH = "img/map.png"

# จุดเริ่มต้นรถ
START = (745, 515)

# รถเริ่มหันไปทางซ้าย
START_DIRECTION = "LEFT"

# ขนาดรถ
ROBOT_WIDTH = 40
ROBOT_HEIGHT = 60

# ระยะปลอดภัยจากวงกลม
SAFETY_MARGIN = 10

# ความละเอียดของ A*
GRID_STEP = 5


# =========================================================
# ทิศทาง
# =========================================================

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


# =========================================================
# วงกลม
# ใช้พิกัดที่ฟิกไว้
# =========================================================

CIRCLES = [

    {
        "color": "GREEN",
        "center": (69, 197),
        "radius": 40
    },

    {
        "color": "BLUE",
        "center": (294, 111),
        "radius": 40
    },

    {
        "color": "RED",
        "center": (535, 87),
        "radius": 40
    },

    {
        "color": "PURPLE",
        "center": (79, 392),
        "radius": 40
    },

    {
        "color": "CYAN",
        "center": (266, 502),
        "radius": 40
    },

    {
        "color": "ORANGE",
        "center": (517, 487),
        "radius": 40
    }

]


# =========================================================
# คำนวณพื้นที่ปลอดภัยของรถ
#
# ใช้ครึ่งเส้นทแยงมุมของรถ
# เพื่อให้รถไม่ชนวงกลม
# =========================================================

def robot_radius():

    return math.sqrt(

        (ROBOT_WIDTH / 2) ** 2
        +
        (ROBOT_HEIGHT / 2) ** 2

    )


# =========================================================
# ตรวจว่าจุดชนวงกลมหรือไม่
# =========================================================

def is_blocked(point):

    x, y = point


    safe_robot = (

        robot_radius()
        +
        SAFETY_MARGIN

    )


    for circle in CIRCLES:

        cx, cy = circle["center"]

        radius = circle["radius"]


        safe_distance = (

            radius
            +
            safe_robot

        )


        distance = math.sqrt(

            (x - cx) ** 2
            +
            (y - cy) ** 2

        )


        if distance < safe_distance:

            return True


    return False


# =========================================================
# หา "ด้านหน้าวงกลม"
#
# ดูจากตำแหน่ง A
#
# เช่น A อยู่ด้านขวาของวงกลม
# -> รถควรจอดด้านขวา
# -> หน้ารถหัน LEFT
# =========================================================

def get_preferred_side(target):

    cx, cy = target["center"]

    ax, ay = START


    dx = ax - cx

    dy = ay - cy


    # -----------------------------------------
    # A อยู่ทางซ้าย/ขวาชัดกว่า
    # -----------------------------------------

    if abs(dx) >= abs(dy):

        if dx > 0:

            return "RIGHT"

        else:

            return "LEFT"


    # -----------------------------------------
    # A อยู่ด้านบน/ล่างชัดกว่า
    # -----------------------------------------

    else:

        if dy > 0:

            return "BOTTOM"

        else:

            return "TOP"


# =========================================================
# สร้างจุดจอดทั้ง 4 ด้าน
# =========================================================

def get_parking_candidates(target):

    cx, cy = target["center"]

    radius = target["radius"]


    distance = (

        radius
        +
        robot_radius()
        +
        SAFETY_MARGIN

    )


    candidates = {

        "TOP": {

            "position": (

                int(cx),

                int(cy - distance)

            ),

            # อยู่ด้านบน
            # ต้องหันลง
            "direction": "DOWN"

        },


        "RIGHT": {

            "position": (

                int(cx + distance),

                int(cy)

            ),

            # อยู่ด้านขวา
            # ต้องหันซ้าย
            "direction": "LEFT"

        },


        "BOTTOM": {

            "position": (

                int(cx),

                int(cy + distance)

            ),

            # อยู่ด้านล่าง
            # ต้องหันขึ้น
            "direction": "UP"

        },


        "LEFT": {

            "position": (

                int(cx - distance),

                int(cy)

            ),

            # อยู่ด้านซ้าย
            # ต้องหันขวา
            "direction": "RIGHT"

        }

    }


    return candidates


# =========================================================
# A*
#
# เดินได้แค่ 4 ทิศ
#
# ไม่มี diagonal
# =========================================================

def astar(
    start,
    goal,
    width,
    height
):

    # -----------------------------------------------------
    # Pixel -> Grid
    # -----------------------------------------------------

    start_grid = (

        round(start[0] / GRID_STEP),

        round(start[1] / GRID_STEP)

    )


    goal_grid = (

        round(goal[0] / GRID_STEP),

        round(goal[1] / GRID_STEP)

    )


    max_x = width // GRID_STEP

    max_y = height // GRID_STEP


    # -----------------------------------------------------
    # Grid -> Pixel
    # -----------------------------------------------------

    def to_pixel(node):

        return (

            node[0] * GRID_STEP,

            node[1] * GRID_STEP

        )


    # -----------------------------------------------------
    # จุดเริ่มต้นชนหรือไม่
    # -----------------------------------------------------

    if is_blocked(

        to_pixel(start_grid)

    ):

        print(
            "❌ จุดเริ่มต้นชนสิ่งกีดขวาง"
        )

        return None


    # -----------------------------------------------------
    # จุดหมายชนหรือไม่
    # -----------------------------------------------------

    if is_blocked(

        to_pixel(goal_grid)

    ):

        return None


    # -----------------------------------------------------
    # Priority Queue
    # -----------------------------------------------------

    open_set = []


    heapq.heappush(

        open_set,

        (

            0,

            start_grid

        )

    )


    # จุดก่อนหน้า
    came_from = {}


    # ค่า g
    g_score = {

        start_grid: 0

    }


    # =====================================================
    # A*
    # =====================================================

    while open_set:

        _, current = heapq.heappop(

            open_set

        )


        # -------------------------------------------------
        # ถึงเป้าหมาย
        # -------------------------------------------------

        if current == goal_grid:

            path = []


            while current in came_from:

                path.append(

                    current

                )

                current = came_from[current]


            path.append(

                start_grid

            )


            path.reverse()


            return [

                to_pixel(point)

                for point in path

            ]


        # -------------------------------------------------
        # เดินได้ 4 ทิศเท่านั้น
        # -------------------------------------------------

        neighbors = [

            (1, 0),      # RIGHT

            (-1, 0),     # LEFT

            (0, 1),      # DOWN

            (0, -1)      # UP

        ]


        for dx, dy in neighbors:

            neighbor = (

                current[0] + dx,

                current[1] + dy

            )


            # ---------------------------------------------
            # อยู่นอกภาพ
            # ---------------------------------------------

            if not (

                0 <= neighbor[0] < max_x

                and

                0 <= neighbor[1] < max_y

            ):

                continue


            # ---------------------------------------------
            # ตรวจชน
            # ---------------------------------------------

            pixel = to_pixel(

                neighbor

            )


            if is_blocked(pixel):

                continue


            # ---------------------------------------------
            # ค่า g ใหม่
            # ---------------------------------------------

            new_g = (

                g_score[current]

                +

                1

            )


            # ---------------------------------------------
            # ถ้าทางนี้ดีกว่า
            # ---------------------------------------------

            if (

                neighbor not in g_score

                or

                new_g < g_score[neighbor]

            ):

                came_from[neighbor] = current

                g_score[neighbor] = new_g


                # -----------------------------------------
                # Manhattan distance
                # -----------------------------------------

                h = (

                    abs(

                        neighbor[0]
                        -
                        goal_grid[0]

                    )

                    +

                    abs(

                        neighbor[1]
                        -
                        goal_grid[1]

                    )

                )


                f = new_g + h


                heapq.heappush(

                    open_set,

                    (

                        f,

                        neighbor

                    )

                )


    return None


# =========================================================
# ลดจำนวนจุด
#
# แต่ยังคงเป็นเส้นแนวนอน/แนวตั้ง
# =========================================================

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


        # ---------------------------------------------
        # เมื่อเปลี่ยนทิศ
        # เก็บจุดก่อนเลี้ยว
        # ---------------------------------------------

        if (

            previous_direction is not None

            and

            direction != previous_direction

        ):

            result.append(

                path[i - 1]

            )


        previous_direction = direction


    result.append(

        path[-1]

    )


    return result


# =========================================================
# คำนวณการหมุน
# =========================================================

def turn_commands(

    current_direction,

    target_direction

):

    current_index = DIRECTIONS.index(

        current_direction

    )


    target_index = DIRECTIONS.index(

        target_direction

    )


    difference = (

        target_index
        -
        current_index

    ) % 4


    commands = []


    # -----------------------------------------
    # ขวา 90
    # -----------------------------------------

    if difference == 1:

        commands.append(

            "หมุนขวา 90°"

        )


    # -----------------------------------------
    # 180
    # -----------------------------------------

    elif difference == 2:

        commands.append(

            "หมุนขวา 90°"

        )

        commands.append(

            "หมุนขวา 90°"

        )


    # -----------------------------------------
    # ซ้าย 90
    # -----------------------------------------

    elif difference == 3:

        commands.append(

            "หมุนซ้าย 90°"

        )


    return commands


# =========================================================
# แปลง Path -> คำสั่งรถ
#
# รถจะ:
#
# 1. หมุนอยู่กับที่
# 2. เดินตรง
#
# ไม่มีโค้ง
# =========================================================

def path_to_commands(

    path,

    start_direction,

    final_direction

):

    commands = []


    current_direction = (

        start_direction

    )


    opposite = {

        "UP": "DOWN",

        "DOWN": "UP",

        "LEFT": "RIGHT",

        "RIGHT": "LEFT"

    }


    # =====================================================
    # เดินตามเส้นทาง
    # =====================================================

    for i in range(

        1,

        len(path)

    ):

        x1, y1 = path[i - 1]

        x2, y2 = path[i]


        dx = x2 - x1

        dy = y2 - y1


        # -------------------------------------------------
        # หา direction
        # -------------------------------------------------

        if dx > 0:

            move_direction = "RIGHT"

            distance = abs(dx)


        elif dx < 0:

            move_direction = "LEFT"

            distance = abs(dx)


        elif dy > 0:

            move_direction = "DOWN"

            distance = abs(dy)


        else:

            move_direction = "UP"

            distance = abs(dy)


        # =================================================
        # ถ้าทางตรงข้ามกับหน้ารถ
        #
        # ใช้ถอยหลัง
        # =================================================

        if (

            move_direction
            ==
            opposite[current_direction]

        ):

            commands.append(

                f"ถอยหลัง {distance} px"

            )


        # =================================================
        # ถ้าต้องเปลี่ยนทิศ
        #
        # หมุนก่อน
        # แล้วเดิน
        # =================================================

        elif (

            move_direction
            !=
            current_direction

        ):

            turns = turn_commands(

                current_direction,

                move_direction

            )


            commands.extend(

                turns

            )


            current_direction = (

                move_direction

            )


            commands.append(

                f"เดินหน้า {distance} px"

            )


        # =================================================
        # เดินตรง
        # =================================================

        else:

            commands.append(

                f"เดินหน้า {distance} px"

            )


    # =====================================================
    # ถึงหน้าวงกลม
    # หันเข้าหาวงกลม
    # =====================================================

    if (

        current_direction
        !=
        final_direction

    ):

        commands.extend(

            turn_commands(

                current_direction,

                final_direction

            )

        )


    return commands


# =========================================================
# วาดรถ
# =========================================================

def draw_robot(

    image,

    center,

    direction

):

    cx, cy = center


    width = ROBOT_WIDTH

    height = ROBOT_HEIGHT


    # -----------------------------------------------------
    # สร้างสี่เหลี่ยม
    # -----------------------------------------------------

    corners = np.array([

        [

            -width / 2,

            -height / 2

        ],

        [

            width / 2,

            -height / 2

        ],

        [

            width / 2,

            height / 2

        ],

        [

            -width / 2,

            height / 2

        ]

    ])


    # -----------------------------------------------------
    # หมุนรถ
    # -----------------------------------------------------

    if direction == "UP":

        angle = 0


    elif direction == "RIGHT":

        angle = 90


    elif direction == "DOWN":

        angle = 180


    else:

        angle = 270


    rad = math.radians(angle)


    rotation = np.array([

        [

            math.cos(rad),

            -math.sin(rad)

        ],

        [

            math.sin(rad),

            math.cos(rad)

        ]

    ])


    rotated = (

        corners

        @

        rotation.T

    )


    points = []


    for x, y in rotated:

        points.append([

            int(cx + x),

            int(cy + y)

        ])


    points = np.array(

        points,

        dtype=np.int32

    )


    # -----------------------------------------------------
    # ตัวรถ
    # -----------------------------------------------------

    cv2.fillPoly(

        image,

        [points],

        (255, 255, 0)

    )


    # -----------------------------------------------------
    # ขอบรถ
    # -----------------------------------------------------

    cv2.polylines(

        image,

        [points],

        True,

        (0, 0, 0),

        3

    )


    # -----------------------------------------------------
    # จุดกลางรถ
    # -----------------------------------------------------

    cv2.circle(

        image,

        center,

        4,

        (0, 0, 255),

        -1

    )


    # -----------------------------------------------------
    # ลูกศรหน้ารถ
    #
    # ใช้เส้นธรรมดา ไม่ใช้ arrowedLine
    # เพื่อไม่ให้เกิดหัวลูกศรเฉียงใหญ่
    # -----------------------------------------------------

    dx, dy = VECTOR[direction]


    arrow_length = 25


    end = (

        int(

            cx
            +
            dx * arrow_length

        ),

        int(

            cy
            +
            dy * arrow_length

        )

    )


    cv2.line(

        image,

        center,

        end,

        (0, 0, 255),

        4

    )


    # จุดปลายแสดง "หน้ารถ"
    cv2.circle(

        image,

        end,

        4,

        (0, 0, 255),

        -1

    )


# =========================================================
# วาดเส้นทาง
#
# ใช้เส้นตรงธรรมดา
# ไม่ใช้ arrowedLine
# =========================================================

def draw_path(

    image,

    path

):

    if path is None:

        return


    for i in range(

        1,

        len(path)

    ):

        p1 = path[i - 1]

        p2 = path[i]


        # -------------------------------------------------
        # เส้นทาง
        # -------------------------------------------------

        cv2.line(

            image,

            p1,

            p2,

            (255, 0, 255),

            5

        )


        # -------------------------------------------------
        # จุดเลี้ยว
        # -------------------------------------------------

        if i < len(path) - 1:

            cv2.circle(

                image,

                p2,

                6,

                (255, 0, 255),

                -1

            )


# =========================================================
# วาดผลลัพธ์
# =========================================================

def draw_result(

    image,

    path,

    parking_position,

    final_direction,

    target_index

):

    result = image.copy()


    # =====================================================
    # วาดวงกลม
    # =====================================================

    for i, circle in enumerate(

        CIRCLES

    ):

        cx, cy = circle["center"]

        radius = int(

            circle["radius"]

        )


        # -------------------------------------------------
        # วงกลมเป้าหมาย
        # -------------------------------------------------

        if i == target_index:

            cv2.circle(

                result,

                (cx, cy),

                radius,

                (0, 255, 0),

                4

            )


            cv2.putText(

                result,

                "TARGET",

                (

                    cx - 35,

                    cy + 5

                ),

                cv2.FONT_HERSHEY_SIMPLEX,

                0.5,

                (0, 0, 0),

                2

            )


        # -------------------------------------------------
        # วงกลมอื่น
        # -------------------------------------------------

        else:

            cv2.circle(

                result,

                (cx, cy),

                radius,

                (0, 0, 255),

                3

            )


        # -------------------------------------------------
        # ชื่อสี
        # -------------------------------------------------

        cv2.putText(

            result,

            circle["color"],

            (

                cx - 30,

                cy - radius - 8

            ),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.5,

            (0, 0, 0),

            2

        )


    # =====================================================
    # วาดเส้นทาง
    # =====================================================

    draw_path(

        result,

        path

    )


    # =====================================================
    # จุด A
    # =====================================================

    cv2.circle(

        result,

        START,

        8,

        (0, 255, 0),

        -1

    )


    cv2.putText(

        result,

        "A",

        (

            START[0] + 10,

            START[1]

        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.8,

        (0, 255, 0),

        2

    )


    # =====================================================
    # รถเริ่มต้น
    # =====================================================

    draw_robot(

        result,

        START,

        START_DIRECTION

    )


    # =====================================================
    # จุดจอด
    # =====================================================

    cv2.circle(

        result,

        parking_position,

        7,

        (255, 0, 0),

        -1

    )


    cv2.putText(

        result,

        "PARK",

        (

            parking_position[0] + 10,

            parking_position[1] - 10

        ),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.5,

        (255, 0, 0),

        2

    )


    # =====================================================
    # รถตอนจอด
    # =====================================================

    draw_robot(

        result,

        parking_position,

        final_direction

    )


    return result


# =========================================================
# MAIN
# =========================================================

def main():

    print()

    print(
        "================================"
    )

    print(
        "       ROBOT PATH PLANNER"
    )

    print(
        "================================"
    )

    print()


    # =====================================================
    # โหลดรูป
    # =====================================================

    image = cv2.imread(

        IMAGE_PATH

    )


    if image is None:

        print(

            "❌ ไม่พบไฟล์:",

            IMAGE_PATH

        )

        return


    height, width = image.shape[:2]


    # =====================================================
    # แสดงสี
    # =====================================================

    print(
        "เลือกสีเป้าหมาย"
    )

    print(
        "1. GREEN"
    )

    print(
        "2. BLUE"
    )

    print(
        "3. RED"
    )

    print(
        "4. PURPLE"
    )

    print(
        "5. CYAN"
    )

    print(
        "6. ORANGE"
    )


    print()


    choice = input(

        "เลือก = "

    ).strip()


    # =====================================================
    # ตรวจ input
    # =====================================================

    if not choice.isdigit():

        print(

            "❌ กรุณาเลือกเป็นตัวเลข 1-6"

        )

        return


    choice = int(choice)


    if choice < 1 or choice > 6:

        print(

            "❌ กรุณาเลือก 1-6"

        )

        return


    # =====================================================
    # เลือก target
    # =====================================================

    target_index = choice - 1

    target = CIRCLES[

        target_index

    ]


    print()

    print(

        "Target =",

        target["color"]

    )


    print(

        "Center =",

        target["center"]

    )


    # =====================================================
    # หา "ด้านหน้าวงกลม"
    # จากตำแหน่ง A
    # =====================================================

    preferred_side = get_preferred_side(

        target

    )


    print(

        "ด้านที่ควรจอด =",

        preferred_side

    )


    # =====================================================
    # Candidate ทั้ง 4 ด้าน
    # =====================================================

    candidates = get_parking_candidates(

        target

    )


    # =====================================================
    # ลำดับการลอง
    #
    # เอาด้านที่หันเข้าหา A ก่อน
    # =====================================================

    side_order = [

        preferred_side

    ]


    for side in [

        "TOP",

        "RIGHT",

        "BOTTOM",

        "LEFT"

    ]:

        if side not in side_order:

            side_order.append(side)


    # =====================================================
    # หาเส้นทาง
    # =====================================================

    best_path = None

    best_candidate = None


    print()

    print(

        "กำลังหาเส้นทาง..."

    )


    # =====================================================
    # ลองทีละด้าน
    # =====================================================

    for side in side_order:

        candidate = candidates[side]

        parking_position = candidate[

            "position"

        ]


        # -------------------------------------------------
        # อยู่นอกภาพ
        # -------------------------------------------------

        if not (

            0 <= parking_position[0] < width

            and

            0 <= parking_position[1] < height

        ):

            print(

                side,

                "-> อยู่นอกภาพ"

            )

            continue


        # -------------------------------------------------
        # จุดจอดชนหรือไม่
        # -------------------------------------------------

        if is_blocked(

            parking_position

        ):

            print(

                side,

                "-> จุดจอดชน"

            )

            continue


        # -------------------------------------------------
        # A*
        # -------------------------------------------------

        path = astar(

            START,

            parking_position,

            width,

            height

        )


        if path is None:

            print(

                side,

                "-> ไม่มีเส้นทาง"

            )

            continue


        # -------------------------------------------------
        # เจอแล้ว
        #
        # ถ้าเป็นด้านที่ควรจอด
        # ใช้ทันที
        # -------------------------------------------------

        best_path = path

        best_candidate = candidate

        break


    # =====================================================
    # ไม่มีเส้นทาง
    # =====================================================

    if best_path is None:

        print()

        print(

            "❌ ไม่พบเส้นทางไปวงกลม"

        )

        return


    # =====================================================
    # จุดจอด
    # =====================================================

    parking_position = (

        best_candidate["position"]

    )


    final_direction = (

        best_candidate["direction"]

    )


    # =====================================================
    # ลดจุด
    # =====================================================

    best_path = simplify_path(

        best_path

    )


    # =====================================================
    # สร้างคำสั่ง
    # =====================================================

    commands = path_to_commands(

        best_path,

        START_DIRECTION,

        final_direction

    )


    # =====================================================
    # คำนวณระยะทาง
    # =====================================================

    total_distance = 0


    for i in range(

        1,

        len(best_path)

    ):

        x1, y1 = best_path[i - 1]

        x2, y2 = best_path[i]


        total_distance += (

            abs(x2 - x1)

            +

            abs(y2 - y1)

        )


    # =====================================================
    # RESULT
    # =====================================================

    print()

    print(
        "================================"
    )

    print(
        "             RESULT"
    )

    print(
        "================================"
    )


    print()

    print(

        "จุดเริ่ม A =",

        START

    )


    print(

        "เป้าหมาย =",

        target["color"]

    )


    print(

        "ศูนย์กลาง =",

        target["center"]

    )


    print(

        "ด้านที่จอด =",

        best_candidate["direction"]

    )


    print(

        "จุดจอด =",

        parking_position

    )


    print(

        "หน้ารถ =",

        final_direction

    )


    print(

        "ระยะทาง =",

        total_distance,

        "px"

    )


    # =====================================================
    # คำสั่ง
    # =====================================================

    print()

    print(
        "========== คำสั่งรถ =========="
    )


    for i, command in enumerate(

        commands,

        start=1

    ):

        print(

            f"{i}. {command}"

        )


    # =====================================================
    # วาดภาพ
    # =====================================================

    result = draw_result(

        image,

        best_path,

        parking_position,

        final_direction,

        target_index

    )


    # =====================================================
    # บันทึก
    # =====================================================

    cv2.imwrite(

        "img/route.png",

        result

    )


    print()

    print(

        "บันทึกแล้ว -> img/route.png"

    )


    # =====================================================
    # แสดง
    # =====================================================

    cv2.imshow(

        "Robot Route",

        result

    )


    cv2.waitKey(0)

    cv2.destroyAllWindows()


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()