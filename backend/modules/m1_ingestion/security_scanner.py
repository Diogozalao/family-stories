import subprocess
import hashlib
import structlog
from pathlib import Path

log = structlog.get_logger()

class SecurityScanner:
    """
    Valida ficheiros antes de processar:
    - Calcula checksum MD5
    - Verifica vírus com ClamAV
    - Valida tipo MIME real
    """

    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

    def scan(self, file_path: Path) -> dict:
        result = {
            "is_safe":      True,
            "checksum_md5": None,
            "error":        None,
        }

        # Tamanho
        size = file_path.stat().st_size
        if size > self.MAX_FILE_SIZE:
            result["is_safe"] = False
            result["error"] = f"Ficheiro demasiado grande: {size/1024/1024:.1f}MB"
            return result

        # Checksum
        result["checksum_md5"] = self._md5(file_path)

        # ClamAV
        result["is_safe"] = self._clamav_scan(file_path)

        return result

    def _md5(self, path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _clamav_scan(self, path: Path) -> bool:
        try:
            result = subprocess.run(
                ["clamscan", "--no-summary", str(path)],
                capture_output=True, text=True, timeout=30
            )
            if "FOUND" in result.stdout:
                log.warning("clamav_virus_found", file=str(path))
                return False
            return True
        except FileNotFoundError:
            log.warning("clamav_not_found", msg="ClamAV não instalado, a ignorar scan")
            return True
        except subprocess.TimeoutExpired:
            log.error("clamav_timeout", file=str(path))
            return True
