"""Host-side checks for widgets/timezone.py, the one runtime module that is
pure enough to run off the device.

    python3 tests/test_timezone.py

Every case is compared against CPython's own zoneinfo, so this is really a
check that the hand-rolled POSIX TZ rules agree with the system tz database.
"""

import calendar
import sys
import time as real_time
import types
from datetime import datetime
from os.path import abspath, dirname
from zoneinfo import ZoneInfo

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from widgets.timezone import Timezone

ZONES = [
    ("Europe/Kyiv", "EET-2EEST,M3.5.0/3,M10.5.0/4"),
    ("Europe/Berlin", "CET-1CEST,M3.5.0,M10.5.0/3"),
    ("Europe/London", "GMT0BST,M3.5.0/1,M10.5.0/2"),
    ("America/New_York", "EST5EDT,M3.2.0,M11.1.0"),
    ("America/Los_Angeles", "PST8PDT,M3.2.0,M11.1.0"),
    # Southern hemisphere: the DST period wraps around the new year
    ("Australia/Sydney", "AEST-10AEDT,M10.1.0,M4.1.0/3"),
    ("Asia/Kolkata", "IST-5:30"),  # sub-hour offset, no DST
    ("Asia/Tehran", "<+0330>-3:30"),  # numeric zone name
    # Sub-hour offset *and* DST, which breaks most naive implementations
    ("Pacific/Chatham", "<+1245>-12:45<+1345>,M9.5.0/2:45,M4.1.0/3:45"),
    ("UTC", "UTC0"),
]

YEARS = (2024, 2025, 2026, 2027)


def _utc(*t):
    return calendar.timegm(t + (0,) * (9 - len(t)))


def _sample_times(zone):
    """Every 6h across each year, plus every minute either side of a transition."""
    stamps = []
    for year in YEARS:
        start, end = _utc(year, 1, 1), _utc(year + 1, 1, 1)
        stamps.extend(range(start, end, 6 * 3600))
        previous = None
        for t in range(start, end, 3600):
            current = datetime.fromtimestamp(t, zone).utcoffset()
            if previous is not None and current != previous:
                stamps.extend(range(t - 7200, t + 7200, 60))
            previous = current
    return stamps


def test_against_zoneinfo():
    failures = 0
    total = 0
    for zone_name, tz_string in ZONES:
        zone = ZoneInfo(zone_name)
        tz = Timezone(tz_string)
        bad = 0

        for t in _sample_times(zone):
            total += 1
            expected = datetime.fromtimestamp(t, zone)
            want = int(expected.utcoffset().total_seconds())
            got = tz.offset(t)
            if want != got:
                bad += 1
                if bad <= 2:
                    print(f"  offset {expected}: want {want}, got {got}")
                continue

            tt = tz.localtime(t)
            fields = (
                expected.year,
                expected.month,
                expected.day,
                expected.hour,
                expected.minute,
                expected.second,
                expected.weekday(),
            )
            if tuple(tt[:7]) != fields:
                bad += 1
                if bad <= 2:
                    print(f"  tuple {expected}: want {fields}, got {tuple(tt[:7])}")

        failures += bad
        print(f"{'ok  ' if bad == 0 else 'FAIL'} {zone_name:22s} {tz_string}")

    print(f"{total} comparisons against zoneinfo")
    assert failures == 0, f"{failures} mismatches"


def test_epoch_independence():
    """MicroPython counts from 2000-01-01 on the esp32 but 1970-01-01 here, and
    the module is supposed to work that out at import time."""
    shift = 946684800

    fake = types.ModuleType("time")
    fake.gmtime = lambda secs=0: real_time.gmtime(secs + shift)
    fake.time = lambda: real_time.time() - shift

    saved = sys.modules.pop("widgets.timezone")
    sys.modules["time"] = fake
    try:
        import widgets.timezone as device
    finally:
        sys.modules["time"] = real_time
        sys.modules["widgets.timezone"] = saved

    assert device._e[0] == 2000, device._e

    zone = ZoneInfo("Europe/Kyiv")
    tz = device.Timezone("EET-2EEST,M3.5.0/3,M10.5.0/4")
    for year in YEARS:
        start = _utc(year, 1, 1)
        for t in range(start, start + 365 * 86400, 3607):
            want = int(datetime.fromtimestamp(t, zone).utcoffset().total_seconds())
            assert tz.offset(t - shift) == want, (t, want, tz.offset(t - shift))
    print("ok   epoch independence (2000-01-01 epoch behaves like 1970-01-01)")


def test_fixed_offset():
    for hours, seconds in ((0, 0), (3, 10800), (5.5, 19800), (-8, -28800)):
        assert Timezone(offset_hours=hours).offset(0) == seconds
    print("ok   fixed offsets, fractional included")


def test_rejects_malformed():
    for bad in (
        "EET-2EEST,J89,J302",  # Julian day form, deliberately unsupported
        "EET-2EEST",  # DST named with no rules
        "EET-2EEST,M3.5.0",  # only one rule
        "-2",  # no zone name
        "EET-2EEST,M13.5.0/3,M10.5.0/4",  # month out of range
        "EET-2EEST,M3.9.0/3,M10.5.0/4",  # week out of range
    ):
        try:
            Timezone(bad)
        except ValueError:
            continue
        raise AssertionError(f"accepted malformed TZ {bad!r}")
    print("ok   malformed TZ strings rejected")


if __name__ == "__main__":
    test_against_zoneinfo()
    test_epoch_independence()
    test_fixed_offset()
    test_rejects_malformed()
    print("\nAll timezone checks passed")
