import urequests
import ujson
import time
import config
import network
import sys


class WebsiteStats:
    def __init__(self, api_url, update_interval=3600):
        self.api_url = api_url
        self.update_interval = update_interval
        self.last_update = 0
        self.root_views = None
        self.total_views = None
        self.wlan = network.WLAN(network.STA_IF)
        self.ssid = config.Network_Config.WIFI_SSID
        self.password = config.Network_Config.WIFI_PASSWORD

    def connect_wifi(self):
        """Connect to Wi-Fi."""
        if not self.wlan.isconnected():
            print("Connecting to WiFi network:", self.ssid)
            self.wlan.active(True)
            self.wlan.connect(self.ssid, self.password)
            # Add timeout for connection
            max_wait = 20  # 20 seconds timeout
            start_time = time.time()
            while not self.wlan.isconnected() and time.time() - start_time < max_wait:
                time.sleep(1)
                print("Waiting for connection...")

            if self.wlan.isconnected():
                print("Connected to WiFi")
                print("Network config:", self.wlan.ifconfig())
                return True
            else:
                print("WiFi connection failed - timeout")
                return False
        else:
            print("Already connected to WiFi")
            return True

    def disconnect_wifi(self):
        """Disconnect from Wi-Fi."""
        if self.wlan.isconnected():
            self.wlan.disconnect()
            self.wlan.active(False)
            print("WiFi disconnected")
        else:
            print("WiFi not connected")

    def update_views(self, force=False):
        """Fetch website statistics and extract total views."""
        current_time = time.time()
        if force or (current_time - self.last_update) > self.update_interval:
            print("Updating website views...")
            try:
                if not self.connect_wifi():
                    print("Failed to connect to WiFi")
                    return False

                try:
                    print(f"Fetching from URL: {self.api_url}")
                    # Add timeout to prevent hanging indefinitely
                    response = urequests.get(self.api_url, timeout=10)
                    print(f"Initial response status code: {response.status_code}")

                    # If got a redirect (301 or 302), try with trailing slash
                    if response.status_code in (301, 302):
                        print(
                            f"Got redirect {response.status_code}, trying with trailing slash"
                        )
                        response.close()

                        # Ensure URL ends with trailing slash
                        url_with_slash = self.api_url
                        if not url_with_slash.endswith("/"):
                            url_with_slash += "/"

                        print(f"New URL: {url_with_slash}")
                        response = urequests.get(url_with_slash, timeout=10)
                        print(f"Second response status code: {response.status_code}")

                    if response.status_code == 200:
                        text = response.text
                        print(f"Response text: {text}")
                        data = ujson.loads(text)
                        print(f"Parsed data: {data}")

                        # Update this part to handle new structure
                        if "pages" in data:
                            # New structured format
                            for page in data["pages"]:
                                if page["path"] == "/":
                                    self.root_views = page["count"]
                                    break
                            else:
                                # If root page not found in pages list
                                self.root_views = 0
                        else:
                            # Old format (fallback)
                            self.root_views = data.get("/", 0)

                        self.last_update = current_time
                        print("Website views updated successfully")
                        print("Root page views:", self.root_views)
                    else:
                        print(f"Error fetching website stats: {response.status_code}")
                        # Don't reset values here, keep previous ones

                    response.close()
                    return True

                except OSError as e:
                    print(f"Network error updating website stats: {e}")
                    sys.print_exception(e)
                    return False
                except Exception as e:
                    print(f"Error updating website stats: {e}")
                    sys.print_exception(e)
                    return False

            finally:
                # Always try to disconnect WiFi regardless of success/failure
                try:
                    self.disconnect_wifi()
                except:
                    pass

        return True

    def get_root_views(self):
        """Get root page views."""
        return self.root_views if self.root_views is not None else 0

    def get_views_for_display(self):
        """Get total views formatted for display."""
        views = self.get_root_views()
        if views >= 1000:
            return f"{views / 1000:.1f}k"
        else:
            return f"{views}"
