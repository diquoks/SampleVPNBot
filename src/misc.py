from __future__ import annotations
import aiogram
import models, data


class ButtonsContainer:
    def __init__(self) -> None:
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()

        # region /start

        self.plans = aiogram.types.InlineKeyboardButton(
            text="Тарифные планы",
            callback_data="plans",
        )
        self.add_funds = aiogram.types.InlineKeyboardButton(
            text="Пополнить баланс",
            callback_data="add_funds",
        )
        self.invite = aiogram.types.InlineKeyboardButton(
            text="Пригласить друга",
        )
        self.subscriptions = aiogram.types.InlineKeyboardButton(
            text="Мои подписки",
            callback_data=f"subscriptions {data.Constants.FIRST_PAGE_ID}",
        )
        self.profile = aiogram.types.InlineKeyboardButton(
            text="Профиль",
            callback_data="profile",
        )

        # endregion

        # region /admin

        self.admin_users = aiogram.types.InlineKeyboardButton(
            text="Пользователи",
            callback_data=f"admin_users {data.Constants.FIRST_PAGE_ID}",
        )
        self.admin_configs = aiogram.types.InlineKeyboardButton(
            text="Конфигурации",
            callback_data=f"admin_configs {data.Constants.FIRST_PAGE_ID}",
        )
        self.admin_subscriptions = aiogram.types.InlineKeyboardButton(
            text="Подписки",
            callback_data=f"admin_subscriptions {data.Constants.FIRST_PAGE_ID}",
        )
        self.admin_payments = aiogram.types.InlineKeyboardButton(
            text="Платежи",
            callback_data=f"admin_payments {data.Constants.FIRST_PAGE_ID}",
        )
        self.admin_logs = aiogram.types.InlineKeyboardButton(
            text="Логи",
            callback_data="admin_logs",
        )
        self.admin_settings = aiogram.types.InlineKeyboardButton(
            text="Настройки",
            callback_data="admin_settings",
        )

        self.admin_user_balance_enter = aiogram.types.InlineKeyboardButton(
            text="Изменить баланс",
            callback_data="admin_user_balance_enter {0}",
        )
        self.admin_user_referral = aiogram.types.InlineKeyboardButton(
            text="Реферал",
            callback_data="admin_user {0}",
        )

        self.admin_user = aiogram.types.InlineKeyboardButton(
            text="Пользователь",
            callback_data="admin_user {0}",
        )
        self.admin_subscription_expire = aiogram.types.InlineKeyboardButton(
            text="Завершить подписку",
            callback_data="admin_subscription_expire {0}",
        )

        # endregion

        # region plans

        self.plan_add_funds = aiogram.types.InlineKeyboardButton(
            text="Пополнить на {0}",
            callback_data="add_funds {0}",
        )
        self._plan = aiogram.types.InlineKeyboardButton(
            text=str(),
            callback_data="plan {0}",
        )
        self._plan_subscribe = aiogram.types.InlineKeyboardButton(
            text="Подписаться за {0}",
            callback_data="plan_subscribe {0}",
        )
        # plan_*
        for plan_type in models.PlansType:
            plan = self._data.plans.plans[plan_type.value]

            button = self._plan.model_copy()
            button.text = plan.name
            button.callback_data = button.callback_data.format(plan_type.value)

            setattr(self, f"plan_{plan_type.value}", button)
        # plan_subscribe_*
        for plan_type in models.PlansType:
            plan = self._data.plans.plans[plan_type.value]

            button = self._plan_subscribe.model_copy()
            button.text = button.text.format(self._get_amount_with_currency(plan.price * plan.months))
            button.callback_data = button.callback_data.format(plan_type.value)

            setattr(self, f"plan_subscribe_{plan_type.value}", button)

        # endregion

        # region add_funds

        self.add_funds_enter = aiogram.types.InlineKeyboardButton(
            text="Ввести сумму",
            callback_data="add_funds_enter",
        )
        self._add_funds = aiogram.types.InlineKeyboardButton(
            text=str(),
            callback_data="add_funds {0}",
        )
        # add_funds_*
        for plan_type in models.PlansType:
            plan = self._data.plans.plans[plan_type.value]
            amount = plan.price * plan.months

            button = self._add_funds.model_copy()
            button.text = self._get_amount_with_currency(amount)
            button.callback_data = button.callback_data.format(amount)

            setattr(self, f"add_funds_{plan_type.value}", button)

        # endregion

        # region subscriptions
        self.subscription_config_data = aiogram.types.InlineKeyboardButton(
            text="Данные для подключения",
            callback_data="subscription_config_file {0}",
        )
        self.subscription_config_file = aiogram.types.InlineKeyboardButton(
            text="Файл конфигурации",
            callback_data="subscription_config_file {0}",
        )
        self.subscription_config_copy = aiogram.types.InlineKeyboardButton(
            text="Ключ для подключения",
            callback_data="subscription_config_copy {0}",
        )
        self.subscription_config_download = aiogram.types.InlineKeyboardButton(
            text="Скачать AmneziaVPN",
            url="https://storage.googleapis.com/amnezia/amnezia.org",
        )
        self.subscription_switch_active = aiogram.types.InlineKeyboardButton(
            text=str(),
            callback_data="subscription_switch_active {0}",
        )

        # endregion

        # region page

        self.page_previous = aiogram.types.InlineKeyboardButton(
            text="<",
            callback_data=str(),
        )
        self.page_info = aiogram.types.InlineKeyboardButton(
            text="{0} / {1} ({2})",
            callback_data=str(),
        )
        self.page_next = aiogram.types.InlineKeyboardButton(
            text=">",
            callback_data=str(),
        )

        self.page_item_user = aiogram.types.InlineKeyboardButton(
            text="{0} ({1})",
            callback_data=str(),
        )
        self.page_item_subscription = aiogram.types.InlineKeyboardButton(
            text="#{0} «{1}»",
            callback_data=str(),
        )
        self.page_item_payment = aiogram.types.InlineKeyboardButton(
            text="#{0} ({1})",
            callback_data=str(),
        )

        # endregion

        # region back_to_*

        self.back_to_start = aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="start",
        )
        self.back_to_plans = aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="plans",
        )
        self.back_to_plan = aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="plan {0}",
        )
        self.back_to_subscriptions = aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data=f"subscriptions {data.Constants.FIRST_PAGE_ID}",
        )
        self.back_to_add_funds = aiogram.types.InlineKeyboardButton(
            text="Отмена",
            callback_data="add_funds",
        )
        self.back_to_admin = aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="admin",
        )

        self.delete_to_start = aiogram.types.InlineKeyboardButton(
            text="Главное меню",
            callback_data="delete_to_start",
        )

        # endregion

        # region view_*

        self.view_start = aiogram.types.InlineKeyboardButton(
            text="Главное меню",
            callback_data="start",
        )
        self.view_plans = aiogram.types.InlineKeyboardButton(
            text="Перейти к тарифам",
            callback_data="plans",
        )

        # endregion

    def _get_amount_with_currency(self, amount: int) -> str:
        return f"{amount} {self._config.payments.currency}"
