# ESP32 Dashboard

## Description

ESP32 Dashboard is a project that displays useful information on a 2.9" e-paper display. It leverages an ESP32 microcontroller, MicroPython, and various APIs to provide real-time data. Key information displayed includes:

* **Clock:** Synchronized via NTP (Network Time Protocol) for accurate timekeeping.
* **Weather:** Fetches current weather conditions and forecasts using the OpenWeatherMap API.
* **Personal website view counter:** Displays statistics from personal website analytics.
* **Pi-hole statistics:** Integrates with the Pi-hole API to show ad-blocking and network statistics from Raspberry Pi or other Pi-hole instance.

This project utilizes **Python** and **MicroPython** for the ESP32, interacts with the **OpenWeatherMAP API** for weather data, and the **Pi-hole API** for network statistics.

## Table of contents

1.  [Description](#description)
2.  [Hardware requirements](#hardware-requirements)
3.  [Pin connections](#pin-connections)
4.  [Setup and installation](#setup-and-installation)
5.  [Files and core components](#files-and-core-components)
6.  [Visual demo](#visual-demo)
7.  [Blog post](#blog-post)
8.  [License](#license)

## Hardware requirements

* ESP32-WROOM development board
* 2.9" E-paper display WeActStudio (296x128, black/white)
* Micro USB cable
* Power source (USB or battery)

## Pin connections

Connect the e-paper display to the ESP32 as follows:

| E-paper pin | ESP32 pin |
|-------------|-----------|
| BUSY        | GPIO4     |
| RST         | GPIO16    |
| DC          | GPIO17    |
| CS          | GPIO5     |
| CLK/SCL     | GPIO18    |
| DIN/SDA     | GPIO23    |
| GND         | GND       |
| VCC         | 3.3V      |

## Setup and installation

This section guides through setting up the project on host computer and the ESP32.

1.  **Clone the repository:**
    First, clone the project repository to local machine.
    ```bash
    $ git clone https://github.com/pflaumax/esp32_dashboard
    $ cd esp32-dashboard
    ```

2.  **Install host computer requirements:**
    Tools needed on computer to interact with the ESP32 and manage files.
    * **`ampy`**: For transferring files to the MicroPython filesystem.
        ```bash
        $ pip install adafruit-ampy
        ```
    * **`esptool.py`** (Recommended): For flashing MicroPython firmware to the ESP32.
        ```bash
        $ pip install esptool
        ```

3.  **Install MicroPython on ESP32:**
    If ESP32 doesn't have MicroPython, or you want to use a specific version, you'll need to flash it.
    * Download the latest firmware from the [official MicroPython website for ESP32](https://micropython.org/download/ESP32_GENERIC/).
    * Follow the flashing instructions provided on the MicroPython website, typically using `esptool.py`. For example:
        ```bash
        # Erase flash (optional, but good for a clean start)
        $ esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
        # Flash MicroPython firmware
        $ esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-generic-XXX.bin
        ```
        (Replace `/dev/ttyUSB0` with your ESP32's serial port and `esp32-generic-XXX.bin` with the downloaded firmware file name).

4.  **Prepare font files:**
    The dashboard requires MicroPython-compatible font files (`.py`).
    * It can be generated from standard font formats (like TTF) using [Peter Hinch's Official GitHub repository - micropython-font-to-py](https://github.com/peterhinch/micropython-font-to-py) tool.
    * Alternatively, pre-generated font files might be included in the repository or available for download. Ensure you have the necessary font files (e.g., `freesans20.py`).

5.  **Configure `config.py`:**
    This file contains all personalized settings. Create a `config.py` file in the root of the cloned repository with the following information, adjusting values as needed:
    * **WiFi credentials:**
        ```python
        WIFI_SSID = "your_wifi_ssid"
        WIFI_PASSWORD = "your_wifi_password"
        ```
    * **Time zone offset:**
        ```python
        TIMEZONE_OFFSET = "3" # Example for EEST
        ```
    * **OpenWeatherMap API:**
        ```python
        API_KEY = "your_api_key"  
        CITY_ID = "your_city_id"
        ```
    * **Website stats API endpoint:**
        ```python
        STATS_API_URL = "https://your.website.com/api/stats"
        ```
    * **Pi-hole configuration:**
        ```python
        PIHOLE_IP = "your_pihole_ip" 
        PIHOLE_PASSWORD_API = "your_pihole_api_password"
        # For new version v6.x.x find password API in Pi-hole: Settings > Web interface/API > Enable expert mode in the top right corner > Enable 2FA (optional) > Configure app password (API)
        ```

6.  **Upload files to ESP32:**
    Connect your ESP32 to your computer. Identify its serial port (e.g., `/dev/ttyUSB0` on Linux, `COM3` on Windows).
    Upload the project files and MicroPython libraries to the ESP32's root directory using `ampy`.
    * **All core project files:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put main.py
        $ ampy --port /dev/ttyUSB0 put boot.py
        $ ampy --port /dev/ttyUSB0 put config.py
        ```
    * **E-paper driver library from `"driver"` directory:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put epd_29_ssd1680.py 
        # Or your specific display driver name
        ```
    * **Libraries from `"display"` directory:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put nanogui.py
        # Add other components (e.g., boolpalette.py, writer.py)
        ```
    * **Font files from `"fonts"` directory:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put freesans20.py
        # Upload all necessary font files
        ```
    * **Widgets and additional support files from `"widgets` directory:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put clock.py
        # And other components 
        ```

7.  **Run the dashboard:**
    * **Option 1: Reset the ESP32.** Press the reset button on board. If `main.py` and `boot.py` is present, MicroPython will execute it automatically.
    * **Option 2: Run Manually via `ampy` (for testing).**
        ```bash
        $ ampy --port /dev/ttyUSB0 run main.py
        ```

## Files and core components

**This project typically consists of the following files to be uploaded to the ESP32:**

* `main.py`: The main script that initializes the display, networking, and orchestrates the fetching and displaying of data.
* `boot.py`: This script runs on boot and is used to configure low-level system settings.
* `config.py`: Contains all user-specific configurations like WiFi, API keys, and other settings.

**E-paper driver library:**
* `epd29_ssd1680.py`: Driver library specific to the WeActStudio 2.9" e-paper display, handling low-level communication and drawing functions.

**Font files (`*.py`):** 
* Python files generated by `micropython-font-to-py`, defining pixel patterns for different characters.

**Display libraries (include files from the [official repository micropython-nano-gui by Peter Hinch](https://github.com/peterhinch/micropython-nano-gui))**:
* `nanogui.py`: The core GUI library. It provides the framework for creating graphical user interfaces with widgets like labels, buttons, and meters on framebuf-based displays.
* `writer.py`: A module for rendering Python fonts. It's used by `nanogui` to display text with various fonts.
* `display`: Contains utility classes and methods to manage the frame buffer, handle screen refreshes, and abstract low-level display operations. 
* `boolpalette.py`: Defines color palettes for 1-bit or multi-bit frame buffers, essential for correct color rendering on monochrome e-paper displays.  
* `frame_buffer_wrapper.py`: A wrapper around the MicroPython framebuf module to extend or customize drawing capabilities for the e-paper display.

**Widgets and other support files:**
* `clock.py`: Implements the clock widget, managing time display synchronized via NTP and updating the dashboard in real time. 
* `ntp_client.py`: Handles communication with NTP servers to fetch accurate current time for synchronization.
* `pihole_stats.py`: Interfaces with the Pi-hole API to retrieve ad-blocking statistics and network data to be displayed on the dashboard.
* `weather.py`: Manages fetching and parsing weather data from the OpenWeatherMap API and provides current weather and forecast information for display. 
* `website_views.py`: Connects to the personal website's analytics API to retrieve and display visitor statistics.
* `network_manager.py`: Utility to manage WiFi connections, handle reconnections, and maintain network status for the ESP32.


## Visual demo

[A GIF loop will be soon]

*(Consider embedding a static image as a placeholder if the GIF is not ready, or a link to an image/video if hosted elsewhere).*

## Blog Post

[Coming soon]

*(Link to your blog post once it's published).*

## License

This project is licensed under the [MIT License](LICENSE).