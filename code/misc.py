from __future__ import annotations
import aiogram
import models, data


class ButtonsContainer:
    def __init__(self):
        self._data = data.DataProvider()

        # /start
        self.plans = aiogram.types.InlineKeyboardButton(text="Тарифы", callback_data="plans")
        self.subscriptions = aiogram.types.InlineKeyboardButton(text="Подписки", callback_data="subscriptions")
        self.profile = aiogram.types.InlineKeyboardButton(text="Профиль", callback_data="profile")

        # TODO: subscriptions
        self.config_copy_settings = aiogram.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="config_copy_settings")
        self.download_amnezia = aiogram.types.InlineKeyboardButton(text="Скачать AmneziaVPN", url="https://amnezia.org/downloads")

        # profile
        self.invite_friend = aiogram.types.InlineKeyboardButton(text="Поделиться")
        self.add_funds = aiogram.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

        # add_funds
        self.add_funds_enter = aiogram.types.InlineKeyboardButton(text="Ввести сумму", callback_data="add_funds_enter")
        for i in models.PlansType:
            selected_plan = self._data.plans.plans[i.value]
            selected_button = aiogram.types.InlineKeyboardButton(text="{0}₽", callback_data=f"add_funds_{i.name}")
            selected_button.text = selected_button.text.format(selected_plan.price * selected_plan.months)
            setattr(self, f"add_funds_{i.name}", selected_button)

        # back_to_*
        self.back_to_start = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="start")
        self.back_to_plans = aiogram.types.InlineKeyboardButton(text="Посмотреть тарифы", callback_data="plans")
        self.back_to_profile = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="profile")
        self.back_to_add_funds = aiogram.types.InlineKeyboardButton(text="Отмена", callback_data="add_funds")
