# TODO: (REFACTOR)

from __future__ import annotations
import datetime, logging
import aiogram, aiogram.exceptions, aiogram.filters, aiogram.client.default, aiogram.fsm.context, aiogram.fsm.state
import models, data, misc


class AiogramClient(aiogram.Dispatcher):
    _COMMANDS = [
        aiogram.types.BotCommand(command="start", description="Запустить бота"),
    ]

    class Form(aiogram.fsm.state.StatesGroup):
        add_funds_enter = aiogram.fsm.state.State()

    def __init__(self) -> None:
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()
        self._db_users = data.UsersDatabaseManager()
        self._logger = data.LoggerService(
            name=__name__,
            file_handling=self._config.settings.file_logging,
            level=logging.INFO,
        )
        self._buttons = misc.ButtonsContainer()
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

        self.errors.register(self.error_handler)
        self.startup.register(self.startup_handler)
        self.shutdown.register(self.shutdown_handler)
        self.message.register(self.start_handler, aiogram.filters.Command("start"))
        self.message.register(self.admin_handler, aiogram.filters.Command("admin"))
        self.message.register(self.success_add_funds_handler, aiogram.F.successful_payment)
        self.pre_checkout_query.register(self.pre_add_funds_handler)
        self._form_router.callback_query.register(self.callback_handler)
        self._form_router.message.register(self.add_funds_enter_handler, self._form.add_funds_enter)

        self._minimum_plan = self._data.plans.plans[models.PlansType.MONTH]
        self._time_started = datetime.datetime.now(tz=datetime.timezone.utc)
        self._logger.info(f"{self.name} initialized!")

    # Properties and helpers
    @property
    async def clean_username(self) -> str:
        return (await self.user).username[:-3]

    @property
    async def user(self) -> aiogram.types.User:
        if not self._user:
            self._user = (await self._bot.get_me())
        return self._user

    @staticmethod
    def _get_ref_id(user_id: int, args: str | None) -> int | None:
        try:
            ref_id = int(args)
            return ref_id if ref_id != user_id else None
        except:
            return None

    @staticmethod
    def _get_message_thread_id(message: aiogram.types.Message) -> int | None:
        if message.reply_to_message and message.reply_to_message.is_topic_message:
            return message.reply_to_message.message_thread_id
        elif message.is_topic_message:
            return message.message_thread_id
        else:
            return None

    @staticmethod
    def _get_plan_from_string(plan_string: str, replace_string: str = None) -> models.PlansType | None:
        if replace_string:
            plan_string = plan_string.replace(replace_string, str())
        try:
            return models.PlansType[plan_string]
        except KeyError:
            return None

    def _get_amount_with_currency(self, amount: int, use_sign: bool = True) -> str:
        return str(amount) + self._data.plans.currency_sign if use_sign else self._data.plans.currency

    async def polling_coroutine(self) -> None:
        try:
            await self._bot.delete_webhook(drop_pending_updates=self._config.settings.skip_updates)
            await self.start_polling(self._bot)
        except Exception as e:
            self._logger.log_exception(e)

    # Handlers
    async def error_handler(self, event: aiogram.types.ErrorEvent) -> None:
        self._logger.log_exception(event.exception)

    async def startup_handler(self) -> None:
        await self._bot.set_my_commands(
            commands=self._COMMANDS,
            scope=aiogram.types.BotCommandScopeDefault(),
            language_code="ru",
        )

    async def shutdown_handler(self) -> None:
        self._db_users.close()
        self._logger.info(f"{self.name} terminated")

    async def start_handler(self, message: aiogram.types.Message, command: aiogram.filters.CommandObject) -> None:
        self._logger.log_user_interaction(message.from_user, command.text)

        self._db_users.add_user(
            tg_id=message.from_user.id,
            tg_username=f"@{message.from_user.username}",
            balance=0,
            ref_id=self._get_ref_id(message.from_user.id, command.args)
        )

        markup = aiogram.types.InlineKeyboardMarkup(
            inline_keyboard=[
                [self._buttons.plans],
                [self._buttons.subscriptions, self._buttons.profile],
            ],
        )
        await self._bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=self._get_message_thread_id(message),
            text=f"Добро пожаловать в {(await self.user).full_name}!",
            reply_markup=markup,
        )

    async def admin_handler(self, message: aiogram.types.Message, command: aiogram.filters.CommandObject) -> None:
        self._logger.log_user_interaction(message.from_user, f"{command.text} (admin={message.from_user.id in self._config.settings.admin_list})")

        if message.from_user.id in self._config.settings.admin_list:
            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text="Вы являетесь администратором!",
            )

    async def callback_handler(self, call: aiogram.types.CallbackQuery, state: aiogram.fsm.context.FSMContext) -> None:
        self._logger.log_user_interaction(call.from_user, call.data)

        self._db_users.add_user(
            tg_id=call.from_user.id,
            tg_username=f"@{call.from_user.username}",
            balance=0,
            ref_id=None,
        )
        current_user = self._db_users.get_user(
            tg_id=call.from_user.id,
        )

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
            elif call.data == "plans":
                plans_buttons = [getattr(self._buttons, f"plans_{i.name}") for i in models.PlansType]
                markup = aiogram.types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        plans_buttons[:len(plans_buttons) // 2],
                        plans_buttons[len(plans_buttons) // 2:],
                        [self._buttons.back_to_start],
                    ],
                )
                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Выберите тариф:",
                    reply_markup=markup,
                )
            elif self._get_plan_from_string(call.data, "plans_") in [i for i in models.PlansType]:
                selected_plan_type = self._get_plan_from_string(call.data, "plans_")
                selected_plan = self._data.plans.plans[selected_plan_type]
                markup = aiogram.types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [getattr(self._buttons, f"plans_subscribe_{selected_plan_type.name}")],
                        [self._buttons.back_to_plans],
                    ],
                )
                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Тариф «{selected_plan.name}»:\n{selected_plan.description}\n\nПериод подписки: {selected_plan.months * 30} дней",
                    reply_markup=markup,
                )
            elif self._get_plan_from_string(call.data, "plans_subscribe_") in [i for i in models.PlansType]:
                selected_plan_type = self._get_plan_from_string(call.data, "plans_subscribe_")
                selected_plan = self._data.plans.plans[selected_plan_type]

                if selected_plan.price * selected_plan.months <= current_user.balance:
                    pass  # TODO: подписка на тариф (DATABASE)
                else:
                    markup = aiogram.types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [self._buttons.view_add_funds],
                        ],
                    )
                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"Пополните баланс для\nподписки на «{selected_plan.name}»!",
                        reply_markup=markup,
                    )
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
                    text=f"Профиль {call.from_user.full_name}:\n\nБаланс: {self._get_amount_with_currency(current_user.balance)}\nПриглашено друзей: {self._db_users.get_ref_count(tg_id=current_user.tg_id)}\n\nUser ID: <code>{call.from_user.id}</code>",
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
                if current_user.balance + self._minimum_plan.price < self._data.plans.max_balance:
                    markup = aiogram.types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [self._buttons.cancel_to_add_funds],
                        ],
                    )
                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="Введите сумму, на которую\nхотите пополнить баланс:",
                        reply_markup=markup,
                    )
                    await state.set_state(self._form.add_funds_enter)
                else:
                    await self._bot.answer_callback_query(
                        callback_query_id=call.id,
                        text="Сумма для пополнения не может быть указана!",
                        show_alert=True,
                    )
            elif call.data.replace("add_funds_", str()) in [i.name for i in models.PlansType]:
                selected_plan_type = models.PlansType[call.data.replace("add_funds_", str())]
                selected_plan = self._data.plans.plans[selected_plan_type]
                # TODO: проверка баланса пользователя (DATABASE)
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
                        message_thread_id=self._get_message_thread_id(call.message),
                        text=f"Настройки для подключения:\n<pre>{config_key}</pre>",
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
            message_thread_id=self._get_message_thread_id(call.message),
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
            prices=[aiogram.types.LabeledPrice(label=f"Счёт на сумму {self._get_amount_with_currency(amount)}", amount=amount * self._data.plans.multiplier)],
            currency=self._data.plans.currency,
            provider_token=self._config.settings.provider_token,
            payload=" ".join((str(user.id), self._get_amount_with_currency(amount, use_sign=False))),
            title="Пополнение баланса",
            description=f"Счёт на сумму {self._get_amount_with_currency(amount)}",
        )

    async def pre_add_funds_handler(self, pre_checkout_query: aiogram.types.PreCheckoutQuery) -> None:
        self._logger.log_user_interaction(pre_checkout_query.from_user, self.pre_add_funds_handler.__name__)

        self._db_users.add_user(
            tg_id=pre_checkout_query.from_user.id,
            tg_username=f"@{pre_checkout_query.from_user.username}",
            balance=0,
            ref_id=None,
        )
        current_user = self._db_users.get_user(
            tg_id=pre_checkout_query.from_user.id,
        )

        await pre_checkout_query.answer(
            ok=self._minimum_plan.price <= current_user.balance + pre_checkout_query.total_amount / self._data.plans.multiplier <= self._data.plans.max_balance,
            error_message="Сумма пополнения выше максимальной!",
        )

    async def success_add_funds_handler(self, message: aiogram.types.Message) -> None:
        self._logger.log_user_interaction(message.from_user, self.success_add_funds_handler.__name__)

        self._db_users.add_balance(
            tg_id=message.from_user.id,
            amount=int(message.successful_payment.total_amount / self._data.plans.multiplier)
        )

        markup = aiogram.types.InlineKeyboardMarkup(
            inline_keyboard=[
                [self._buttons.view_plans],
            ],
        )
        try:
            await self._bot.send_message(
                chat_id=message.chat.id,
                text=f"Баланс пополнен на {self._get_amount_with_currency(int(message.successful_payment.total_amount / self._data.plans.multiplier))}!",
                reply_markup=markup,
            )
        except aiogram.exceptions.TelegramForbiddenError as e:
            self._logger.log_exception(e)

    async def add_funds_enter_handler(self, message: aiogram.types.Message, state: aiogram.fsm.context.FSMContext) -> None:
        self._logger.log_user_interaction(message.from_user, f"{self.add_funds_enter_handler.__name__}({message.text})")

        self._db_users.add_user(
            tg_id=message.from_user.id,
            tg_username=f"@{message.from_user.username}",
            balance=0,
            ref_id=None,
        )
        current_user = self._db_users.get_user(
            tg_id=message.from_user.id,
        )

        try:
            amount = int(message.text)
            if self._minimum_plan.price <= current_user.balance + amount <= self._data.plans.max_balance:
                await self.add_funds_invoice(
                    user=message.from_user,
                    chat=message.chat,
                    amount=amount,
                )
                await state.clear()
            else:
                raise Exception()
        except:
            markup = aiogram.types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [self._buttons.cancel_to_add_funds],
                ],
            )
            await self._bot.send_message(
                chat_id=message.chat.id,
                text=f"Сумма пополнения должна\nбыть числом от {self._minimum_plan.price} до {self._data.plans.max_balance - current_user.balance}!\n\nВведите сумму, на которую\nхотите пополнить баланс:",
                reply_to_message_id=message.message_id,
                reply_markup=markup,
            )
            await state.set_state(self._form.add_funds_enter)
