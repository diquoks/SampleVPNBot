from __future__ import annotations
import aiogram
import models, data


class ButtonsContainer:
    def __init__(self):
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()

        # /start
        self.plans = aiogram.types.InlineKeyboardButton(text="Тарифы", callback_data="plans")
        self.subscriptions = aiogram.types.InlineKeyboardButton(text="Подписки", callback_data="subscriptions")
        self.profile = aiogram.types.InlineKeyboardButton(text="Профиль", callback_data="profile")

        # plans
        # plans_*
        for i in models.PlansType:
            selected_plan = self._data.plans.plans[i.value]
            selected_button = aiogram.types.InlineKeyboardButton(text=selected_plan.name, callback_data=f"plans_{i.name}")
            setattr(self, f"plans_{i.name}", selected_button)
        # plans_subscribe_*
        for i in models.PlansType:
            selected_plan = self._data.plans.plans[i.value]
            selected_button = aiogram.types.InlineKeyboardButton(text=f"Оплатить {self._get_amount_with_currency(selected_plan.price * selected_plan.months)}", callback_data=f"plans_subscribe_{i.name}")
            setattr(self, f"plans_subscribe_{i.name}", selected_button)

        # TODO: subscriptions
        self.config_copy_settings = aiogram.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="config_copy_settings")
        self.download_amnezia = aiogram.types.InlineKeyboardButton(text="Скачать AmneziaVPN", url="https://amnezia.org/downloads")

        # profile
        self.invite_friend = aiogram.types.InlineKeyboardButton(text="Поделиться")
        self.add_funds = aiogram.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

        # add_funds
        self.add_funds_enter = aiogram.types.InlineKeyboardButton(text="Ввести сумму", callback_data="add_funds_enter")
        # add_funds_*
        for i in models.PlansType:
            selected_plan = self._data.plans.plans[i.value]
            selected_button = aiogram.types.InlineKeyboardButton(text=f"{self._get_amount_with_currency(selected_plan.price * selected_plan.months)}", callback_data=f"add_funds_{i.name}")
            setattr(self, f"add_funds_{i.name}", selected_button)

        # back_to_*
        self.back_to_start = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="start")
        self.back_to_plans = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="plans")
        self.back_to_profile = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="profile")

        # cancel_to_*
        self.cancel_to_add_funds = aiogram.types.InlineKeyboardButton(text="Отмена", callback_data="add_funds")

        # view_*
        self.view_plans = aiogram.types.InlineKeyboardButton(text="Посмотреть тарифы", callback_data="plans")
        self.view_add_funds = aiogram.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

    def _get_amount_with_currency(self, amount: int) -> str:
        return str(amount) + self._data.plans.currency_sign
