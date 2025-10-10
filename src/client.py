from __future__ import annotations
import datetime, logging
import aiogram, aiogram.exceptions, aiogram.filters, aiogram.client.default, aiogram.utils.keyboard, \
    aiogram.fsm.context, aiogram.fsm.state
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
        self._database = data.DatabaseManager()
        self._logger = data.LoggerService(
            name=__name__,
            file_handling=self._config.settings.file_logging,
            level=logging.DEBUG if self._config.settings.debug_logging else logging.INFO,
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

    # region Properties and helpers

    @property
    async def clean_username(self) -> str:
        return (await self.user).username[:-3]

    @property
    async def user(self) -> aiogram.types.User:
        if not self._user:
            self._user = (await self._bot.get_me())
        return self._user

    @staticmethod
    def _get_referrer_id(user_id: int, args: str | None) -> int | None:
        try:
            referrer_id = int(args)
            return referrer_id if referrer_id != user_id else None
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

    def _get_subscription_from_string(
            self,
            subscription_string: str,
            replace_string: str = None,
    ) -> models.SubscriptionValues | None:
        if replace_string:
            subscription_string = subscription_string.replace(replace_string, str())
        try:
            return self._database.subscriptions.get_subscription(
                subscription_id=int(subscription_string),
            )
        except ValueError:
            return None

    def _get_amount_with_currency(self, amount: int) -> str:
        return " ".join([str(amount), self._config.payments.currency])

    async def polling_coroutine(self) -> None:
        try:
            await self._bot.delete_webhook(drop_pending_updates=self._config.settings.skip_updates)
            await self.start_polling(self._bot)
        except Exception as e:
            self._logger.log_exception(e)

    # endregion

    # region Handlers

    async def error_handler(self, event: aiogram.types.ErrorEvent) -> None:
        self._logger.log_exception(event.exception)

    async def startup_handler(self) -> None:
        await self._bot.set_my_commands(
            commands=self._COMMANDS,
            scope=aiogram.types.BotCommandScopeDefault(),
            language_code="ru",
        )

        self._logger.info(f"{self.name} started!")

    async def shutdown_handler(self) -> None:
        self._database.close_all()

        self._logger.info(f"{self.name} terminated")

    async def start_handler(self, message: aiogram.types.Message, command: aiogram.filters.CommandObject) -> None:
        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=command.text,
        )

        self._database.users.add_user(
            tg_id=message.from_user.id,
            tg_username=f"@{message.from_user.username}",
            balance=0,
            referrer_id=self._get_referrer_id(message.from_user.id, command.args)
        )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(self._buttons.plans)
        markup_builder.row(self._buttons.subscriptions, self._buttons.profile)

        await self._bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=self._get_message_thread_id(message),
            # (TEXT_PENDING)
            text=f"Добро пожаловать в {(await self.user).full_name}!",
            reply_markup=markup_builder.as_markup(),
        )

    # TODO: /admin
    async def admin_handler(
            self,
            message: aiogram.types.Message,
            command: aiogram.filters.CommandObject,
    ) -> None:
        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{command.text} (admin={message.from_user.id in self._config.settings.admin_list})",
        )

        if message.from_user.id in self._config.settings.admin_list:
            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text="Вы являетесь администратором!",
            )

    async def callback_handler(self, call: aiogram.types.CallbackQuery, state: aiogram.fsm.context.FSMContext) -> None:
        self._logger.log_user_interaction(
            user=call.from_user,
            interaction=call.data,
        )

        self._database.users.add_user(
            tg_id=call.from_user.id,
            tg_username=f"@{call.from_user.username}",
            balance=0,
            referrer_id=None,
        )
        current_user = self._database.users.get_user(
            tg_id=call.from_user.id,
        )

        current_state = await state.get_state()
        if current_state:
            await state.clear()

        try:
            if call.data == "start":
                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(self._buttons.plans)
                markup_builder.row(self._buttons.subscriptions, self._buttons.profile)

                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    # (TEXT_PENDING)
                    text=f"Добро пожаловать в {(await self.user).full_name}!",
                    reply_markup=markup_builder.as_markup(),
                )
            elif call.data == "plans":
                plans_buttons = [getattr(self._buttons, f"plans_{i.name}") for i in models.PlansType]

                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(*plans_buttons[:len(plans_buttons) // 2])
                markup_builder.row(*plans_buttons[len(plans_buttons) // 2:])
                markup_builder.row(self._buttons.back_to_start)

                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    # (TEXT_PENDING)
                    text="Выберите тариф:",
                    reply_markup=markup_builder.as_markup(),
                )
            elif (current_plan_type := self._get_plan_from_string(call.data, "plans_")) in models.PlansType:
                current_plan = self._data.plans.plans[current_plan_type]

                view_profile_button = self._buttons.view_profile.copy()
                view_profile_button.text = self._get_amount_with_currency(
                    amount=current_user.balance,
                )

                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(getattr(self._buttons, f"plans_subscribe_{current_plan_type.name}"))
                markup_builder.row(view_profile_button, self._buttons.back_to_plans)

                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"Тариф «{current_plan.name}»\n{current_plan.description}\n\nПериод подписки: {current_plan.months * 30} дней",
                    reply_markup=markup_builder.as_markup(),
                )
            elif (current_plan_type := self._get_plan_from_string(call.data, "plans_subscribe_")) in models.PlansType:
                current_plan = self._data.plans.plans[current_plan_type]

                if current_plan.price * current_plan.months <= current_user.balance:
                    self._database.users.reduce_balance(
                        tg_id=call.from_user.id,
                        amount=current_plan.price * current_plan.months,
                    )
                    datetime_subscribed = datetime.datetime.now()
                    self._database.payments.add_payment(
                        tg_id=call.from_user.id,
                        payment_amount=-(current_plan.price * current_plan.months),
                        payment_currency=self._config.payments.currency,
                        provider_payment_id=None,
                        payment_date=int(datetime_subscribed.timestamp()),
                    )
                    self._database.subscriptions.add_subscription(
                        tg_id=call.from_user.id,
                        plan_id=current_plan_type.value,
                        payment_amount=current_plan.price * current_plan.months,
                        subscribed_date=int(datetime_subscribed.timestamp()),
                        expires_date=int(
                            (datetime_subscribed + datetime.timedelta(
                                days=current_plan.months * 30,
                            )).timestamp()
                        )
                    )
                    try:
                        await self._bot.delete_message(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                        )
                    finally:
                        # TODO: выдача ключа (DATABASE)
                        await self.send_config(
                            call=call,
                            config_key=str(None),
                        )
                else:
                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.view_add_funds)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"Пополните баланс на {self._get_amount_with_currency(amount=current_plan.price * current_plan.months - current_user.balance)}\nдля подписки на «{current_plan.name}»!",
                        reply_markup=markup_builder.as_markup(),
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
            elif call.data == "subscriptions":
                current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                    tg_id=call.from_user.id,
                )

                if current_subscriptions:
                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    for i in current_subscriptions:
                        button = self._buttons.view_subscription.copy()
                        button.text = button.text.format(i.subscription_id, self._data.plans.plans[i.plan_id].name)
                        button.callback_data = button.callback_data.format(i.subscription_id)
                        markup_builder.row(button)
                    markup_builder.row(self._buttons.back_to_start)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        # (TEXT_PENDING)
                        text="Выберите подписку:",
                        reply_markup=markup_builder.as_markup(),
                    )
                else:
                    await self._bot.answer_callback_query(
                        callback_query_id=call.id,
                        # (TEXT_PENDING)
                        text="У вас нет активных подписок!",
                        show_alert=True,
                    )
            elif isinstance(
                    current_subscription := self._get_subscription_from_string(call.data, "view_subscription_"),
                    models.SubscriptionValues,
            ):
                view_subscription_config_button = self._buttons.view_subscription_config.copy()
                view_subscription_config_button.callback_data = view_subscription_config_button.callback_data.format(
                    current_subscription.subscription_id,
                )

                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(view_subscription_config_button)
                markup_builder.row(self._buttons.back_to_subscriptions)

                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    # (TEXT_PENDING)
                    text=f"Подписка #{current_subscription.subscription_id}\nТариф «{self._data.plans.plans[current_subscription.plan_id].name}»\n\nДата подписки:\n{datetime.datetime.fromtimestamp(current_subscription.subscribed_date).strftime("%d.%m.%y %H:%M")}\nИстекает:\n{datetime.datetime.fromtimestamp(current_subscription.expires_date).strftime("%d.%m.%y %H:%M")}",
                    reply_markup=markup_builder.as_markup(),
                )
            elif isinstance(
                    current_subscription := self._get_subscription_from_string(call.data, "view_subscription_config_"),
                    models.SubscriptionValues,
            ):
                try:
                    await self._bot.delete_message(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                    )
                finally:
                    # TODO: выдача ключа (DATABASE)
                    await self.send_config(
                        call=call,
                        config_key=str(None),
                    )
            elif call.data == "profile":
                current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                    tg_id=call.from_user.id,
                )

                invite_friend_button = self._buttons.invite_friend.copy()
                invite_friend_button.copy_text = aiogram.types.CopyTextButton(
                    text=f"https://t.me/{(await self.user).username}?start={call.from_user.id}",
                )

                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(self._buttons.add_funds)
                markup_builder.row(invite_friend_button, self._buttons.back_to_start)

                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    # (TEXT_PENDING)
                    text=f"Профиль {call.from_user.full_name}:\n\nБаланс: {self._get_amount_with_currency(current_user.balance)}\nАктивных подписок: {len(current_subscriptions)}\nПриглашено друзей: {self._database.users.get_ref_count(tg_id=current_user.tg_id)}\n\nUser ID: <code>{call.from_user.id}</code>",
                    reply_markup=markup_builder.as_markup(),
                )
            elif call.data == "add_funds":
                plans_buttons = [getattr(self._buttons, f"add_funds_{i.name}") for i in models.PlansType]

                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(self._buttons.add_funds_enter)
                markup_builder.row(*plans_buttons[:len(plans_buttons) // 2])
                markup_builder.row(*plans_buttons[len(plans_buttons) // 2:])
                markup_builder.row(self._buttons.back_to_profile)

                await self._bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    # (TEXT_PENDING)
                    text="Пополнение баланса",
                    reply_markup=markup_builder.as_markup(),
                )
            elif call.data == "add_funds_enter":
                if current_user.balance + self._minimum_plan.price * self._minimum_plan.months < self._config.payments.max_balance:
                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.back_to_add_funds)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"Введите сумму, на которую\nхотите пополнить баланс\n(число от {self._minimum_plan.price * self._minimum_plan.months} до {self._config.payments.max_balance - current_user.balance}):",
                        reply_markup=markup_builder.as_markup(),
                    )
                    await state.set_state(self._form.add_funds_enter)
                else:
                    await self._bot.answer_callback_query(
                        callback_query_id=call.id,
                        text="Сейчас вы не можете выбрать сумму пополнения!",
                        show_alert=True,
                    )
            elif (current_plan_type := self._get_plan_from_string(call.data, "add_funds_")) in models.PlansType:
                current_plan = self._data.plans.plans[current_plan_type]

                if current_user.balance + current_plan.price * current_plan.months < self._config.payments.max_balance:
                    try:
                        await self._bot.delete_message(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                        )
                    finally:
                        await self.add_funds_invoice(
                            user=call.from_user,
                            chat=call.message.chat,
                            amount=current_plan.price * current_plan.months,
                        )
                else:
                    await self._bot.answer_callback_query(
                        callback_query_id=call.id,
                        text=f"Сумма пополнения превышает максимальную ({self._get_amount_with_currency(self._config.payments.max_balance - current_user.balance)})!",
                        show_alert=True,
                    )
            else:
                await self._bot.answer_callback_query(
                    callback_query_id=call.id,
                    text="Эта кнопка недоступна!",
                    show_alert=True,
                )
        except Exception as e:
            if e is not aiogram.exceptions.TelegramBadRequest:
                self._logger.log_exception(e)
        finally:
            await self._bot.answer_callback_query(callback_query_id=call.id)

    async def send_config(self, call: aiogram.types.CallbackQuery, config_key: str) -> None:
        self._logger.log_user_interaction(
            user=call.from_user,
            interaction=f"{self.send_config.__name__}(config_key={config_key})",
        )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(self._buttons.config_copy_settings)
        markup_builder.row(self._buttons.download_amnezia)

        await self._bot.send_document(
            chat_id=call.message.chat.id,
            message_thread_id=self._get_message_thread_id(call.message),
            document=aiogram.types.BufferedInputFile(
                file=bytes(config_key, encoding="utf8"),
                filename=f"{await self.clean_username}_config.vpn"
            ),
            caption="Ваш файл конфигурации\nдоступен для скачивания!",
            reply_markup=markup_builder.as_markup(),
        )

    async def add_funds_invoice(self, user: aiogram.types.User, chat: aiogram.types.Chat, amount: int) -> None:
        self._logger.log_user_interaction(
            user=user,
            interaction=f"{self.add_funds_invoice.__name__}(amount={amount})",
        )

        await self._bot.send_invoice(
            chat_id=chat.id,
            prices=[
                aiogram.types.LabeledPrice(
                    label=f"Счёт на сумму {self._get_amount_with_currency(amount)}",
                    amount=amount * self._config.payments.multiplier,
                ),
            ],
            currency=self._config.payments.currency,
            provider_token=self._config.payments.provider_token,
            payload=" ".join((str(user.id), self._get_amount_with_currency(amount))),
            title="Пополнение баланса",
            description=f"Счёт на сумму {self._get_amount_with_currency(amount)}",
        )

    async def pre_add_funds_handler(self, pre_checkout_query: aiogram.types.PreCheckoutQuery) -> None:
        self._logger.log_user_interaction(
            user=pre_checkout_query.from_user,
            interaction=self.pre_add_funds_handler.__name__,
        )

        self._database.users.add_user(
            tg_id=pre_checkout_query.from_user.id,
            tg_username=f"@{pre_checkout_query.from_user.username}",
            balance=0,
            referrer_id=None,
        )
        current_user = self._database.users.get_user(
            tg_id=pre_checkout_query.from_user.id,
        )

        await pre_checkout_query.answer(
            ok=self._minimum_plan.price * self._minimum_plan.months <= current_user.balance + pre_checkout_query.total_amount / self._config.payments.multiplier <= self._config.payments.max_balance,
            error_message=f"Сумма пополнения превышает максимальную ({self._get_amount_with_currency(self._config.payments.max_balance - current_user.balance)})!",
        )

    async def success_add_funds_handler(self, message: aiogram.types.Message) -> None:
        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=self.success_add_funds_handler.__name__,
        )

        successful_payment_date = datetime.datetime.now()
        self._database.payments.add_payment(
            tg_id=message.from_user.id,
            payment_amount=int(message.successful_payment.total_amount / self._config.payments.multiplier),
            payment_currency=message.successful_payment.currency,
            provider_payment_id=message.successful_payment.provider_payment_charge_id,
            payment_date=int(successful_payment_date.timestamp()),
        )
        self._database.users.add_balance(
            tg_id=message.from_user.id,
            amount=int(message.successful_payment.total_amount / self._config.payments.multiplier)
        )

        try:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.view_start)

            await self._bot.send_message(
                chat_id=message.chat.id,
                # (TEXT_PENDING)
                text=f"Баланс пополнен на {self._get_amount_with_currency(int(message.successful_payment.total_amount / self._config.payments.multiplier))}!",
                reply_markup=markup_builder.as_markup(),
            )
        except aiogram.exceptions.TelegramForbiddenError as e:
            self._logger.log_exception(e)

    async def add_funds_enter_handler(
            self,
            message: aiogram.types.Message,
            state: aiogram.fsm.context.FSMContext,
    ) -> None:
        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{self.add_funds_enter_handler.__name__} (amount={message.text})",
        )

        self._database.users.add_user(
            tg_id=message.from_user.id,
            tg_username=f"@{message.from_user.username}",
            balance=0,
            referrer_id=None,
        )
        current_user = self._database.users.get_user(
            tg_id=message.from_user.id,
        )

        try:
            amount = int(message.text)

            if self._minimum_plan.price * self._minimum_plan.months <= current_user.balance + amount <= self._config.payments.max_balance and self._minimum_plan.price * self._minimum_plan.months < amount:
                await self.add_funds_invoice(
                    user=message.from_user,
                    chat=message.chat,
                    amount=amount,
                )
                await state.clear()
            else:
                raise Exception()
        except:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.back_to_add_funds)

            await self._bot.send_message(
                chat_id=message.chat.id,
                text=f"Сумма пополнения должна\nбыть числом от {self._minimum_plan.price * self._minimum_plan.months} до {self._config.payments.max_balance - current_user.balance}!\n\nВведите сумму, на которую\nхотите пополнить баланс:",
                reply_to_message_id=message.message_id,
                reply_markup=markup_builder.as_markup(),
            )
            await state.set_state(self._form.add_funds_enter)

    # endregion
