import subprocess
import json
import structlog
from pathlib import Path
from datetime import datetime
from typing import Optional

log = structlog.get_logger()

class ExifExtractor:
    """
    Extrai metadados EXIF de fotografias usando ExifTool.
    Obtém: data, GPS, câmara, e todos os metadados em bruto.
    """

    def extract(self, file_path: Path) -> dict:
        try:
            result = subprocess.run(
                ["exiftool", "-json", "-coordFormat", "%.6f", str(file_path)],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                log.warning("exiftool_warning", file=str(file_path), stderr=result.stderr)
                return {}

            data = json.loads(result.stdout)
            raw = data[0] if data else {}

            return {
                "date_taken":    self._parse_date(raw),
                "latitude":      self._parse_gps_lat(raw),
                "longitude":     self._parse_gps_lon(raw),
                "camera_make":   raw.get("Make"),
                "camera_model":  raw.get("Model"),
                "raw_exif":      raw,
            }

        except subprocess.TimeoutExpired:
            log.error("exiftool_timeout", file=str(file_path))
            return {}
        except Exception as e:
            log.error("exiftool_error", file=str(file_path), error=str(e))
            return {}

    def _parse_date(self, raw: dict) -> Optional[datetime]:
        for field in ["DateTimeOriginal", "CreateDate", "ModifyDate", "FileModifyDate"]:
            val = raw.get(field)
            if val:
                for fmt in ["%Y:%m:%d %H:%M:%S", "%Y:%m:%d %H:%M:%S%z"]:
                    try:
                        return datetime.strptime(str(val)[:19], fmt)
                    except ValueError:
                        continue
        return None

    def _parse_gps_lat(self, raw: dict) -> Optional[float]:
        try:
            val = raw.get("GPSLatitude")
            ref = raw.get("GPSLatitudeRef", "N")
            if val is None:
                return None
            lat = float(val)
            return -lat if ref == "S" else lat
        except (ValueError, TypeError):
            return None

    def _parse_gps_lon(self, raw: dict) -> Optional[float]:
        try:
            val = raw.get("GPSLongitude")
            ref = raw.get("GPSLongitudeRef", "E")
            if val is None:
                return None
            lon = float(val)
            return -lon if ref == "W" else lon
        except (ValueError, TypeError):
            return None
