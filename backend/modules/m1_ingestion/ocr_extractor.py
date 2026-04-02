import pytesseract
import structlog
from pathlib import Path
from PIL import Image

log = structlog.get_logger()

class OCRExtractor:
    """
    Extrai texto de documentos digitalizados usando Tesseract.
    Suporta português e inglês.
    """

    SUPPORTED_TYPES = {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".pdf"}

    def extract(self, file_path: Path) -> str | None:
        if file_path.suffix.lower() not in self.SUPPORTED_TYPES:
            return None

        try:
            img = Image.open(file_path)
            # Tesseract: português primeiro, inglês como fallback
            text = pytesseract.image_to_string(img, lang="por+eng")
            cleaned = text.strip()
            if len(cleaned) < 10:
                return None
            log.info("ocr_success", file=file_path.name, chars=len(cleaned))
            return cleaned
        except Exception as e:
            log.error("ocr_error", file=str(file_path), error=str(e))
            return None
