#!/usr/bin/env python3
"""HC-SR04 + SG90 near-continuous OLED radar, version 4.

Version 4 changes:
  - 3-degree sampling during a near-continuous servo sweep
  - one ultrasonic reading every 75 ms or longer
  - neighboring three-point median correction for isolated noise
  - approximately three seconds per 120-degree one-way sweep

The 2 m full-screen display and persistent points are inherited from version 3.
"""

import argparse
import math
from collections import deque
from queue import Empty, Full, Queue
from statistics import median
from threading import Event, Thread
from time import monotonic, monotonic_ns, sleep

from gpiozero import AngularServo, DigitalInputDevice, OutputDevice
from gpiozero.pins.pigpio import PiGPIOFactory
from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306


TRIG_GPIO = 5
ECHO_GPIO = 6
SERVO_GPIO = 12

ECHO_TIMEOUT_S = 0.03
PING_INTERVAL_S = 0.075
SERVO_SETTLE_S = 0.010
SERVO_SMOOTH_STEP_DEG = 1
SERVO_SMOOTH_STEP_S = 0.004

DEFAULT_SCAN_MIN_DEG = 30
DEFAULT_SCAN_MAX_DEG = 150
DEFAULT_SCAN_STEP_DEG = 3

# Calibrated on the installed SG90: 500-2500 us gives approximately 180 degrees.
SERVO_MIN_PULSE_S = 0.0005
SERVO_MAX_PULSE_S = 0.0025

OLED_MAX_DISTANCE_CM = 200.0
OLED_CENTER_X = 63
OLED_CENTER_Y = 63
OLED_MAX_RADIUS = 60
OLED_SCAN_ARC_START_DEG = 210
OLED_SCAN_ARC_END_DEG = 330
OLED_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

parser = argparse.ArgumentParser(description="HC-SR04 + SG90 OLED radar Ver4")
parser.add_argument("--min-angle", type=int, default=DEFAULT_SCAN_MIN_DEG)
parser.add_argument("--max-angle", type=int, default=DEFAULT_SCAN_MAX_DEG)
parser.add_argument("--step", type=int, default=DEFAULT_SCAN_STEP_DEG)
args = parser.parse_args()

if not 0 <= args.min_angle < args.max_angle <= 180:
    parser.error("angles must satisfy 0 <= min-angle < max-angle <= 180")
if args.step <= 0:
    parser.error("step must be greater than zero")

SCAN_MIN_DEG = args.min_angle
SCAN_MAX_DEG = args.max_angle
SCAN_STEP_DEG = args.step

pin_factory = PiGPIOFactory()
trigger = OutputDevice(
    TRIG_GPIO,
    active_high=True,
    initial_value=False,
    pin_factory=pin_factory,
)
echo = DigitalInputDevice(ECHO_GPIO, pull_up=False, pin_factory=pin_factory)
servo = AngularServo(
    SERVO_GPIO,
    min_angle=0,
    max_angle=180,
    min_pulse_width=SERVO_MIN_PULSE_S,
    max_pulse_width=SERVO_MAX_PULSE_S,
    initial_angle=None,
    pin_factory=pin_factory,
)
oled_device = ssd1306(i2c(port=1, address=0x3C))
oled_device.persist = True
oled_device.contrast(255)

try:
    oled_small_font = ImageFont.truetype(OLED_FONT_PATH, 8, index=0)
except OSError:
    oled_small_font = ImageFont.load_default()

oled_queue = Queue(maxsize=1)
oled_stop = Event()


def wait_for_level(level: bool, timeout_s: float) -> bool:
    deadline = monotonic_ns() + int(timeout_s * 1_000_000_000)
    while echo.is_active != level:
        if monotonic_ns() >= deadline:
            return False
    return True


def measure_once():
    if not wait_for_level(False, 0.01):
        return None, "ECHO HIGH"

    trigger.on()
    sleep(0.00001)
    trigger.off()

    if not wait_for_level(True, ECHO_TIMEOUT_S):
        return None, "TIMEOUT"

    start_ns = monotonic_ns()
    if not wait_for_level(False, ECHO_TIMEOUT_S):
        return None, "TIMEOUT"

    pulse_us = (monotonic_ns() - start_ns) / 1_000.0
    distance_cm = pulse_us / 58.0
    if not 2.0 <= distance_cm <= 400.0:
        return None, "OUT RANGE"

    return distance_cm, "OK"


def update_scan_with_neighbor_median(
    scan: dict[int, float],
    recent_points: deque[tuple[int, float]],
    angle_deg: int,
    distance_cm: float,
) -> None:
    # Show the new point immediately.
    scan[angle_deg] = distance_cm
    recent_points.append((angle_deg, distance_cm))

    # Once three adjacent samples exist, correct the middle point with their median.
    if len(recent_points) == 3:
        middle_angle_deg = recent_points[1][0]
        scan[middle_angle_deg] = median(
            point_distance_cm for _, point_distance_cm in recent_points
        )


def update_oled(
    angle_deg: int,
    distance_cm: float | None,
    status: str,
    scan: dict[int, float],
) -> None:
    image = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(image)

    draw.arc(
        (
            OLED_CENTER_X - OLED_MAX_RADIUS,
            OLED_CENTER_Y - OLED_MAX_RADIUS,
            OLED_CENTER_X + OLED_MAX_RADIUS,
            OLED_CENTER_Y + OLED_MAX_RADIUS,
        ),
        OLED_SCAN_ARC_START_DEG,
        OLED_SCAN_ARC_END_DEG,
        fill=1,
    )

    for measured_angle_deg, measured_distance_cm in scan.items():
        measured_angle = math.radians(measured_angle_deg)
        point_radius = int(
            OLED_MAX_RADIUS
            * min(measured_distance_cm, OLED_MAX_DISTANCE_CM)
            / OLED_MAX_DISTANCE_CM
        )
        point_x = OLED_CENTER_X + int(point_radius * math.cos(measured_angle))
        point_y = OLED_CENTER_Y - int(point_radius * math.sin(measured_angle))
        draw.rectangle((point_x, point_y, point_x + 1, point_y + 1), fill=1)

    draw.rectangle(
        (
            OLED_CENTER_X - 1,
            OLED_CENTER_Y - 1,
            OLED_CENTER_X + 1,
            OLED_CENTER_Y + 1,
        ),
        fill=1,
    )

    if distance_cm is not None:
        current_angle = math.radians(angle_deg)
        point_radius = int(
            OLED_MAX_RADIUS
            * min(distance_cm, OLED_MAX_DISTANCE_CM)
            / OLED_MAX_DISTANCE_CM
        )
        point_x = OLED_CENTER_X + int(point_radius * math.cos(current_angle))
        point_y = OLED_CENTER_Y - int(point_radius * math.sin(current_angle))
        draw.line(
            (OLED_CENTER_X, OLED_CENTER_Y, point_x, point_y),
            fill=1,
        )
        draw.ellipse(
            (point_x - 2, point_y - 2, point_x + 2, point_y + 2),
            fill=1,
        )
        distance_text = f"{int(round(distance_cm))}cm"
    else:
        distance_text = status[:8]

    draw.rectangle((0, 0, 31, 9), fill=0)
    draw.text((1, 0), distance_text, font=oled_small_font, fill=1)
    draw.rectangle((53, 0, 73, 9), fill=0)
    draw.text((57, 0), "2m", font=oled_small_font, fill=1)
    draw.rectangle((99, 0, 127, 9), fill=0)
    draw.text((101, 0), f"{angle_deg}d", font=oled_small_font, fill=1)

    oled_device.display(image)


def oled_worker() -> None:
    while not oled_stop.is_set() or not oled_queue.empty():
        try:
            payload = oled_queue.get(timeout=0.1)
        except Empty:
            continue

        try:
            update_oled(*payload)
        except Exception as error:
            print(f"OLED ERROR: {error}", flush=True)
        finally:
            oled_queue.task_done()


def submit_oled(
    angle_deg: int,
    distance_cm: float | None,
    status: str,
    scan: dict[int, float],
) -> None:
    # Keep only the newest frame so OLED I/O never delays the servo sweep.
    payload = (angle_deg, distance_cm, status, dict(scan))
    while True:
        try:
            oled_queue.put_nowait(payload)
            return
        except Full:
            try:
                oled_queue.get_nowait()
                oled_queue.task_done()
            except Empty:
                pass


def scan_angles():
    forward = range(SCAN_MIN_DEG, SCAN_MAX_DEG + 1, SCAN_STEP_DEG)
    reverse = range(
        SCAN_MAX_DEG - SCAN_STEP_DEG,
        SCAN_MIN_DEG,
        -SCAN_STEP_DEG,
    )
    while True:
        yield from forward
        yield from reverse


def move_servo_smooth(current_angle_deg: int, target_angle_deg: int) -> int:
    if current_angle_deg == target_angle_deg:
        return target_angle_deg

    direction = (
        SERVO_SMOOTH_STEP_DEG
        if target_angle_deg > current_angle_deg
        else -SERVO_SMOOTH_STEP_DEG
    )
    for angle_deg in range(
        current_angle_deg + direction,
        target_angle_deg + direction,
        direction,
    ):
        servo.angle = angle_deg
        sleep(SERVO_SMOOTH_STEP_S)
    return target_angle_deg


print(
    "HC-SR04 servo radar Ver4: "
    f"TRIG=GPIO{TRIG_GPIO}, ECHO=GPIO{ECHO_GPIO}, SERVO=GPIO{SERVO_GPIO}"
)
print(
    f"走査範囲 {SCAN_MIN_DEG}〜{SCAN_MAX_DEG}度 / {SCAN_STEP_DEG}度刻み。"
    f"測定間隔 {PING_INTERVAL_S * 1000:.0f}ms以上。"
    "終了するには Ctrl+C を押します。"
)

scan: dict[int, float] = {}
recent_points: deque[tuple[int, float]] = deque(maxlen=3)
current_angle_deg = 90
last_ping_started = 0.0
sweep_started = None
oled_worker_thread = Thread(target=oled_worker, name="oled-v4", daemon=True)
oled_worker_thread.start()

try:
    servo.angle = current_angle_deg
    sleep(0.3)

    for angle_deg in scan_angles():
        current_angle_deg = move_servo_smooth(current_angle_deg, angle_deg)
        sleep(SERVO_SETTLE_S)

        wait_s = PING_INTERVAL_S - (monotonic() - last_ping_started)
        if wait_s > 0.0:
            sleep(wait_s)

        last_ping_started = monotonic()
        distance_cm, status = measure_once()
        if distance_cm is not None:
            update_scan_with_neighbor_median(
                scan,
                recent_points,
                angle_deg,
                distance_cm,
            )
            print(
                f"{angle_deg:3d} deg  {distance_cm:6.1f} cm  {status}",
                flush=True,
            )
        else:
            print(f"{angle_deg:3d} deg  ---.- cm  {status}", flush=True)

        submit_oled(angle_deg, distance_cm, status, scan)

        if angle_deg in (SCAN_MIN_DEG, SCAN_MAX_DEG):
            endpoint_time = monotonic()
            if sweep_started is not None:
                print(
                    f"ONE-WAY SWEEP: {endpoint_time - sweep_started:.2f} s",
                    flush=True,
                )
            sweep_started = endpoint_time
except KeyboardInterrupt:
    print("\n停止しました。サーボを中央へ戻します。")
finally:
    for attempt in range(2):
        try:
            trigger.off()
            break
        except Exception as error:
            if attempt == 1:
                print(f"TRIGGER CLEANUP WARNING: {error}", flush=True)
            sleep(0.05)

    try:
        current_angle_deg = move_servo_smooth(current_angle_deg, 90)
        sleep(0.3)
    except Exception as error:
        print(f"SERVO CENTER WARNING: {error}", flush=True)
        try:
            servo.angle = 90
            sleep(0.3)
        except Exception as retry_error:
            print(f"SERVO CENTER RETRY WARNING: {retry_error}", flush=True)

    try:
        servo.detach()
    except Exception as error:
        print(f"SERVO DETACH WARNING: {error}", flush=True)

    for device_name, device in (
        ("servo", servo),
        ("trigger", trigger),
        ("echo", echo),
    ):
        try:
            device.close()
        except Exception as error:
            print(f"{device_name.upper()} CLOSE WARNING: {error}", flush=True)

    oled_stop.set()
    oled_worker_thread.join(timeout=2.0)
    if oled_worker_thread.is_alive():
        print("OLED CLOSE WARNING: worker did not stop", flush=True)
    else:
        try:
            oled_device.cleanup()
        except Exception as error:
            print(f"OLED CLOSE WARNING: {error}", flush=True)

    try:
        pin_factory.close()
    except Exception as error:
        print(f"GPIO FACTORY CLOSE WARNING: {error}", flush=True)
