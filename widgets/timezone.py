"""Minimal POSIX TZ rule engine, sized for MicroPython.

Handles the subset of the POSIX TZ format that real zones actually use:

    EET-2EEST,M3.5.0/3,M10.5.0/4     Europe/Kyiv
    CET-1CEST,M3.5.0,M10.5.0/3       Europe/Berlin
    EST5EDT,M3.2.0,M11.1.0           America/New_York
    AEST-10AEDT,M10.1.0,M4.1.0/3     Australia/Sydney - DST spans the new year
    IST-5:30                         Asia/Kolkata - no DST, sub-hour offset
    <+0330>-3:30                     Asia/Tehran - numeric zone name

Only the Mm.n.d transition form is supported; the Jn and n day-of-year forms
raise ValueError rather than being silently mishandled.

POSIX offsets are west-positive - "EET-2" means UTC+2 - which reads backwards
often enough that they are negated on parse and stored as a value that can
simply be added to UTC.
"""

import time

_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def _is_leap(y):
    return (y % 4 == 0 and y % 100 != 0) or y % 400 == 0


def _days_from_civil(y, m, d):
    """Days between 1970-01-01 and the given date. Integer only, no calendar lib."""
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


# MicroPython counts from 2000-01-01 on the baremetal ports and from
# 1970-01-01 on unix/CPython, so anchor to whatever this runtime uses.
_e = time.gmtime(0)
_EPOCH_DAYS = _days_from_civil(_e[0], _e[1], _e[2])


def _secs(y, mo, d, h, mi, s):
    """Seconds from this runtime's epoch to the given UTC civil time."""
    return (_days_from_civil(y, mo, d) - _EPOCH_DAYS) * 86400 + h * 3600 + mi * 60 + s


def _parse_offset(s, i, default=None):
    """Parse [+|-]hh[:mm[:ss]] at s[i:]. Returns (seconds, next index)."""
    sign = 1
    if i < len(s) and s[i] in "+-":
        sign = -1 if s[i] == "-" else 1
        i += 1

    parts = []
    while len(parts) < 3:
        start = i
        while i < len(s) and s[i].isdigit():
            i += 1
        if i == start:
            break
        parts.append(int(s[start:i]))
        if i < len(s) and s[i] == ":":
            i += 1
        else:
            break

    if not parts:
        if default is None:
            raise ValueError(f"missing offset at {s[i:]!r}")
        return default, i

    while len(parts) < 3:
        parts.append(0)
    return sign * (parts[0] * 3600 + parts[1] * 60 + parts[2]), i


def _parse_name(s, i):
    """Parse a zone abbreviation, either bare letters or <...>."""
    if i < len(s) and s[i] == "<":
        end = s.find(">", i)
        if end < 0:
            raise ValueError(f"unterminated zone name in {s!r}")
        return s[i + 1 : end], end + 1
    start = i
    while i < len(s) and s[i].isalpha():
        i += 1
    return s[start:i], i


def _parse_rule(s):
    """Parse Mm.n.d[/time] into (month, week, weekday, seconds into the day)."""
    if not s or s[0] != "M":
        raise ValueError(f"only Mm.n.d transitions are supported, got {s!r}")

    date, _, at = s.partition("/")
    fields = date[1:].split(".")
    if len(fields) != 3:
        raise ValueError(f"malformed transition rule {s!r}")
    month, week, weekday = (int(f) for f in fields)

    if not 1 <= month <= 12:
        raise ValueError(f"month out of range in {s!r}")
    if not 1 <= week <= 5:
        raise ValueError(f"week out of range in {s!r}")
    if not 0 <= weekday <= 6:
        raise ValueError(f"weekday out of range in {s!r}")

    # POSIX defaults the changeover to 02:00 local when no time is given
    secs = _parse_offset(at, 0)[0] if at else 7200
    return (month, week, weekday, secs)


def _rule_instant(rule, year, utc_offset):
    """The UTC moment a transition rule fires in the given year.

    Rule times are wall-clock local, so the offset in force just before the
    transition has to be subtracted to get back to UTC.
    """
    month, week, weekday, secs = rule

    first = _days_from_civil(year, month, 1)
    first_weekday = (first + 4) % 7  # 0 = Sunday, matching the POSIX 'd' field
    dom = 1 + (weekday - first_weekday) % 7 + (week - 1) * 7

    month_days = _MONTH_DAYS[month - 1] + (1 if month == 2 and _is_leap(year) else 0)
    while dom > month_days:  # week 5 means "the last one", not "the fifth"
        dom -= 7

    return _secs(year, month, dom, 0, 0, 0) + secs - utc_offset


class Timezone:
    """A parsed POSIX TZ string, or a plain fixed offset when tz is omitted."""

    def __init__(self, tz=None, offset_hours=0):
        if tz:
            self._parse(tz)
            return

        self.std_name = ""
        self.dst_name = ""
        self.std_offset = int(offset_hours * 3600)
        self.dst_offset = self.std_offset
        self.start = None
        self.end = None

    def _parse(self, tz):
        self.std_name, i = _parse_name(tz, 0)
        if not self.std_name:
            raise ValueError(f"missing zone name in {tz!r}")

        posix_offset, i = _parse_offset(tz, i, default=0)
        self.std_offset = -posix_offset

        self.dst_name, i = _parse_name(tz, i)
        self.dst_offset = self.std_offset
        self.start = None
        self.end = None
        if not self.dst_name:
            return

        if i < len(tz) and tz[i] != ",":
            posix_offset, i = _parse_offset(tz, i)
            self.dst_offset = -posix_offset
        else:
            self.dst_offset = self.std_offset + 3600  # POSIX default

        if i >= len(tz) or tz[i] != ",":
            raise ValueError(f"DST named but no transition rules in {tz!r}")

        rules = tz[i + 1 :].split(",")
        if len(rules) != 2:
            raise ValueError(f"expected two transition rules in {tz!r}")
        self.start = _parse_rule(rules[0])
        self.end = _parse_rule(rules[1])

    def offset(self, utc_secs):
        """Seconds to add to UTC at this moment, DST included."""
        if self.start is None:
            return self.std_offset

        year = time.gmtime(utc_secs)[0]
        start = _rule_instant(self.start, year, self.std_offset)
        end = _rule_instant(self.end, year, self.dst_offset)

        if start <= end:
            in_dst = start <= utc_secs < end
        else:
            # Southern hemisphere: the DST period wraps around the new year
            in_dst = utc_secs >= start or utc_secs < end

        return self.dst_offset if in_dst else self.std_offset

    def name(self, utc_secs=None):
        """The abbreviation in force, e.g. EET or EEST. Empty for a fixed offset."""
        if utc_secs is None:
            utc_secs = time.time()
        if self.start is not None and self.offset(utc_secs) == self.dst_offset:
            return self.dst_name
        return self.std_name

    def localtime(self, utc_secs=None):
        """Local time tuple, same shape as time.localtime()."""
        if utc_secs is None:
            utc_secs = time.time()
        return time.gmtime(utc_secs + self.offset(utc_secs))
