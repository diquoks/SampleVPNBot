import telebot

# /start
view_plans = telebot.types.InlineKeyboardButton(text="Тарифы", callback_data="view_plans")
view_subscriptions = telebot.types.InlineKeyboardButton(text="Подписки", callback_data="view_subscriptions")
view_profile = telebot.types.InlineKeyboardButton(text="Профиль", callback_data="view_profile")

# view_profile
invite_friend = telebot.types.InlineKeyboardButton(text="Поделиться")
add_funds = telebot.types.InlineKeyboardButton(text="Пополнить баланс", callback_data="add_funds")

# download_amnezia
download_amnezia_desktop = telebot.types.InlineKeyboardButton(text="Для ПК", url="https://github.com/amnezia-vpn/amnezia-client/releases/latest")
download_amnezia_apple = telebot.types.InlineKeyboardButton(text="Для iOS, iPadOS & MacOS", url="https://apps.apple.com/us/app/amneziavpn/id1600529900")
download_amnezia_android = telebot.types.InlineKeyboardButton(text="Для Android", url="https://play.google.com/store/apps/details?id=org.amnezia.vpn")

# back_to_*
back_to_start = telebot.types.InlineKeyboardButton(text="Назад", callback_data="start")

# TODO: /test_config
config_copy_settings = telebot.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="config_copy_settings")
download_amnezia = telebot.types.InlineKeyboardButton(text="Скачать AmneziaVPN", callback_data="download_amnezia")
