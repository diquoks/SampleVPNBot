from __future__ import annotations
import sys, os


def get_path(relative_path: str, only_abspath: bool = False) -> str:
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.abspath(".")
    finally:
        if only_abspath:
            base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
