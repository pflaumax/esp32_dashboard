import time
from machine import RTC
from ntp_client import NTPClient


class Clock:
    def __init__(
        self, timezone_offset=0, update_interval=3600, display_update_interval=300
    ):
        self.timezone_offset = timezone_offset  # Offset in hours
        self.update_interval = update_interval  # Seconds between NTP updates
        self.display_update_interval = (
            display_update_interval  # Seconds between time display updates
        )
        self.last_update = 0
        self.last_display_update = 0  # Track when we last updated the display time
        self.cached_time = None  # Cache for time display
        self.cached_date = None  # Cache for date display
        self.ntp_client = NTPClient(timezone_offset=timezone_offset)
        self.rtc = RTC()

        # Initialize RTC with a default time in case NTP fails
        # Year, Month, Day, Weekday, Hour, Minute, Second, Millisecond
        default_time = (
            2025,
            5,
            4,
            7,
            12,
            0,
            0,
            0,
        )
        self.rtc.datetime(default_time)

    def update_time(self, force=False):
        """Update system time from NTP server if update_interval has passed."""
        current_time = time.time()

        if force or (current_time - self.last_update > self.update_interval):
            print("Updating time from NTP server...")
            try:
                # Get time from NTP
                ntp_time = self.ntp_client.get_time()

                if ntp_time[0] > 2030:
                    print(f"Invalid year from NTP: {ntp_time[0]}")
                    year = 2025
                else:
                    year = ntp_time[0]

                # Adjust weekday for RTC (0-6 to 1-7)
                weekday = ntp_time[6] + 1  # 0-6 (Mon-Sun) to 1-7 (Mon-Sun)

                # Update RTC
                # Year, Month, Day, Weekday, Hour, Minute, Second, Millisecond
                self.rtc.datetime(
                    (
                        year,
                        ntp_time[1],
                        ntp_time[2],
                        weekday,
                        ntp_time[3],
                        ntp_time[4],
                        ntp_time[5],
                        0,
                    )
                )

                self.last_update = current_time
                # Force display update after NTP sync
                self.last_display_update = 0
                print("Time updated successfully")
                return True

            except Exception as e:
                print("Error updating time:", e)
                return False

        return True

    def get_time(self):
        """Get current time tuple."""
        return time.localtime()

    def get_formatted_time(self, include_seconds=False):
        """Get formatted time string without date."""
        time_tuple = self.get_time()
        hour, minute = time_tuple[3], time_tuple[4]

        # Format: HH:MM (24-hour format)
        if include_seconds:
            second = time_tuple[5]
            return f"{hour:02d}:{minute:02d}:{second:02d}"
        else:
            return f"{hour:02d}:{minute:02d}"

    def get_formatted_date(self):
        """Get formatted date string without year."""
        time_tuple = self.get_time()
        weekday = time_tuple[6]  # 0-6 (Mon-Sun)
        day = time_tuple[2]
        month = time_tuple[1]

        # Convert numeric weekday to abbreviated name
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_name = days[weekday]

        # Convert numeric month to abbreviated name
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        month_name = months[month - 1]  # Adjust for 1-indexed months

        # Format: "Day Month DD" (no year, no commas)
        return f"{day_name} {month_name} {day}"

    def get_time_for_display(self):
        """Get formatted time and date for display, but only update if display_update_interval has passed."""
        current_time = time.time()

        # Update cached values if display update interval has passed or if no cache exists
        if (current_time - self.last_display_update > self.display_update_interval) or (
            self.cached_time is None
        ):
            self.cached_time = self.get_formatted_time()
            self.cached_date = self.get_formatted_date()
            self.last_display_update = current_time
            print(f"Time display updated: {self.cached_time}, {self.cached_date}")

        # Return cached values
        return self.cached_time, self.cached_date
