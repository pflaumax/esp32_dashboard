import utime
from machine import Pin, SPI
import config
import epd29_ssd1680
from frame_buffer_wrapper import FrameBufferWrapper


class EPaperDisplay:
    def __init__(self):
        # Initialize SPI
        spi = SPI(
            1,
            baudrate=4000000,
            polarity=0,
            phase=0,
            sck=Pin(18),
            mosi=Pin(23),
            miso=Pin(19),
        )

        # Initialize display pins
        rst = Pin(config.EPD_Config.RST_PIN, Pin.OUT)
        dc = Pin(config.EPD_Config.DC_PIN, Pin.OUT)
        cs = Pin(config.EPD_Config.CS_PIN, Pin.OUT)
        busy = Pin(config.EPD_Config.BUSY_PIN, Pin.IN)

        # Create the display instance
        self.epd = epd29_ssd1680.EPD(spi, cs, dc, rst, busy)
        self.width = self.epd.width
        self.height = self.epd.height

        # Initialize the display
        self.epd.init()

        # Won't use the wrapper, we'll use the display directly
        self.fb = FrameBufferWrapper(self.epd)

        # Clear to start
        self.clear()

    def clear(self):
        # Fill with white (0 for this specific driver)
        self.epd.fill(0)  # Using 0 for white based on working test

    def display(self):
        # Update the display
        print("Updating display...")
        self.epd.show()
        print("Display updated")

    def sleep(self):
        # Put display in low power mode
        self.epd.show(deepsleep_after_refresh=True)

    def text(self, text, x, y, color=None):
        """Draw text on the display
        Args:
            text: string to display
            x, y: coordinates
            color: 0 for white, 1 for black (EPD convention for this specific display)
        """
        if color is not None:
            # If color is 0 (normally black), use 1 (black for this display)
            # If color is 1 (normally white), use 0 (white for this display)
            display_color = 1 if color == 0 else 0
            self.epd.text(text, x, y, display_color)
        else:
            # Use default (which should be black)
            self.epd.text(text, x, y)

    def rect(self, x, y, width, height, color=0):
        """Draw a rectangle
        Args:
            x, y: coordinates of top-left corner
            width, height: dimensions
            color: 0 for white, 1 for black (EPD convention for this display)
        """
        display_color = 1 if color == 0 else 0  # Invert the color
        self.epd.rect(x, y, width, height, display_color)

    def fill_rect(self, x, y, width, height, color=0):
        """Draw a filled rectangle
        Args:
            x, y: coordinates of top-left corner
            width, height: dimensions
            color: 0 for white, 1 for black (EPD convention for this display)
        """
        display_color = 1 if color == 0 else 0  # Invert the color
        self.epd.fill_rect(x, y, width, height, display_color)

    def line(self, x1, y1, x2, y2, color=0):
        """Draw a line
        Args:
            x1, y1: start coordinates
            x2, y2: end coordinates
            color: 0 for white, 1 for black (EPD convention for this display)
        """
        display_color = 1 if color == 0 else 0  # Invert the color
        self.epd.line(x1, y1, x2, y2, display_color)

    def hline(self, x, y, width, color=0):
        """Draw a horizontal line
        Args:
            x, y: start coordinates
            width: length of line
            color: 0 for white, 1 for black (EPD convention for this display)
        """
        display_color = 1 if color == 0 else 0  # Invert the color
        self.epd.hline(x, y, width, display_color)

    def vline(self, x, y, height, color=0):
        """Draw a vertical line
        Args:
            x, y: start coordinates
            height: length of line
            color: 0 for white, 1 for black (EPD convention for this display)
        """
        display_color = 1 if color == 0 else 0  # Invert the color
        self.epd.vline(x, y, height, display_color)
