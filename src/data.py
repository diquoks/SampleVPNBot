from __future__ import annotations
import sqlite3, os
import aiogram
import pyquoks.data, pyquoks.utils
import models


# Abstract classes
class IDatabaseManager(sqlite3.Connection):  # TODO: по готовности перенести в `pyquoks`
    def __init__(self, name: str, sql: str, folder_name: str = "db") -> None:
        os.makedirs(pyquoks.utils.get_path(folder_name, only_abspath=True), exist_ok=True)
        super().__init__(
            database=f"{folder_name}/{name}.db",
            check_same_thread=False,
        )

        self._cursor = self.cursor()
        self.db_cursor.execute(sql)
        self.commit()

    @property
    def db_cursor(self) -> sqlite3.Cursor:
        return self._cursor


# Named classes
class DataProvider(pyquoks.data.IDataProvider):
    _PATH = pyquoks.utils.get_path("data/{0}.json")
    _DATA_VALUES = {
        "plans": models.PlansContainer,
    }
    plans: models.PlansContainer


class ConfigProvider(pyquoks.data.IConfigProvider):
    class SettingsConfig(pyquoks.data.IConfigProvider.IConfig):
        _SECTION = "Settings"
        admin_list: list[int]
        bot_token: str
        file_logging: bool
        skip_updates: bool
        provider_token: str

    _CONFIG_VALUES = {
        "Settings":
            {
                "admin_list": list,
                "bot_token": str,
                "file_logging": bool,
                "skip_updates": bool,
                "provider_token": str,
            },
    }
    _CONFIG_OBJECTS = {
        "settings": SettingsConfig,
    }
    settings: SettingsConfig


class UsersDatabaseManager(IDatabaseManager):
    def __init__(self) -> None:
        super().__init__(
            name="users",
            sql="""
            CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY NOT NULL,
            tg_username TEXT,
            balance INTEGER NOT NULL,
            ref_id INTEGER
            )
            """
        )

    def add_user(self, tg_id: int, tg_username: str | None, balance: int, ref_id: int | None) -> None:
        self.db_cursor.execute(
            """
            INSERT OR IGNORE INTO users (
            tg_id,
            tg_username,
            balance,
            ref_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (tg_id, tg_username, balance, ref_id),
        )
        self.commit()

    def get_user(self, tg_id: int) -> models.UserValues | None:
        self.db_cursor.execute(
            """
            SELECT * FROM users WHERE tg_id == ?
            """,
            (tg_id,),
        )
        result = self.db_cursor.fetchone()
        if result:
            return models.UserValues(**dict(zip(("tg_id", "tg_username", "balance", "ref_id"), result)))
        else:
            return None

    def edit_balance(self, tg_id: int, balance: int) -> None:
        self.db_cursor.execute(
            """
            UPDATE users SET balance = ? WHERE tg_id == ?
            """,
            (balance, tg_id),
        )

    def add_balance(self, tg_id: int, amount: int) -> None:
        current_user = self.get_user(tg_id)
        self.edit_balance(tg_id, current_user.balance + amount)

    def get_ref_count(self, tg_id: int) -> int:
        self.db_cursor.execute(
            """
            SELECT COUNT(*) from users WHERE ref_id == ?
            """,
            (tg_id,),
        )
        return self.db_cursor.fetchone()[0]


class LoggerService(pyquoks.data.LoggerService):
    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - \"{interaction}\"")
