"""Unit tests for the M1 EXIF extractor (exifread-based).

These tests exercise the parsing logic — date strings and the
degrees/minutes/seconds → decimal conversion, including the N/S/E/W sign —
without needing a real photo with embedded EXIF, by feeding the helpers the
same shapes that ``exifread`` produces.
"""

from datetime import datetime

from backend.modules.m1_ingestion.exif_extractor import ExifExtractor


class _Ratio:
    def __init__(self, num, den=1):
        self.num, self.den = num, den


class _Coord:
    def __init__(self, values):
        self.values = values


class _Tag:
    def __init__(self, s):
        self._s = s

    def __str__(self):
        return self._s


ex = ExifExtractor()


def test_parse_date_from_datetimeoriginal():
    tags = {"EXIF DateTimeOriginal": _Tag("2014:07:15 18:30:00")}
    assert ex._parse_date(tags) == datetime(2014, 7, 15, 18, 30, 0)


def test_parse_date_missing_returns_none():
    assert ex._parse_date({}) is None


def test_parse_date_invalid_returns_none():
    assert ex._parse_date({"Image DateTime": _Tag("not-a-date")}) is None


def test_gps_north_is_positive():
    tags = {
        "GPS GPSLatitude": _Coord([_Ratio(38), _Ratio(43), _Ratio(0)]),
        "GPS GPSLatitudeRef": _Tag("N"),
    }
    lat = ex._parse_gps(tags, "GPS GPSLatitude", "GPS GPSLatitudeRef", "S")
    assert abs(lat - 38.7167) < 1e-3


def test_gps_west_is_negative():
    tags = {
        "GPS GPSLongitude": _Coord([_Ratio(9), _Ratio(8), _Ratio(0)]),
        "GPS GPSLongitudeRef": _Tag("W"),
    }
    lon = ex._parse_gps(tags, "GPS GPSLongitude", "GPS GPSLongitudeRef", "W")
    assert abs(lon - (-9.1333)) < 1e-3


def test_gps_south_is_negative():
    tags = {
        "GPS GPSLatitude": _Coord([_Ratio(33), _Ratio(52), _Ratio(0)]),
        "GPS GPSLatitudeRef": _Tag("S"),
    }
    lat = ex._parse_gps(tags, "GPS GPSLatitude", "GPS GPSLatitudeRef", "S")
    assert lat < 0


def test_gps_missing_returns_none():
    assert ex._parse_gps({}, "GPS GPSLatitude", "GPS GPSLatitudeRef", "S") is None


def test_gps_fractional_ratio():
    # 26 minutes 30 seconds with ratio denominators (e.g. 30/1).
    tags = {
        "GPS GPSLatitude": _Coord([_Ratio(40), _Ratio(26), _Ratio(60, 2)]),
        "GPS GPSLatitudeRef": _Tag("N"),
    }
    lat = ex._parse_gps(tags, "GPS GPSLatitude", "GPS GPSLatitudeRef", "S")
    # 40 + 26/60 + 30/3600
    assert abs(lat - (40 + 26 / 60 + 30 / 3600)) < 1e-6
