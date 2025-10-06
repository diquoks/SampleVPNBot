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
            self._db_cursor.execute(self._SQL)
            self.commit()

        @property
        def _db_cursor(self) -> sqlite3.Cursor:
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
        debug: bool
        file_logging: bool
        skip_updates: bool
        provider_token: str

    _CONFIG_VALUES = {
        "Settings":
            {
                "admin_list": list,
                "bot_token": str,
                "debug": bool,
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
    class SubscriptionsDatabase(IDatabaseManager.IDatabase):
        _NAME = "subscriptions"
        _SQL = f"""
        CREATE TABLE IF NOT EXISTS {_NAME} (
        subscription_id INTEGER PRIMARY KEY NOT NULL,
        tg_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        payment_amount INTEGER NOT NULL,
        date_subscribed INTEGER NOT NULL,
        date_expires INTEGER NOT NULL
        )
        """

        def add_subscription(
                self,
                tg_id: int,
                plan_id: int,
                payment_amount: int,
                date_subscribed: int,
                date_expires: int,
        ) -> None:
            self._db_cursor.execute(
                f"""
                INSERT INTO {self._NAME} (
                tg_id,
                plan_id,
                payment_amount,
                date_subscribed,
                date_expires
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (tg_id, plan_id, payment_amount, date_subscribed, date_expires),
            )
            self.commit()

        def get_subscription(self, subscription_id: int) -> models.SubscriptionValues | None:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE subscription_id == ?
                """,
                (subscription_id,),
            )
            result = self._db_cursor.fetchone()
            if result:
                return models.SubscriptionValues(
                    **dict(
                        zip(
                            [
                                "subscription_id",
                                "tg_id",
                                "plan_id",
                                "payment_amount",
                                "date_subscribed",
                                "date_expires",
                            ],
                            result,
                        ),
                    ),
                )
            else:
                return None

        def get_user_subscriptions(self, tg_id: int) -> list[models.SubscriptionValues] | None:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )
            results = self._db_cursor.fetchall()
            if results:
                return [
                    models.SubscriptionValues(
                        **dict(
                            zip(
                                [
                                    "subscription_id",
                                    "tg_id",
                                    "plan_id",
                                    "payment_amount",
                                    "date_subscribed",
                                    "date_expires",
                                ],
                                i,
                            ),
                        ),
                    ) for i in results
                ]
            else:
                return None

    class UsersDatabase(IDatabaseManager.IDatabase):
        _NAME = "users"
        _SQL = f"""
        CREATE TABLE IF NOT EXISTS {_NAME} (
        tg_id INTEGER PRIMARY KEY NOT NULL,
        tg_username TEXT,
        balance INTEGER NOT NULL,
        referrer_id INTEGER
        )
        """

        def add_user(self, tg_id: int, tg_username: str | None, balance: int, referrer_id: int | None) -> None:
            self._db_cursor.execute(
                f"""
                INSERT OR IGNORE INTO {self._NAME} (
                tg_id,
                tg_username,
                balance,
                referrer_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (tg_id, tg_username, balance, referrer_id),
            )
            self.commit()

        def get_user(self, tg_id: int) -> models.UserValues | None:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )
            result = self._db_cursor.fetchone()
            if result:
                return models.UserValues(
                    **dict(
                        zip(
                            [
                                "tg_id",
                                "tg_username",
                                "balance",
                                "referrer_id",
                            ],
                            result,
                        ),
                    ),
                )
            else:
                return None

        def edit_balance(self, tg_id: int, balance: int) -> None:
            self._db_cursor.execute(
                f"""
                UPDATE {self._NAME} SET balance = ? WHERE tg_id == ?
                """,
                (balance, tg_id),
            )
            self.commit()

        def add_balance(self, tg_id: int, amount: int) -> None:
            current_user = self.get_user(tg_id)
            self.edit_balance(tg_id, current_user.balance + amount)

        def reduce_balance(self, tg_id: int, amount: int) -> None:
            current_user = self.get_user(tg_id)
            self.edit_balance(tg_id, current_user.balance - amount)

        def get_ref_count(self, tg_id: int) -> int:
            self._db_cursor.execute(
                f"""
                SELECT COUNT(*) from {self._NAME} WHERE referrer_id == ?
                """,
                (tg_id,),
            )
            return self._db_cursor.fetchone()[0]

    _PATH = pyquoks.utils.get_path("db/")
    _DATABASE_OBJECTS = {
        "subscriptions": SubscriptionsDatabase,
        "users": UsersDatabase,
    }
    subscriptions: SubscriptionsDatabase
    users: UsersDatabase


class LoggerService(pyquoks.data.LoggerService):
    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - \"{interaction}\"")
