from __future__ import annotations
import datetime
import aiogram
import pyquoks.data, pyquoks.utils
import models


# region Constants

class Constants:
    DAYS_IN_MONTH = 30
    ITEMS_PER_PAGE = 5
    ITEMS_PER_ROW = 1
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
        currency_multiplier: int
        max_balance: int
        max_subscriptions: int
        provider_token: str

        def get_amount_with_currency(self, amount: int) -> str:
            return f"{amount} {self.currency}"

    class ReferralConfig(pyquoks.data.IConfigProvider.IConfig):
        _SECTION = "Referral"
        multiplier_common: float
        multiplier_first: float

        def get_referrer_model(
                self,
                referrer: models.Referrer | None
        ) -> models.Referrer | ConfigProvider.ReferralConfig:
            return referrer if referrer else self

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
                "currency_multiplier": int,
                "max_balance": int,
                "max_subscriptions": int,
                "provider_token": str
            },
        "Referral":
            {
                "multiplier_common": float,
                "multiplier_first": float,
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
        "referral": ReferralConfig,
        "settings": SettingsConfig,
    }
    payments: PaymentsConfig
    referral: ReferralConfig
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
        payment_payload TEXT NOT NULL,
        payment_provider_id TEXT,
        payment_date INTEGER NOT NULL
        )
        """

        def add_payment(
                self,
                tg_id: int,
                payment_amount: int,
                payment_currency: str,
                payment_payload: str,
                payment_provider_id: str | None,
                payment_date: int,
        ) -> None:
            cursor = self.cursor()

            cursor.execute(
                f"""
                INSERT INTO {self._NAME} (
                tg_id,
                payment_amount,
                payment_currency,
                payment_payload,
                payment_provider_id,
                payment_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (tg_id, payment_amount, payment_currency, payment_payload, payment_provider_id, payment_date),
            )

            self.commit()

        def get_payment(self, payment_id: int) -> models.PaymentValues | None:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE payment_id == ?
                """,
                (payment_id,),
            )

            result = cursor.fetchone()
            return models.PaymentValues(
                **dict(result),
            ) if result else None

        def get_all_payments(self) -> list[models.PaymentValues] | None:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME}
                """,
            )

            return [
                models.PaymentValues(
                    **dict(row),
                ) for row in cursor.fetchall()
            ]

        def get_user_payments(self, tg_id: int) -> list[models.PaymentValues]:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )

            return [
                models.PaymentValues(
                    **dict(row),
                ) for row in cursor.fetchall()
            ]

        def check_payments(self, tg_id: int) -> bool:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE payment_provider_id IS NOT NULL AND tg_id == ?
                """,
                (tg_id,),
            )

            return bool(cursor.fetchone())

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
        ) -> models.SubscriptionValues | None:
            cursor = self.cursor()

            cursor.execute(
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

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE rowid = ?
                """,
                (cursor.lastrowid,),
            )
            result = cursor.fetchone()
            return models.SubscriptionValues(
                **dict(result),
            ) if result else None

        def get_subscription(self, subscription_id: int) -> models.SubscriptionValues | None:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE subscription_id == ?
                """,
                (subscription_id,),
            )

            result = cursor.fetchone()
            return models.SubscriptionValues(
                **dict(result),
            ) if result else None

        def get_all_subscriptions(self) -> list[models.SubscriptionValues]:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME}
                """,
            )

            return [
                models.SubscriptionValues(
                    **dict(row),
                ) for row in cursor.fetchall()
            ]

        def get_user_subscriptions(self, tg_id: int) -> list[models.SubscriptionValues]:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )

            return [
                models.SubscriptionValues(
                    **dict(row),
                ) for row in cursor.fetchall()
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
            cursor = self.cursor()

            cursor.execute(
                f"""
                UPDATE {self._NAME} SET expires_date = ? WHERE subscription_id == ?
                """,
                (expires_date, subscription_id),
            )

            self.commit()

        def switch_active(self, subscription_id: int) -> None:
            cursor = self.cursor()

            current_subscription = self.get_subscription(
                subscription_id=subscription_id,
            )

            cursor.execute(
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
            cursor = self.cursor()

            cursor.execute(
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
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE tg_id == ?
                """,
                (tg_id,),
            )

            result = cursor.fetchone()
            return models.UserValues(
                **dict(result),
            ) if result else None

        def get_all_users(self) -> list[models.UserValues]:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME}
                """,
            )

            return [
                models.UserValues(
                    **dict(row),
                ) for row in cursor.fetchall()
            ]

        def get_ref_count(self, tg_id: int) -> int:
            cursor = self.cursor()

            cursor.execute(
                f"""
                SELECT COUNT(*) from {self._NAME} WHERE referrer_id == ?
                """,
                (tg_id,),
            )

            return cursor.fetchone()[0]

        def edit_balance(self, tg_id: int, balance: int) -> None:
            cursor = self.cursor()

            cursor.execute(
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
