from __future__ import annotations
import telebot


class ButtonsContainer:

    def __init__(self):
        # /start
        self.plans = telebot.types.InlineKeyboardButton(text="Тарифы", callback_data="plans")
        self.subscriptions = telebot.types.InlineKeyboardButton(text="Подписки", callback_data="subscriptions")
        self.profile = telebot.types.InlineKeyboardButton(text="Профиль", callback_data="profile")

        # profile
        self.invite_friend = telebot.types.InlineKeyboardButton(text="Поделиться", copy_text=telebot.types.CopyTextButton(text="https://t.me/{0}?start={1}"))
        self.add_funds = telebot.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

        # add_funds
        self.add_funds_enter = telebot.types.InlineKeyboardButton(text="Ввести сумму", callback_data="add_funds_enter")
        self.add_funds_month = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_month")
        self.add_funds_quarter = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_quarter")
        self.add_funds_half = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_half")
        self.add_funds_year = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_year")

        # back_to_*
        self.back_to_start = telebot.types.InlineKeyboardButton(text="Назад", callback_data="start")
        self.back_to_profile = telebot.types.InlineKeyboardButton(text="Назад", callback_data="profile")
        self.back_to_add_funds = telebot.types.InlineKeyboardButton(text="Отмена", callback_data="add_funds")

        # TODO: тестовые функции
        # /test_config
        self.config_copy_settings = telebot.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="config_copy_settings")
        self.download_amnezia = telebot.types.InlineKeyboardButton(text="Скачать AmneziaVPN", url="https://amnezia.org/downloads")
