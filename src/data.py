from __future__ import annotations
import sqlite3, os
import aiogram
import pyquoks.data, pyquoks.utils
import models


# Abstract classes
class IDatabaseManager:  # TODO: по готовности перенести в `pyquoks`
    class IDatabase(sqlite3.Connection):
        _NAME: str = None
        _SQL: str = None
        _PATH: str = "{0}.db"

        def __init__(self, parent: IDatabaseManager = None) -> None:
            os.makedirs(parent._PATH, exist_ok=True)
            self._PATH = parent._PATH + self._PATH
            super().__init__(
                database=self._PATH.format(self._NAME),
                check_same_thread=False,
            )

            self._cursor = self.cursor()
            self.db_cursor.execute(self._SQL)
            self.commit()

        @property
        def db_cursor(self) -> sqlite3.Cursor:
            return self._cursor

    _PATH: str
    _DATABASE_OBJECTS: dict[str, type]

    def __init__(self) -> None:
        for k, v in self._DATABASE_OBJECTS.items():
            setattr(self, k, v(self))

    def close_all(self) -> None:
        for i in self._DATABASE_OBJECTS.keys():
            getattr(self, i).close()


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


class DatabaseManager(IDatabaseManager):
    class UsersDatabase(IDatabaseManager.IDatabase):
        _NAME = "users"
        _SQL = """
        CREATE TABLE IF NOT EXISTS users (
        tg_id INTEGER PRIMARY KEY NOT NULL,
        tg_username TEXT,
        balance INTEGER NOT NULL,
        ref_id INTEGER
        )
        """

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
            self.commit()

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

    _PATH = pyquoks.utils.get_path("db/")
    _DATABASE_OBJECTS = {
        "users": UsersDatabase,
    }
    users: UsersDatabase


class LoggerService(pyquoks.data.LoggerService):
    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - \"{interaction}\"")
