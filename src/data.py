from __future__ import annotations
import sqlite3, os
import aiogram
import pyquoks.data, pyquoks.utils
import models


# Abstract classes
class IDatabaseManager(sqlite3.Connection):  # TODO: по готовности перенести в `pyquoks`
    def __init__(self, name: str, sql: str, folder_name: str = "db") -> None:
        os.makedirs(pyquoks.utils.get_path(folder_name, only_abspath=True), exist_ok=True)
        super().__init__(database=f"db/{name}.db", check_same_thread=False)

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

    class TestConfig(pyquoks.data.IConfigProvider.IConfig):  # TODO: удалить после интеграции базы данных (DATABASE)
        _SECTION = "Test"
        balance: int

    _CONFIG_VALUES = {
        "Settings":
            {
                "admin_list": list,
                "bot_token": str,
                "file_logging": bool,
                "skip_updates": bool,
                "provider_token": str,
            },
        "Test":
            {
                "balance": int,
            },
    }
    _CONFIG_OBJECTS = {
        "settings": SettingsConfig,
        "test": TestConfig,
    }
    settings: SettingsConfig
    test: TestConfig


class UsersDatabaseManager(IDatabaseManager):
    def __init__(self) -> None:
        super().__init__(
            name="users",
            sql="""
            CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY NOT NULL,
            tg_username TEXT,
            ref_id INTEGER
            )
            """
        )

    def add_user(self, tg_id: int, tg_username: str = None, ref_id: int = None) -> None:
        self.db_cursor.execute(
            """
            INSERT OR IGNORE INTO users (
            tg_id,
            tg_username,
            ref_id
            )
            VALUES (?, ?, ?)
            """,
            (tg_id, tg_username, ref_id),
        )
        self.commit()


class LoggerService(pyquoks.data.LoggerService):
    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - «{interaction}»")
