# ESP32 Dashboard

## Description
ESP32 Dashboard displays useful information on a 2.9" e-paper display:
- Clock (NTP)
- Weather (Open-Meteo API)
- Personal website view counter
- Pi-hole statistics (FTL API)



## Hardware Requirements

- ESP32 WROOM development board  
- 2.9" E-paper display WeActStudio (296x128, black/white)  
- Micro USB cable  
- Power source (USB or battery)  


## Pin Connections

Connect the e-paper display to ESP32 as follows:

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


## Software Setup

1. Install MicroPython on your ESP32 if not already installed:  
   [here](https://micropython.org/download/ESP32_GENERIC/).

2. Install requirements, such as `ampy`, `edp_lib`. 

3. Download or generate font files with (with python [font_to_py.py](https://github.com/peterhinch/micropython-font-to-py) for example).

4. Edit the `config.py` file with your:  
- WiFi credentials  
- Time zone offset  
- Open-Meteo API key  
- Website stats API endpoint  
- Pi-hole URL and token/password

5. Upload all files to your ESP32 with `ampy`

## Visual Demo

[A GIF loop will be soon]


## Blog Post

[Coming soon]

## License

This project is licensed under the [MIT License](LICENSE).