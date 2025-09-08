from __future__ import annotations
import aiogram


class ButtonsContainer:
    def __init__(self):
        # /start
        self.plans = aiogram.types.InlineKeyboardButton(text="Тарифы", callback_data="plans")
        self.subscriptions = aiogram.types.InlineKeyboardButton(text="Подписки", callback_data="subscriptions")
        self.profile = aiogram.types.InlineKeyboardButton(text="Профиль", callback_data="profile")

        # profile
        self.invite_friend = aiogram.types.InlineKeyboardButton(text="Поделиться")
        self.add_funds = aiogram.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

        # add_funds
        self.add_funds_enter = aiogram.types.InlineKeyboardButton(text="Ввести сумму", callback_data="add_funds_enter")
        self.add_funds_month = aiogram.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_month")
        self.add_funds_quarter = aiogram.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_quarter")
        self.add_funds_half = aiogram.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_half")
        self.add_funds_year = aiogram.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_year")

        # back_to_*
        self.back_to_start = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="start")
        self.back_to_profile = aiogram.types.InlineKeyboardButton(text="Назад", callback_data="profile")
        self.back_to_add_funds = aiogram.types.InlineKeyboardButton(text="Отмена", callback_data="add_funds")

        # TODO: тестовые функции
        # /test_config
        self.config_copy_settings = aiogram.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="config_copy_settings")
        self.download_amnezia = aiogram.types.InlineKeyboardButton(text="Скачать AmneziaVPN", url="https://amnezia.org/downloads")
