
from datetime import datetime, timezone

def get_time_impl(fmt: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    iso = now.isoformat().replace("+00:00", "Z")
    data = {"iso": iso}
    if fmt:
        try:
            data["formatted"] = now.strftime(fmt)
        except Exception:
            # If format is invalid, just omit formatted (schema does not require it)
            pass
    return data
