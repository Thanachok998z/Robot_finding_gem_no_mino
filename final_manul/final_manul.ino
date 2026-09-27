#include <WiFi.h>
#include <WebServer.h>
#include <InEngMotor.h>

const char* WIFI_SSID = "nut_connect";
const char* WIFI_PASSWORD = "112234567";

WebServer server(80);

bool moving = false;
unsigned long stopTime = 0;

int leftSpeed = 200;
int rightSpeed = 200;

void stopRobot() {
  inengmotor.stop();
  moving = false;
  Serial.println("STOP");
}

void forwardRobot(int left, int right) {
  left = constrain(left, 0, 255);
  right = constrain(right, 0, 255);

  inengmotor.forward(left, right);

  moving = true;

  Serial.print("FORWARD L=");
  Serial.print(left);
  Serial.print(" R=");
  Serial.println(right);
}

void handleRoot() {
  String html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Robot Control</title>

<style>
body {
  font-family: Arial;
  text-align: center;
  background: #111;
  color: white;
  margin: 0;
  padding: 30px;
}

.container {
  max-width: 450px;
  margin: auto;
  background: #222;
  padding: 25px;
  border-radius: 20px;
}

input {
  width: 90%;
  padding: 15px;
  margin: 8px;
  font-size: 22px;
  text-align: center;
  border-radius: 10px;
  border: none;
}

button {
  width: 90%;
  padding: 18px;
  margin: 10px;
  font-size: 22px;
  font-weight: bold;
  border: none;
  border-radius: 12px;
}

.forward {
  background: #00c853;
  color: white;
}

.stop {
  background: #d50000;
  color: white;
}

.status {
  margin-top: 20px;
  font-size: 18px;
}
</style>
</head>

<body>

<div class="container">

<h1>ROBOT CONTROL</h1>

<h3>ความเร็ว</h3>

<input id="speed" type="text" value="200 200">

<h3>เวลา (วินาที)</h3>

<input id="time" type="number" value="1" step="0.1">

<button class="forward" onclick="forward()">
เดินหน้า
</button>

<button class="stop" onclick="stopRobot()">
STOP
</button>

<div class="status" id="status">
พร้อม
</div>

</div>

<script>

function forward() {

  let speed = document.getElementById("speed").value;
  let time = document.getElementById("time").value;

  fetch("/forward?speed=" + encodeURIComponent(speed) + "&time=" + time)
    .then(response => response.text())
    .then(data => {
      document.getElementById("status").innerHTML = data;
    });

}

function stopRobot() {

  fetch("/stop")
    .then(response => response.text())
    .then(data => {
      document.getElementById("status").innerHTML = data;
    });

}

</script>

</body>
</html>
)rawliteral";

  server.send(200, "text/html", html);
}

void handleForward() {

  if (!server.hasArg("speed") || !server.hasArg("time")) {
    server.send(400, "text/plain", "ข้อมูลไม่ครบ");
    return;
  }

  String speed = server.arg("speed");
  float seconds = server.arg("time").toFloat();

  int spaceIndex = speed.indexOf(' ');

  if (spaceIndex == -1) {
    server.send(400, "text/plain", "กรอกความเร็วแบบ 200 200");
    return;
  }

  int left = speed.substring(0, spaceIndex).toInt();
  int right = speed.substring(spaceIndex + 1).toInt();

  if (left < 0 || left > 255 ||
      right < 0 || right > 255) {
    server.send(400, "text/plain", "ความเร็วต้องอยู่ 0-255");
    return;
  }

  if (seconds <= 0) {
    server.send(400, "text/plain", "เวลาต้องมากกว่า 0");
    return;
  }

  leftSpeed = left;
  rightSpeed = right;

  forwardRobot(leftSpeed, rightSpeed);

  stopTime = millis() + (unsigned long)(seconds * 1000);

  String result = "เดินหน้า L=";
  result += left;
  result += " R=";
  result += right;
  result += " เป็นเวลา ";
  result += seconds;
  result += " วินาที";

  server.send(200, "text/plain", result);
}

void handleStop() {
  stopRobot();
  server.send(200, "text/plain", "STOP");
}

void setup() {

  Serial.begin(115200);

  inengmotor.begin();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi Connected");

  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/forward", handleForward);
  server.on("/stop", handleStop);

  server.begin();

  Serial.println("Web Server Started");
}

void loop() {

  server.handleClient();

  if (moving && millis() >= stopTime) {
    stopRobot();
  }
}