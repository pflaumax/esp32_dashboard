import gc
import time
import machine
import sys
import framebuf

from display.display import EPaperDisplay
from widgets.clock import Clock
from widgets.weather import WeatherAPI
from widgets.pihole_stats import PiholeStats
from widgets.website_views import WebsiteStats
from widgets.network_manager import NetworkManager
import config
from display.writer import Writer
from fonts import freesans14, freesans17, freesans20


class Dashboard:
    def __init__(self):
        self.DISPLAY_UPDATE_INTERVAL = 300  # 5 minutes in seconds
        self.WDT_TIMEOUT = 120000  # 2 minutes in milliseconds
        self.WDT_FEED_INTERVAL = 10  # Feed at least this often while sleeping
        self.wdt = None

        print("Initializing display...")
        self.display = EPaperDisplay()

        print("Setting up network...")
        self.network = NetworkManager(
            config.Network_Config.WIFI_SSID, config.Network_Config.WIFI_PASSWORD
        )

        print("Setting up clock...")
        self.clock = Clock(
            timezone_offset=config.Time_Config.TIMEZONE_OFFSET,
            # Optional, so a config.py written before TZ support keeps working
            tz=getattr(config.Time_Config, "TZ", None),
            display_update_interval=self.DISPLAY_UPDATE_INTERVAL,
        )

        print("Setting up weather client...")
        self.weather = WeatherAPI(
            api_key=config.Weather_Config.API_KEY,
            city_id=config.Weather_Config.CITY_ID,
            update_interval=self.DISPLAY_UPDATE_INTERVAL,
        )

        print("Setting up website stats client...")
        self.website = WebsiteStats(
            api_url=config.Website_Config.API_URL,
            update_interval=self.DISPLAY_UPDATE_INTERVAL,
        )

        print("Setting up Pi-hole client...")
        self.pihole = PiholeStats(
            pihole_ip=config.Pihole_Config.PIHOLE_IP,
            password=config.Pihole_Config.PIHOLE_PASSWORD,
            update_interval=3600,
        )

        self.last_refresh_time = 0
        self.width = self.display.width
        self.height = self.display.height

        # Define layout regions
        self.top_section_height = self.height // 2
        self.left_section_width = self.width // 2
        self.right_section_width = self.width - self.left_section_width

    def connect_network(self):
        """Connect to Wi-Fi."""
        return self.network.connect()

    def feed_wdt(self):
        """Feed the watchdog, if one is running."""
        if self.wdt is not None:
            self.wdt.feed()

    def sleep(self, seconds):
        """Sleep, feeding the watchdog so it doesn't reset us mid-wait."""
        remaining = seconds
        while remaining > 0:
            interval = min(self.WDT_FEED_INTERVAL, remaining)
            time.sleep(interval)
            self.feed_wdt()
            remaining -= interval

    def update_data(self):
        """Try to data update."""
        success = True

        if not self.network.is_connected():
            if not self.connect_network():
                print("Failed to connect to network")
                return False

        try:
            self.clock.update_time()
        except Exception as e:
            print(f"Error updating time: {e}")
            sys.print_exception(e)
            success = False
        self.feed_wdt()

        try:
            self.weather.update_weather()
        except Exception as e:
            print(f"Error updating weather: {e}")
            sys.print_exception(e)
            success = False
        self.feed_wdt()

        try:
            self.pihole.update_stats()
        except Exception as e:
            print(f"Error updating Pi-hole stats: {e}")
            sys.print_exception(e)
            success = False
        self.feed_wdt()

        # Runs last: this widget disconnects Wi-Fi in a finally block
        try:
            self.website.update_views()
        except Exception as e:
            print(f"Error updating website views: {e}")
            sys.print_exception(e)
            success = False
        self.feed_wdt()

        return success

    def render_time_section(self):
        """Render date and time section data."""
        time_str, date_str = self.clock.get_time_for_display()

        w_time = Writer(self.display.fb, freesans20)
        time_width_main = w_time.stringlen(time_str)
        x_time = (self.left_section_width - time_width_main) // 2
        w_time.set_textpos(10, x_time)
        w_time.printstring(time_str)

        w_date = Writer(self.display.fb, freesans14)
        date_width_main = w_date.stringlen(date_str)
        x_date = (self.left_section_width - date_width_main) // 2
        w_date.set_textpos(35, x_date)
        w_date.printstring(date_str)

    def render_weather_section(self):
        """Render weather section data."""

        weather_main, weather_details = self.weather.get_formatted_display()

        w_main = Writer(self.display.fb, freesans20)
        text_width_main = w_main.stringlen(weather_main)
        x_main = (
            self.width
            - self.right_section_width
            + (self.right_section_width - text_width_main) // 2
        )
        w_main.set_textpos(10, x_main)
        w_main.printstring(weather_main)

        w_details = Writer(self.display.fb, freesans14)
        text_width_details = w_details.stringlen(weather_details)
        x_details = (
            self.width
            - self.right_section_width
            + (self.right_section_width - text_width_details) // 2
        )
        w_details.set_textpos(35, x_details)
        w_details.printstring(weather_details)

    def render_website_section(self):
        """Render views of personal website section data."""

        label_text = "Site Views:"
        value_text = self.website.get_views_for_display()

        w_label = Writer(self.display.fb, freesans20)
        w_value = Writer(self.display.fb, freesans17)

        label_width = w_label.stringlen(label_text)
        x_label = (self.left_section_width - label_width) // 2
        y_label = self.top_section_height + 10
        w_label.set_textpos(y_label, x_label)
        w_label.printstring(label_text)

        value_width = w_value.stringlen(value_text)
        x_value = (self.left_section_width - value_width) // 2
        y_value = y_label + 25  # Space between label and value
        w_value.set_textpos(y_value, x_value)
        w_value.printstring(value_text)

    def render_pihole_section(self):
        """Render pi-hole ad block section data."""

        pihole_total, pihole_blocked = self.pihole.get_stats_for_display()

        w_total = Writer(self.display.fb, freesans17)
        text_width_total = w_total.stringlen(pihole_total)
        x_total = (
            self.width
            - self.right_section_width
            + (self.right_section_width - text_width_total) // 2
        )
        y_total = self.top_section_height + 10
        w_total.set_textpos(y_total, x_total)
        w_total.printstring(pihole_total)

        w_blocked = Writer(self.display.fb, freesans17)
        text_width_blocked = w_blocked.stringlen(pihole_blocked)
        x_blocked = (
            self.width
            - self.right_section_width
            + (self.right_section_width - text_width_blocked) // 2
        )
        y_blocked = self.top_section_height + 35
        w_blocked.set_textpos(y_blocked, x_blocked)
        w_blocked.printstring(pihole_blocked)

    def render_dashboard(self):
        """Render whole sections display data."""

        try:
            self.display.fb.fill(0)

            self.render_time_section()
            self.render_weather_section()
            self.render_website_section()
            self.render_pihole_section()

            self.display.fb.show()
            return True
        except Exception as e:
            print(f"Error rendering dashboard: {e}")
            sys.print_exception(e)
            return False

    def run(self):
        """Run the dashboard"""
        print(
            f"Dashboard will update every {self.DISPLAY_UPDATE_INTERVAL} seconds EXACTLY."
        )
        print("\n[STARTUP] Initial update cycle...")
        self.update_data()
        self.render_dashboard()
        self.last_refresh_time = time.time()

        print(f"Starting watchdog ({self.WDT_TIMEOUT // 1000}s timeout)")
        self.wdt = machine.WDT(timeout=self.WDT_TIMEOUT)

        def get_sleep_time():
            current_time = time.time()
            elapsed = current_time - self.last_refresh_time
            if elapsed >= self.DISPLAY_UPDATE_INTERVAL:
                return 0
            return self.DISPLAY_UPDATE_INTERVAL - elapsed

        while True:
            try:
                sleep_time = get_sleep_time()

                if sleep_time > 0:
                    print(f"Sleeping for {sleep_time:.0f} seconds until next update")
                    self.sleep(sleep_time)

                current_time = time.time()
                elapsed = current_time - self.last_refresh_time
                print(
                    f"\n[{self.clock.get_time()}] Scheduled update cycle (after {elapsed:.0f}s)..."
                )

                self.update_data()
                self.render_dashboard()
                self.last_refresh_time = time.time()

                gc.collect()

                print(
                    f"Update complete. Next update in {self.DISPLAY_UPDATE_INTERVAL} seconds."
                )

            except Exception as e:
                print(f"Error in main loop: {e}")
                sys.print_exception(e)
                print("Reconnecting network and retrying in 60 seconds...")
                self.feed_wdt()
                self.connect_network()
                self.sleep(60)


def start():
    """Start the dashboard. Shared by boot.py and by running main.py directly."""
    print("Starting E-Paper Dashboard")
    try:
        dashboard = Dashboard()

        print("Connecting to network...")
        if dashboard.connect_network():
            print("Network connected")
            dashboard.run()
        else:
            print("Failed to connect to network. Check your WiFi credentials.")
            print("Restarting in 300 seconds...")
            time.sleep(300)
            machine.reset()
    except Exception as e:
        print(f"Critical error: {e}")
        sys.print_exception(e)
        print("Restarting in 300 seconds...")
        time.sleep(300)
        machine.reset()


if __name__ == "__main__":
    start()
