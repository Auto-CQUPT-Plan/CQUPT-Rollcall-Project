import re
import time


def extract_qr_data(raw_data: str) -> str | None:
    """
    Extracts the hex check-in payload from a raw QR code string.
    Validates that the result is exactly 40 hexadecimal characters.
    Returns None if invalid.
    """
    if not raw_data:
        return None

    data = raw_data
    if raw_data.startswith("/j?p="):
        # Match between !3~ and !4~
        match = re.search(r"!3~([a-f0-9]+)!4~", raw_data)
        if match:
            data = match.group(1)
        else:
            # Fallback: if !4~ is missing, take everything after !3~
            match = re.search(r"!3~([a-f0-9]+)", raw_data)
            if match:
                data = match.group(1)

    # Validation: must be exactly 42 hexadecimal characters (10-digit timestamp + 32-digit hash)
    if re.match(r"^[a-f0-9]{42}$", data, re.IGNORECASE):
        try:
            ts = int(data[:10])
            if time.time() - ts <= 15:
                return data
        except Exception:
            pass

    return None
