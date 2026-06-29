import structlog
from pathlib import Path
from datetime import datetime
from typing import Optional

import exifread

log = structlog.get_logger()


class ExifExtractor:
    """
    Extrai metadados EXIF de fotografias com a biblioteca ``exifread``
    (puro Python, sem dependências de sistema — funciona de forma idêntica
    em ambiente local e na nuvem, ao contrário do ExifTool, que exigia um
    binário externo ausente na imagem de produção).

    Obtém: data de captura, coordenadas GPS, marca/modelo da câmara e os
    metadados em bruto. Qualquer falha degrada graciosamente para ``{}``.
    """

    def extract(self, file_path: Path) -> dict:
        try:
            with open(file_path, "rb") as f:
                # details=False evita parsing de MakerNote/thumbnail (mais
                # rápido e robusto; só precisamos de data, GPS e câmara).
                tags = exifread.process_file(f, details=False)
        except Exception as e:
            log.error("exif_error", file=str(file_path), error=str(e))
            return {}

        if not tags:
            return {}

        return {
            "date_taken":    self._parse_date(tags),
            "latitude":      self._parse_gps(tags, "GPS GPSLatitude", "GPS GPSLatitudeRef", "S"),
            "longitude":     self._parse_gps(tags, "GPS GPSLongitude", "GPS GPSLongitudeRef", "W"),
            "camera_make":   self._clean(tags.get("Image Make")),
            "camera_model":  self._clean(tags.get("Image Model")),
            # Metadados em bruto, normalizados para strings (coluna JSON).
            "raw_exif":      {k: str(v) for k, v in tags.items()},
        }

    @staticmethod
    def _clean(tag) -> Optional[str]:
        if tag is None:
            return None
        val = str(tag).strip()
        return val or None

    def _parse_date(self, tags) -> Optional[datetime]:
        for field in ("EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime"):
            tag = tags.get(field)
            if not tag:
                continue
            try:
                return datetime.strptime(str(tag)[:19], "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
        return None

    def _parse_gps(self, tags, coord_key, ref_key, negative_ref) -> Optional[float]:
        coord = tags.get(coord_key)
        if coord is None:
            return None
        try:
            # exifread guarda DMS como lista de Ratio: [graus, minutos, segundos].
            d, m, s = (self._ratio(r) for r in coord.values)
            decimal = d + m / 60.0 + s / 3600.0
            ref = str(tags.get(ref_key, "")).strip().upper()
            return -decimal if ref == negative_ref else decimal
        except Exception:
            return None

    @staticmethod
    def _ratio(r) -> float:
        # Ratio do exifread expõe .num/.den; tolera também int/float simples.
        try:
            return float(r.num) / float(r.den) if r.den else 0.0
        except AttributeError:
            return float(r)
