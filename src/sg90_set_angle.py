#!/usr/bin/env python3
"""Move the SG90 on BCM GPIO12 to a requested angle, then release PWM."""

import argparse
from time import sleep

from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory


SERVO_GPIO = 12
# Calibrated on the installed SG90: 500-2500 us gives approximately 180 degrees.
SERVO_MIN_PULSE_S = 0.0005
SERVO_MAX_PULSE_S = 0.0025
DEFAULT_ANGLE_DEG = 90.0
HOLD_S = 1.0


def angle_value(text: str) -> float:
    try:
        angle_deg = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError("角度は数字で指定してください") from error

    if not 0.0 <= angle_deg <= 180.0:
        raise argparse.ArgumentTypeError("角度は0～180度で指定してください")
    return angle_deg


parser = argparse.ArgumentParser(
    description="GPIO12へ接続したSG90を指定角度へ動かします。"
)
parser.add_argument(
    "angle",
    nargs="?",
    type=angle_value,
    default=DEFAULT_ANGLE_DEG,
    help="角度（0～180、未指定時は90）",
)
args = parser.parse_args()

pin_factory = PiGPIOFactory()
servo = AngularServo(
    SERVO_GPIO,
    min_angle=0,
    max_angle=180,
    min_pulse_width=SERVO_MIN_PULSE_S,
    max_pulse_width=SERVO_MAX_PULSE_S,
    initial_angle=None,
    pin_factory=pin_factory,
)

try:
    print(f"SG90: GPIO{SERVO_GPIO} -> {args.angle:g} deg", flush=True)
    servo.angle = args.angle
    sleep(HOLD_S)
finally:
    servo.detach()
    servo.close()
    pin_factory.close()

print("PWM released", flush=True)
