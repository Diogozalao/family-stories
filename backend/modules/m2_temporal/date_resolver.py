import structlog
from datetime import UTC, datetime, timezone
from typing import Optional

log = structlog.get_logger()

class DateResolver:
    MIN_VALID_DATE = datetime(1800, 1, 1)

    def validate_and_fix(self, date: Optional[datetime], source: str = "unknown") -> tuple[Optional[datetime], str]:
        if date is None:
            return None, "sem data"

        # Remove timezone info para comparação simples (ambos naive)
        date_naive = date.replace(tzinfo=None) if date.tzinfo else date
        now = datetime.now(UTC).replace(tzinfo=None)

        # Data anterior a 1800
        if date_naive < self.MIN_VALID_DATE:
            log.warning("date_too_old", date=str(date), source=source)
            return None, f"data inválida (anterior a 1800): {date}"

        # Clássico erro Unix epoch
        if date_naive.year == 1970 and date_naive.month == 1 and date_naive.day == 1:
            log.warning("date_unix_epoch", source=source)
            return None, "data inválida (epoch Unix)"

        # Data no futuro — tolerância de 1 dia para timezone
        tolerance_days = 2
        diff = (date_naive - now).days
        if diff > tolerance_days:
            log.warning("date_in_future", date=str(date), source=source)
            return None, f"data inválida (futuro): {date}"

        return date_naive, "válida"

    def estimate_decade(self, clues: list[str]) -> Optional[str]:
        decade_keywords = {
            "1950": ["anos 50", "anos cinquenta"],
            "1960": ["anos 60", "anos sessenta"],
            "1970": ["anos 70", "anos setenta"],
            "1980": ["anos 80", "anos oitenta", "cassete", "walkman"],
            "1990": ["anos 90", "anos noventa", "cd "],
            "2000": ["anos 2000", "mp3"],
            "2010": ["anos 2010", "instagram"],
        }
        text = " ".join(clues).lower()
        for decade, keywords in decade_keywords.items():
            for kw in keywords:
                if kw in text:
                    return f"{decade}s"
        return None

    def sort_events(self, events: list) -> list:
        def sort_key(e):
            if e.event_date:
                return (0, e.event_date.timestamp())
            return (1, e.id)
        return sorted(events, key=sort_key)
