import network
import time
import socket
import gc


class NetworkManager:
    def __init__(self, ssid, password, timeout=30):
        self.ssid = ssid
        self.password = password
        self.timeout = timeout
        self.wlan = network.WLAN(network.STA_IF)

    def connect(self):
        print("Connecting to WiFi network:", self.ssid)

        # Activate WiFi interface if it's not already active
        if not self.wlan.active():
            self.wlan.active(True)

        # Check if already connected
        if self.wlan.isconnected():
            print("Already connected to WiFi")
            return True

        # Connect to network
        self.wlan.connect(self.ssid, self.password)

        # Wait for connection with timeout
        start_time = time.time()
        while not self.wlan.isconnected():
            if time.time() - start_time > self.timeout:
                print("WiFi connection timeout")
                return False
            print("Waiting for connection...")
            time.sleep(1)

        # Print connection info
        print("Connected to WiFi")
        print("Network config:", self.wlan.ifconfig())
        return True

    def get_config(self):
        return self.wlan.ifconfig() if self.wlan.isconnected() else None

    def disconnect(self):
        if self.wlan.active():
            self.wlan.disconnect()
            self.wlan.active(False)
            print("WiFi disconnected")

    def is_connected(self):
        return self.wlan.isconnected()
