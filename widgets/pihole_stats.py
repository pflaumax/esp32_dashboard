import urequests
import ujson
import time


class PiholeStats:
    def __init__(self, pihole_ip, password=None, api_token=None, update_interval=7200):
        self.pihole_ip = pihole_ip
        self.password = password
        self.api_token = api_token
        self.update_interval = update_interval
        self.base_url = f"http://{pihole_ip}/api"
        self.auth_endpoint = "/auth"
        self.summary_endpoint = "/stats/summary"
        self.logout_endpoint = "/logout"

        self.session_sid = None
        self.csrf_token = None
        self.last_update = 0
        self.stats_data = None
        self.auth_failed = False

        # Rate limiting protection
        self.request_times = []
        self.max_requests_per_minute = 1  # Maximum allowed requests per minute
        self.rate_limit_window = 60  # Window in seconds for rate limiting
        self.rate_limited_until = 0  # Timestamp until rate limiting expires

        # Retry configuration with exponential backoff
        self.max_retries = 2
        self.base_retry_delay = 5  # Base delay in seconds
        self.cached_stats = None

    def _is_rate_limited(self):
        """Check if we should avoid making requests due to rate limiting"""
        # If we're in a rate limited state
        current_time = time.time()
        if current_time < self.rate_limited_until:
            return True

        # Clean up old request timestamps
        self.request_times = [
            t for t in self.request_times if current_time - t < self.rate_limit_window
        ]

        # If we've made too many requests recently
        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 2 * self.rate_limit_window  # Wait for twice the window time
            self.rate_limited_until = current_time + wait_time
            print(
                f"Rate limit threshold reached. Pausing requests for {wait_time} seconds"
            )
            return True

        return False

    def _track_request(self):
        """Record a request timestamp for rate limiting"""
        self.request_times.append(time.time())

    def authenticate(self):
        """Authenticate with Pi-hole API"""
        if self._is_rate_limited():
            print("Rate limited. Skipping authentication")
            return False

        print("Authenticating with Pi-hole...")
        self.auth_failed = False

        # Skip authentication if using API token
        if self.api_token and not self.password:
            print("Using API token authentication")
            self.session_sid = None  # No session needed with token
            return True

        for attempt in range(self.max_retries):
            try:
                # Track this request for rate limiting
                self._track_request()

                auth_url = self.base_url + self.auth_endpoint
                auth_payload = {"password": self.password}
                headers = {"Content-Type": "application/json"}

                response = urequests.post(auth_url, json=auth_payload, headers=headers)
                print(f"Auth response status: {response.status_code}")

                # Handle rate limiting specifically
                if response.status_code == 429:
                    print("Rate limit detected during authentication")
                    retry_after = 300  # Default 5 minutes
                    try:
                        # Try to get the retry-after header
                        retry_header = response.headers.get("Retry-After")
                        if retry_header:
                            retry_after = int(retry_header)
                    except:
                        pass

                    self.rate_limited_until = time.time() + retry_after
                    print(f"Rate limited. Waiting for {retry_after} seconds")
                    response.close()
                    return False

                if response.status_code == 200:
                    try:
                        auth_data = ujson.loads(response.text)
                        if auth_data.get("session") and auth_data["session"].get("sid"):
                            self.session_sid = auth_data["session"]["sid"]
                            self.csrf_token = auth_data["session"].get("csrf")
                            print("Authentication successful. SID obtained.")
                            response.close()
                            return True
                        else:
                            print(
                                "Authentication response received, but SID not found."
                            )
                    except ValueError as e:
                        print(f"Invalid JSON in authentication response: {e}")
                else:
                    print(f"Authentication failed with status: {response.status_code}")

                response.close()

                if attempt < self.max_retries - 1:
                    # Exponential backoff
                    retry_delay = self.base_retry_delay * (2**attempt)
                    print(
                        f"Retrying authentication in {retry_delay} seconds... (Attempt {attempt+1}/{self.max_retries})"
                    )
                    time.sleep(retry_delay)

            except Exception as e:
                print(
                    f"Error authenticating (attempt {attempt+1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    retry_delay = self.base_retry_delay * (2**attempt)
                    time.sleep(retry_delay)

        self.auth_failed = True
        return False

    def logout(self):
        # Skip logout if using API token
        if self.api_token and not self.session_sid:
            return

        if self.session_sid:
            if self._is_rate_limited():
                print("Rate limited. Skipping logout")
                self.session_sid = None  # Just clear it locally
                self.csrf_token = None
                return

            try:
                # Track this request for rate limiting
                self._track_request()

                logout_url = self.base_url + self.logout_endpoint
                headers = {
                    "X-FTL-SID": self.session_sid,
                    "X-FTL-CSRF": self.csrf_token,
                }
                response = urequests.post(logout_url, headers=headers)
                response.close()
                print("Logged out from Pi-hole session.")
            except Exception as e:
                print(f"Error during logout: {e}")

            self.session_sid = None
            self.csrf_token = None

    def update_stats(self, force=False):
        current_time = time.time()

        # Check rate limiting
        if self._is_rate_limited():
            time_to_wait = self.rate_limited_until - current_time
            print(f"Rate limited. Waiting {int(time_to_wait)} more seconds")
            if self.cached_stats:
                print("Using cached stats due to rate limiting")
                self.stats_data = self.cached_stats
                return True
            return False

        if self.auth_failed and not force:
            print("Skipping update due to previous auth failure")
            return False

        # Skip if interval is too short (protection against misconfigured clock or reboots)
        time_since_update = current_time - self.last_update
        if not force and time_since_update < self.update_interval * 0.5:
            print(
                f"Skipping update. Only {int(time_since_update)}s since last update (min: {int(self.update_interval * 0.5)}s)"
            )
            return True

        if force or time_since_update > self.update_interval:
            print("Updating Pi-hole stats...")

            # Only authenticate if needed and not using token
            if not self.api_token and not self.session_sid and not self.authenticate():
                return False

            for attempt in range(self.max_retries):
                try:
                    # Track this request for rate limiting
                    self._track_request()

                    # Always use the original endpoint first
                    summary_url = self.base_url + self.summary_endpoint
                    headers = {}

                    # Add token to URL if using API token
                    if self.api_token:
                        if "?" in summary_url:
                            summary_url += f"&auth={self.api_token}"
                        else:
                            summary_url += f"?auth={self.api_token}"

                    # Otherwise use session-based auth
                    elif self.session_sid:
                        headers["X-FTL-SID"] = self.session_sid
                        if self.csrf_token:
                            headers["X-FTL-CSRF"] = self.csrf_token

                    print(f"Requesting from: {summary_url}")
                    response = urequests.get(summary_url, headers=headers)

                    # Handle rate limiting error
                    if response.status_code == 429:
                        print("Rate limit detected during stats update")
                        retry_after = 300  # Default 5 minutes
                        try:
                            retry_header = response.headers.get("Retry-After")
                            if retry_header:
                                retry_after = int(retry_header)
                        except:
                            pass

                        self.rate_limited_until = current_time + retry_after
                        print(f"Rate limited. Waiting for {retry_after} seconds")
                        response.close()

                        if self.cached_stats:
                            print("Using cached stats due to rate limiting")
                            self.stats_data = self.cached_stats
                            return True
                        return False

                    if response.status_code == 200:
                        try:
                            print("Received valid response from Pi-hole API")
                            response_text = response.text
                            print(f"Response content length: {len(response_text)}")
                            new_stats = ujson.loads(response_text)
                            print("Successfully parsed JSON response")

                            if self._validate_stats_data(new_stats):
                                self.stats_data = new_stats
                                self.cached_stats = new_stats
                                self.last_update = current_time
                                print("Pi-hole stats updated successfully")
                                response.close()
                                # Don't logout if using API token
                                if not self.api_token:
                                    self.logout()  # free session after success
                                return True
                            else:
                                print("Invalid stats data structure received")
                                if self.cached_stats:
                                    print("Using cached stats instead")
                                    self.stats_data = self.cached_stats
                                    self.last_update = current_time
                                    response.close()
                                    return True
                        except ValueError as e:
                            print(f"Invalid JSON in response: {e}")

                    elif response.status_code == 401:
                        print("Session expired, re-authenticating...")
                        response.close()
                        self.session_sid = None
                        self.csrf_token = None
                        if not self.api_token and not self.authenticate():
                            break
                        else:
                            continue
                    else:
                        print(f"Error fetching Pi-hole stats: {response.status_code}")

                    response.close()

                    if attempt < self.max_retries - 1:
                        # Just retry the same endpoint
                        retry_delay = self.base_retry_delay * (2**attempt)
                        print(
                            f"Retrying stats update in {retry_delay} seconds... (Attempt {attempt+1}/{self.max_retries})"
                        )
                        time.sleep(retry_delay)
                    else:
                        if self.cached_stats:
                            print("Using cached stats after all retries failed")
                            self.stats_data = self.cached_stats
                            return True

                except Exception as e:
                    print(
                        f"Error updating Pi-hole stats (attempt {attempt+1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        retry_delay = self.base_retry_delay * (2**attempt)
                        time.sleep(retry_delay)

            return False

        return True

    def _validate_stats_data(self, data):
        """Validate Pi-hole stats data structure, supporting various formats"""
        if not isinstance(data, dict):
            print("Data is not a dictionary")
            return False

        print(f"Received data keys: {', '.join(data.keys())}")

        if (
            "queries" in data
            and isinstance(data["queries"], dict)
            and "total" in data["queries"]
            and "blocked" in data["queries"]
        ):
            print("Detected Pi-hole data structure with direct queries object")
            return True

        # Pi-hole v6 structure
        if "gravity" in data and "dns" in data:
            print("Detected Pi-hole v6 data structure")
            has_queries = (
                isinstance(data.get("dns"), dict)
                and "queries" in data["dns"]
                and "blocked" in data["dns"]
            )
            has_status = "status" in data
            return has_queries and has_status

        # Pi-hole v5 structure (backward compatibility)
        else:
            print("Checking for Pi-hole v5 data structure")
            has_queries = (
                isinstance(data.get("queries"), dict)
                and "blocked" in data["queries"]
                and "total" in data["queries"]
            )
            has_status = "status" in data
            return has_queries and has_status

    def get_queries_total(self):
        try:
            if not self.stats_data:
                return 0

            # Direct queries structure
            if "queries" in self.stats_data and "total" in self.stats_data["queries"]:
                return self.stats_data["queries"]["total"]

            # Pi-hole v6 structure
            if "dns" in self.stats_data and "queries" in self.stats_data["dns"]:
                return self.stats_data["dns"]["queries"]

            # Pi-hole v5 structure
            elif "queries" in self.stats_data and "total" in self.stats_data["queries"]:
                return self.stats_data["queries"].get("total", 0)

            return 0
        except Exception as e:
            print(f"Error retrieving total queries: {e}")
            return 0

    def get_queries_blocked(self):
        try:
            if not self.stats_data:
                return 0

            # Direct queries structure
            if "queries" in self.stats_data and "blocked" in self.stats_data["queries"]:
                return self.stats_data["queries"]["blocked"]

            # Pi-hole v6 structure
            if "dns" in self.stats_data and "blocked" in self.stats_data["dns"]:
                return self.stats_data["dns"]["blocked"]

            # Pi-hole v5 structure
            elif (
                "queries" in self.stats_data and "blocked" in self.stats_data["queries"]
            ):
                return self.stats_data["queries"].get("blocked", 0)

            return 0
        except Exception as e:
            print(f"Error retrieving blocked queries: {e}")
            return 0

    def get_status(self):
        try:
            if not self.stats_data:
                return "unknown"

            if "status" in self.stats_data:
                status_data = self.stats_data["status"]
                if isinstance(status_data, dict):
                    return status_data.get("state", "unknown")
                elif isinstance(status_data, str):
                    return status_data

            # Pi-hole v6 might have a different status field
            if "core" in self.stats_data and "status" in self.stats_data["core"]:
                return str(self.stats_data["core"]["status"]).lower()

            return "unknown"
        except Exception as e:
            print(f"Error retrieving status: {e}")
            return "unknown"

    def format_number(self, num):
        if num is None:
            return "0"

        try:
            num = float(num)
            if num >= 1000000:
                return f"{num/1000000:.1f}M"
            elif num >= 1000:
                return f"{num/1000:.1f}k"
            else:
                return str(int(num))
        except:
            return "0"

    def get_stats_for_display(self):
        if not self.stats_data:
            if self.cached_stats:
                print("Using cached stats for display")
                self.stats_data = self.cached_stats
            else:
                return ("Loading", "...")

        total = self.get_queries_total()
        blocked = self.get_queries_blocked()

        total_formatted = self.format_number(total)
        blocked_formatted = self.format_number(blocked)

        return (f"DNS Queries: {total_formatted}", f"Blocked Ads: {blocked_formatted}")
