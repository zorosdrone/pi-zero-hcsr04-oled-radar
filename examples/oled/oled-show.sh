#!/bin/sh
set -eu

if [ "$#" -gt 0 ]; then
    MESSAGE="$*"
elif [ ! -t 0 ]; then
    MESSAGE=$(cat)
else
    echo "使い方: $0 表示文字 または コマンド | $0" >&2
    exit 2
fi

PYTHON=python3

"$PYTHON" - "$MESSAGE" <<'PY'
import sys

from PIL import Image, ImageDraw, ImageFont
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306


message = sys.argv[1]
font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
try:
    font = ImageFont.truetype(font_path, 10, index=0)
except OSError:
    font = ImageFont.load_default()

image = Image.new("1", (128, 64))
draw = ImageDraw.Draw(image)


def wrap_line(line, max_width=126):
    result = []
    current = ""
    for char in line:
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            result.append(current)
            current = char
        else:
            current = candidate
    result.append(current)
    return result


lines = []
for original_line in message.splitlines() or [""]:
    lines.extend(wrap_line(original_line))
lines = lines[:5]

device = ssd1306(i2c(port=1, address=0x3C))
device.persist = True
device.contrast(255)
device.show()
for line_no, line in enumerate(lines):
    draw.text((1, line_no * 12), line, font=font, fill=255)
device.display(image)
PY
