from __future__ import annotations
import aiogram
import models, data


class ButtonsContainer:
    def __init__(self) -> None:
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()

        # /start
        self.plans = aiogram.types.InlineKeyboardButton(text="Тарифы", callback_data="plans")
        self.subscriptions = aiogram.types.InlineKeyboardButton(text="Подписки", callback_data="subscriptions")
        self.profile = aiogram.types.InlineKeyboardButton(text="Профиль", callback_data="profile")

        # plans
        # plans_*
        for i in models.PlansType:
            plan = self._data.plans.plans[i.value]
            button = aiogram.types.InlineKeyboardButton(
                text=plan.name,
                callback_data=f"plans_{i.name}",
            )
            setattr(self, f"plans_{i.name}", button)
        # plans_subscribe_*
        for i in models.PlansType:
            plan = self._data.plans.plans[i.value]
            button = aiogram.types.InlineKeyboardButton(
                text=f"Подписаться за {self._get_amount_with_currency(plan.price * plan.months)}",
                callback_data=f"plans_subscribe_{i.name}",
            )
            setattr(self, f"plans_subscribe_{i.name}", button)

        # subscriptions
        self.view_subscription = aiogram.types.InlineKeyboardButton(
            text="#{0} «{1}»",
            callback_data="view_subscription_{0}",
        )
        self.view_subscription_config = aiogram.types.InlineKeyboardButton(
            text="Файл конфигурации",
            callback_data="view_subscription_config_{0}",
        )
        self.config_copy_settings = aiogram.types.InlineKeyboardButton(
            text="Настройки для подключения",
            callback_data="config_copy_settings",
        )
        self.download_amnezia = aiogram.types.InlineKeyboardButton(
            text="Скачать AmneziaVPN",
            url="https://storage.googleapis.com/amnezia/amnezia.org",
        )

        # profile
        self.invite_friend = aiogram.types.InlineKeyboardButton(text="Поделиться")
        self.add_funds = aiogram.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

        # add_funds
        self.add_funds_enter = aiogram.types.InlineKeyboardButton(text="Ввести сумму", callback_data="add_funds_enter")
        # add_funds_*
        for i in models.PlansType:
            plan = self._data.plans.plans[i.value]
            button = aiogram.types.InlineKeyboardButton(
                text=f"{self._get_amount_with_currency(plan.price * plan.months)}",
                callback_data=f"add_funds_{i.name}",
            )
            setattr(self, f"add_funds_{i.name}", button)

        # back_to_*
        self.back_to_start = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="start")
        self.back_to_plans = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="plans")
        self.back_to_subscriptions = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="subscriptions")
        self.back_to_profile = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="profile")
        self.back_to_add_funds = aiogram.types.InlineKeyboardButton(text="Отмена", callback_data="add_funds")

        # view_*
        self.view_start = aiogram.types.InlineKeyboardButton(text="Главное меню", callback_data="start")
        self.view_plans = aiogram.types.InlineKeyboardButton(text="Посмотреть тарифы", callback_data="plans")
        self.view_profile = aiogram.types.InlineKeyboardButton(text=str(), callback_data="profile")
        self.view_add_funds = aiogram.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

    def _get_amount_with_currency(self, amount: int) -> str:
        return " ".join([str(amount), self._config.payments.currency])
