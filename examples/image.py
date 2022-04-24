# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import sys

from PIL import Image
import ST7789 as ST7789
from ST7789 import ILI9341 as ILI9341

print("""
image.py - Display an image on the LCD.

If you're using Breakout Garden, plug the 1.3 or 2.8" LCD (IPS)
breakout into the rear slot.
""")

if len(sys.argv) < 2:
    print("""Usage: {} <image_file> <display_type>

Where <display_type> is one of:
  * daczero    - 240x240 1.3" Display for NosPi DAC Zero
  * dacmax     - 320x240 2.8" Display for NosPi DAC MAX
  * dacmax_spi - 320x240 2.8" IPS Display for NosPi DAC MAX
""".format(sys.argv[0]))
    sys.exit(1)

image_file = sys.argv[1]

try:
    display_type = sys.argv[2]
except IndexError:
    display_type = "daczero"
    
# Create ST7789 LCD display class.
if display_type in ("daczero"):
    disp = ST7789.ST7789(
        height=240,
        width=240,
        rotation=0,
        port=0,
        cs=0,
        rst=5,
        dc=25,
        backlight=12,
        spi_speed_hz=50 * 1000 * 1000,
        spi_mode=3
   )

elif display_type == "dacmax_ips":
    disp = ST7789.ST7789(
        width=320,
        port=0,
        cs=0,
        rst=14,
        dc=25,
        backlight=16,
        spi_speed_hz=33 * 1000 * 1000
   )

elif display_type == "dacmax":
    disp = ILI9341(
        port=0,
        cs=0,
        rst=14,
        dc=25,
        backlight=16
   )

else:
    print ("Invalid display type!")
    sys.exit(1)
 

WIDTH = disp.width
HEIGHT = disp.height

# Initialize display.
disp.begin()

# Load an image.
print('Loading image: {}...'.format(image_file))
image = Image.open(image_file)

# Resize the image
image = image.resize((WIDTH, HEIGHT))

# Draw the image on the display hardware.
print('Drawing image')

disp.display(image)
