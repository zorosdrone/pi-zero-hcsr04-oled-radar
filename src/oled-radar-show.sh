#!/bin/sh
set -eu

if [ "$#" -ne 4 ]; then
    echo "使い方: $0 角度 距離cm ステータス 走査データ" >&2
    exit 2
fi

ANGLE="$1"
DISTANCE="$2"
STATUS="$3"
SCAN_DATA="$4"
PYTHON=python3

"$PYTHON" - "$ANGLE" "$DISTANCE" "$STATUS" "$SCAN_DATA" <<'PY'
import math
import sys

from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306


angle_deg = int(sys.argv[1])
distance_text = sys.argv[2]
status = sys.argv[3]
scan_text = sys.argv[4]
max_distance_cm = 100.0

try:
    distance_cm = float(distance_text)
except ValueError:
    distance_cm = -1.0

scan = {}
for item in scan_text.split(","):
    if not item:
        continue
    item_angle, item_distance = item.split(":", 1)
    parsed_distance = float(item_distance)
    scan[int(item_angle)] = None if parsed_distance < 0.0 else parsed_distance

image = Image.new("1", (128, 64))
draw = ImageDraw.Draw(image)

# 左側に、角度ごとの最新距離を保持する半円レーダーを描く。
center_x = 38
center_y = 62
max_radius = 36

for radius in (12, 24, max_radius):
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

draw.line((center_x - max_radius, center_y, center_x + max_radius, center_y), fill=1)

for grid_angle_deg in (30, 60, 90, 120, 150):
    grid_angle = math.radians(grid_angle_deg)
    end_x = center_x + int(max_radius * math.cos(grid_angle))
    end_y = center_y - int(max_radius * math.sin(grid_angle))
    draw.line((center_x, center_y, end_x, end_y), fill=1)

for measured_angle_deg, measured_distance_cm in scan.items():
    if measured_distance_cm is None:
        continue
    measured_angle = math.radians(measured_angle_deg)
    point_radius = int(
        max_radius * min(measured_distance_cm, max_distance_cm) / max_distance_cm
    )
    point_x = center_x + int(point_radius * math.cos(measured_angle))
    point_y = center_y - int(point_radius * math.sin(measured_angle))
    draw.point((point_x, point_y), fill=1)

# 現在の走査方向を線で示し、現在点だけを大きく描く。
current_angle = math.radians(angle_deg)
beam_x = center_x + int(max_radius * math.cos(current_angle))
beam_y = center_y - int(max_radius * math.sin(current_angle))
draw.line((center_x, center_y, beam_x, beam_y), fill=1)

if distance_cm >= 0.0:
    point_radius = int(
        max_radius * min(distance_cm, max_distance_cm) / max_distance_cm
    )
    point_x = center_x + int(point_radius * math.cos(current_angle))
    point_y = center_y - int(point_radius * math.sin(current_angle))
    draw.ellipse((point_x - 2, point_y - 2, point_x + 2, point_y + 2), fill=1)

font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

try:
    small_font = ImageFont.truetype(font_path, 10, index=0)
except OSError:
    small_font = ImageFont.load_default()

if distance_cm >= 0.0:
    value = str(int(round(distance_cm)))
else:
    value = "---"

font_size = {1: 29, 2: 27, 3: 23}.get(len(value), 19)
try:
    value_font = ImageFont.truetype(font_path, font_size, index=0)
except OSError:
    value_font = ImageFont.load_default()

panel_left = 79
panel_right = 127
bbox = draw.textbbox((0, 0), value, font=value_font)
text_width = bbox[2] - bbox[0]
text_x = panel_left + (panel_right - panel_left - text_width) // 2 - bbox[0]
draw.text((text_x, 5 - bbox[1]), value, font=value_font, fill=1)

draw.text((91, 36), "cm", font=small_font, fill=1)
draw.text((83, 49), f"{angle_deg:3d}deg", font=small_font, fill=1)

if status != "OK":
    draw.rectangle((78, 0, 127, 7), fill=0)
    draw.text((79, 0), status[:9], font=small_font, fill=1)

device = ssd1306(i2c(port=1, address=0x3C))
device.persist = True
device.contrast(255)
device.display(image)
PY
