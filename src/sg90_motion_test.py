#!/usr/bin/env python3
"""SG90 motion test for Raspberry Pi GPIO12.

Wiring:
  Signal: BCM GPIO12 / physical pin 32
  Power: stable external 5 V
  GND: servo supply and Raspberry Pi GND connected together
"""

import argparse
from time import sleep

from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory


SERVO_GPIO = 12
# Calibrated on the installed SG90: 500-2500 us gives approximately 180 degrees.
SERVO_MIN_PULSE_S = 0.0005
SERVO_MAX_PULSE_S = 0.0025
SMALL_SEQUENCE_DEG = (90, 80, 90, 100, 90)
WIDE_SEQUENCE_DEG = (90, 60, 90, 120, 90)
HOLD_S = 0.7


parser = argparse.ArgumentParser(description="SG90 motion test on BCM GPIO12")
parser.add_argument(
    "--wide",
    action="store_true",
    help="use the 60-120 degree test instead of the default 80-100 degree test",
)
args = parser.parse_args()
test_sequence = WIDE_SEQUENCE_DEG if args.wide else SMALL_SEQUENCE_DEG

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
    print(f"SG90 motion test: GPIO{SERVO_GPIO}", flush=True)
    for angle_deg in test_sequence:
        print(f"MOVE {angle_deg} deg", flush=True)
        servo.angle = angle_deg
        sleep(HOLD_S)
    print("PASS: command sequence completed", flush=True)
finally:
    print("CENTER 90 deg, then detach PWM", flush=True)
    servo.angle = 90
    sleep(0.5)
    servo.detach()
    servo.close()
    pin_factory.close()
