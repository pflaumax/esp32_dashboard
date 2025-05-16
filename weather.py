import urequests
import ujson
import time


class WeatherAPI:
    def __init__(self, api_key, city_id, update_interval=3600):
        self.api_key = api_key
        self.city_id = city_id
        self.update_interval = update_interval
        self.last_update = 0
        self.weather_data = None

    def update_weather(self, force=False):
        """Fetch weather data from OpenWeatherMap API."""
        current_time = time.time()

        if force or (current_time - self.last_update) > self.update_interval:
            print("Updating weather data...")
            try:
                url = f"http://api.openweathermap.org/data/2.5/weather?id={self.city_id}&appid={self.api_key}&units=metric"
                # Add timeout to prevent hanging indefinitely
                response = urequests.get(url, timeout=10)

                if response.status_code == 200:
                    self.weather_data = ujson.loads(response.text)
                    self.last_update = current_time
                    print("Weather data updated successfully")
                else:
                    print(f"Error fetching weather data: {response.status_code}")

                # Ensure response is always closed, even if an exception occurs
                response.close()
                return True
            except OSError as e:
                print(f"Network error: {e}")
                return False
            except Exception as e:
                print(f"Error updating weather: {e}")
                return False

        return True  # No update needed

    def get_location_name(self):
        """Get city and country code."""
        if self.weather_data:
            city = self.weather_data.get("name", "Unknown")
            country = self.weather_data.get("sys", {}).get("country", "")
            return f"{city},{country}"
        return "Location Unknown"

    def get_temperature(self):
        """Get current temperature in Celsius."""
        if (
            self.weather_data
            and "main" in self.weather_data
            and "temp" in self.weather_data["main"]
        ):
            return round(self.weather_data["main"]["temp"])
        return None

    def get_rainfall(self):
        """Get rainfall in mm (last 3 hours)."""
        if self.weather_data and "rain" in self.weather_data:
            # Try to get rain data for the last 3 hours, fall back to 1 hour if not present
            return self.weather_data["rain"].get(
                "3h", self.weather_data["rain"].get("1h", 0)
            )
        return 0  # Return 0 if no rain data found

    def get_humidity(self):
        """Get humidity percentage."""
        if (
            self.weather_data
            and "main" in self.weather_data
            and "humidity" in self.weather_data["main"]
        ):
            return self.weather_data["main"]["humidity"]
        return None

    def get_formatted_display(self):
        """Format weather data for e-paper display with compact format."""
        if not self.weather_data:
            return "No weather data", ""

        location = self.get_location_name()
        temp = self.get_temperature()
        humid = self.get_humidity()
        rain = self.get_rainfall()

        # Handle potential None values
        temp_str = f"{temp}`C" if temp is not None else "?`C"
        humid_str = f"{humid}%" if humid is not None else "?%"

        # Location and temperature for main display (larger font)
        main_line = f"{location} {temp_str}"

        # Humidity and rainfall for secondary display (smaller font)
        # Compact format without spaces
        secondary_line = f"Hum:{humid_str} Rain:{rain:.1f}mm"

        return main_line, secondary_line
