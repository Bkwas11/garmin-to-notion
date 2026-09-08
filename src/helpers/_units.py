METERS_PER_MILE = 1609.344
KILOMETERS_PER_MILE = 1.609344


def format_duration(total_seconds: float, suffix: str = "") -> str:
    """Format seconds as M:SS, optionally followed by a unit suffix."""
    rounded_seconds = max(0, round(total_seconds))
    minutes, seconds = divmod(rounded_seconds, 60)
    formatted = f"{minutes}:{seconds:02d}"
    return f"{formatted} {suffix}" if suffix else formatted


def format_pace_per_mile(average_speed_mps: float) -> str:
    """Convert an average speed in metres/second to a min/mile pace."""
    if average_speed_mps <= 0:
        return ""
    seconds_per_mile = METERS_PER_MILE / average_speed_mps
    return format_duration(seconds_per_mile, "min/mi")


def format_race_pace_per_mile(total_seconds: float, distance_km: float) -> str:
    """Convert a race time over a kilometre distance to a per-mile pace."""
    if total_seconds <= 0 or distance_km <= 0:
        return ""
    return format_duration(total_seconds * KILOMETERS_PER_MILE / distance_km, "/mi")
