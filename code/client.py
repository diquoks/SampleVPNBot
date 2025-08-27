from __future__ import annotations
import traceback, logging, telebot, sys, io
import data, buttons


class Client(telebot.TeleBot):
    # TODO: добавить класс для взаимодействия с логами
    class ExceptionHandler(telebot.ExceptionHandler):
        def handle(self, _):
            logging.error(traceback.format_exc())
            return True

    def __init__(self):
        self._config = data.BotConfig()
        logging.basicConfig(level=logging.INFO)
        super().__init__(
            token=self._config.settings.token,
            exception_handler=self.ExceptionHandler(),
        )


client = Client()


@client.message_handler(commands=["test"])
def test(message: telebot.types.Message):
    # TODO: при переносе функционала `config_key` должен выступать атрибутом функции
    config_key = "test_dev_key"
    logging.info(f"{sys._getframe().f_code.co_name}: {message.from_user.id} - \"{message.text}\"")

    file_obj = io.BytesIO(bytes(config_key, encoding="utf8"))
    file_obj.name = "amnezia_config.vpn"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(buttons.copy_config_settings)
    markup.row(buttons.download_amnezia)
    client.send_document(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        document=file_obj,
        caption="Ваш файл конфигурации\nдоступен для скачивания!",
        reply_markup=markup,
    )


@client.callback_query_handler(func=lambda _: True)
def callback(call: telebot.types.CallbackQuery):
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
    except:
        logging.error(traceback.format_exc())
    finally:
        client.answer_callback_query(callback_query_id=call.id)
