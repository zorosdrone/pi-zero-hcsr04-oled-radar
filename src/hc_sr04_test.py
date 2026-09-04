#!/usr/bin/env python3
"""HC-SR04 distance test for Raspberry Pi Zero 2 W.

Wiring used by the project documentation:
  TRIG: BCM GPIO5 / physical pin 29
  ECHO: BCM GPIO6 / physical pin 31
"""

from time import monotonic_ns, sleep

from gpiozero import DigitalInputDevice, OutputDevice


TRIG_GPIO = 5
ECHO_GPIO = 6
ECHO_TIMEOUT_S = 0.03

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
        return None, "ECHOがHighのまま"

    # HC-SR04のTRIGには10us以上のHighパルスを与える。
    trigger.on()
    sleep(0.00001)
    trigger.off()

    if not wait_for_level(True, ECHO_TIMEOUT_S):
        return None, "ECHO開始タイムアウト"

    start_ns = monotonic_ns()
    if not wait_for_level(False, ECHO_TIMEOUT_S):
        return None, "ECHO終了タイムアウト"

    pulse_us = (monotonic_ns() - start_ns) / 1_000.0
    distance_cm = pulse_us / 58.0

    if not 2.0 <= distance_cm <= 400.0:
        return None, f"測定範囲外: {distance_cm:.1f} cm"

    return distance_cm, "OK"


print(f"HC-SR04 test: TRIG=GPIO{TRIG_GPIO}, ECHO=GPIO{ECHO_GPIO}")
print("終了するには Ctrl+C を押します。")

try:
    while True:
        distance_cm, status = measure_once()
        if distance_cm is None:
            print(status, flush=True)
        else:
            print(f"{distance_cm:6.1f} cm  {status}", flush=True)

        # 連続測定による超音波の干渉を避けるため、60ms以上空ける。
        sleep(0.10)
except KeyboardInterrupt:
    print("\n停止しました。")
finally:
    trigger.off()
    trigger.close()
    echo.close()
