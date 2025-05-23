import socket
import struct
import time


class NTPClient:
    def __init__(self, host="pool.ntp.org", timezone_offset=0):
        self.host = host
        self.timezone_offset = timezone_offset  # Offset in hours
        # NTP constants
        self.NTP_PACKET_FORMAT = "!12I"
        self.NTP_DELTA = 2208988800  # Seconds between 1900 and 1970
        # Backup servers
        self.backup_hosts = ["0.pool.ntp.org", "1.pool.ntp.org", "time.google.com"]

    def _create_ntp_packet(self):
        """Create a new NTP packet marked to be transmitting (client mode)."""
        packet = bytearray(48)

        # Set the first byte - leap indicator, version and mode bits
        # LI = 0, VN = 3, Mode = 3 (client)
        packet[0] = 0x1B  # 00 011 011 in binary

        return packet

    def get_time(self):
        """Query NTP server and return local timestamp."""
        # Try primary host first
        try:
            # Create NTP packet
            packet = self._create_ntp_packet()

            # Create UDP socket and set timeout
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(5)

            # Get IP address of the NTP server and send packet
            try:
                addr = socket.getaddrinfo(self.host, 123)[0][-1]
                sock.sendto(packet, addr)

                # Receive response
                msg = sock.recv(48)
                sock.close()

                # Extract time value from packet
                unpacked = struct.unpack(self.NTP_PACKET_FORMAT, msg[0:48])

                # The timestamp starts at the 10th word, contains seconds
                # since 1900-01-01
                ntp_time = unpacked[10]

                # Convert to unix time (seconds since 1970-01-01)
                unix_time = ntp_time - self.NTP_DELTA

                # Apply timezone offset
                unix_time += int(self.timezone_offset * 3600)

                # Get time tuple
                time_tuple = time.localtime(unix_time)

                if time_tuple[0] > 2030:
                    corrected_time = list(time_tuple)
                    corrected_time[0] = 2025  # Set to current year
                    return tuple(corrected_time)

                return time_tuple

            except Exception as e:
                print(f"NTP error with primary server: {e}")
                # If primary fails, try backup servers
                sock.close()
                for backup_host in self.backup_hosts:
                    try:
                        print(f"Trying backup NTP server: {backup_host}")
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.settimeout(5)
                        addr = socket.getaddrinfo(backup_host, 123)[0][-1]
                        sock.sendto(packet, addr)
                        msg = sock.recv(48)
                        sock.close()

                        unpacked = struct.unpack(self.NTP_PACKET_FORMAT, msg[0:48])
                        ntp_time = unpacked[10]
                        unix_time = ntp_time - self.NTP_DELTA
                        unix_time += int(self.timezone_offset * 3600)

                        time_tuple = time.localtime(unix_time)
                        # Same verification for backup servers
                        if time_tuple[0] > 2030:
                            corrected_time = list(time_tuple)
                            corrected_time[0] = 2025
                            return tuple(corrected_time)

                        return time_tuple
                    except Exception as e:
                        print(f"Backup server error: {e}")
                        sock.close()
                        continue

                # If all servers fail, return system time
                print("All NTP servers failed, using system time")
                return time.localtime()

        except Exception as e:
            print(f"Error getting NTP time: {e}")
            return time.localtime()
