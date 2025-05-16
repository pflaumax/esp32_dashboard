# ESP32 Dashboard

## Description

ESP32 Dashboard is a project that displays useful information on a 2.9" e-paper display. It leverages an ESP32 microcontroller, MicroPython, and various APIs to provide real-time data. Key information displayed includes:

* **Clock:** Synchronized via NTP (Network Time Protocol) for accurate timekeeping.
* **Weather:** Fetches current weather conditions and forecasts using the Open-Meteo API.
* **Personal Website View Counter:** Displays statistics from your website's analytics.
* **Pi-hole Statistics:** Integrates with the Pi-hole FTL API to show ad-blocking and network statistics from your Raspberry Pi or other Pi-hole instance.

This project utilizes **Python** and **MicroPython** for the ESP32, interacts with the **Open-Meteo API** for weather data, and the **Pi-hole API** (FTL API) for network statistics.

## Table of Contents

1.  [Description](#description)
2.  [Hardware Requirements](#hardware-requirements)
3.  [Pin Connections](#pin-connections)
4.  [Setup and Installation](#setup-and-installation)
5.  [Files and Core Components](#files-and-core-components)
6.  [More Info about micropython-nano-gui](#more-info-about-micropython-nano-gui)
7.  [Visual Demo](#visual-demo)
8.  [Blog Post](#blog-post)
9.  [License](#license)

## Hardware Requirements

* ESP32 WROOM development board
* 2.9" E-paper display WeActStudio (296x128, black/white)
* Micro USB cable
* Power source (USB or battery)

## Pin Connections

Connect the e-paper display to the ESP32 as follows:

| E-Paper Pin | ESP32 Pin |
|-------------|-----------|
| BUSY        | GPIO4     |
| RST         | GPIO16    |
| DC          | GPIO17    |
| CS          | GPIO5     |
| CLK         | GPIO18    |
| DIN         | GPIO23    |
| GND         | GND       |
| VCC         | 3.3V      |

## Setup and Installation

This section guides you through setting up the project on your host computer and the ESP32.

1.  **Clone the Repository:**
    First, clone the project repository to your local machine.
    ```bash
    $ git clone https://github.com/pflaumax/esp32_dashboard
    $ cd esp32-dashboard
    ```

2.  **Install Host Computer Requirements:**
    You'll need a few tools on your computer to interact with the ESP32 and manage files.
    * **`ampy`**: For transferring files to the MicroPython filesystem.
        ```bash
        $ pip install adafruit-ampy
        ```
    * **`esptool.py`** (Recommended): For flashing MicroPython firmware to the ESP32 if it's not already installed or if you need to update it.
        ```bash
        $ pip install esptool
        ```

3.  **Install MicroPython on ESP32:**
    If your ESP32 doesn't have MicroPython, or you want to use a specific version, you'll need to flash it.
    * Download the latest firmware from the [official MicroPython website for ESP32_GENERIC](https://micropython.org/download/ESP32_GENERIC/).
    * Follow the flashing instructions provided on the MicroPython website, typically using `esptool.py`. For example:
        ```bash
        # Erase flash (optional, but good for a clean start)
        $ esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
        # Flash MicroPython firmware
        $ esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32-generic-XXX.bin
        ```
        (Replace `/dev/ttyUSB0` with your ESP32's serial port and `esp32-generic-XXX.bin` with the downloaded firmware file name).

4.  **Prepare Font Files:**
    The dashboard requires MicroPython-compatible font files (`.py`).
    * You can generate these from standard font formats (like TTF) using Peter Hinch's Official GitHub repository [micropython-font-to-py](https://github.com/peterhinch/micropython-font-to-py) tool.
    * Alternatively, pre-generated font files might be included in the repository or available for download. Ensure you have the necessary font files (e.g., `freesans20.py`).

5.  **Configure `config.py`:**
    This file contains all your personalized settings. Create a `config.py` file in the root of the cloned repository with the following information, adjusting values as needed:
    * **WiFi Credentials:**
        ```python
        WIFI_SSID = "your_wifi_ssid"
        WIFI_PASSWORD = "your_wifi_password"
        ```
    * **Time Zone Offset:**
        ```python
        TIMEZONE_OFFSET = "3" # Example for EEST
        ```
    * **OpenWeatherMap API (Location):**
        ```python
        API_KEY = "your_api_key"  
        CITY_ID = "your_city_id"
        ```
    * **Website Stats API Endpoint:**
        ```python
        STATS_API_URL = "https://your.website.com/api/stats"
        ```
    * **Pi-hole Configuration:**
        ```python
        PIHOLE_IP = "your_pihole_ip" 
        PIHOLE_PASSWORD_API = "your_pihole_api_token"
        # For new version v6.x.x find password API in Pi-hole: Settings > API/Web interface > 2FA change password
        ```

6.  **Upload Files to ESP32:**
    Connect your ESP32 to your computer. Identify its serial port (e.g., `/dev/ttyUSB0` on Linux, `COM3` on Windows).
    Upload the project files and MicroPython libraries to the ESP32's root directory using `ampy`.
    * **Core Project Files:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put main.py
        $ ampy --port /dev/ttyUSB0 put config.py
        ```
    * **E-Paper Display Library:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put epd_29_ssd1680.py 
        # Or your specific display driver name
        ```
    * **GUI Libraries (`micropython-nano-gui`):**
        ```bash
        $ ampy --port /dev/ttyUSB0 put nanogui.py
        $ ampy --port /dev/ttyUSB0 put writer.py
        # Add other nano-gui components if you use them (e.g., colors.py)
        ```
    * **Font Files:**
        ```bash
        $ ampy --port /dev/ttyUSB0 put freesans20.py
        # Upload all necessary font files
        ```
    * **Other Helper/MicroPython Libraries:**
        Upload any other `.py` files required by your project.

7.  **Run the Dashboard:**
    Once all files are uploaded, you can run the dashboard:
    * **Option 1: Reset the ESP32.** Press the reset button on your ESP32 board. If `main.py` is present, MicroPython will execute it automatically.
    * **Option 2: Run Manually via `ampy` (for testing).**
        ```bash
        $ ampy --port /dev/ttyUSB0 run main.py
        ```

## Files and Core Components

This project typically consists of the following files to be uploaded to the ESP32:

* `main.py`: The main script that initializes the display, networking, and orchestrates the fetching and displaying of data.
* `config.py`: Contains all user-specific configurations like WiFi credentials, API keys, and other settings.
* `epd29_ssd1680.py`: (Or a similar name like `display_driver.py`). Driver library specific to the WeActStudio 2.9" e-paper display, handling low-level communication and drawing functions.
* **Font Files (`*.py`):** Python files generated by `micropython-font-to-py`, defining pixel patterns for different characters.
* **GUI Libraries from the [micropython-nano-gui](https://github.com/peterhinch/micropython-nano-gui) by Peter Hinch, from official repository:**
    * `nanogui.py`: The core GUI library. It provides the framework for creating graphical user interfaces with widgets like labels, buttons, and meters on framebuf-based displays.
    * `writer.py`: A module for rendering Python fonts. It's used by `nanogui` to display text with various fonts.
    * Other optional `nano-gui` components if used (e.g., `colors.py`, specific widget files).
    * ADD MORE
* **Helper Modules (Optional):**
    * `wifi_manager.py`: A common utility to handle WiFi connections.
    * ADD MORE 


## Visual Demo

[A GIF loop will be soon]

*(Consider embedding a static image as a placeholder if the GIF is not ready, or a link to an image/video if hosted elsewhere).*

## Blog Post

[Coming soon]

*(Link to your blog post once it's published).*

## License

This project is licensed under the [MIT License](LICENSE).