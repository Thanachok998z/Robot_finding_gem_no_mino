import cv2
import time
import threading
import requests

from flask import Flask, Response, jsonify, request, render_template_string

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# =========================================================
# CONFIG
# =========================================================

MODEL_PATH = "hand_landmarker.task"

CAMERA_INDEX = 0

DEFAULT_ROBOT_CODE = "1234"

DEFAULT_LEFT_SPEED = 100
DEFAULT_RIGHT_SPEED = 100


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


# =========================================================
# ROBOT STATE
# =========================================================

ESP32_IP = ""
ROBOT_CODE = DEFAULT_ROBOT_CODE

LEFT_SPEED = DEFAULT_LEFT_SPEED
RIGHT_SPEED = DEFAULT_RIGHT_SPEED

CURRENT_COMMAND = "STOP"
LAST_SENT_COMMAND = "STOP"

ROBOT_CONNECTED = False

state_lock = threading.Lock()


# =========================================================
# COMMAND
# =========================================================

COMMAND_MAP = {
    "STOP": 0,
    "LEFT": 1,
    "RIGHT": 2,
    "FORWARD": 3,
    "BACKWARD": 4,
    "GRAB": 5,
    "DROP": 6
}


# =========================================================
# CAMERA
# =========================================================

camera = cv2.VideoCapture(CAMERA_INDEX)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

latest_frame = None
frame_lock = threading.Lock()


# =========================================================
# MEDIAPIPE
# =========================================================

BaseOptions = python.BaseOptions

options = vision.HandLandmarkerOptions(
    base_options=BaseOptions(
        model_asset_path=MODEL_PATH
    ),
    running_mode=vision.RunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

detector = vision.HandLandmarker.create_from_options(options)


# =========================================================
# FINGER COUNT
# =========================================================

def distance(p1, p2):
    dx = p1.x - p2.x
    dy = p1.y - p2.y

    return (dx * dx + dy * dy) ** 0.5


def count_fingers(hand_landmarks, handedness):
    """
    Count fingers.

    MediaPipe landmark:
    0  = wrist

    Thumb:
    4  = thumb tip
    3  = thumb IP

    Index:
    8  = tip
    6  = PIP

    Middle:
    12 = tip
    10 = PIP

    Ring:
    16 = tip
    14 = PIP

    Pinky:
    20 = tip
    18 = PIP
    """

    fingers = 0

    # -----------------------------------------------------
    # INDEX
    # -----------------------------------------------------

    if hand_landmarks[8].y < hand_landmarks[6].y:
        fingers += 1

    # -----------------------------------------------------
    # MIDDLE
    # -----------------------------------------------------

    if hand_landmarks[12].y < hand_landmarks[10].y:
        fingers += 1

    # -----------------------------------------------------
    # RING
    # -----------------------------------------------------

    if hand_landmarks[16].y < hand_landmarks[14].y:
        fingers += 1

    # -----------------------------------------------------
    # PINKY
    # -----------------------------------------------------

    if hand_landmarks[20].y < hand_landmarks[18].y:
        fingers += 1

    # -----------------------------------------------------
    # THUMB
    #
    # ใช้ระยะจากปลายนิ้วถึงนิ้วก้อย/ข้อมือ
    # เพื่อให้การนับเหมาะกับมือที่หมุน
    # -----------------------------------------------------

    thumb_tip = hand_landmarks[4]
    thumb_ip = hand_landmarks[3]

    if handedness == "Right":

        if thumb_tip.x < thumb_ip.x:
            fingers += 1

    else:

        if thumb_tip.x > thumb_ip.x:
            fingers += 1

    return fingers


# =========================================================
# GESTURE → COMMAND
# =========================================================

def right_hand_command(fingers):

    if fingers == 1:
        return "LEFT"

    elif fingers == 2:
        return "RIGHT"

    elif fingers == 3:
        return "FORWARD"

    elif fingers == 4:
        return "BACKWARD"

    else:
        return "STOP"


def left_hand_command(fingers):

    if fingers <= 3:
        return "GRAB"

    elif fingers >= 4:
        return "DROP"

    return "STOP"


# =========================================================
# SEND COMMAND TO ESP32
# =========================================================

def send_command(command, force=False):

    global LAST_SENT_COMMAND
    global ROBOT_CONNECTED

    with state_lock:

        ip = ESP32_IP
        code = ROBOT_CODE
        left_speed = LEFT_SPEED
        right_speed = RIGHT_SPEED

    if not ip:
        ROBOT_CONNECTED = False
        return False

    if command not in COMMAND_MAP:
        return False

    # ไม่ส่งคำสั่งซ้ำ
    if not force and command == LAST_SENT_COMMAND:
        return True

    cmd_number = COMMAND_MAP[command]

    url = f"http://{ip}/command"

    params = {
        "code": code,
        "cmd": cmd_number,
        "left": left_speed,
        "right": right_speed
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=0.5
        )

        if response.ok:

            LAST_SENT_COMMAND = command
            ROBOT_CONNECTED = True

            print(
                f"[ESP32] "
                f"{command} "
                f"L={left_speed} "
                f"R={right_speed}"
            )

            return True

        ROBOT_CONNECTED = False

        return False

    except requests.RequestException as e:

        ROBOT_CONNECTED = False

        print("[ESP32 ERROR]", e)

        return False


# =========================================================
# SET CURRENT COMMAND
# =========================================================

def set_command(command, force=False):

    global CURRENT_COMMAND

    with state_lock:
        CURRENT_COMMAND = command

    send_command(command, force=force)


# =========================================================
# DRAW HAND
# =========================================================

def draw_hand(frame, landmarks, hand_name, fingers):

    h, w, _ = frame.shape

    # -----------------------------------------------------
    # Draw points
    # -----------------------------------------------------

    for i, point in enumerate(landmarks):

        x = int(point.x * w)
        y = int(point.y * h)

        cv2.circle(
            frame,
            (x, y),
            4,
            (0, 255, 0),
            -1
        )

    # -----------------------------------------------------
    # Draw hand name
    # -----------------------------------------------------

    wrist = landmarks[0]

    x = int(wrist.x * w)
    y = int(wrist.y * h)

    text = f"{hand_name}: {fingers} fingers"

    cv2.putText(
        frame,
        text,
        (x, y - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 255),
        2
    )


# =========================================================
# AI CAMERA LOOP
# =========================================================

def ai_loop():

    global latest_frame

    print("AI camera starting...")

    last_ai_command = "STOP"

    while True:

        success, frame = camera.read()

        if not success:

            print("Cannot read camera")

            time.sleep(0.1)

            continue

        # -------------------------------------------------
        # Mirror camera
        # -------------------------------------------------

        frame = cv2.flip(frame, 1)

        # -------------------------------------------------
        # Convert BGR → RGB
        # -------------------------------------------------

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        # -------------------------------------------------
        # MediaPipe
        # -------------------------------------------------

        try:

            result = detector.detect(mp_image)

        except Exception as e:

            print("[MEDIAPIPE ERROR]", e)

            continue

        right_command = None
        left_command = None

        right_fingers = 0
        left_fingers = 0

        # -------------------------------------------------
        # Detect hands
        # -------------------------------------------------

        for i, landmarks in enumerate(
            result.hand_landmarks
        ):

            if i >= len(result.handedness):

                continue

            mp_hand = result.handedness[i][0].category_name

            # เพราะภาพถูก mirror
            if mp_hand == "Left":
                real_hand = "Right"
            else:
                real_hand = "Left"

            fingers = count_fingers(
                landmarks,
                real_hand
            )

            # ---------------------------------------------
            # Right hand
            # ---------------------------------------------

            if real_hand == "Right":

                right_fingers = fingers

                right_command = right_hand_command(
                    fingers
                )

            # ---------------------------------------------
            # Left hand
            # ---------------------------------------------

            elif real_hand == "Left":

                left_fingers = fingers

                left_command = left_hand_command(
                    fingers
                )

            # ---------------------------------------------
            # Draw
            # ---------------------------------------------

            draw_hand(
                frame,
                landmarks,
                real_hand,
                fingers
            )

        # =================================================
        # COMMAND PRIORITY
        # =================================================

        if right_command is not None:

            # Right hand controls movement
            ai_command = right_command

        elif left_command is not None:

            # Left hand controls grab/drop
            ai_command = left_command

        else:

            # No hand = STOP
            ai_command = "STOP"

        # =================================================
        # SEND ONLY WHEN COMMAND CHANGES
        # =================================================

        if ai_command != last_ai_command:

            set_command(ai_command)

            last_ai_command = ai_command

        # =================================================
        # DISPLAY
        # =================================================

        cv2.rectangle(
            frame,
            (10, 10),
            (630, 120),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            frame,
            f"AI COMMAND: {ai_command}",
            (25, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Right: {right_fingers}",
            (25, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Left: {left_fingers}",
            (200, 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        # -------------------------------------------------
        # Robot connection
        # -------------------------------------------------

        if ROBOT_CONNECTED:

            connection_text = "ESP32: CONNECTED"

        else:

            connection_text = "ESP32: NOT CONNECTED"

        cv2.putText(
            frame,
            connection_text,
            (25, 105),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        # =================================================
        # SAVE FRAME
        # =================================================

        with frame_lock:

            latest_frame = frame.copy()


# =========================================================
# CAMERA STREAM
# =========================================================

def generate_frames():

    while True:

        with frame_lock:

            if latest_frame is None:

                time.sleep(0.05)

                continue

            frame = latest_frame.copy()

        success, buffer = cv2.imencode(
            ".jpg",
            frame
        )

        if not success:

            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )

        time.sleep(0.03)


# =========================================================
# WEB PAGE
# =========================================================

HTML = """

<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Robot AI Control</title>

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    font-family:
        Arial,
        sans-serif;

    background: #111;

    color: white;

}

.container {

    max-width: 1100px;

    margin: auto;

    padding: 20px;

}

h1 {

    text-align: center;

    margin-bottom: 20px;

}

.card {

    background: #1e1e1e;

    border-radius: 15px;

    padding: 20px;

    margin-bottom: 20px;

}

input {

    width: 100%;

    padding: 12px;

    margin-top: 8px;

    margin-bottom: 12px;

    border-radius: 8px;

    border: 1px solid #555;

    background: #2b2b2b;

    color: white;

    font-size: 16px;

}

button {

    border: none;

    border-radius: 10px;

    padding: 15px 20px;

    font-size: 16px;

    cursor: pointer;

}

.connect {

    background: #2196f3;

    color: white;

    width: 100%;

}

.stop {

    background: #f44336;

    color: white;

}

.controls {

    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 10px;

    max-width: 500px;

    margin: auto;

}

.controls button {

    min-height: 65px;

}

.speed {

    margin: 15px 0;

}

.speed input {

    padding: 0;

}

.status {

    font-size: 18px;

    padding: 10px;

    border-radius: 8px;

    background: #292929;

}

.camera {

    width: 100%;

    max-width: 800px;

    display: block;

    margin: auto;

    border-radius: 12px;

}

.value {

    font-weight: bold;

    color: #00ff99;

}

.ai-command {

    font-size: 30px;

    text-align: center;

    font-weight: bold;

    padding: 20px;

    background: #252525;

    border-radius: 12px;

}

</style>

</head>


<body>

<div class="container">

<h1>🤖 Robot AI Control</h1>


<!-- ============================================= -->

<!-- CONNECTION -->

<!-- ============================================= -->

<div class="card">

<h2>ESP32 Connection</h2>

<label>ESP32 IP</label>

<input
    id="ip"
    type="text"
    placeholder="192.168.1.123"
>


<label>Robot Code</label>

<input
    id="code"
    type="text"
    value="1234"
>


<button
    class="connect"
    onclick="connectRobot()"
>
    CONNECT ESP32
</button>

</div>


<!-- ============================================= -->

<!-- STATUS -->

<!-- ============================================= -->

<div class="card">

<h2>Status</h2>

<div class="status">

ESP32:

<span
    id="connection"
    class="value"
>
NOT CONNECTED
</span>

</div>

<br>

<div class="ai-command">

AI:

<span id="command">
STOP
</span>

</div>

</div>


<!-- ============================================= -->

<!-- SPEED -->

<!-- ============================================= -->

<div class="card">

<h2>Motor Speed</h2>


<div class="speed">

<label>
Left:
<span
    id="leftValue"
    class="value"
>
100
</span>
</label>

<input
    id="left"
    type="range"
    min="0"
    max="255"
    value="100"
    oninput="updateSpeed()"
>

</div>


<div class="speed">

<label>
Right:
<span
    id="rightValue"
    class="value"
>
100
</span>
</label>

<input
    id="right"
    type="range"
    min="0"
    max="255"
    value="100"
    oninput="updateSpeed()"
>

</div>

</div>


<!-- ============================================= -->

<!-- MANUAL CONTROL -->

<!-- ============================================= -->

<div class="card">

<h2>Manual Control</h2>

<div class="controls">

<div></div>

<button
    onclick="sendCommand('FORWARD')"
>
    ▲<br>
    FORWARD
</button>

<div></div>


<button
    onclick="sendCommand('LEFT')"
>
    ◀<br>
    LEFT
</button>


<button
    class="stop"
    onclick="sendCommand('STOP')"
>
    ■<br>
    STOP
</button>


<button
    onclick="sendCommand('RIGHT')"
>
    ▶<br>
    RIGHT
</button>


<div></div>

<button
    onclick="sendCommand('BACKWARD')"
>
    ▼<br>
    BACKWARD
</button>

<div></div>

</div>


<br>


<div class="controls">

<button
    onclick="sendCommand('GRAB')"
>
    GRAB
</button>

<button
    onclick="sendCommand('DROP')"
>
    DROP
</button>

</div>

</div>


<!-- ============================================= -->

<!-- CAMERA -->

<!-- ============================================= -->

<div class="card">

<h2>AI Camera</h2>

<img
    class="camera"
    src="/video_feed"
>

</div>


</div>


<script>


async function connectRobot() {

    const ip =
        document.getElementById("ip").value;

    const code =
        document.getElementById("code").value;


    const response =
        await fetch("/connect", {

            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body: JSON.stringify({
                ip: ip,
                code: code
            })

        });


    const data =
        await response.json();


    if (data.success) {

        alert("ESP32 information saved");

    } else {

        alert(data.message);

    }

}


async function updateSpeed() {

    const left =
        document.getElementById("left").value;

    const right =
        document.getElementById("right").value;


    document.getElementById(
        "leftValue"
    ).innerText = left;


    document.getElementById(
        "rightValue"
    ).innerText = right;


    await fetch("/speed", {

        method: "POST",

        headers: {
            "Content-Type":
                "application/json"
        },

        body: JSON.stringify({

            left: left,
            right: right

        })

    });

}


async function sendCommand(command) {

    await fetch("/command", {

        method: "POST",

        headers: {
            "Content-Type":
                "application/json"
        },

        body: JSON.stringify({

            command: command

        })

    });

}


async function updateStatus() {

    try {

        const response =
            await fetch("/status");

        const data =
            await response.json();


        document.getElementById(
            "command"
        ).innerText = data.command;


        document.getElementById(
            "connection"
        ).innerText =
            data.connected
            ? "CONNECTED"
            : "NOT CONNECTED";


    } catch (error) {

        console.log(error);

    }

}


setInterval(
    updateStatus,
    300
);


</script>

</body>

</html>

"""


# =========================================================
# ROUTES
# =========================================================

@app.route("/")
def index():

    return render_template_string(
        HTML
    )


# =========================================================
# CONNECT
# =========================================================

@app.route(
    "/connect",
    methods=["POST"]
)
def connect():

    global ESP32_IP
    global ROBOT_CODE

    data = request.get_json() or {}

    ip = data.get(
        "ip",
        ""
    ).strip()

    code = data.get(
        "code",
        ""
    ).strip()


    if not ip:

        return jsonify({

            "success": False,

            "message":
                "กรุณาใส่ ESP32 IP"

        })


    if not code:

        return jsonify({

            "success": False,

            "message":
                "กรุณาใส่ Robot Code"

        })


    with state_lock:

        ESP32_IP = ip
        ROBOT_CODE = code


    # Test connection
    success = send_command(
        "STOP",
        force=True
    )


    return jsonify({

        "success": success,

        "message":
            "Connected"
            if success
            else "Cannot connect to ESP32"

    })


# =========================================================
# SPEED
# =========================================================

@app.route(
    "/speed",
    methods=["POST"]
)
def speed():

    global LEFT_SPEED
    global RIGHT_SPEED


    data = request.get_json() or {}


    try:

        left = int(
            data.get(
                "left",
                DEFAULT_LEFT_SPEED
            )
        )

        right = int(
            data.get(
                "right",
                DEFAULT_RIGHT_SPEED
            )
        )


    except ValueError:

        return jsonify({

            "success": False,

            "message":
                "Invalid speed"

        })


    left = max(
        0,
        min(255, left)
    )

    right = max(
        0,
        min(255, right)
    )


    with state_lock:

        LEFT_SPEED = left
        RIGHT_SPEED = right


    return jsonify({

        "success": True,

        "left": left,

        "right": right

    })


# =========================================================
# MANUAL COMMAND
# =========================================================

@app.route(
    "/command",
    methods=["POST"]
)
def command():

    data = request.get_json() or {}

    cmd = data.get(
        "command",
        "STOP"
    )


    if cmd not in COMMAND_MAP:

        return jsonify({

            "success": False,

            "message":
                "Unknown command"

        })


    success = send_command(
        cmd,
        force=True
    )


    global CURRENT_COMMAND

    with state_lock:

        CURRENT_COMMAND = cmd


    return jsonify({

        "success": success,

        "command": cmd

    })


# =========================================================
# STATUS
# =========================================================

@app.route("/status")
def status():

    with state_lock:

        command = CURRENT_COMMAND
        ip = ESP32_IP


    return jsonify({

        "command": command,

        "connected":
            ROBOT_CONNECTED,

        "ip":
            ip

    })


# =========================================================
# VIDEO
# =========================================================

@app.route("/video_feed")
def video_feed():

    return Response(

        generate_frames(),

        mimetype=
            "multipart/x-mixed-replace; boundary=frame"

    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print()
    print("==============================")
    print(" ROBOT AI WEB CONTROL")
    print("==============================")
    print()
    print("Open browser:")
    print("http://127.0.0.1:5000")
    print()
    print("AI mapping:")
    print("Right hand:")
    print("1 finger = LEFT")
    print("2 fingers = RIGHT")
    print("3 fingers = FORWARD")
    print("4 fingers = BACKWARD")
    print()
    print("Left hand:")
    print("0-3 fingers = GRAB")
    print("4-5 fingers = DROP")
    print()
    print("No hand = STOP")
    print()

    # -----------------------------------------------------
    # Start AI in background
    # -----------------------------------------------------

    ai_thread = threading.Thread(
        target=ai_loop,
        daemon=True
    )

    ai_thread.start()

    # -----------------------------------------------------
    # Start Flask
    # -----------------------------------------------------

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )