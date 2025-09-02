import telebot

# TODO: Добавить класс для хранения кнопок

# /start
plans = telebot.types.InlineKeyboardButton(text="Тарифы", callback_data="plans")
subscriptions = telebot.types.InlineKeyboardButton(text="Подписки", callback_data="subscriptions")
profile = telebot.types.InlineKeyboardButton(text="Профиль", callback_data="profile")

# profile
invite_friend = telebot.types.InlineKeyboardButton(text="Поделиться", copy_text=telebot.types.CopyTextButton(text="https://t.me/{0}?start={1}"))
add_funds = telebot.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

# add_funds
add_funds_enter = telebot.types.InlineKeyboardButton(text="Ввести сумму", callback_data="add_funds_enter")
add_funds_month = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_month")
add_funds_quarter = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_quarter")
add_funds_half = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_half")
add_funds_year = telebot.types.InlineKeyboardButton(text="{0}₽", callback_data="add_funds_year")

# back_to_*
back_to_start = telebot.types.InlineKeyboardButton(text="Назад", callback_data="start")
back_to_profile = telebot.types.InlineKeyboardButton(text="Назад", callback_data="profile")
back_to_add_funds = telebot.types.InlineKeyboardButton(text="Отмена", callback_data="add_funds")

# TODO: /test_config
config_copy_settings = telebot.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="config_copy_settings")
download_amnezia = telebot.types.InlineKeyboardButton(text="Скачать AmneziaVPN", url="https://amnezia.org/downloads")
