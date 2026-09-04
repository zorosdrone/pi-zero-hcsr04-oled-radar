#!/usr/bin/env python3
"""Send a calibrated pulse width to the SG90 on BCM GPIO12."""

import argparse
from time import sleep

import pigpio


SERVO_GPIO = 12
DEFAULT_PULSE_US = 1500
MIN_ALLOWED_PULSE_US = 500
MAX_ALLOWED_PULSE_US = 2500
HOLD_S = 0.8


def pulse_value(text: str) -> int:
    try:
        pulse_us = int(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("パルス幅は整数で指定してください") from error

    if not MIN_ALLOWED_PULSE_US <= pulse_us <= MAX_ALLOWED_PULSE_US:
        raise argparse.ArgumentTypeError(
            f"パルス幅は{MIN_ALLOWED_PULSE_US}～{MAX_ALLOWED_PULSE_US}µsで指定してください"
        )
    return pulse_us


parser = argparse.ArgumentParser(
    description="GPIO12のSG90へパルス幅を直接指定して校正します。"
)
parser.add_argument(
    "pulse_us",
    nargs="?",
    type=pulse_value,
    default=DEFAULT_PULSE_US,
    help="パルス幅µs（500～2500、未指定時は1500）",
)
args = parser.parse_args()

pi = pigpio.pi()
if not pi.connected:
    raise SystemExit("pigpiodへ接続できません")

try:
    print(f"SG90: GPIO{SERVO_GPIO} -> {args.pulse_us} us", flush=True)
    pi.set_servo_pulsewidth(SERVO_GPIO, args.pulse_us)
    sleep(HOLD_S)
finally:
    pi.set_servo_pulsewidth(SERVO_GPIO, 0)
    pi.stop()

print("PWM released", flush=True)
