#!/usr/bin/env python3
"""Display HC-SR04 distance on the existing SSD1306 OLED.

HC-SR04:
  TRIG: BCM GPIO5 / physical pin 29
  ECHO: BCM GPIO6 / physical pin 31

The sensor is read by the system Python gpiozero installation. The OLED helper
in the sibling oled-ssd1306 directory is used for output, so the OLED keeps its
I2C GPIO2/GPIO3 wiring and does not conflict with the sensor pins.
"""

from pathlib import Path
from subprocess import run
from time import monotonic, monotonic_ns, sleep

from gpiozero import DigitalInputDevice, OutputDevice


TRIG_GPIO = 5
ECHO_GPIO = 6
ECHO_TIMEOUT_S = 0.03
OLED_UPDATE_S = 1.0
PROJECT_DIR = Path(__file__).resolve().parents[1]
OLED_SHOW = PROJECT_DIR / "oled-ssd1306" / "oled-show.sh"

trigger = OutputDevice(TRIG_GPIO, active_high=True, initial_value=False)
echo = DigitalInputDevice(ECHO_GPIO, pull_up=False)


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
        return None, "ECHO START TIMEOUT"

    start_ns = monotonic_ns()
    if not wait_for_level(False, ECHO_TIMEOUT_S):
        return None, "ECHO END TIMEOUT"

    pulse_us = (monotonic_ns() - start_ns) / 1_000.0
    distance_cm = pulse_us / 58.0

    if not 2.0 <= distance_cm <= 400.0:
        return None, f"OUT OF RANGE {distance_cm:.1f}"

    return distance_cm, "OK"


def update_oled(distance_cm: float | None, status: str) -> None:
    if distance_cm is None:
        message = f"HC-SR04\n{status}"
    else:
        message = f"HC-SR04\nDistance\n{distance_cm:5.1f} cm\n{status}"

    result = run(
        [str(OLED_SHOW), message],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "unknown OLED error"
        print(f"OLED ERROR: {detail}", flush=True)


print(f"HC-SR04 + OLED: TRIG=GPIO{TRIG_GPIO}, ECHO=GPIO{ECHO_GPIO}")
print("終了するには Ctrl+C を押します。")

last_oled_update = 0.0

try:
    while True:
        distance_cm, status = measure_once()
        if distance_cm is None:
            print(status, flush=True)
        else:
            print(f"{distance_cm:6.1f} cm  {status}", flush=True)

        now = monotonic()
        if now - last_oled_update >= OLED_UPDATE_S:
            update_oled(distance_cm, status)
            last_oled_update = now

        sleep(0.10)
except KeyboardInterrupt:
    print("\n停止しました。")
finally:
    trigger.off()
    trigger.close()
    echo.close()
