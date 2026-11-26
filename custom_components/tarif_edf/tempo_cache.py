"""Cache of the Tempo colour API answers, one per day."""
from datetime import date, time, timedelta

TEMPO_CODES_KNOWN = (1, 2, 3)


class TempoDayCache:
    """Keeps the answers of the Tempo colour API so it is not called every minute.

    A known colour (codeJour 1 to 3) is kept. An undetermined one (0) is only kept for a day
    after the one it was fetched on, the same day, before the next day's colour is published:
    after that, or once that day has come, it is fetched again.
    """

    def __init__(self, available_at: time) -> None:
        self._available_at = available_at
        self._days: dict[str, tuple[dict, date]] = {}

    def get(self, day: date, today: date, now: time) -> dict | None:
        """Return the cached answer for *day*, or None when it must be fetched again."""
        entry = self._days.get(day.isoformat())
        if entry is None:
            return None
        payload, fetched_on = entry
        code_jour = payload.get("codeJour")
        if code_jour in TEMPO_CODES_KNOWN:
            return payload
        if code_jour == 0 and day > fetched_on == today and now < self._available_at:
            return payload
        return None

    def put(self, payload: dict, today: date) -> None:
        """Store an answer of the API, fetched on *today*, replacing the older one for its day."""
        if "dateJour" not in payload:
            return
        self._days[payload["dateJour"]] = (payload, today)
        oldest = (today - timedelta(days=1)).isoformat()
        for key in [key for key in self._days if key < oldest]:
            del self._days[key]
