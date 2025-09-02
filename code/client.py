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
        self.register_message_handler(callback=self.start, commands=["start"])
        self.register_callback_query_handler(callback=self.callback, func=lambda *args: True)

        # TODO: тестовые функции
        self.register_message_handler(callback=self.send_config, commands=["test_config"])

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
        markup.row(buttons.plans)
        markup.row(buttons.subscriptions, buttons.profile)
        self.send_message(
            chat_id=message.chat.id,
            message_thread_id=message.message_thread_id,
            text=f"Добро пожаловать в {self.bot.full_name}!",
            reply_markup=markup,
        )

    def callback(self, call: telebot.types.CallbackQuery) -> None:
        self._logger.log_user_interaction(call.from_user, call.data)

        self.clear_step_handler_by_chat_id(chat_id=call.message.chat.id)  # в будущем можно очищать хендлеры при определённых `call.data`
        try:
            if call.data == "start":
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.plans)
                markup.row(buttons.subscriptions, buttons.profile)
                self.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Добро пожаловать в {self.bot.full_name}!",
                    reply_markup=markup,
                )
            elif call.data == "profile":
                invite_friend_button = buttons.invite_friend
                invite_friend_button.copy_text.text = invite_friend_button.copy_text.text.format(self.bot.username, call.from_user.id)
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.add_funds)
                markup.row(invite_friend_button, buttons.back_to_start)
                self.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Профиль {call.from_user.full_name}",
                    reply_markup=markup,
                )
            elif call.data == "add_funds":
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.add_funds_enter)
                markup.row(buttons.add_funds_month, buttons.add_funds_quarter)
                markup.row(buttons.add_funds_half, buttons.add_funds_year)
                markup.row(buttons.back_to_profile)
                self.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Пополнить баланс",
                    reply_markup=markup,
                )
            elif call.data == "add_funds_enter":
                markup = telebot.types.InlineKeyboardMarkup()
                markup.row(buttons.back_to_add_funds)
                self.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Введите сумму, на которую\nхотите пополнить баланс:",
                    reply_markup=markup,
                )
                self.register_next_step_handler_by_chat_id(
                    chat_id=call.message.chat.id,
                    callback=self.add_funds_enter_handler,
                )
            # TODO: получение стоимостей тарифов из .json
            elif call.data == "add_funds_month":
                self.add_funds_invoice(
                    user=call.from_user,
                    chat=call.message.chat,
                    amount=75,
                )
            elif call.data == "add_funds_quarter":
                self.add_funds_invoice(
                    user=call.from_user,
                    chat=call.message.chat,
                    amount=210,
                )
            elif call.data == "add_funds_half":
                self.add_funds_invoice(
                    user=call.from_user,
                    chat=call.message.chat,
                    amount=360,
                )
            elif call.data == "add_funds_year":
                self.add_funds_invoice(
                    user=call.from_user,
                    chat=call.message.chat,
                    amount=660,
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

    # TODO: тестовые функции
    def send_config(self, message: telebot.types.Message, config_key: str = str(None)) -> None:  # TODO: убрать значение `config_key` по умолчанию
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

    def add_funds_enter_handler(self, message: telebot.types.Message) -> None:
        self._logger.log_user_interaction(message.from_user, " ".join((self.add_funds_invoice.__name__, message.text)))
        try:
            # TODO: добавить область доступных значений для пополнения
            self.add_funds_invoice(
                user=message.from_user,
                chat=message.chat,
                amount=int(message.text),
            )
        except:
            markup = telebot.types.InlineKeyboardMarkup()
            markup.row(buttons.back_to_add_funds)
            self.reply_to(
                message,
                text="Сумма пополнения должна быть числом!\n\nВведите сумму, на которую\nхотите пополнить баланс:",
                reply_markup=markup,
            )
            self.register_next_step_handler_by_chat_id(
                chat_id=message.chat.id,
                callback=self.add_funds_enter_handler,
            )

    # noinspection PyUnusedLocal
    def add_funds_invoice(self, user: telebot.types.User, chat: telebot.types.Chat, amount: int) -> None:  # TODO
        self._logger.log_user_interaction(user, " ".join((self.add_funds_invoice.__name__, str(amount))))
