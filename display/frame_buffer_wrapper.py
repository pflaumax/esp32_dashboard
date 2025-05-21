import framebuf


class FrameBufferWrapper(framebuf.FrameBuffer):
    def __init__(self, epd):
        self.epd = epd
        self.width = epd.width
        self.height = epd.height

        # Create a buffer for FrameBuffer
        self.buffer = bytearray(self.width * self.height // 8)

        # Initialize FrameBuffer parent
        fmt = framebuf.MONO_VLSB if self.width > self.height else framebuf.MONO_HLSB
        super().__init__(self.buffer, self.width, self.height, fmt)

    def show(self, deepsleep_after_refresh=False):
        """Copy our buffer to the EPD's internal buffer"""
        self.epd._buffer[:] = self.buffer
        self.epd.show(deepsleep_after_refresh=deepsleep_after_refresh)
