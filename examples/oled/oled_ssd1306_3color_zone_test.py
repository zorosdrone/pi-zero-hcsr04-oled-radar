#!/usr/bin/env python3
"""SSD1306 OLED physical-color zone test.

SSD1306 is a 1-bit display controller. If the OLED panel has fixed color
bands, software turns pixels on and off but does not choose RGB colors. This
test lights the top, middle, and bottom zones separately so the panel's real
color arrangement can be observed.
"""

from __future__ import annotations

import argparse
import time

from PIL import Image, ImageDraw
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306


WIDTH = 128
HEIGHT = 64
ZONE_BOUNDS = ((0, 0, 127, 15), (0, 16, 127, 31), (0, 32, 127, 63))


def zone_map() -> Image.Image:
    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    draw.line((0, 15, 127, 15), fill=1)
    draw.line((0, 31, 127, 31), fill=1)
    draw.text((3, 3), "Z1", fill=1)
    draw.text((3, 19), "Z2", fill=1)
    draw.text((3, 43), "Z3", fill=1)
    draw.text((27, 3), "TOP", fill=1)
    draw.text((27, 19), "MIDDLE", fill=1)
    draw.text((27, 43), "BOTTOM", fill=1)
    return image


def single_zone(zone_index: int) -> Image.Image:
    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = ZONE_BOUNDS[zone_index]
    draw.rectangle((x0, y0, x1, y1), outline=1)
    for y in range(y0 + 2, y1, 4):
        draw.line((x0 + 2, y, x1 - 2, y), fill=1)
    label_y = y0 + 3 if zone_index < 2 else y0 + 11
    draw.text((43, label_y), f"ZONE {zone_index + 1}", fill=1)
    return image


def all_zones() -> Image.Image:
    image = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    for zone_index, (x0, y0, x1, y1) in enumerate(ZONE_BOUNDS):
        draw.rectangle((x0, y0, x1, y1), outline=1)
        draw.text((43, y0 + (3 if zone_index < 2 else 11)), f"ZONE {zone_index + 1}", fill=1)
    draw.text((2, 55), "ALL ZONES", fill=1)
    return image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--address", default="0x3C")
    parser.add_argument("--seconds", type=float, default=30.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    serial = i2c(port=1, address=int(args.address, 0))
    device = ssd1306(serial)
    frames = (zone_map(), single_zone(0), single_zone(1), single_zone(2), all_zones())
    started = time.monotonic()
    frame_index = 0

    try:
        while time.monotonic() - started < args.seconds:
            device.display(frames[frame_index % len(frames)])
            frame_index += 1
            time.sleep(3.0)
    except KeyboardInterrupt:
        pass
    finally:
        device.command(0xA6)
        device.contrast(255)
        device.display(frames[-1])


if __name__ == "__main__":
    main()
