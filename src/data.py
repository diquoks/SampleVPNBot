from __future__ import annotations
import datetime
import aiogram
import pyquoks.data, pyquoks.utils
import models


# region Constants

class Constants:
    DAYS_IN_MONTH = 30
    ELEMENTS_PER_PAGE = 5
    ELEMENTS_PER_ROW = 2
    FIRST_PAGE_ID = 0
    MINIMUM_PLAN = models.PlansType.MONTH


# endregion

# region Providers

class DataProvider(pyquoks.data.IDataProvider):
    _DATA_VALUES = {
        "plans": models.PlansContainer,
        "referrers": models.ReferrersContainer,
    }
    plans: models.PlansContainer
    referrers: models.ReferrersContainer


class ConfigProvider(pyquoks.data.IConfigProvider):
    class PaymentsConfig(pyquoks.data.IConfigProvider.IConfig):
        _SECTION = "Payments"
        currency: str
        max_balance: int
        max_subscriptions: int
        multiplier: int
        provider_token: str

    class SettingsConfig(pyquoks.data.IConfigProvider.IConfig):
        _SECTION = "Settings"
        admin_list: list[int]
        bot_token: str
        debug_logging: bool
        file_logging: bool
        skip_updates: bool

    _CONFIG_VALUES = {
        "Payments":
            {
                "currency": str,
                "max_balance": int,
                "max_subscriptions": int,
                "multiplier": int,
                "provider_token": str
            },
        "Settings":
            {
                "admin_list": list,
                "bot_token": str,
                "debug_logging": bool,
                "file_logging": bool,
                "skip_updates": bool,
            },
    }
    _CONFIG_OBJECTS = {
        "payments": PaymentsConfig,
        "settings": SettingsConfig,
    }
    payments: PaymentsConfig
    settings: SettingsConfig


# endregion

# region Managers

class DatabaseManager(pyquoks.data.IDatabaseManager):
    class PaymentsDatabase(pyquoks.data.IDatabaseManager.IDatabase):
        _NAME = "payments"
        _SQL = f"""
        CREATE TABLE IF NOT EXISTS {_NAME} (
        payment_id INTEGER PRIMARY KEY NOT NULL,
        tg_id INTEGER NOT NULL,
        payment_amount INTEGER NOT NULL,
        payment_currency TEXT NOT NULL,
        provider_payment_id TEXT,
        payment_payload TEXT NOT NULL,
        payment_date INTEGER NOT NULL
        )
        """

        def add_payment(
                self,
                tg_id: int,
                payment_amount: int,
                payment_currency: str,
                provider_payment_id: str | None,
                payment_payload: str,
                payment_date: int,
        ) -> None:
            self._db_cursor.execute(
                f"""
                INSERT INTO {self._NAME} (
                tg_id,
                payment_amount,
                payment_currency,
                provider_payment_id,
                payment_payload,
                payment_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tg_id, payment_amount, payment_currency, provider_payment_id, payment_payload, payment_date),
            )
            self.commit()

        def get_payment(self, payment_id: int) -> models.PaymentValues | None:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE payment_id == ?
                """,
                (payment_id,),
            )
            result = self._db_cursor.fetchone()
            if result:
                return models.PaymentValues(
                    **dict(
                        zip(
                            [
                                "payment_id",
                                "tg_id",
                                "payment_amount",
                                "payment_currency",
                                "provider_payment_id",
                                "payment_payload",
                                "payment_date",
                            ],
                            result,
                        ),
                    ),
                )
            else:
                return None

        def get_all_payments(self) -> list[models.PaymentValues] | None:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME}
                """,
            )
            results = self._db_cursor.fetchall()
            return [
                models.PaymentValues(
                    **dict(
                        zip(
                            [
                                "payment_id",
                                "tg_id",
                                "payment_amount",
                                "payment_currency",
                                "provider_payment_id",
                                "payment_payload",
                                "payment_date",
                            ],
                            i,
                        ),
                    ),
                ) for i in results
            ]

        def get_user_payments(self, tg_id: int) -> list[models.PaymentValues]:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )
            results = self._db_cursor.fetchall()
            return [
                models.PaymentValues(
                    **dict(
                        zip(
                            [
                                "payment_id",
                                "tg_id",
                                "payment_amount",
                                "payment_currency",
                                "provider_payment_id",
                                "payment_payload",
                                "payment_date",
                            ],
                            i,
                        ),
                    ),
                ) for i in results
            ]

        def check_payments(self, tg_id: int) -> bool:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )
            return bool(self._db_cursor.fetchone())

    class SubscriptionsDatabase(pyquoks.data.IDatabaseManager.IDatabase):
        _NAME = "subscriptions"
        _SQL = f"""
        CREATE TABLE IF NOT EXISTS {_NAME} (
        subscription_id INTEGER PRIMARY KEY NOT NULL,
        tg_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        payment_amount INTEGER NOT NULL,
        subscribed_date INTEGER NOT NULL,
        expires_date INTEGER NOT NULL,
        is_active INTEGER NOT NULL
        )
        """

        def add_subscription(
                self,
                tg_id: int,
                plan_id: int,
                payment_amount: int,
                subscribed_date: int,
                expires_date: int,
                is_active: int,
        ) -> None:
            self._db_cursor.execute(
                f"""
                INSERT INTO {self._NAME} (
                tg_id,
                plan_id,
                payment_amount,
                subscribed_date,
                expires_date,
                is_active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tg_id, plan_id, payment_amount, subscribed_date, expires_date, is_active),
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
                                "subscribed_date",
                                "expires_date",
                                "is_active",
                            ],
                            result,
                        ),
                    ),
                )
            else:
                return None

        def get_all_subscriptions(self) -> list[models.SubscriptionValues]:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME}
                """,
            )
            results = self._db_cursor.fetchall()
            return [
                models.SubscriptionValues(
                    **dict(
                        zip(
                            [
                                "subscription_id",
                                "tg_id",
                                "plan_id",
                                "payment_amount",
                                "subscribed_date",
                                "expires_date",
                                "is_active",
                            ],
                            i,
                        ),
                    ),
                ) for i in results
            ]

        def get_user_subscriptions(self, tg_id: int) -> list[models.SubscriptionValues]:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )
            results = self._db_cursor.fetchall()
            return [
                models.SubscriptionValues(
                    **dict(
                        zip(
                            [
                                "subscription_id",
                                "tg_id",
                                "plan_id",
                                "payment_amount",
                                "subscribed_date",
                                "expires_date",
                                "is_active",
                            ],
                            i,
                        ),
                    ),
                ) for i in results
            ]

        def get_user_active_subscriptions(self, tg_id: int) -> list[models.SubscriptionValues]:
            subscriptions = self.get_user_subscriptions(tg_id)
            return list(
                filter(
                    lambda subscription: subscription.expires_date > datetime.datetime.now().timestamp(),
                    subscriptions,
                )
            )

        def edit_expires_date(self, subscription_id: int, expires_date: int) -> None:
            self._db_cursor.execute(
                f"""
                UPDATE {self._NAME} SET expires_date = ? WHERE subscription_id == ?
                """,
                (expires_date, subscription_id),
            )
            self.commit()

        def switch_active(self, subscription_id: int) -> None:
            current_subscription = self.get_subscription(
                subscription_id=subscription_id,
            )

            self._db_cursor.execute(
                f"""
                UPDATE {self._NAME} SET is_active = ? WHERE subscription_id == ?
                """,
                (int(not bool(current_subscription.is_active)), subscription_id),
            )
            self.commit()

    class UsersDatabase(pyquoks.data.IDatabaseManager.IDatabase):
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

        def get_all_users(self) -> list[models.UserValues]:
            self._db_cursor.execute(
                f"""
                SELECT * FROM {self._NAME}
                """,
            )
            results = self._db_cursor.fetchall()
            return [
                models.UserValues(
                    **dict(
                        zip(
                            [
                                "tg_id",
                                "tg_username",
                                "balance",
                                "referrer_id",
                            ],
                            i,
                        ),
                    ),
                ) for i in results
            ]

        def get_ref_count(self, tg_id: int) -> int:
            self._db_cursor.execute(
                f"""
                SELECT COUNT(*) from {self._NAME} WHERE referrer_id == ?
                """,
                (tg_id,),
            )
            return self._db_cursor.fetchone()[0]

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

    _DATABASE_OBJECTS = {
        "payments": PaymentsDatabase,
        "subscriptions": SubscriptionsDatabase,
        "users": UsersDatabase,
    }
    payments: PaymentsDatabase
    subscriptions: SubscriptionsDatabase
    users: UsersDatabase


# endregion

# region Services

class LoggerService(pyquoks.data.LoggerService):
    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - \"{interaction}\"")

# endregion
