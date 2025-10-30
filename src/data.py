from __future__ import annotations
import aiogram
import pyquoks.data, pyquoks.utils
import models, utils


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

        def is_admin(self, tg_id) -> bool:
            return tg_id in self.admin_list

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


class StringsProvider(pyquoks.data.IStringsProvider):
    class AlertStrings(pyquoks.data.IStringsProvider.IStrings):

        # region add_funds

        @property
        def add_funds_enter_unavailable(self) -> str:
            return "Сейчас вы не можете выбрать сумму пополнения!"

        @property
        def add_funds_unavailable(self) -> str:
            return "Сумма пополнения выходит за доступные пределы!"

        # endregion

        # region subscriptions

        @property
        def subscriptions_unavailable(self) -> str:
            return "У вас нет активных подписок!"

        # endregion

        # region /admin

        @property
        def admin_subscriptions_unavailable(self) -> str:
            return "Купленные подписки отсутствуют!"

        @property
        def admin_payments_unavailable(self) -> str:
            return "Совершённые платежи отсутствуют!"

        @property
        def admin_logs_unavailable(self) -> str:
            return "Логирование отключено!"

        # endregion

        @property
        def button_unavailable(self) -> str:
            return "Эта кнопка недоступна!"

    class MenuStrings(pyquoks.data.IStringsProvider.IStrings):
        def __init__(self):
            self._data = DataProvider()
            self._config = ConfigProvider()

        # region /start

        @staticmethod
        def start(bot_full_name: str) -> str:
            return (
                f"<b>Добро пожаловать в {bot_full_name}!</b>\n"
                f"\n"
                f"Благодарим за выбор нашего сервиса,\n"
                f"ваша безопасность — наш приоритет!\n"
            )

        @property
        def plans(self) -> str:
            # (TEXT_PENDING)
            return "<b>Выбор тарифа:</b>"

        @property
        def add_funds(self) -> str:
            return (
                "<b>Пополнение баланса:</b>\n"
                "\n"
                "Выберите нужную сумму для\n"
                "пополнения или введите свою:\n"
            )

        @property
        def subscriptions(self) -> str:
            # (TEXT_PENDING)
            return "<b>Выбор подписки:</b>"

        def profile(
                self,
                user: models.UserValues,
                referrer_model: models.Referrer | ConfigProvider.ReferralConfig,
                referrer_user: models.UserValues | None,
                subscriptions_count: int,
                friends_count: int,
        ) -> str:
            return (
                f"<b>Профиль {user.html_text}:</b>\n"
                f"\n"
                f"<b>Баланс: {self._config.payments.get_amount_with_currency(user.balance)}</b>\n"
                f"Активных подписок: <b>{subscriptions_count}</b>\n"
                f"Приглашено друзей: <b>{friends_count}</b>\n"
                f"\n"
                f"<b>Реферальные выплаты:</b>\n"
                f"Первое пополнение: <b>{referrer_model.multiplier_first:.0%}</b>\n"
                f"Следующие пополнения: <b>{referrer_model.multiplier_common:.0%}</b>\n"
            ) + (
                (
                    f"\n"
                    f"Пригласил: <b>{referrer_user.html_text}</b>\n"
                ) if referrer_user else str()
            )

        # endregion

        # region plans

        def plan(self, user: models.UserValues, plan: models.Plan) -> str:
            return (
                f"<b>Тариф «{plan.name}»</b>\n"
                f"{plan.description}\n"
                f"\n"
                f"Период подписки: <b>{plan.days} дней</b>\n"
                f"\n"
                f"<b>(Текущий баланс: {self._config.payments.get_amount_with_currency(user.balance)})</b>\n"
            )

        def plan_subscribe_unavailable(self, current_plan: models.Plan, amount: int) -> str:
            return (
                f"<b>Недостаточно средств!</b>\n"
                f"\n"
                f"Пополните баланс на <b>{self._config.payments.get_amount_with_currency(amount)}</b>\n"
                f"для подписки на «{current_plan.name}»!\n"
            )

        # endregion

        # region add_funds

        @property
        def add_funds_title(self) -> str:
            return "Пополнение баланса"

        def add_funds_description(self, amount: int) -> str:
            return f"Счёт на сумму {self._config.payments.get_amount_with_currency(amount)}"

        @staticmethod
        def add_funds_enter(min_amount: int, max_amount: int, error: bool = False) -> str:
            return (
                (
                    f"<b>Сумма пополнения выходит\n"
                    f"за доступные пределы!</b>\n"
                    f"\n"
                ) if error else str()
            ) + (
                f"Введите сумму, на которую\n"
                f"хотите пополнить баланс:\n"
                f"<b>(число от {min_amount} до {max_amount})</b>\n"
            )

        def add_funds_success(self, amount: int) -> str:
            return f"Баланс пополнен на <b>{self._config.payments.get_amount_with_currency(amount)}</b>!"

        # endregion

        # region subscriptions

        def subscription(self, subscription: models.SubscriptionValues, user: models.UserValues = None) -> str:
            current_plan = self._data.plans.get_plan_by_id(
                plan_id=subscription.plan_id,
            )

            return (
                f"<b>Подписка #{subscription.subscription_id}</b>\n"
                f"Тариф «{current_plan.name}»\n"
                f"\n"
                f"<b>Статус: {subscription.status}</b>\n"
                f"Подключена: <b>{utils.get_formatted_timestamp(subscription.subscribed_date)}</b>\n"
                f"Истекает: <b>{utils.get_formatted_timestamp(subscription.expires_date)}</b>\n"
            ) + (
                (
                    f"\n"
                    f"Пользователь: {user.html_text}\n"
                ) if user else str()
            )

        @property
        def subscription_config_file(self) -> str:
            return (
                "Ваш файл конфигурации\n"
                "доступен для скачивания!\n"
            )

        @staticmethod
        def subscription_config_copy(config_key: str) -> str:
            return (
                f"Ключ для подключения:\n"
                f"<pre>{config_key}</pre>\n"
            )

        # endregion

        # region /admin

        @staticmethod
        def admin(tg_full_name: str) -> str:
            return (
                f"<b>Меню администратора</b>\n"
                f"\n"
                f"Добро пожаловать, {tg_full_name}!\n"
            )

        @staticmethod
        def admin_users(users_count: int) -> str:
            return (
                f"<b>Выберите пользователя:</b>\n"
                f"(Всего: {users_count})\n"
            )

        @staticmethod
        def admin_user_balance_enter(current_user: models.UserValues, max_balance: int, error: bool = False) -> str:
            return (
                (
                    f"<b>Баланс должен быть числом!</b>\n"
                    f"\n"
                ) if error else str()
            ) + (
                f"Введите новый баланс для\n"
                f"{current_user.html_text}:\n"
                f"(Сейчас: {current_user.balance}/{max_balance})\n"
            )

        def admin_user_balance_enter_success(self, current_user: models.UserValues) -> str:
            return (
                f"<b>Баланс изменён!</b>\n"
                f"<b>{self._config.payments.get_amount_with_currency(current_user.balance)}</b> | {current_user.html_text})\n"
            )

        @staticmethod
        def admin_subscriptions(subscriptions_count: int) -> str:
            return (
                f"<b>Выберите подписку:</b>\n"
                f"(Всего: {subscriptions_count})\n"
            )

        @staticmethod
        def admin_payments(payments_count: int) -> str:
            return (
                f"<b>Выберите платёж:</b>\n"
                f"(Всего: {payments_count})\n"
            )

        @staticmethod
        def admin_payment(payment: models.PaymentValues, user: models.UserValues) -> str:
            return (
                f"<b>Платёж #{payment.payment_id}</b>\n"
                f"\n"
                f"<b>Информация: «{payment.payment_payload}»</b>\n"
                f"Сумма: <b>{payment.payment_amount} {payment.payment_currency}</b>\n"
                f"Совершён: <b>{utils.get_formatted_timestamp(payment.payment_date)}</b>\n"
            ) + (
                (
                    f"\n"
                    f"ID платежа: <code>{payment.payment_provider_id}</code>\n"
                ) if payment.payment_provider_id else str()
            ) + (
                f"\n"
                f"Пользователь: {user.html_text}\n"
            )

        # endregion

        # region page

        @staticmethod
        def admin_page_enter(error: bool = False) -> str:
            return (
                (
                    "<b>Элемент с выбранным ID не найден!</b>\n"
                    "\n"
                ) if error else str()
            ) + (
                "Введите ID элемента:\n"
            )

        # endregion

    class StatusStrings(pyquoks.data.IStringsProvider.IStrings):

        # region subscriptions

        @property
        def _subscription_disable_renewal(self) -> str:
            return "Отключить автопродление"

        @property
        def _subscription_enable_renewal(self) -> str:
            return "Подключить автопродление"

        def subscription_renewal(self, is_active: bool) -> str:
            return self._subscription_disable_renewal if is_active else self._subscription_enable_renewal

        # endregion

    _STRINGS_OBJECTS = {
        "alert": AlertStrings,
        "menu": MenuStrings,
        "status": StatusStrings,
    }
    alert: AlertStrings
    menu: MenuStrings
    status: StatusStrings


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
        ) -> models.PaymentValues | None:
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

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE rowid = ?
                """,
                (cursor.lastrowid,),
            )
            result = cursor.fetchone()
            return models.PaymentValues(
                **dict(result),
            ) if result else None

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
                    lambda subscription: not subscription.is_expired,
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

        def add_user(
                self,
                tg_id: int,
                tg_username: str | None,
                balance: int,
                referrer_id: int | None,
        ) -> models.UserValues | None:
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

            cursor.execute(
                f"""
                SELECT * FROM {self._NAME} WHERE rowid = ?
                """,
                (cursor.lastrowid,),
            )
            result = cursor.fetchone()
            return models.UserValues(
                **dict(result),
            ) if result else None

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
