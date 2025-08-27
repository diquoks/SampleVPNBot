from __future__ import annotations
import traceback, logging, telebot, io
import buttons, data, utils


class Client(telebot.TeleBot):
    class ExceptionHandler(telebot.ExceptionHandler):
        def handle(self, _) -> bool:  # рассмотреть возможность не приватить параметр `exception`
            # TODO: добавить класс для взаимодействия с логами
            logging.error(traceback.format_exc())
            return True

    def __init__(self) -> None:
        self._config = data.ConfigProvider()
        logging.basicConfig(level=logging.INFO)
        super().__init__(
            token=self._config.settings.token,
            exception_handler=self.ExceptionHandler(),
        )


client = Client()


@client.message_handler(commands=["start"])
def start(message: telebot.types.Message) -> None:
    utils.log_user_interaction(message.from_user.username, message.from_user.id, message.text)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(buttons.view_plans, buttons.view_profile)
    bot = client.get_me()
    client.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text=f"Добро пожаловать в {bot.full_name}!",
        reply_markup=markup
    )


@client.callback_query_handler()
def callback(call: telebot.types.CallbackQuery) -> None:
    utils.log_user_interaction(call.from_user.username, call.from_user.id, call.data)

    try:
        if call.data == "copy_config_settings":
            if call.message.document:
                file = client.get_file(call.message.document.file_id)
                config_key = client.download_file(file_path=file.file_path).decode("utf-8")
                client.send_message(
                    chat_id=call.message.chat.id,
                    message_thread_id=call.message.message_thread_id,
                    text=f"Настройки для подключения доступны ниже:\n```{config_key}```",
                    parse_mode="markdown",
                )
            else:
                client.answer_callback_query(callback_query_id=call.id, text="Настройки для подключения недоступны!", show_alert=True)
        elif call.data == "download_amnezia":
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(buttons.download_amnezia_desktop, buttons.download_amnezia_android)
            markup.row(buttons.download_amnezia_apple)
            client.send_message(
                chat_id=call.message.chat.id,
                message_thread_id=call.message.message_thread_id,
                text="Скачать клиент Amnezia VPN:",
                reply_markup=markup,
            )
        else:
            client.answer_callback_query(callback_query_id=call.id, text="Эта кнопка недоступна!", show_alert=True)
    except:
        # TODO: добавить класс для взаимодействия с логами
        logging.error(traceback.format_exc())


# TODO: временные функции

@client.message_handler(commands=["test_config"])
def send_config(message: telebot.types.Message, config_key: str = "test_dev_key") -> None:  # TODO: удалить "test_dev_key" при переносе функционала
    utils.log_user_interaction(message.from_user.username, message.from_user.id, message.text)

    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(buttons.copy_config_settings)
    markup.row(buttons.download_amnezia)
    bot = client.get_me()
    file_obj = io.BytesIO(bytes(config_key, encoding="utf8"))
    file_obj.name = f"{bot.full_name}_config.vpn"
    client.send_document(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        document=file_obj,
        caption="Ваш файл конфигурации\nдоступен для скачивания!",
        reply_markup=markup,
    )
