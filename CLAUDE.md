# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MicroPython firmware for an ESP32-WROOM driving a 2.9" WeAct Studio SSD1680 e-paper display (296x128, mono). It renders a four-quadrant dashboard (time/date, weather, website views, Pi-hole stats) refreshed every 5 minutes.

There is no build system, test suite, or linter config. The code is Black-formatted by convention. Runtime code targets the MicroPython stdlib (`machine`, `network`, `framebuf`, `urequests`, `ujson`, `utime`) and **cannot be executed on the host** — verification means flashing to the device and reading the serial REPL.

`requirements.txt` is host tooling, but don't `pip install -r` it blindly: alongside `ampy`/`esptool`/`rshell`/`pyserial` it pins `RPi.GPIO`, `spidev`, `pyudev`, and `epd-library`, which are Linux/Raspberry-Pi-only and fail to build on macOS. Install the two tools you actually need (`adafruit-ampy`, `esptool`) instead. Note also that `.gitignore` ignores `esp_venv/`, not the `.venv/` that is currently checked out here.

## Commands

```bash
# Port is /dev/ttyUSB0 (Linux) or /dev/tty.usbserial-* (macOS)
PORT=/dev/ttyUSB0

# Upload — directory structure MUST be preserved (imports are package-qualified)
ampy --port $PORT put main.py
ampy --port $PORT put boot.py
ampy --port $PORT put config.py
ampy --port $PORT put display display
ampy --port $PORT put driver driver
ampy --port $PORT put fonts fonts
ampy --port $PORT put widgets widgets

ampy --port $PORT ls           # inspect device filesystem

# Serial REPL / live logs (every widget logs its state via print)
pyserial-miniterm $PORT 115200

# Flash MicroPython firmware
esptool.py --chip esp32 --port $PORT erase_flash
esptool.py --chip esp32 --port $PORT --baud 460800 write_flash -z 0x1000 <firmware.bin>
```

Uploading the modules flat into the device root breaks the package-qualified imports (`from widgets.clock import Clock`) — always use the directory form above.

`ampy run main.py` is not useful here: `Dashboard.run()` is an infinite loop and `ampy run` blocks waiting for the script to exit, so it just hangs until ampy times out. To watch a run, upload and reset the board, then read the serial output with `pyserial-miniterm`.

## config.py

Gitignored and not in the repo; it must be created before anything runs. Settings are grouped into classes (README step 5 has a full template):

```python
class Network_Config:  WIFI_SSID, WIFI_PASSWORD
class Time_Config:     TIMEZONE_OFFSET          # hours, numeric
class Weather_Config:  API_KEY, CITY_ID         # OpenWeatherMap
class Website_Config:  API_URL
class Pihole_Config:   PIHOLE_IP, PIHOLE_PASSWORD
class EPD_Config:      RST_PIN, DC_PIN, CS_PIN, BUSY_PIN   # 16, 17, 5, 4
```

SPI pins (SCK 18, MOSI 23, MISO 19, SPI bus 1) are hardcoded in `display/display.py`, not config-driven.

## Architecture

**Entry point.** Both paths go through `main.start()`: `boot.py` imports and calls it, and `main.py`'s `if __name__ == "__main__"` block calls it too. `start()` owns the error handling — construction failure, or a network that never comes up at all, sleeps 300s and `machine.reset()`s rather than dropping to the REPL. Keep new startup logic inside `start()` so both paths inherit it.

**Dashboard (`main.py`)** owns everything: it constructs the display and all four data widgets, then loops `update_data()` → `render_dashboard()` → sleep to the next 300s boundary. Widget failures are caught individually so one dead API doesn't stop the others; a failure in the loop body triggers a network reconnect and a 60s retry.

**Data widgets (`widgets/`)** are independent and share a contract rather than a base class: each holds its own `update_interval` + `last_update`, exposes an `update_*()` method that no-ops until the interval elapses, and a display getter that returns preformatted strings — `get_time_for_display()`, `get_views_for_display()`, `get_stats_for_display()`, but `WeatherAPI.get_formatted_display()` breaks the naming pattern. They cache the last good value and degrade to it (or a placeholder) rather than raising. Adding a widget means following that shape and wiring it into `Dashboard.__init__`, `update_data()`, and a new `render_*_section()`.

**Display stack**, bottom-up:
- `driver/epd29_ssd1680.py` — `EPD` subclasses `framebuf.FrameBuffer` over its own `_buffer`; handles SSD1680 commands, BUSY-pin waits, full/partial refresh, and optional deep sleep after refresh.
- `display/frame_buffer_wrapper.py` — `FrameBufferWrapper` is a *second* FrameBuffer with its own buffer; `show()` blits it into `epd._buffer` (reaching into a private attribute) and triggers the refresh. This indirection exists so rendering never touches a partially-written device buffer.
- `display/display.py` — `EPaperDisplay` wires SPI + pins, owns `self.fb` (the wrapper), and provides primitives that **invert the color argument** (this panel treats 0 as white).
- `display/writer.py` + `fonts/*.py` — Peter Hinch's `Writer` renders `micropython-font-to-py`-generated fonts. Regenerate fonts with that tool; don't hand-edit the font modules.

Rendering always goes: `fb.fill(0)` → `Writer(display.fb, font).set_textpos(row, col).printstring(...)` → `fb.show()`. Note `set_textpos(row, col)` is **y, x** — the reverse of the usual argument order.

Layout is only half-parameterized, so don't trust `Dashboard.__init__` as the single source of truth. Horizontal positions do derive from `self.right_section_width`, but the render methods recompute `left_section_width` locally (`main.py:117`, `:162`) instead of using the instance attribute, `self.bottom_section_height` (`:62`) is dead, and every vertical position is a hardcoded constant (`:119` y=10, `:126` y=35, `:172` +25). Changing the panel size means editing the render methods too.

## Gotchas

- **The watchdog has a feeding contract — don't break it.** `Dashboard.run()` starts a single `machine.WDT(self.WDT_TIMEOUT)` (120s) *after* the first successful cycle, so a bad `config.py` or miswired panel still fails visibly at the REPL instead of reboot-looping. An ESP32 WDT cannot be stopped once started, so every code path below it must keep feeding: `update_data()` calls `feed_wdt()` between widgets, and all waiting goes through `Dashboard.sleep()`, which feeds every 10s. **Never call `time.sleep()` directly inside the run loop** — a bare sleep longer than 120s resets the board. The timeout is sized to cover the slowest *single* widget (Pi-hole's retry backoff, ~30s), not a whole cycle, because feeding happens between widgets rather than inside them.
- `widgets/website_views.py` manages Wi-Fi itself: it reconnects on entry and **disconnects in a `finally` block** on every update, independent of `NetworkManager`. It runs last in `update_data()` for that reason; anything added after it will find the network down.
- `widgets/pihole_stats.py` targets the Pi-hole v6 session API (`/api/auth` → `X-FTL-SID`/`X-FTL-CSRF` → `/api/stats/summary` → `/api/logout`) with v5 fallbacks in `_validate_stats_data` and the getters. Its update interval is 3600s, unlike the other widgets. The self-imposed rate limit is deliberate — Pi-hole bans aggressive clients — and `max_requests_per_minute` is sized at exactly one cycle's three requests (auth, stats, logout). Lowering it starves `logout()`, which then clears the SID locally only and leaks the server-side session.
- `display/nanogui.py` is vendored but unused and would fail to import (`from colors import *` — no `colors.py` in the repo). Only `writer.py` and `boolpalette.py` from the nano-gui vendor set are live.
- `clock.py` and `ntp_client.py` both clamp any NTP year > 2030 back to 2025 to survive garbage NTP responses; the RTC also seeds a hardcoded 2025 default at construction.
- E-paper full refreshes are slow and wear the panel — that, not CPU cost, is why the update interval is 300s.
