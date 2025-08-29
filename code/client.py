from __future__ import annotations
import logging, telebot, io
import buttons, data


class Client(telebot.TeleBot):
    class ExceptionHandler(telebot.ExceptionHandler):
        def __init__(self, parent: Client) -> None:
            self._logger = parent._logger
            super().__init__()

        def handle(self, e) -> bool:
            self._logger.log_exception(e)
            return True

    def __init__(self) -> None:
        self._config = data.ConfigProvider()
        self._logger = data.LoggerService(name=__name__, level=logging.INFO)
        self._exception_handler = self.ExceptionHandler(self)
        super().__init__(
            token=self._config.settings.token,
            exception_handler=self._exception_handler,
        )
        self.message_handler(commands=["start"])(self.start)
        self.callback_query_handler()(self.callback)

        # TODO: временные функции
        self.message_handler(commands=["test_config"])(self.send_config)

        self._logger.info(f"{self.bot.full_name} initialized!")

    @property
    def bot(self) -> telebot.types.User:
        return self.get_me()

    @property
    def clean_username(self) -> str:
        return self.bot.username[:-4]

    def polling_thread(self) -> None:
        while True:
            try:
                self.polling(non_stop=True)
            except Exception as e:
                self._logger.log_exception(e)

    def start(self, message: telebot.types.Message) -> None:
        self._logger.log_user_interaction(message.from_user, message.text)

        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(buttons.view_plans)
        markup.row(buttons.view_subscriptions, buttons.view_profile)
        self.send_message(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            text=f"Добро пожаловать в {self.bot.full_name}!",
            reply_markup=markup,
        )

    def callback(self, call: telebot.types.CallbackQuery) -> None:
        self._logger.log_user_interaction(call.from_user, call.data)

        try:
            if call.data == "start":
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.view_plans)
                markup.row(buttons.view_subscriptions, buttons.view_profile)
                self.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Добро пожаловать в {self.bot.full_name}!",
                    reply_markup=markup,
                )
            elif call.data == "view_profile":
                invite_friend_button = buttons.invite_friend
                invite_friend_button.copy_text = telebot.types.CopyTextButton(text=f"https://t.me/{self.bot.username}?start={call.from_user.id}")
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.add_funds)
                markup.row(invite_friend_button, buttons.back_to_start)
                self.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Профиль {call.from_user.full_name}",
                    reply_markup=markup,
                )
            elif call.data == "config_copy_settings":
                if call.message.document:
                    file = self.get_file(call.message.document.file_id)
                    config_key = self.download_file(file_path=file.file_path).decode("utf-8")
                    self.send_message(
                        chat_id=call.message.chat.id,
                        message_thread_id=call.message.message_thread_id,
                        text=f"Настройки для подключения:\n```{config_key}```",
                        parse_mode="markdown",
                    )
                else:
                    self.answer_callback_query(
                        callback_query_id=call.id,
                        text="Настройки для подключения недоступны!",
                        show_alert=True,
                    )
            elif call.data == "download_amnezia":
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.download_amnezia_desktop, buttons.download_amnezia_android)
                markup.row(buttons.download_amnezia_apple)
                self.send_message(
                    chat_id=call.message.chat.id,
                    message_thread_id=call.message.message_thread_id,
                    text="Скачать клиент Amnezia VPN:",
                    reply_markup=markup,
                )
            else:
                self.answer_callback_query(
                    callback_query_id=call.id,
                    text="Эта кнопка недоступна!",
                    show_alert=True,
                )
        except Exception as e:
            self._logger.log_exception(e)
        finally:
            self.answer_callback_query(callback_query_id=call.id)

    # TODO: временные функции

    def send_config(self, message: telebot.types.Message, config_key: str = str(None)) -> None:  # TODO: убрать значение `config_key` по умолчанию при переносе функции
        self._logger.log_user_interaction(message.from_user, message.text)

        file_obj = io.BytesIO(bytes(config_key, encoding="utf8"))
        file_obj.name = f"{self.clean_username}_config.vpn"
        markup = telebot.types.InlineKeyboardMarkup()
        markup.row(buttons.config_copy_settings)
        markup.row(buttons.download_amnezia)
        self.send_document(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            document=file_obj,
            caption="Ваш файл конфигурации\nдоступен для скачивания!",
            reply_markup=markup,
        )
