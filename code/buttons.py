import telebot

# /start
view_plans = telebot.types.InlineKeyboardButton(text="Тарифы", callback_data="view_plans")
view_profile = telebot.types.InlineKeyboardButton(text="Профиль", callback_data="view_profile")
# /test
copy_config_settings = telebot.types.InlineKeyboardButton(text="Настройки для подключения", callback_data="copy_config_settings")
download_amnezia = telebot.types.InlineKeyboardButton(text="Скачать AmneziaVPN", callback_data="download_amnezia")
# download_amnezia
download_amnezia_desktop = telebot.types.InlineKeyboardButton(text="Для Windows & Linux", url="https://github.com/amnezia-vpn/amnezia-client/releases/latest")
download_amnezia_apple = telebot.types.InlineKeyboardButton(text="Для iOS, iPadOS & MacOS", url="https://apps.apple.com/us/app/amneziavpn/id1600529900")
download_amnezia_android = telebot.types.InlineKeyboardButton(text="Для Android", url="https://play.google.com/store/apps/details?id=org.amnezia.vpn")
