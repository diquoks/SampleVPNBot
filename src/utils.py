from __future__ import annotations
import datetime


def get_formatted_date(date: float | datetime.datetime) -> str:
    return (date if isinstance(date, datetime.datetime) else datetime.datetime.fromtimestamp(date)).strftime(
        format="%d.%m.%y %H:%M:%S",
    )
