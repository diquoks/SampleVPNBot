from __future__ import annotations
import datetime, logging
import aiogram, aiogram.filters, aiogram.client.default, aiogram.fsm.context, aiogram.fsm.state
import models, data, misc


class AiogramClient(aiogram.Dispatcher):
    class Form(aiogram.fsm.state.StatesGroup):
        add_funds_enter = aiogram.fsm.state.State()

    def __init__(self):
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()
        self._buttons = misc.ButtonsContainer()
        self._logger = data.LoggerService(
            name=__name__,
            level=logging.INFO,
        )
        self._user = None
        self._form = self.Form()
        self._form_router = aiogram.Router()
        self._bot = aiogram.Bot(
            token=self._config.settings.bot_token,
            default=aiogram.client.default.DefaultBotProperties(
                parse_mode=aiogram.enums.ParseMode.HTML,
            ),
        )
        super().__init__(name="VastNetVPNDispatcher")
        self.include_router(self._form_router)

        self.errors.register(self.handle_error)
        self.message.register(self.start, aiogram.filters.Command("start"))
        self.message.register(self.admin, aiogram.filters.Command("admin"))
        self.message.register(self.success_add_funds_handler, aiogram.MagicFilter().successful_payment)
        self.pre_checkout_query.register(self.pre_add_funds_handler)
        self._form_router.callback_query.register(self.callback)
        self._form_router.message.register(self.add_funds_enter_handler, self._form.add_funds_enter)

        self._time_started = datetime.datetime.now(tz=datetime.timezone.utc)
        self._logger.info(f"{self.name} initialized!")

    @property
    async def user(self) -> aiogram.types.User:
        if not self._user:
            self._user = (await self._bot.get_me())
        return self._user

    @property
    async def clean_username(self) -> str:
        return (await self.user).username[:-3]

    @staticmethod
    def get_message_thread_id(message: aiogram.types.Message) -> int | None:
        if message.reply_to_message and message.reply_to_message.is_topic_message:
            return message.reply_to_message.message_thread_id
        elif message.is_topic_message:
            return message.message_thread_id
        else:
            return None

    async def handle_error(self, event: aiogram.types.ErrorEvent) -> None:
        self._logger.log_exception(event.exception)

    async def polling_coroutine(self) -> None:
        try:
            await self.start_polling(self._bot)
        except Exception as e:
            self._logger.log_exception(e)

    async def start(self, message: aiogram.types.Message) -> None:
        self._logger.log_user_interaction(message.from_user, message.text)

        markup = aiogram.types.InlineKeyboardMarkup(
            inline_keyboard=[
                [self._buttons.plans],
                [self._buttons.subscriptions, self._buttons.profile],
            ],
        )
        await self._bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=self.get_message_thread_id(message),
            text=f"Добро пожаловать в {(await self.user).full_name}!",
            reply_markup=markup,
        )

    async def admin(self, message: aiogram.types.Message) -> None:
        self._logger.log_user_interaction(message.from_user, f"{message.text} (admin={message.from_user.id in self._config.settings.admin_list})")

        if message.from_user.id in self._config.settings.admin_list:
            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self.get_message_thread_id(message),
                text="Вы являетесь администратором!",
            )

    async def callback(self, call: aiogram.types.CallbackQuery, state: aiogram.fsm.context.FSMContext) -> None:
        self._logger.log_user_interaction(call.from_user, call.data)

        current_state = await state.get_state()
        if current_state:
            await state.clear()
        try:
            if call.data == "start":
                markup = aiogram.types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [self._buttons.plans],
                        [self._buttons.subscriptions, self._buttons.profile],
                    ],
                )
                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Добро пожаловать в {(await self.user).full_name}!",
                    reply_markup=markup,
                )
            # TODO: просмотр и оплата тарифов
            # elif call.data == "plans":
            #     pass
            elif call.data == "subscriptions":  # TODO: просмотр активных подписок (DATABASE)
                await self.send_config(
                    call=call,
                    config_key=str(None),
                )
            elif call.data == "profile":
                invite_friend_button = self._buttons.invite_friend
                invite_friend_button.copy_text = aiogram.types.CopyTextButton(text=f"https://t.me/{(await self.user).username}?start={call.from_user.id}")
                markup = aiogram.types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [self._buttons.add_funds],
                        [invite_friend_button, self._buttons.back_to_start],
                    ],
                )
                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Профиль {call.from_user.full_name}:\n\nБаланс: {int()}\nПриглашено друзей: {int()}\n\nUser ID: <code>{call.from_user.id}</code>",  # TODO: получение данных пользователя (DATABASE)
                    reply_markup=markup,
                )
            elif call.data == "add_funds":
                plans_buttons = [getattr(self._buttons, f"add_funds_{i.name}") for i in models.PlansType]
                markup = aiogram.types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [self._buttons.add_funds_enter],
                        plans_buttons[:len(plans_buttons) // 2],
                        plans_buttons[len(plans_buttons) // 2:],
                        [self._buttons.back_to_profile],
                    ],
                )
                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Пополнить баланс",
                    reply_markup=markup,
                )
            elif call.data == "add_funds_enter":
                markup = aiogram.types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [self._buttons.back_to_add_funds],
                    ],
                )
                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Введите сумму, на которую\nхотите пополнить баланс:",
                    reply_markup=markup,
                )
                await state.set_state(self._form.add_funds_enter)
            elif call.data.replace("add_funds_", str()) in [i.name for i in models.PlansType]:
                selected_plan = self._data.plans.plans[models.PlansType[call.data.replace("add_funds_", str())]]
                await self.add_funds_invoice(
                    user=call.from_user,
                    chat=call.message.chat,
                    amount=selected_plan.price * selected_plan.months,
                )
            elif call.data == "config_copy_settings":
                if call.message.document:
                    file = await self._bot.get_file(call.message.document.file_id)
                    config_key = (await self._bot.download_file(file_path=file.file_path)).read().decode("utf-8")
                    await self._bot.send_message(
                        chat_id=call.message.chat.id,
                        message_thread_id=self.get_message_thread_id(call.message),
                        text=f"Настройки для подключения:\n```{config_key}```",
                        parse_mode="markdown",
                    )
                else:
                    await self._bot.answer_callback_query(
                        callback_query_id=call.id,
                        text="Настройки для подключения недоступны!",
                        show_alert=True,
                    )
            else:
                await self._bot.answer_callback_query(
                    callback_query_id=call.id,
                    text="Эта кнопка недоступна!",
                    show_alert=True,
                )
        except Exception as e:
            self._logger.log_exception(e)
        finally:
            await self._bot.answer_callback_query(callback_query_id=call.id)

    async def send_config(self, call: aiogram.types.CallbackQuery, config_key: str) -> None:
        self._logger.log_user_interaction(call.from_user, f"{self.send_config.__name__}(config_key={config_key})")

        markup = aiogram.types.InlineKeyboardMarkup(
            inline_keyboard=[
                [self._buttons.config_copy_settings],
                [self._buttons.download_amnezia],
            ],
        )
        await self._bot.send_document(
            chat_id=call.message.chat.id,
            message_thread_id=self.get_message_thread_id(call.message),
            document=aiogram.types.BufferedInputFile(
                file=bytes(config_key, encoding="utf8"),
                filename=f"{await self.clean_username}_config.vpn"
            ),
            caption="Ваш файл конфигурации\nдоступен для скачивания!",
            reply_markup=markup,
        )

    async def add_funds_invoice(self, user: aiogram.types.User, chat: aiogram.types.Chat, amount: int) -> None:
        self._logger.log_user_interaction(user, f"{self.add_funds_invoice.__name__}(amount={amount})")

        await self._bot.send_invoice(
            chat_id=chat.id,
            prices=[aiogram.types.LabeledPrice(label=f"Пополнение на сумму {amount} {self._config.payments.currency}", amount=amount * self._config.payments.multiplier)],
            currency=self._config.payments.currency,
            provider_token=self._config.payments.provider_token,
            payload=f"{user.id} {amount}",
            title="Пополнение баланса",
            description=f"Пополнение на сумму {amount} {self._config.payments.currency}",
        )

    async def pre_add_funds_handler(self, pre_checkout_query: aiogram.types.PreCheckoutQuery) -> None:
        self._logger.log_user_interaction(pre_checkout_query.from_user, self.pre_add_funds_handler.__name__)

        await pre_checkout_query.answer(ok=True)

    async def success_add_funds_handler(self, message: aiogram.types.Message) -> None:
        self._logger.log_user_interaction(message.from_user, self.success_add_funds_handler.__name__)

        # TODO: пополнение баланса (DATABASE)
        markup = aiogram.types.InlineKeyboardMarkup(
            inline_keyboard=[
                [self._buttons.back_to_plans],
            ],
        )
        await self._bot.send_message(
            chat_id=message.chat.id,
            text=f"Баланс пополнен на {int(message.successful_payment.total_amount / self._config.payments.multiplier)} {message.successful_payment.currency}!",
            reply_markup=markup,
        )

    async def add_funds_enter_handler(self, message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext) -> None:
        self._logger.log_user_interaction(message.from_user, f"{self.add_funds_enter_handler.__name__}({message.text})")

        minimum_plan = self._data.plans.plans[models.PlansType.MONTH]
        current_balance = 0  # TODO: текущий баланс пользователя (DATABASE)
        try:
            amount = int(message.text)
            if current_balance + amount < minimum_plan.price or current_balance + amount > self._data.plans.max_balance:
                raise Exception()
            else:
                await self.add_funds_invoice(
                    user=message.from_user,
                    chat=message.chat,
                    amount=amount,
                )
                await state.clear()
        except:
            markup = aiogram.types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [self._buttons.back_to_add_funds],
                ],
            )
            await self._bot.send_message(
                chat_id=message.chat.id,
                text=f"Сумма пополнения должна\nбыть числом от {minimum_plan.price} до {self._data.plans.max_balance - current_balance}!\n\nВведите сумму, на которую\nхотите пополнить баланс:",
                reply_to_message_id=message.message_id,
                reply_markup=markup,
            )
            await state.set_state(self._form.add_funds_enter)
