from __future__ import annotations
import datetime


def get_formatted_timestamp(timestamp: float) -> str:
    return datetime.datetime.fromtimestamp(timestamp).strftime("%d.%m.%y %H:%M:%S")
