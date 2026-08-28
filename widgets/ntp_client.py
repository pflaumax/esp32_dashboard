import socket
import struct
import time


class NTPClient:
    def __init__(self, host="pool.ntp.org"):
        self.host = host
        # NTP constants
        self.NTP_PACKET_FORMAT = "!12I"
        # NTP counts seconds from 1900. MicroPython's own epoch is 2000-01-01
        # on the baremetal ports but 1970-01-01 on unix/CPython, so ask the
        # runtime which one it is instead of hardcoding a delta.
        self.NTP_DELTA = 3155673600 if time.gmtime(0)[0] == 2000 else 2208988800
        # Backup servers
        self.backup_hosts = ["0.pool.ntp.org", "1.pool.ntp.org", "time.google.com"]

    def _create_ntp_packet(self):
        """Create a new NTP packet marked to be transmitting (client mode)."""
        packet = bytearray(48)

        # Set the first byte - leap indicator, version and mode bits
        # LI = 0, VN = 3, Mode = 3 (client)
        packet[0] = 0x1B  # 00 011 011 in binary

        return packet

    def _query(self, host):
        """Ask one server for the time and return a UTC time tuple."""
        packet = self._create_ntp_packet()

        # Create UDP socket and set timeout
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)

        # Get IP address of the NTP server, send packet and receive response
        try:
            addr = socket.getaddrinfo(host, 123)[0][-1]
            sock.sendto(packet, addr)
            msg = sock.recv(48)
        finally:
            sock.close()

        # Extract time value from packet
        unpacked = struct.unpack(self.NTP_PACKET_FORMAT, msg[0:48])

        # The timestamp starts at the 10th word, contains seconds since 1900
        ntp_time = unpacked[10]
        time_tuple = time.gmtime(ntp_time - self.NTP_DELTA)

        # Reject a nonsense answer rather than rewriting it into a
        # plausible-looking lie - the caller can still try another server.
        if not 2024 <= time_tuple[0] <= 2100:
            raise ValueError(f"Implausible year from NTP: {time_tuple[0]}")

        return time_tuple

    def get_time(self):
        """Query NTP and return a UTC time tuple, or None if every server failed.

        The timezone offset is applied by the caller when the time is read, so
        that the RTC itself stays on UTC.
        """
        # Try primary host first
        try:
            return self._query(self.host)
        except Exception as e:
            print(f"NTP error with primary server: {e}")

        # If primary fails, try backup servers
        for backup_host in self.backup_hosts:
            try:
                print(f"Trying backup NTP server: {backup_host}")
                return self._query(backup_host)
            except Exception as e:
                print(f"Backup server error: {e}")

        print("All NTP servers failed, keeping current RTC time")
        return None
