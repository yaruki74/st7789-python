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
import numbers
import time
import numpy as np

import spidev
import RPi.GPIO as GPIO


__version__ = '0.0.2'

BG_SPI_CS_BACK = 0
BG_SPI_CS_FRONT = 1

SPI_CLOCK_HZ = 16000000

ST7789_NOP = 0x00
ST7789_SWRESET = 0x01
ST7789_RDDID = 0x04
ST7789_RDDST = 0x09

ST7789_SLPIN = 0x10
ST7789_SLPOUT = 0x11
ST7789_PTLON = 0x12
ST7789_NORON = 0x13

ST7789_INVOFF = 0x20
ST7789_INVON = 0x21

ST7789_DISPOFF = 0x28
ST7789_DISPON = 0x29

ST7789_CASET = 0x2A
ST7789_RASET = 0x2B
ST7789_RAMWR = 0x2C
ST7789_RAMRD = 0x2E


ST7789_PTLAR = 0x30
ST7789_MADCTL = 0x36
ST7789_COLMOD = 0x3A

ST7789_FRMCTR1 = 0xB1
ST7789_FRMCTR2 = 0xB2
ST7789_FRMCTR3 = 0xB3
ST7789_INVCTR = 0xB4

ST7789_DISSET5 = 0xB6

ST7789_GCTRL = 0xB7
ST7789_GTADJ = 0xB8
ST7789_VCOMS = 0xBB

ST7789_LCMCTRL = 0xC0
ST7789_IDSET = 0xC1
ST7789_VDVVRHEN = 0xC2
ST7789_VRHS = 0xC3
ST7789_VDVS = 0xC4
ST7789_VMCTR1 = 0xC5
ST7789_FRCTRL2 = 0xC6
ST7789_CABCCTRL = 0xC7

ST7789_RDID1 = 0xDA
ST7789_RDID2 = 0xDB
ST7789_RDID3 = 0xDC
ST7789_RDID4 = 0xDD

ST7789_GMCTRP1 = 0xE0
ST7789_GMCTRN1 = 0xE1

ST7789_PWCTR6 = 0xFC

ILI9341_MADCTL = 0x36
ILI9341_COLMOD = 0x3A
ILI9341_SWRESET = 0x01
ILI9341_INITSEQ1 = 0xCF
ILI9341_INITSEQ2 = 0xED
ILI9341_INITSEQ3 = 0xE8
ILI9341_INITSEQ4 = 0xCB
ILI9341_INITSEQ5 = 0xF7
ILI9341_INITSEQ6 = 0xEA

ILI9341_LCMCTRL = 0xC0
ILI9341_IDSET = 0xC1
ILI9341_VDVVRHEN = 0xC2
ILI9341_VRHS = 0xC3
ILI9341_VCMCTR1 = 0xC5
ILI9341_VCMCTR2 = 0xC7
ILI9341_FRMCTR1 = 0xB1
ILI9341_FRMCTR2 = 0xB2
ILI9341_FRMCTR3 = 0xB3
ILI9341_GAMMASET = 0x26
ILI9341_GFUNDSL = 0xF2
ILI9341_DFUNCTR = 0xB6
ILI9341_GMCTRP1 = 0xE0
ILI9341_GMCTRN1 = 0xE1
ILI9341_NORON = 0x13
ILI9341_INVOFF = 0x20
ILI9341_INVCTR = 0xB4


class ST7789(object):
    """Representation of an ST7789 TFT LCD."""

    def __init__(self, port, cs, dc, backlight=None, rst=None, width=240,
                 height=240, rotation=0, invert=True, spi_speed_hz=4000000,
                 spi_mode=0):
        """Create an instance of the display using SPI communication.

        Must provide the GPIO pin number for the D/C pin and the SPI driver.

        Can optionally provide the GPIO pin number for the reset pin as the rst parameter.

        :param port: SPI port number
        :param cs: SPI chip-select number (0 or 1 for BCM
        :param backlight: Pin for controlling backlight
        :param rst: Reset pin for ST7789
        :param width: Width of display connected to ST7789
        :param height: Height of display connected to ST7789
        :param rotation: Rotation of display connected to ST7789
        :param invert: Invert display
        :param spi_speed_hz: SPI speed (in Hz)

        """

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        self._spi = spidev.SpiDev(port, cs)
        self._spi.mode = spi_mode
        self._spi.lsbfirst = False
        self._spi.max_speed_hz = spi_speed_hz

        self._dc = dc
        self._rst = rst
        self._width = width
        self._height = height
        self._rotation = rotation
        self._invert = invert

        self._offset_left = 0
        self._offset_top = 0

        # Set DC as output.
        GPIO.setup(dc, GPIO.OUT)

        # Setup backlight as output (if provided).
        self._backlight = backlight
        if backlight is not None:
            GPIO.setup(backlight, GPIO.OUT)
            GPIO.output(backlight, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(backlight, GPIO.HIGH)

        # Setup reset as output (if provided).
        if rst is not None:
            GPIO.setup(rst, GPIO.OUT)
            self.reset()
        
        self._init()

    def send(self, data, is_data=True, chunk_size=4096):
        """Write a byte or array of bytes to the display. Is_data parameter
        controls if byte should be interpreted as display data (True) or command
        data (False).  Chunk_size is an optional size of bytes to write in a
        single SPI transaction, with a default of 4096.
        """
        # Set DC low for command, high for data.
        GPIO.output(self._dc, is_data)
        # Convert scalar argument to list so either can be passed as parameter.
        if isinstance(data, numbers.Number):
            data = [data & 0xFF]
        # Write data a chunk at a time.
        for start in range(0, len(data), chunk_size):
            end = min(start + chunk_size, len(data))
            self._spi.xfer(data[start:end])

    def set_backlight(self, value):
        """Set the backlight on/off."""
        if self._backlight is not None:
            GPIO.output(self._backlight, value)

    @property
    def width(self):
        return self._width if self._rotation == 0 or self._rotation == 180 else self._height

    @property
    def height(self):
        return self._height if self._rotation == 0 or self._rotation == 180 else self._width

    def command(self, data):
        """Write a byte or array of bytes to the display as command data."""
        self.send(data, False)

    def data(self, data):
        """Write a byte or array of bytes to the display as display data."""
        self.send(data, True)

    def reset(self):
        """Reset the display, if reset pin is connected."""
        if self._rst is not None:
            GPIO.output(self._rst, 1)
            time.sleep(0.500)
            GPIO.output(self._rst, 0)
            time.sleep(0.500)
            GPIO.output(self._rst, 1)
            time.sleep(0.500)

    def _init(self):
        # Initialize the display.

        self.command(ST7789_SWRESET)    # Software reset
        time.sleep(0.150)               # delay 150 ms

        self.command(ST7789_MADCTL)
        self.data(0x70)

        self.command(ST7789_FRMCTR2)    # Frame rate ctrl - idle mode
        self.data(0x0C)
        self.data(0x0C)
        self.data(0x00)
        self.data(0x33)
        self.data(0x33)

        self.command(ST7789_COLMOD)
        self.data(0x05)

        self.command(ST7789_GCTRL)
        self.data(0x14)

        self.command(ST7789_VCOMS)
        self.data(0x37)

        self.command(ST7789_LCMCTRL)    # Power control
        self.data(0x2C)

        self.command(ST7789_VDVVRHEN)   # Power control
        self.data(0x01)

        self.command(ST7789_VRHS)       # Power control
        self.data(0x12)

        self.command(ST7789_VDVS)       # Power control
        self.data(0x20)

        self.command(0xD0)
        self.data(0xA4)
        self.data(0xA1)

        self.command(ST7789_FRCTRL2)
        self.data(0x0F)

        self.command(ST7789_GMCTRP1)    # Set Gamma
        self.data(0xD0)
        self.data(0x04)
        self.data(0x0D)
        self.data(0x11)
        self.data(0x13)
        self.data(0x2B)
        self.data(0x3F)
        self.data(0x54)
        self.data(0x4C)
        self.data(0x18)
        self.data(0x0D)
        self.data(0x0B)
        self.data(0x1F)
        self.data(0x23)

        self.command(ST7789_GMCTRN1)    # Set Gamma
        self.data(0xD0)
        self.data(0x04)
        self.data(0x0C)
        self.data(0x11)
        self.data(0x13)
        self.data(0x2C)
        self.data(0x3F)
        self.data(0x44)
        self.data(0x51)
        self.data(0x2F)
        self.data(0x1F)
        self.data(0x1F)
        self.data(0x20)
        self.data(0x23)

        if self._invert:
            self.command(ST7789_INVON)   # Invert display
        else:
            self.command(ST7789_INVOFF)  # Don't invert display

        self.command(ST7789_SLPOUT)

        self.command(ST7789_DISPON)     # Display on
        time.sleep(0.100)               # 100 ms

    def begin(self):
        """Set up the display

        Deprecated. Included in __init__.

        """
        pass

    def set_window(self, x0=0, y0=0, x1=None, y1=None):
        """Set the pixel address window for proceeding drawing commands. x0 and
        x1 should define the minimum and maximum x pixel bounds.  y0 and y1
        should define the minimum and maximum y pixel bound.  If no parameters
        are specified the default will be to update the entire display from 0,0
        to width-1,height-1.
        """
        if x1 is None:
            x1 = self._width - 1

        if y1 is None:
            y1 = self._height - 1

        y0 += self._offset_top
        y1 += self._offset_top

        x0 += self._offset_left
        x1 += self._offset_left

        self.command(ST7789_CASET)       # Column addr set
        self.data(x0 >> 8)
        self.data(x0 & 0xFF)             # XSTART
        self.data(x1 >> 8)
        self.data(x1 & 0xFF)             # XEND
        self.command(ST7789_RASET)       # Row addr set
        self.data(y0 >> 8)
        self.data(y0 & 0xFF)             # YSTART
        self.data(y1 >> 8)
        self.data(y1 & 0xFF)             # YEND
        self.command(ST7789_RAMWR)       # write to RAM

    def display(self, image):
        """Write the provided image to the hardware.

        :param image: Should be RGB format and the same dimensions as the display hardware.

        """
        # Set address bounds to entire display.
        self.set_window()
        # Convert image to array of 18bit 666 RGB data bytes.
        # Unfortunate that this copy has to occur, but the SPI byte writing
        # function needs to take an array of bytes and PIL doesn't natively
        # store images in 18-bit 666 RGB format.
        pixelbytes = self.image_to_data(image, self._rotation)
        # Write data to hardware.
        for i in range(0, len(pixelbytes), 4096):
            self.data(pixelbytes[i:i + 4096])

    def image_to_data(self, image, rotation=0):
        """Generator function to convert a PIL image to 16-bit 565 RGB bytes."""
        # NumPy is much faster at doing this. NumPy code provided by:
        # Keith (https://www.blogger.com/profile/02555547344016007163)
        pb = np.rot90(np.array(image.convert('RGB')), rotation // 90).astype('uint8')

        result = np.zeros((self._height, self._width, 2), dtype=np.uint8)
        result[..., [0]] = np.add(np.bitwise_and(pb[..., [0]], 0xF8), np.right_shift(pb[..., [1]], 5))
        result[..., [1]] = np.add(np.bitwise_and(np.left_shift(pb[..., [1]], 3), 0xE0), np.right_shift(pb[..., [2]], 3))
        return result.flatten().tolist()

class ILI9341(ST7789):
    """Representation of an ILI9341 TFT LCD."""

    def __init__(self, port, cs, dc, backlight=None, rst=None, width=320,
                 height=240, rotation=0, spi_speed_hz=40000000,
                 spi_mode=0):
        """Create an instance of the display using SPI communication.

        Must provide the GPIO pin number for the D/C pin and the SPI driver.

        Can optionally provide the GPIO pin number for the reset pin as the rst parameter.

        :param port: SPI port number
        :param cs: SPI chip-select number (0 or 1 for BCM
        :param backlight: Pin for controlling backlight
        :param rst: Reset pin for ILI9341
        :param width: Width of display connected to ILI9341
        :param height: Height of display connected to ILI9341
        :param rotation: Rotation of display connected to ILI9341
        :param invert: Invert display
        :param spi_speed_hz: SPI speed (in Hz)

        """

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        self._spi = spidev.SpiDev(port, cs)
        self._spi.mode = spi_mode
        self._spi.lsbfirst = False
        self._spi.max_speed_hz = spi_speed_hz

        self._dc = dc
        self._rst = rst
        self._width = width
        self._height = height
        self._rotation = rotation

        self._offset_left = 0
        self._offset_top = 0

        # Set DC as output.
        GPIO.setup(dc, GPIO.OUT)

        # Setup backlight as output (if provided).
        self._backlight = backlight
        if backlight is not None:
            GPIO.setup(backlight, GPIO.OUT)
            GPIO.output(backlight, GPIO.LOW)
            time.sleep(0.1)
            GPIO.output(backlight, GPIO.HIGH)

        # Setup reset as output (if provided).
        if rst is not None:
            GPIO.setup(rst, GPIO.OUT)
            self.reset()
        
        self._init()



    def _init(self):
        # Initialize the display.

        self.command(ILI9341_SWRESET)    # Software reset
        time.sleep(0.120)               # delay 120 ms

        self.command(ILI9341_FRMCTR1)    # frameration control,normal mode full colours
        self.data(0x00)
        self.data(0x1B)

        self.command(ILI9341_FRMCTR2)    # frameration control,normal mode full colours
        self.data(0x00)
        self.data(0x1B)

        self.command(ILI9341_FRMCTR3)    # frameration control,normal mode full colours
        self.data(0x00)
        self.data(0x1B)

        self.command(ILI9341_INVCTR)     # INVCTR Display inversion (no inversion)
        self.data(0x00)

        self.command(ILI9341_LCMCTRL)    # PWCTR1 Power control -4.6V, Auto mode
        self.data(0x21)

        self.command(ILI9341_IDSET)    # PWCTR2 Power control VGH25 2.4C, VGSEL -10, VGH = 3 * AVDD
        self.data(0x11)

        self.command(ILI9341_VDVVRHEN)    # PWCTR3 Power control, opamp current smal, boost frequency
        self.data(0x0A)
        self.data(0x00)

        self.command(ILI9341_VRHS)    # PWCTR4 Power control, BLK/2, opamp current small and medium low
        self.data(0x8A)
        self.data(0x2A)

        self.command(ILI9341_INVOFF)   # Invert display

        self.command(ILI9341_MADCTL)
        self.data(0x28)

        self.command(ILI9341_COLMOD)
        self.data(0x55)


        self.command(ILI9341_INITSEQ1)
        self.data(0x00)
        self.data(0x81)
        self.data(0x30)

        self.command(ILI9341_INITSEQ2)
        self.data(0x64)
        self.data(0x03)
        self.data(0x12)
        self.data(0x81)

        self.command(ILI9341_INITSEQ3)    # power on sequence control
        self.data(0x85)
        self.data(0x10)
        self.data(0x7A)

        self.command(ILI9341_INITSEQ5)    # pump ratio control
        self.data(0x20)

        self.command(ILI9341_INITSEQ6)    # driver timing control B
        self.data(0x00)
        self.data(0x00)  


        self.command(ILI9341_VCMCTR1)    # VCM control
        self.data(0x3F)
        self.data(0x3C)

        self.command(ILI9341_VCMCTR2)    # VCM control2
        self.data(0xA7)

        #self.command(ILI9341_DFUNCTR)    # display function control
        #self.data(0x0A)
        #self.data(0xA2)

        self.command(ILI9341_GFUNDSL)    # 3Gamma Function Disable
        self.data(0x00)

        self.command(ILI9341_GAMMASET)    # Gamma curve selected
        self.data(0x01)

        self.command(ILI9341_GMCTRP1)    # Set Gamma
        self.data(0x0F)
        self.data(0x23)
        self.data(0x1F)
        self.data(0x0B)
        self.data(0x0E)
        self.data(0x08)
        self.data(0x4B)
        self.data(0xA8)
        self.data(0x3B)
        self.data(0x0A)
        self.data(0x14)
        self.data(0x06)
        self.data(0x10)
        self.data(0x09)
        self.data(0x00)

        self.command(ILI9341_GMCTRN1)    # Set Gamma
        self.data(0x00)
        self.data(0x1C)
        self.data(0x20)
        self.data(0x04)
        self.data(0x10)
        self.data(0x08)
        self.data(0x34)
        self.data(0x47)
        self.data(0x44)
        self.data(0x05)
        self.data(0x0B)
        self.data(0x09)
        self.data(0x2F)
        self.data(0x36)
        self.data(0x0F)

        self.command(ST7789_SLPOUT)
        time.sleep(0.120)               # 120 ms

        self.command(ST7789_DISPON)     # Display on
        time.sleep(0.120)               # 120 ms


        self.command(ILI9341_NORON)   # Normal display mode


