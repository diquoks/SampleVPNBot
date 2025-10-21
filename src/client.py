from __future__ import annotations
import itertools, datetime, logging, math
import aiogram, aiogram.exceptions, aiogram.filters, aiogram.client.default, aiogram.utils.keyboard, \
    aiogram.fsm.context, aiogram.fsm.state
import models, data, misc


class AiogramClient(aiogram.Dispatcher):
    _COMMANDS = [
        aiogram.types.BotCommand(command="start", description="Запустить бота"),
    ]

    class States(aiogram.fsm.state.StatesGroup):
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
        self._states = self.States()
        self._states_router = aiogram.Router()
        self._bot = aiogram.Bot(
            token=self._config.settings.bot_token,
            default=aiogram.client.default.DefaultBotProperties(
                parse_mode=aiogram.enums.ParseMode.HTML,
            ),
        )
        super().__init__(name="VastNetVPNDispatcher")
        self.include_router(self._states_router)

        self.errors.register(self.error_handler)
        self.startup.register(self.startup_handler)
        self.shutdown.register(self.shutdown_handler)
        self.message.register(self.start_handler, aiogram.filters.Command("start"))
        self.message.register(self.admin_handler, aiogram.filters.Command("admin"))
        self._states_router.callback_query.register(self.callback_handler)
        self.pre_checkout_query.register(self.pre_add_funds_handler)
        self.message.register(self.success_add_funds_handler, aiogram.F.successful_payment)
        self._states_router.message.register(self.add_funds_enter_handler, self._states.add_funds_enter)

        self._minimum_plan = self._data.plans.plans[data.Constants.MINIMUM_PLAN]
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
    def _get_message_thread_id(message: aiogram.types.Message) -> int | None:
        if message.reply_to_message and message.reply_to_message.is_topic_message:
            return message.reply_to_message.message_thread_id
        elif message.is_topic_message:
            return message.message_thread_id
        else:
            return None

    def _get_referrer_id(self, user_id: int, args: str | None) -> int | None:
        try:
            referrer_id = int(args)

            referrer_user = self._database.users.get_user(
                tg_id=referrer_id,
            )

            return referrer_id if referrer_id != user_id and referrer_user else None
        except:
            return None

    def _get_amount_with_currency(self, amount: int) -> str:
        return f"{amount} {self._config.payments.currency}"

    def _get_page_buttons(
            self,
            page: str,
            page_items: list,
            current_page_id: int,
            current_user_id: int | None = None,
    ) -> tuple[
        aiogram.types.InlineKeyboardButton,
        aiogram.types.InlineKeyboardButton,
        aiogram.types.InlineKeyboardButton,
    ]:
        previous_page_id = current_page_id - 1
        next_page_id = current_page_number = current_page_id + 1
        total_pages_count = math.ceil(len(page_items) / data.Constants.ELEMENTS_PER_PAGE)

        page_previous_button = self._buttons.page_previous.model_copy()
        page_previous_button.callback_data = " ".join(i for i in [
            page,
            str(previous_page_id),
            str(current_user_id) if current_user_id else None,
        ] if i) if previous_page_id >= data.Constants.FIRST_PAGE_ID else "just_answer"

        page_info_button = self._buttons.page_info.model_copy()
        page_info_button.text = page_info_button.text.format(
            current_page_number,
            total_pages_count,
            len(page_items),
        )
        page_info_button.callback_data = " ".join(i for i in [
            page,
            str(data.Constants.FIRST_PAGE_ID),
            str(current_user_id) if current_user_id else None,
        ] if i) if current_page_id != data.Constants.FIRST_PAGE_ID else "just_answer"

        page_next_button = self._buttons.page_next.model_copy()
        page_next_button.callback_data = " ".join(i for i in [
            page,
            str(next_page_id),
            str(current_user_id) if current_user_id else None,
        ] if i) if next_page_id < total_pages_count else "just_answer"

        return page_previous_button, page_info_button, page_next_button

    async def polling_coroutine(self) -> None:
        try:
            await self._bot.delete_webhook(drop_pending_updates=self._config.settings.skip_updates)
            await self.start_polling(self._bot)
        except Exception as e:
            self._logger.log_exception(e)

    async def subscription_config_file(self, call: aiogram.types.CallbackQuery, subscription_id: int) -> None:
        current_subscription = self._database.subscriptions.get_subscription(
            subscription_id=subscription_id,
        )

        config_key = str(None)  # TODO: выдача ключа (DATABASE)

        subscription_config_copy_button = self._buttons.subscription_config_copy.model_copy()
        subscription_config_copy_button.callback_data = subscription_config_copy_button.callback_data.format(
            subscription_id,
        )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(subscription_config_copy_button)
        markup_builder.row(self._buttons.subscription_config_download)
        markup_builder.row(self._buttons.delete_to_start)

        try:
            await self._bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
        finally:
            await self._bot.send_document(
                chat_id=call.message.chat.id,
                message_thread_id=self._get_message_thread_id(call.message),
                document=aiogram.types.BufferedInputFile(
                    file=bytes(config_key, encoding="utf8"),
                    filename=f"{await self.clean_username}_config.vpn"
                ),
                caption=(
                    "Ваш файл конфигурации\n"
                    "доступен для скачивания!\n"
                ),
                reply_markup=markup_builder.as_markup(),
            )

    async def subscription_config_copy(self, call: aiogram.types.CallbackQuery, subscription_id: int) -> None:
        current_subscription = self._database.subscriptions.get_subscription(
            subscription_id=subscription_id,
        )

        config_key = str(None)  # TODO: выдача ключа (DATABASE)

        subscription_config_file_button = self._buttons.subscription_config_file.model_copy()
        subscription_config_file_button.callback_data = subscription_config_file_button.callback_data.format(
            subscription_id,
        )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(subscription_config_file_button)
        markup_builder.row(self._buttons.subscription_config_download)
        markup_builder.row(self._buttons.delete_to_start)

        try:
            await self._bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
        finally:
            await self._bot.send_message(
                chat_id=call.message.chat.id,
                message_thread_id=self._get_message_thread_id(call.message),
                text=(
                    f"Ключ для подключения:\n"
                    f"<pre>{config_key}</pre>\n"
                ),
                reply_markup=markup_builder.as_markup(),
            )

    async def delete_and_send_start(self, call: aiogram.types.CallbackQuery) -> None:
        try:
            await self._bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
        finally:
            profile_invite_button = self._buttons.invite.model_copy()
            profile_invite_button.copy_text = aiogram.types.CopyTextButton(
                text=f"https://t.me/{(await self.user).username}?start={call.from_user.id}",
            )

            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.plans)
            markup_builder.row(self._buttons.add_funds)
            markup_builder.row(profile_invite_button)
            markup_builder.row(self._buttons.subscriptions, self._buttons.profile)

            await self._bot.send_message(
                chat_id=call.message.chat.id,
                text=(
                    f"<b>Добро пожаловать в {(await self.user).full_name}!</b>\n"
                    f"\n"
                    f"Благодарим за выбор нашего сервиса,\n"
                    f"ваша безопасность — наш приоритет!\n"
                ),
                reply_markup=markup_builder.as_markup(),
            )

    async def add_funds_invoice(
            self,
            message: aiogram.types.Message,
            chat: aiogram.types.Chat,
            amount: int,
    ) -> None:
        await self._bot.send_invoice(
            chat_id=chat.id,
            message_thread_id=self._get_message_thread_id(message),
            prices=[
                aiogram.types.LabeledPrice(
                    label=f"Счёт на сумму {self._get_amount_with_currency(amount)}",
                    amount=amount * self._config.payments.currency_multiplier,
                ),
            ],
            currency=self._config.payments.currency,
            provider_token=self._config.payments.provider_token,
            payload=f"{self.add_funds_invoice.__name__} {amount}",
            title="Пополнение баланса",
            description=f"Счёт на сумму {self._get_amount_with_currency(amount)}",
        )

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
            balance=int(),
            referrer_id=self._get_referrer_id(message.from_user.id, command.args)
        )

        profile_invite_button = self._buttons.invite.model_copy()
        profile_invite_button.copy_text = aiogram.types.CopyTextButton(
            text=f"https://t.me/{(await self.user).username}?start={message.from_user.id}",
        )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(self._buttons.plans)
        markup_builder.row(self._buttons.add_funds)
        markup_builder.row(profile_invite_button)
        markup_builder.row(self._buttons.subscriptions, self._buttons.profile)

        await self._bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=self._get_message_thread_id(message),
            text=(
                f"<b>Добро пожаловать в {(await self.user).full_name}!</b>\n"
                f"\n"
                f"Благодарим за выбор нашего сервиса,\n"
                f"ваша безопасность — наш приоритет!\n"
            ),
            reply_markup=markup_builder.as_markup(),
        )

    async def admin_handler(
            self,
            message: aiogram.types.Message,
            command: aiogram.filters.CommandObject,
    ) -> None:
        is_admin = message.from_user.id in self._config.settings.admin_list

        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{command.text} ({is_admin=})",
        )

        if is_admin:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.admin_users, self._buttons.admin_configs)
            markup_builder.row(self._buttons.admin_subscriptions, self._buttons.admin_payments)
            markup_builder.row(self._buttons.admin_logs, self._buttons.admin_settings)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=f"Добро пожаловать, {message.from_user.full_name}!",
                reply_markup=markup_builder.as_markup(),
            )

    async def callback_handler(self, call: aiogram.types.CallbackQuery, state: aiogram.fsm.context.FSMContext) -> None:
        current_state = await state.get_state()
        if current_state:
            await state.clear()

        self._logger.log_user_interaction(
            user=call.from_user,
            interaction=call.data,
        )

        self._database.users.add_user(
            tg_id=call.from_user.id,
            tg_username=f"@{call.from_user.username}",
            balance=int(),
            referrer_id=None,
        )

        current_user = self._database.users.get_user(
            tg_id=call.from_user.id,
        )

        try:
            match call.data.split():
                case ["start"]:
                    profile_invite_button = self._buttons.invite.model_copy()
                    profile_invite_button.copy_text = aiogram.types.CopyTextButton(
                        text=f"https://t.me/{(await self.user).username}?start={call.from_user.id}",
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.plans)
                    markup_builder.row(self._buttons.add_funds)
                    markup_builder.row(profile_invite_button)
                    markup_builder.row(self._buttons.subscriptions, self._buttons.profile)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=(
                            f"<b>Добро пожаловать в {(await self.user).full_name}!</b>\n"
                            f"\n"
                            f"Благодарим за выбор нашего сервиса,\n"
                            f"ваша безопасность — наш приоритет!\n"
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["plans"]:
                    plan_buttons = [getattr(self._buttons, f"plan_{plan_type.value}") for plan_type in models.PlansType]

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    for buttons_row in itertools.batched(
                            plan_buttons,
                            data.Constants.ELEMENTS_PER_ROW,
                    ):
                        markup_builder.row(*buttons_row)
                    markup_builder.row(self._buttons.back_to_start)

                    # (TEXT_PENDING)
                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="Выберите тариф:",
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["add_funds"]:
                    add_funds_buttons = [
                        getattr(self._buttons, f"add_funds_{plan_type.value}") for plan_type in models.PlansType
                    ]

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.add_funds_enter)
                    for buttons_row in itertools.batched(
                            add_funds_buttons,
                            data.Constants.ELEMENTS_PER_ROW,
                    ):
                        markup_builder.row(*buttons_row)
                    markup_builder.row(self._buttons.back_to_start)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=(
                            "Выберите нужную сумму для\n"
                            "пополнения или введите свою:\n"
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["subscriptions", current_page_id]:
                    current_page_id = int(current_page_id)

                    current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                        tg_id=call.from_user.id,
                    )

                    if current_subscriptions:
                        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                        subscription: models.SubscriptionValues
                        for subscription in list(
                                itertools.batched(
                                    current_subscriptions,
                                    data.Constants.ELEMENTS_PER_PAGE,
                                )
                        )[current_page_id]:
                            button = self._buttons.page_item_subscription.model_copy()
                            button.text = button.text.format(
                                subscription.subscription_id,
                                self._data.plans.plans[subscription.plan_id].name,
                            )
                            button.callback_data = f"subscription {subscription.subscription_id}"
                            markup_builder.row(button)
                        markup_builder.row(
                            *self._get_page_buttons(
                                page="subscriptions",
                                page_items=current_subscriptions,
                                current_page_id=current_page_id,
                            )
                        )
                        markup_builder.row(self._buttons.back_to_start)

                        # (TEXT_PENDING)
                        await self._bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text="Выберите подписку:",
                            reply_markup=markup_builder.as_markup(),
                        )
                    else:
                        await self._bot.answer_callback_query(
                            callback_query_id=call.id,
                            text="У вас нет активных подписок!",
                            show_alert=True,
                        )
                case ["profile"]:
                    referrer_user = self._database.users.get_user(
                        tg_id=current_user.referrer_id,
                    ) if current_user.referrer_id else None

                    current_referrer_model = self._data.referrers.get_referrer_by_id(
                        tg_id=current_user.tg_id,
                    )

                    current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                        tg_id=call.from_user.id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.back_to_start)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=(
                                 f"Профиль {call.from_user.full_name}:\n"
                                 f"\n"
                                 f"<b>Баланс: {self._get_amount_with_currency(current_user.balance)}</b>\n"
                                 f"Активных подписок: {len(current_subscriptions)}\n"
                                 f"Приглашено друзей: {self._database.users.get_ref_count(tg_id=current_user.tg_id)}\n"
                             ) + (
                                 f"\n"
                                 f"<b>Реферальные выплаты:</b>\n"
                                 f"Первое пополнение: <b>{(current_referrer_model.multiplier_first if current_referrer_model else self._config.referral.multiplier_first):.0%}</b>\n"
                                 f"Следующие пополнения: <b>{(current_referrer_model.multiplier_common if current_referrer_model else self._config.referral.multiplier_common):.0%}</b>\n"
                             ) + (
                                 (
                                     f"\n"
                                     f"Пригласил: {referrer_user.tg_username if referrer_user.tg_username else f"<code>{referrer_user.tg_id}</code>"}\n"
                                 ) if referrer_user else str()
                             ) + (
                                 f"\n"
                                 f"User ID: <code>{call.from_user.id}</code>\n"
                             ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["plan", current_plan_id]:
                    current_plan_id = int(current_plan_id)
                    current_plan = self._data.plans.plans[current_plan_id]

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(getattr(self._buttons, f"plan_subscribe_{current_plan_id}"))
                    markup_builder.row(self._buttons.back_to_plans)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=(
                            f"<b>Тариф «{current_plan.name}»</b>\n"
                            f"{current_plan.description}\n"
                            f"\n"
                            f"Период подписки: {current_plan.months * data.Constants.DAYS_IN_MONTH} дней\n"
                            f"\n"
                            f"<b>(Текущий баланс: {self._get_amount_with_currency(current_user.balance)})</b>\n"
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["plan_subscribe", current_plan_id]:
                    current_plan_id = int(current_plan_id)
                    current_plan = self._data.plans.plans[current_plan_id]
                    current_plan_price = current_plan.price * current_plan.months

                    if current_plan_price <= current_user.balance:
                        self._database.users.reduce_balance(
                            tg_id=call.from_user.id,
                            amount=current_plan_price,
                        )
                        datetime_subscribed = datetime.datetime.now()

                        self._database.payments.add_payment(
                            tg_id=call.from_user.id,
                            payment_amount=-current_plan_price,
                            payment_currency=self._config.payments.currency,
                            provider_payment_id=None,
                            payment_payload=call.data,
                            payment_date=int(datetime_subscribed.timestamp()),
                        )

                        current_subscription = self._database.subscriptions.add_subscription(
                            tg_id=call.from_user.id,
                            plan_id=current_plan_id,
                            payment_amount=current_plan_price,
                            subscribed_date=int(datetime_subscribed.timestamp()),
                            expires_date=int(
                                (datetime_subscribed + datetime.timedelta(
                                    days=current_plan.months * data.Constants.DAYS_IN_MONTH,
                                )).timestamp()
                            ),
                            is_active=True,
                        )

                        await self.subscription_config_file(
                            call=call,
                            subscription_id=current_subscription.subscription_id,
                        )
                    else:
                        amount_diff = current_plan_price - current_user.balance

                        plan_add_funds_button = self._buttons.plan_add_funds.model_copy()
                        plan_add_funds_button.text = plan_add_funds_button.text.format(
                            self._get_amount_with_currency(amount_diff),
                        )
                        plan_add_funds_button.callback_data = plan_add_funds_button.callback_data.format(
                            amount_diff,
                        )

                        back_to_plan_button = self._buttons.back_to_plan.model_copy()
                        back_to_plan_button.callback_data = back_to_plan_button.callback_data.format(
                            current_plan_id,
                        )

                        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                        markup_builder.row(plan_add_funds_button)
                        markup_builder.row(back_to_plan_button)

                        await self._bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=(
                                f"Пополните баланс на {self._get_amount_with_currency(amount=amount_diff)}\n"
                                f"для подписки на «{current_plan.name}»!\n"
                            ),
                            reply_markup=markup_builder.as_markup(),
                        )
                case ["add_funds_enter"]:
                    if current_user.balance + self._minimum_plan.price * self._minimum_plan.months < self._config.payments.max_balance:
                        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                        markup_builder.row(self._buttons.back_to_add_funds)

                        await self._bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=(
                                f"Введите сумму, на которую\n"
                                f"хотите пополнить баланс\n"
                                f"<b>(число от {self._minimum_plan.price * self._minimum_plan.months} до {self._config.payments.max_balance - current_user.balance}):</b>\n"
                            ),
                            reply_markup=markup_builder.as_markup(),
                        )
                        await state.set_state(self._states.add_funds_enter)
                    else:
                        await self._bot.answer_callback_query(
                            callback_query_id=call.id,
                            text="Сейчас вы не можете выбрать сумму пополнения!",
                            show_alert=True,
                        )
                case ["add_funds", amount]:
                    amount = int(amount)

                    if current_user.balance + amount < self._config.payments.max_balance:
                        try:
                            await self._bot.delete_message(
                                chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                            )
                        finally:
                            await self.add_funds_invoice(
                                message=call.message,
                                chat=call.message.chat,
                                amount=amount,
                            )
                    else:
                        await self._bot.answer_callback_query(
                            callback_query_id=call.id,
                            text=f"Сумма пополнения превышает максимальную ({self._get_amount_with_currency(self._config.payments.max_balance - current_user.balance)})!",
                            show_alert=True,
                        )
                case ["subscription" | "subscription_switch_active", current_subscription_id]:
                    current_subscription_id = int(current_subscription_id)

                    if "subscription_switch_active" in call.data.split():
                        self._database.subscriptions.switch_active(
                            subscription_id=current_subscription_id,
                        )

                    current_subscription = self._database.subscriptions.get_subscription(
                        subscription_id=current_subscription_id,
                    )

                    subscription_config_button = self._buttons.subscription_config_data.model_copy()
                    subscription_config_button.callback_data = subscription_config_button.callback_data.format(
                        current_subscription.subscription_id,
                    )

                    subscription_switch_active_button = self._buttons.subscription_switch_active.model_copy()
                    subscription_switch_active_button.text = "Отключить автопродление" if bool(
                        current_subscription.is_active
                    ) else "Подключить автопродление"
                    subscription_switch_active_button.callback_data = subscription_switch_active_button.callback_data.format(
                        current_subscription_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(subscription_config_button)
                    markup_builder.row(subscription_switch_active_button)
                    markup_builder.row(self._buttons.back_to_subscriptions)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=(
                            f"<b>Подписка #{current_subscription.subscription_id}</b>\n"
                            f"Тариф «{self._data.plans.plans[current_subscription.plan_id].name}»\n"
                            f"\n"
                            f"<b>Статус: {"Активна" if bool(current_subscription.is_active) else "Отменена"}</b>\n"
                            f"Подключена: {datetime.datetime.fromtimestamp(current_subscription.subscribed_date).strftime("%d.%m.%y")}\n"
                            f"Истекает: {datetime.datetime.fromtimestamp(current_subscription.expires_date).strftime("%d.%m.%y")}\n"
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["subscription_config_file" | "subscription_config_copy", current_subscription_id]:
                    current_subscription_id = int(current_subscription_id)

                    await getattr(self, call.data.split()[0])(call=call, subscription_id=current_subscription_id)
                case ["delete_to_start"]:
                    await self.delete_and_send_start(call=call)
                case ["just_answer"]:
                    await self._bot.answer_callback_query(callback_query_id=call.id)
                case _:
                    if call.from_user.id in self._config.settings.admin_list:
                        match call.data.split():
                            case ["admin"]:
                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(self._buttons.admin_users, self._buttons.admin_configs)
                                markup_builder.row(self._buttons.admin_subscriptions, self._buttons.admin_payments)
                                markup_builder.row(self._buttons.admin_logs, self._buttons.admin_settings)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=f"Добро пожаловать, {call.from_user.full_name}!",
                                    reply_markup=markup_builder.as_markup(),
                                )
                            case ["admin_users", current_page_id]:
                                current_page_id = int(current_page_id)

                                current_users = self._database.users.get_all_users()

                                if current_users:
                                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                    user: models.UserValues
                                    for user in list(
                                            itertools.batched(
                                                current_users,
                                                data.Constants.ELEMENTS_PER_PAGE,
                                            )
                                    )[current_page_id]:
                                        button = self._buttons.page_item_user.model_copy()
                                        button.text = button.text.format(
                                            user.tg_username,
                                            user.tg_id,
                                        )
                                        button.callback_data = f"admin_user {user.tg_id}"
                                        markup_builder.row(button)
                                    markup_builder.row(
                                        *self._get_page_buttons(
                                            page="admin_users",
                                            page_items=current_users,
                                            current_page_id=current_page_id,
                                        )
                                    )
                                    markup_builder.row(self._buttons.back_to_admin)

                                    await self._bot.edit_message_text(
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        text="Выберите пользователя:",
                                        reply_markup=markup_builder.as_markup(),
                                    )
                            case ["admin_user", current_user_id]:
                                current_user_id = int(current_user_id)

                                current_user = self._database.users.get_user(
                                    tg_id=current_user_id,
                                )

                                referrer_user = self._database.users.get_user(
                                    tg_id=current_user.referrer_id,
                                ) if current_user.referrer_id else None

                                current_referrer_model = self._data.referrers.get_referrer_by_id(
                                    tg_id=current_user.tg_id,
                                )

                                current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                                    tg_id=current_user_id,
                                )

                                admin_user_balance_enter_button = self._buttons.admin_user_balance_enter.model_copy()
                                admin_user_balance_enter_button.callback_data = admin_user_balance_enter_button.callback_data.format(
                                    current_user.tg_id,
                                )

                                admin_subscriptions_button = self._buttons.admin_subscriptions.model_copy()
                                admin_subscriptions_button.callback_data = f"{admin_subscriptions_button.callback_data} {current_user_id}"

                                admin_payments_button = self._buttons.admin_payments.model_copy()
                                admin_payments_button.callback_data = f"{admin_payments_button.callback_data} {current_user_id}"

                                admin_user_referral_button = self._buttons.admin_user_referral.model_copy()
                                admin_user_referral_button.callback_data = admin_user_referral_button.callback_data.format(
                                    referrer_user.tg_id if referrer_user else str(),
                                )

                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(admin_user_balance_enter_button)
                                markup_builder.row(admin_subscriptions_button)
                                markup_builder.row(admin_payments_button)
                                if referrer_user:
                                    markup_builder.row(admin_user_referral_button)
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=(
                                             f"Пользователь {current_user.tg_username} ({current_user.tg_id})\n"
                                             f"\n"
                                             f"Баланс: {self._get_amount_with_currency(current_user.balance)}\n"
                                             f"Активных подписок: {len(current_subscriptions)}\n"
                                             f"Приглашено друзей: {self._database.users.get_ref_count(tg_id=current_user.tg_id)}\n"
                                         ) + (
                                             f"\n"
                                             f"<b>Реферальные выплаты:</b>\n"
                                             f"Первое пополнение: <b>{(current_referrer_model.multiplier_first if current_referrer_model else self._config.referral.multiplier_first):.0%}</b>\n"
                                             f"Следующие пополнения: <b>{(current_referrer_model.multiplier_common if current_referrer_model else self._config.referral.multiplier_common):.0%}</b>\n"
                                         ) + (
                                             (
                                                 f"\n"
                                                 f"Пригласил: {referrer_user.tg_username} ({referrer_user.tg_id})\n"
                                             ) if referrer_user else str()
                                         ),
                                    reply_markup=markup_builder.as_markup(),
                                )
                            # TODO: `case ["admin_user_balance_enter", current_user_id]`
                            # TODO: `case ["admin_configs", current_page_id]:` (DATABASE)
                            case ["admin_subscriptions", current_page_id, *current_user_id]:
                                current_page_id = int(current_page_id)
                                current_user_id = int(current_user_id[0]) if current_user_id else None

                                current_subscriptions = self._database.subscriptions.get_user_subscriptions(
                                    tg_id=current_user_id,
                                ) if current_user_id else self._database.subscriptions.get_all_subscriptions()

                                if current_subscriptions:
                                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                    subscription: models.SubscriptionValues
                                    for subscription in list(
                                            itertools.batched(
                                                current_subscriptions,
                                                data.Constants.ELEMENTS_PER_PAGE,
                                            )
                                    )[current_page_id]:
                                        button = self._buttons.page_item_subscription.model_copy()
                                        button.text = button.text.format(
                                            subscription.subscription_id,
                                            self._data.plans.plans[subscription.plan_id].name,
                                        )
                                        button.callback_data = f"admin_subscription {subscription.subscription_id}"
                                        markup_builder.row(button)
                                    markup_builder.row(
                                        *self._get_page_buttons(
                                            page="admin_subscriptions",
                                            page_items=current_subscriptions,
                                            current_page_id=current_page_id,
                                            current_user_id=current_user_id,
                                        )
                                    )
                                    markup_builder.row(self._buttons.back_to_admin)

                                    await self._bot.edit_message_text(
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        text="Выберите подписку:",
                                        reply_markup=markup_builder.as_markup(),
                                    )
                                else:
                                    await self._bot.answer_callback_query(
                                        callback_query_id=call.id,
                                        text="Активные подписки отсутствуют!",
                                        show_alert=True,
                                    )
                            case ["admin_subscription" | "admin_subscription_expire", current_subscription_id]:
                                current_subscription_id = int(current_subscription_id)

                                if "admin_subscription_expire" in call.data.split():
                                    self._database.subscriptions.edit_expires_date(
                                        subscription_id=current_subscription_id,
                                        expires_date=int(datetime.datetime.now().timestamp()),
                                    )

                                current_subscription = self._database.subscriptions.get_subscription(
                                    subscription_id=current_subscription_id,
                                )

                                current_user = self._database.users.get_user(
                                    tg_id=current_subscription.tg_id,
                                )

                                subscription_config_button = self._buttons.subscription_config_data.model_copy()
                                subscription_config_button.callback_data = subscription_config_button.callback_data.format(
                                    current_subscription.subscription_id,
                                )

                                admin_subscription_expire_button = self._buttons.admin_subscription_expire.model_copy()
                                admin_subscription_expire_button.callback_data = admin_subscription_expire_button.callback_data.format(
                                    current_subscription.subscription_id,
                                )

                                admin_user_button = self._buttons.admin_user.model_copy()
                                admin_user_button.callback_data = admin_user_button.callback_data.format(
                                    current_user.tg_id,
                                )

                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                if current_subscription.expires_date > datetime.datetime.now().timestamp():
                                    markup_builder.row(subscription_config_button)
                                    markup_builder.row(admin_subscription_expire_button)
                                markup_builder.row(admin_user_button)
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=(
                                        f"Подписка #{current_subscription.subscription_id}\n"
                                        f"Тариф «{self._data.plans.plans[current_subscription.plan_id].name}»\n"
                                        f"\n"
                                        f"Пользователь: {current_user.tg_username} ({current_user.tg_id})\n"
                                        f"\n"
                                        f"Статус: {("Активна" if bool(current_subscription.is_active) else "Отменена") if current_subscription.expires_date > datetime.datetime.now().timestamp() else "Истекла"}\n"
                                        f"Подключена: {datetime.datetime.fromtimestamp(current_subscription.subscribed_date).strftime("%d.%m.%y")}\n"
                                        f"Истекает: {datetime.datetime.fromtimestamp(current_subscription.expires_date).strftime("%d.%m.%y")}\n"
                                    ),
                                    reply_markup=markup_builder.as_markup(),
                                )
                            case ["admin_payments", current_page_id, *current_user_id]:
                                current_page_id = int(current_page_id)
                                current_user_id = int(current_user_id[0]) if current_user_id else None

                                current_payments = self._database.payments.get_user_payments(
                                    tg_id=current_user_id,
                                ) if current_user_id else self._database.payments.get_all_payments()

                                if current_payments:
                                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                    for payment in list(
                                            itertools.batched(
                                                current_payments,
                                                data.Constants.ELEMENTS_PER_PAGE,
                                            )
                                    )[current_page_id]:
                                        payment: models.PaymentValues
                                        button = self._buttons.page_item_payment.model_copy()
                                        button.text = button.text.format(
                                            payment.payment_id,
                                            self._get_amount_with_currency(payment.payment_amount),
                                        )
                                        button.callback_data = f"admin_payment {payment.payment_id}"
                                        markup_builder.row(button)
                                    markup_builder.row(
                                        *self._get_page_buttons(
                                            page="admin_payments",
                                            page_items=current_payments,
                                            current_page_id=current_page_id,
                                            current_user_id=current_user_id,
                                        )
                                    )
                                    markup_builder.row(self._buttons.back_to_admin)

                                    await self._bot.edit_message_text(
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        text="Выберите платёж:",
                                        reply_markup=markup_builder.as_markup(),
                                    )
                                else:
                                    await self._bot.answer_callback_query(
                                        callback_query_id=call.id,
                                        text="Совершённые платежи отсутствуют!",
                                        show_alert=True,
                                    )
                            # TODO: `case ["admin_payment", current_payment_id]:`
                            case ["admin_logs"]:
                                if self._config.settings.file_logging:
                                    logs_file = self._logger.get_logs_file()

                                    await self._bot.send_document(
                                        chat_id=call.message.chat.id,
                                        message_thread_id=self._get_message_thread_id(message=call.message),
                                        document=aiogram.types.BufferedInputFile(
                                            file=logs_file.read(),
                                            filename=logs_file.name,
                                        ),
                                    )

                                    logs_file.close()
                                else:
                                    await self._bot.answer_callback_query(
                                        callback_query_id=call.id,
                                        text="Логирование отключено!",
                                        show_alert=True,
                                    )
                            # TODO: `case ["admin_settings"]:`
                            case _:
                                await self._bot.answer_callback_query(
                                    callback_query_id=call.id,
                                    text="Эта кнопка недоступна!",
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

    async def pre_add_funds_handler(self, pre_checkout_query: aiogram.types.PreCheckoutQuery) -> None:
        self._logger.log_user_interaction(
            user=pre_checkout_query.from_user,
            interaction=self.pre_add_funds_handler.__name__,
        )

        self._database.users.add_user(
            tg_id=pre_checkout_query.from_user.id,
            tg_username=f"@{pre_checkout_query.from_user.username}",
            balance=int(),
            referrer_id=None,
        )

        current_user = self._database.users.get_user(
            tg_id=pre_checkout_query.from_user.id,
        )

        await pre_checkout_query.answer(
            ok=self._minimum_plan.price * self._minimum_plan.months <= current_user.balance + pre_checkout_query.total_amount / self._config.payments.currency_multiplier <= self._config.payments.max_balance,
            error_message=f"Сумма пополнения превышает максимальную ({self._get_amount_with_currency(self._config.payments.max_balance - current_user.balance)})!",
        )

    async def success_add_funds_handler(self, message: aiogram.types.Message) -> None:
        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=self.success_add_funds_handler.__name__,
        )

        payment_amount = int(message.successful_payment.total_amount / self._config.payments.currency_multiplier)
        successful_payment_date = int(datetime.datetime.now().timestamp())

        current_user = self._database.users.get_user(
            tg_id=message.from_user.id,
        )

        referrer_user = self._database.users.get_user(
            tg_id=current_user.referrer_id,
        ) if current_user.referrer_id else None

        is_first_payment = not self._database.payments.check_payments(
            tg_id=message.from_user.id,
        )

        self._database.payments.add_payment(
            tg_id=message.from_user.id,
            payment_amount=payment_amount,
            payment_currency=message.successful_payment.currency,
            provider_payment_id=message.successful_payment.provider_payment_charge_id,
            payment_payload=message.successful_payment.invoice_payload,
            payment_date=successful_payment_date,
        )

        self._database.users.add_balance(
            tg_id=message.from_user.id,
            amount=payment_amount
        )

        if referrer_user:
            referrer_model = self._data.referrers.get_referrer_by_id(
                tg_id=referrer_user.tg_id,
            )

            if is_first_payment:
                referrer_bonus = int(
                    payment_amount * referrer_model.multiplier_first if referrer_model else self._config.referral.multiplier_first
                )
            else:
                referrer_bonus = int(
                    payment_amount * referrer_model.multiplier_common if referrer_model else self._config.referral.multiplier_common
                )

            self._database.payments.add_payment(
                tg_id=referrer_user.tg_id,
                payment_amount=referrer_bonus,
                payment_currency=self._config.payments.currency,
                provider_payment_id=None,
                payment_payload=f"referral {current_user.tg_id} {payment_amount} ({is_first_payment=})",
                payment_date=successful_payment_date,
            )

            self._database.users.add_balance(
                tg_id=referrer_user.tg_id,
                amount=referrer_bonus,
            )

        try:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.view_plans)
            markup_builder.row(self._buttons.view_start)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=f"Баланс пополнен на {self._get_amount_with_currency(payment_amount)}!",
                reply_markup=markup_builder.as_markup(),
            )
        except aiogram.exceptions.TelegramForbiddenError as e:
            self._logger.log_exception(e)

    async def add_funds_enter_handler(
            self,
            message: aiogram.types.Message,
            state: aiogram.fsm.context.FSMContext,
    ) -> None:
        amount = message.text

        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{self.add_funds_enter_handler.__name__} ({amount=})",
        )

        self._database.users.add_user(
            tg_id=message.from_user.id,
            tg_username=f"@{message.from_user.username}",
            balance=int(),
            referrer_id=None,
        )

        current_user = self._database.users.get_user(
            tg_id=message.from_user.id,
        )

        try:
            amount = int(amount)

            if self._minimum_plan.price * self._minimum_plan.months <= current_user.balance + amount <= self._config.payments.max_balance and self._minimum_plan.price * self._minimum_plan.months < amount:
                await self.add_funds_invoice(
                    message=message,
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
                message_thread_id=self._get_message_thread_id(message),
                text=(
                    f"<b>Сумма пополнения должна\n"
                    f"быть числом от {self._minimum_plan.price * self._minimum_plan.months} до {self._config.payments.max_balance - current_user.balance}!</b>\n"
                    f"\n"
                    f"Введите сумму, на которую\n"
                    f"хотите пополнить баланс:\n"
                ),
                reply_to_message_id=message.message_id,
                reply_markup=markup_builder.as_markup(),
            )
            await state.set_state(self._states.add_funds_enter)

    # endregion
