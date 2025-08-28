from __future__ import annotations
import traceback, datetime, logging, telebot, sys, io
import buttons, data, utils


class Client(telebot.TeleBot):
    class ExceptionHandler(telebot.ExceptionHandler):
        def handle(self, e) -> bool:
            # TODO: добавить класс для взаимодействия с логами
            logging.error("\n\n".join([traceback.format_exc(), str(e)]))
            return True

    def __init__(self) -> None:
        self._config = data.ConfigProvider()
        self._exception_handler = self.ExceptionHandler()
        logging.basicConfig(level=logging.INFO)
        super().__init__(
            token=self._config.settings.token,
            exception_handler=self._exception_handler,
        )
        logging.info(f"{sys._getframe().f_code.co_name} - {datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}")

    @property
    def clean_username(self) -> str:
        return self.get_me().username[:-4]


client = Client()


@client.message_handler(commands=["start"])
def start(message: telebot.types.Message) -> None:
    utils.log_user_interaction(message.from_user.username, message.from_user.id, message.text)

    bot = client.get_me()
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(buttons.view_plans)
    markup.row(buttons.view_subscriptions, buttons.view_profile)
    client.send_message(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        text=f"Добро пожаловать в {bot.full_name}!",
        reply_markup=markup,
    )


@client.callback_query_handler()
def callback(call: telebot.types.CallbackQuery) -> None:
    utils.log_user_interaction(call.from_user.username, call.from_user.id, call.data)

    try:
        if call.data == "start":
            bot = client.get_me()
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(buttons.view_plans)
            markup.row(buttons.view_subscriptions, buttons.view_profile)
            client.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Добро пожаловать в {bot.full_name}!",
                reply_markup=markup,
            )
        elif call.data == "view_profile":
            bot = client.get_me()
            invite_friend_button = buttons.invite_friend
            invite_friend_button.copy_text = telebot.types.CopyTextButton(text=f"https://t.me/{bot.username}?start={call.from_user.id}")
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(buttons.add_funds)
            markup.row(invite_friend_button, buttons.back_to_start)
            client.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Профиль {call.from_user.full_name}",
                reply_markup=markup,
            )
        elif call.data == "config_copy_settings":
            if call.message.document:
                file = client.get_file(call.message.document.file_id)
                config_key = client.download_file(file_path=file.file_path).decode("utf-8")
                client.send_message(
                    chat_id=call.message.chat.id,
                    message_thread_id=call.message.message_thread_id,
                    text=f"Настройки для подключения:\n```{config_key}```",
                    parse_mode="markdown",
                )
            else:
                client.answer_callback_query(
                    callback_query_id=call.id,
                    text="Настройки для подключения недоступны!",
                    show_alert=True,
                )
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
            client.answer_callback_query(
                callback_query_id=call.id,
                text="Эта кнопка недоступна!",
                show_alert=True,
            )
    except:
        # TODO: добавить класс для взаимодействия с логами
        logging.error("\n\n".join([traceback.format_exc(), call]))
    finally:
        client.answer_callback_query(callback_query_id=call.id)


# TODO: временные функции

@client.message_handler(commands=["test_config"])
def send_config(message: telebot.types.Message, config_key: str = str(None)) -> None:  # TODO: убрать значение `config_key` по умолчанию при переносе функции
    utils.log_user_interaction(message.from_user.username, message.from_user.id, message.text)

    file_obj = io.BytesIO(bytes(config_key, encoding="utf8"))
    file_obj.name = f"{client.clean_username}_config.vpn"
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(buttons.config_copy_settings)
    markup.row(buttons.download_amnezia)
    client.send_document(
        chat_id=message.chat.id,
        message_thread_id=message.message_thread_id,
        document=file_obj,
        caption="Ваш файл конфигурации\nдоступен для скачивания!",
        reply_markup=markup,
    )
