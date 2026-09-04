#!/usr/bin/env python3
"""0.96-inch SSD1306 I2C OLED expression demo.

This demo cycles through:
  - a scrolling line graph using simulated distance data
  - a small radar-like sweep animation
  - a moving animation
  - contrast and display-invert changes

The display is a 1-bit, blue monochrome 128x64 panel. It cannot show RGB
colors; contrast and inversion are included to demonstrate the available
visual alternatives.
"""

from __future__ import annotations

import argparse
import math
import time

from PIL import Image, ImageDraw
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306


WIDTH = 128
HEIGHT = 64
FRAME_SECONDS = 0.12
ALL_MODE_SECONDS = 6.0
MODE_ORDER = ("graph", "radar", "animation", "contrast")


def draw_header(draw: ImageDraw.ImageDraw, left: str, right: str) -> None:
    """Draw a compact ASCII-only header that works with the default font."""
    draw.text((0, 0), left[:15], fill=1)
    draw.text((89, 0), right[:6], fill=1)
    draw.line((0, 12, WIDTH - 1, 12), fill=1)


def simulated_distance(seconds: float) -> int:
    """Return a changing value until the real HC-SR04 reader is connected."""
    value = 100 + 48 * math.sin(seconds * 1.2) + 14 * math.sin(seconds * 3.1)
    return max(20, min(200, int(value)))


def draw_graph(image: Image.Image, history: list[int]) -> None:
    draw = ImageDraw.Draw(image)
    current = history[-1]
    draw_header(draw, f"D {current:3d}cm", "GRAPH")
    draw.line((0, 19, WIDTH - 1, 19), fill=1)
    draw.line((0, HEIGHT - 4, WIDTH - 1, HEIGHT - 4), fill=1)

    points: list[tuple[int, int]] = []
    visible = history[-WIDTH:]
    for x, value in enumerate(visible):
        value = max(20, min(200, value))
        y = HEIGHT - 5 - int((value - 20) * 36 / 180)
        points.append((x, y))

    if len(points) > 1:
        draw.line(points, fill=1, width=1)
    if points:
        x, y = points[-1]
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), outline=1)


def draw_radar(image: Image.Image, seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    draw_header(draw, "RADAR", "SWEEP")

    center_x = 32
    center_y = 60
    for radius in (12, 23, 34):
        draw.arc(
            (
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
            ),
            180,
            360,
            fill=1,
        )

    angle_deg = 20 + (seconds * 90 % 140)
    angle = math.radians(angle_deg)
    target_distance = 18 + int(12 * math.sin(seconds * 1.7))
    target_x = center_x + int(target_distance * math.cos(angle))
    target_y = center_y - int(target_distance * math.sin(angle))
    draw.line((center_x, center_y, target_x, target_y), fill=1)
    draw.ellipse((target_x - 2, target_y - 2, target_x + 2, target_y + 2), fill=1)

    draw.text((74, 24), "ANGLE", fill=1)
    draw.text((74, 36), f"{int(angle_deg):3d}deg", fill=1)
    draw.text((74, 49), f"{target_distance:3d}cm", fill=1)


def draw_animation(image: Image.Image, seconds: float) -> None:
    draw = ImageDraw.Draw(image)
    draw_header(draw, "ANIM", "MOVE")
    draw.rectangle((3, 19, 124, 59), outline=1)

    travel = 116
    x = 7 + int(abs((seconds * 42) % (travel * 2) - travel))
    y = 38 + int(12 * math.sin(seconds * 2.2))
    draw.rectangle((x - 4, y - 4, x + 4, y + 4), fill=1)
    draw.line((8, 53, 120, 53), fill=1)
    draw.line((x, 51, x, 55), fill=1)


def draw_contrast(
    image: Image.Image,
    device: ssd1306,
    seconds: float,
    state: dict[str, object],
) -> None:
    draw = ImageDraw.Draw(image)
    phase = int(seconds * 0.9) % 4
    levels = (64, 128, 192, 255)
    level = levels[phase]
    inverted = phase == 3

    if state.get("contrast") != level:
        device.contrast(level)
        state["contrast"] = level
    if state.get("inverted") != inverted:
        device.command(0xA7 if inverted else 0xA6)  # invert / normal display
        state["inverted"] = inverted

    draw_header(draw, "LIGHT", "1-BIT")
    draw.text((4, 22), f"CONTRAST {level:3d}", fill=1)
    draw.rectangle((4, 38, 123, 47), outline=1)
    bar_width = 4 + int(115 * level / 255)
    draw.rectangle((6, 40, bar_width, 45), fill=1)
    draw.text((4, 51), "INVERT" if inverted else "NORMAL", fill=1)


def reset_display(device: ssd1306) -> None:
    """Restore a predictable state when the program is stopped."""
    device.command(0xA6)
    device.contrast(255)
    device.clear()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--address",
        default="0x3C",
        help="I2C address from i2cdetect, for example 0x3C or 0x3D",
    )
    parser.add_argument(
        "--mode",
        choices=("all",) + MODE_ORDER,
        default="all",
        help="demo mode; all cycles through every sample",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=30.0,
        help="run time before clearing the display; Ctrl-C also stops",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    address = int(args.address, 0)
    serial = i2c(port=1, address=address)
    device = ssd1306(serial)
    history = [simulated_distance(index * 0.12) for index in range(WIDTH)]
    contrast_state: dict[str, object] = {}
    started = time.monotonic()
    previous_mode: str | None = None

    try:
        while time.monotonic() - started < args.seconds:
            elapsed = time.monotonic() - started
            if args.mode == "all":
                mode_index = int(elapsed // ALL_MODE_SECONDS) % len(MODE_ORDER)
                mode = MODE_ORDER[mode_index]
                mode_elapsed = elapsed % ALL_MODE_SECONDS
            else:
                mode = args.mode
                mode_elapsed = elapsed

            if mode != previous_mode and mode != "contrast":
                device.command(0xA6)
                device.contrast(255)
                contrast_state.clear()
            previous_mode = mode

            image = Image.new("1", (WIDTH, HEIGHT))
            if mode == "graph":
                history.append(simulated_distance(elapsed))
                history[:] = history[-WIDTH:]
                draw_graph(image, history)
            elif mode == "radar":
                draw_radar(image, mode_elapsed)
            elif mode == "animation":
                draw_animation(image, mode_elapsed)
            else:
                draw_contrast(image, device, mode_elapsed, contrast_state)

            device.display(image)
            time.sleep(FRAME_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        reset_display(device)


if __name__ == "__main__":
    main()
