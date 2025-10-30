from __future__ import annotations
import itertools, datetime, logging
import aiogram, aiogram.exceptions, aiogram.filters, aiogram.client.default, aiogram.utils.keyboard, \
    aiogram.fsm.context, aiogram.fsm.state
import models, data, misc, constants


class AiogramClient(aiogram.Dispatcher):
    _COMMANDS = [
        aiogram.types.BotCommand(command="/start", description="Запустить бота"),
    ]

    class States(aiogram.fsm.state.StatesGroup):
        add_funds_enter = aiogram.fsm.state.State()
        admin_user_balance_enter = aiogram.fsm.state.State()
        admin_users_enter = aiogram.fsm.state.State()
        admin_subscriptions_enter = aiogram.fsm.state.State()
        admin_payments_enter = aiogram.fsm.state.State()

    def __init__(self) -> None:
        self._user = None
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()
        self._strings = data.StringsProvider()
        self._database = data.DatabaseManager()
        self._logger = data.LoggerService(
            name=__name__,
            file_handling=self._config.settings.file_logging,
            level=logging.DEBUG if self._config.settings.debug_logging else logging.INFO,
        )
        self._states = self.States()
        self._states_router = aiogram.Router()
        self._buttons = misc.ButtonsContainer()
        self._bot = aiogram.Bot(
            token=self._config.settings.bot_token,
            default=aiogram.client.default.DefaultBotProperties(
                parse_mode=aiogram.enums.ParseMode.HTML,
            ),
        )
        super().__init__(name="AiogramClientDispatcher")
        self.include_router(self._states_router)

        self.errors.register(
            self.error_handler,
        )
        self.startup.register(
            self.startup_handler,
        )
        self.shutdown.register(
            self.shutdown_handler,
        )

        self.message.register(
            self.start_handler,
            aiogram.filters.Command(
                "start",
            ),
        )
        self.message.register(
            self.admin_handler,
            aiogram.filters.Command(
                "admin",
            ),
        )

        self._states_router.callback_query.register(
            self.callback_handler,
        )

        self.pre_checkout_query.register(
            self.pre_add_funds_handler,
        )
        self.message.register(
            self.success_add_funds_handler,
            aiogram.F.successful_payment,
        )

        self._states_router.message.register(
            self.add_funds_enter_handler,
            aiogram.filters.StateFilter(
                self._states.add_funds_enter,
            ),
        )
        self._states_router.message.register(
            self.admin_user_balance_enter_handler,
            aiogram.filters.StateFilter(
                self._states.admin_user_balance_enter,
            ),
        )
        self._states_router.message.register(
            self.admin_page_enter_handler,
            aiogram.filters.StateFilter(
                self._states.admin_users_enter,
                self._states.admin_subscriptions_enter,
                self._states.admin_payments_enter,
            ),
        )

        self._logger.info(f"{self.name} initialized!")

    # region Properties and helpers

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

    def _get_max_balance(
            self,
            tg_id: int,
    ) -> int:
        current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
            tg_id=tg_id,
        )

        return max(
            self._config.payments.max_balance,
            sum([self._data.plans.get_plan_by_id(subscription.plan_id).cost for subscription in current_subscriptions])
        )

    def _get_referrer_id(self, user_id: int, args: str | None) -> int | None:
        try:
            referrer_id = int(args)

            referrer_user = self._database.users.get_user(
                tg_id=referrer_id,
            )

            return referrer_id if referrer_id != user_id and referrer_user else None
        except:
            return None

    async def polling_coroutine(self) -> None:
        try:
            await self._bot.delete_webhook(drop_pending_updates=self._config.settings.skip_updates)
            await self.start_polling(self._bot)
        except Exception as e:
            self._logger.log_exception(e)

    async def delete_and_send_start(self, call: aiogram.types.CallbackQuery) -> None:
        current_user = self._database.users.get_user(
            tg_id=call.from_user.id,
        )

        try:
            await self._bot.delete_message(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
            )
        finally:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.plans)
            markup_builder.row(self._buttons.add_funds)
            markup_builder.row(
                self._buttons.invite_friend(
                    bot_username=(await self.user).username,
                    tg_id=current_user.tg_id,
                ),
            )
            markup_builder.row(self._buttons.subscriptions(), self._buttons.profile)

            await self._bot.send_message(
                chat_id=call.message.chat.id,
                message_thread_id=self._get_message_thread_id(call.message),
                text=self._strings.menu.start(
                    bot_full_name=(await self.user).full_name,
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
                    label=self._strings.menu.add_funds_description(
                        amount=amount,
                    ),
                    amount=amount * self._config.payments.currency_multiplier,
                ),
            ],
            currency=self._config.payments.currency,
            provider_token=self._config.payments.provider_token,
            payload=f"{self.add_funds_invoice.__name__} {amount}",
            title=self._strings.menu.add_funds_title,
            description=self._strings.menu.add_funds_description(
                amount=amount,
            ),
        )

    async def subscription_config_file(self, call: aiogram.types.CallbackQuery, subscription_id: int) -> None:
        config_key = str(None)  # TODO: выдача ключа (DATABASE)

        # current_subscription = self._database.subscriptions.get_subscription(
        #     subscription_id=subscription_id,
        # )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(
            self._buttons.subscription_config_copy(
                subscription_id=subscription_id,
            ),
        )
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
                    filename=f"{(await self.user).full_name}.vpn"
                ),
                caption=self._strings.menu.subscription_config_file,
                reply_markup=markup_builder.as_markup(),
            )

    async def subscription_config_copy(self, call: aiogram.types.CallbackQuery, subscription_id: int) -> None:
        config_key = str(None)  # TODO: выдача ключа (DATABASE)

        # current_subscription = self._database.subscriptions.get_subscription(
        #     subscription_id=subscription_id,
        # )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(
            self._buttons.subscription_config_file(
                subscription_id=subscription_id,
            ),
        )
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
                text=self._strings.menu.subscription_config_copy(
                    config_key=config_key,
                ),
                reply_markup=markup_builder.as_markup(),
            )

    # endregion

    # region Handlers

    async def error_handler(self, event: aiogram.types.ErrorEvent) -> None:
        self._logger.log_exception(event.exception)

    async def startup_handler(self) -> None:
        await self._bot.set_my_commands(
            commands=self._COMMANDS,
            scope=aiogram.types.BotCommandScopeDefault(),
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
            tg_username=message.from_user.username,
            balance=int(),
            referrer_id=self._get_referrer_id(message.from_user.id, command.args)
        )

        current_user = self._database.users.get_user(
            tg_id=message.from_user.id,
        )

        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
        markup_builder.row(self._buttons.plans)
        markup_builder.row(self._buttons.add_funds)
        markup_builder.row(
            self._buttons.invite_friend(
                bot_username=(await self.user).username,
                tg_id=current_user.tg_id,
            ),
        )
        markup_builder.row(self._buttons.subscriptions(), self._buttons.profile)

        await self._bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=self._get_message_thread_id(message),
            text=self._strings.menu.start(
                bot_full_name=(await self.user).full_name,
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
            markup_builder.row(self._buttons.admin_users(), self._buttons.admin_configs())
            markup_builder.row(self._buttons.admin_subscriptions(), self._buttons.admin_payments())
            markup_builder.row(self._buttons.admin_logs, self._buttons.admin_settings)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=self._strings.menu.admin(
                    tg_full_name=message.from_user.full_name,
                ),
                reply_markup=markup_builder.as_markup(),
            )

    async def callback_handler(self, call: aiogram.types.CallbackQuery, state: aiogram.fsm.context.FSMContext) -> None:
        self._logger.log_user_interaction(
            user=call.from_user,
            interaction=call.data,
        )

        await state.clear()

        self._database.users.add_user(
            tg_id=call.from_user.id,
            tg_username=call.from_user.username,
            balance=int(),
            referrer_id=None,
        )

        current_user = self._database.users.get_user(
            tg_id=call.from_user.id,
        )

        try:
            match call.data.split():

                # region /start
                case ["start"]:
                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.plans)
                    markup_builder.row(self._buttons.add_funds)
                    markup_builder.row(
                        self._buttons.invite_friend(
                            bot_username=(await self.user).username,
                            tg_id=current_user.tg_id,
                        ),
                    )
                    markup_builder.row(self._buttons.subscriptions(), self._buttons.profile)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=self._strings.menu.start(
                            bot_full_name=(await self.user).full_name,
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["plans"]:
                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(
                        *self._buttons.plan_buttons,
                        width=constants.PLANS_PER_ROW,
                    )
                    markup_builder.row(self._buttons.back_to_start)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=self._strings.menu.plans,
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["add_funds"]:
                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.add_funds_enter)
                    markup_builder.row(
                        *self._buttons.add_funds_buttons,
                        width=constants.PLANS_PER_ROW,
                    )
                    markup_builder.row(self._buttons.back_to_start)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=self._strings.menu.add_funds,
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["subscriptions", _current_page_id]:
                    current_page_id = int(_current_page_id)

                    current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                        tg_id=current_user.tg_id,
                    )

                    if current_subscriptions:
                        subscription: models.SubscriptionValues

                        _, page_buttons = self._buttons.get_page_buttons(
                            page_items=current_subscriptions,
                            page="subscriptions",
                            page_id=current_page_id,
                        )

                        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                        markup_builder.row(
                            *[
                                self._buttons.page_item_subscription(
                                    page="subscription",
                                    plan_name=self._data.plans.get_plan_by_id(subscription.plan_id).name,
                                    subscription_id=subscription.subscription_id,
                                ) for subscription in list(
                                    itertools.batched(
                                        current_subscriptions,
                                        constants.ITEMS_PER_PAGE,
                                    )
                                )[current_page_id]
                            ],
                            width=constants.ITEMS_PER_ROW,
                        )
                        markup_builder.row(*page_buttons)
                        markup_builder.row(self._buttons.back_to_start)

                        await self._bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=self._strings.menu.subscriptions,
                            reply_markup=markup_builder.as_markup(),
                        )
                    else:
                        await self._bot.answer_callback_query(
                            callback_query_id=call.id,
                            text=self._strings.alert.subscriptions_unavailable,
                            show_alert=True,
                        )
                case ["profile"]:
                    current_referrer_user = self._database.users.get_user(
                        tg_id=current_user.referrer_id,
                    ) if current_user.referrer_id else None

                    current_referrer_model = self._config.referral.get_referrer_model(
                        referrer=self._data.referrers.get_referrer_by_id(
                            tg_id=current_user.tg_id,
                        ),
                    )

                    current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                        tg_id=current_user.tg_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.back_to_start)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=self._strings.menu.profile(
                            user=current_user,
                            referrer_model=current_referrer_model,
                            referrer_user=current_referrer_user,
                            subscriptions_count=len(current_subscriptions),
                            friends_count=self._database.users.get_ref_count(
                                tg_id=current_user.tg_id,
                            ),
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                # endregion

                # region plans
                case ["plan", _current_plan_id]:
                    current_plan_id = int(_current_plan_id)
                    current_plan = self._data.plans.get_plan_by_id(
                        plan_id=current_plan_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(self._buttons.plan_subscribe_buttons[current_plan_id])
                    markup_builder.row(self._buttons.back_to_plans)

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=self._strings.menu.plan(
                            user=current_user,
                            plan=current_plan,
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["plan_subscribe", _current_plan_id]:
                    current_plan_id = int(_current_plan_id)
                    current_plan = self._data.plans.get_plan_by_id(
                        plan_id=current_plan_id,
                    )

                    if current_plan.cost <= current_user.balance:
                        self._database.users.reduce_balance(
                            tg_id=current_user.tg_id,
                            amount=current_plan.cost,
                        )
                        datetime_subscribed = datetime.datetime.now()

                        self._database.payments.add_payment(
                            tg_id=current_user.tg_id,
                            payment_amount=-current_plan.cost,
                            payment_currency=self._config.payments.currency,
                            payment_payload=call.data,
                            payment_provider_id=None,
                            payment_date=int(datetime_subscribed.timestamp()),
                        )

                        current_subscription = self._database.subscriptions.add_subscription(
                            tg_id=current_user.tg_id,
                            plan_id=current_plan_id,
                            payment_amount=current_plan.cost,
                            subscribed_date=int(datetime_subscribed.timestamp()),
                            expires_date=int(
                                (datetime_subscribed + datetime.timedelta(
                                    days=current_plan.days,
                                )).timestamp()
                            ),
                            is_active=True,
                        )

                        await self.subscription_config_file(
                            call=call,
                            subscription_id=current_subscription.subscription_id,
                        )
                    else:
                        amount_diff = current_plan.cost - current_user.balance

                        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                        markup_builder.row(
                            self._buttons.plan_add_funds(
                                amount=max(amount_diff, self._data.plans.minimum_plan.cost),
                            ),
                        )
                        markup_builder.row(
                            self._buttons.back_to_plan(
                                plan_id=current_plan_id,
                            ),
                        )

                        await self._bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=self._strings.menu.plan_subscribe_unavailable(
                                current_plan=current_plan,
                                amount=amount_diff,
                            ),
                            reply_markup=markup_builder.as_markup(),
                        )
                # endregion

                # region add_funds
                case ["add_funds_enter"]:
                    if current_user.balance + self._data.plans.minimum_plan.cost <= self._get_max_balance(
                            tg_id=current_user.tg_id,
                    ):
                        markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                        markup_builder.row(self._buttons.back_to_add_funds)

                        await self._bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=self._strings.menu.add_funds_enter(
                                min_amount=self._data.plans.minimum_plan.cost,
                                max_amount=self._get_max_balance(tg_id=current_user.tg_id) - current_user.balance,
                            ),
                            reply_markup=markup_builder.as_markup(),
                        )

                        await state.set_state(self._states.add_funds_enter)
                    else:
                        await self._bot.answer_callback_query(
                            callback_query_id=call.id,
                            text=self._strings.alert.add_funds_enter_unavailable,
                            show_alert=True,
                        )
                case ["add_funds", _amount]:
                    amount = int(_amount)

                    if current_user.balance + amount <= self._get_max_balance(tg_id=current_user.tg_id):
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
                            text=self._strings.alert.add_funds_unavailable,
                            show_alert=True,
                        )
                # endregion

                # region subscriptions
                case ["subscription" | "subscription_switch_active", _current_subscription_id]:
                    current_subscription_id = int(_current_subscription_id)

                    if "subscription_switch_active" in call.data.split():
                        self._database.subscriptions.switch_active(
                            subscription_id=current_subscription_id,
                        )

                    current_subscription = self._database.subscriptions.get_subscription(
                        subscription_id=current_subscription_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(
                        self._buttons.subscription_config(
                            subscription_id=current_subscription.subscription_id,
                        ),
                    )
                    markup_builder.row(
                        self._buttons.subscription_switch_active(
                            status_text=self._strings.status.subscription_renewal(
                                is_active=bool(current_subscription.is_active),
                            ),
                            subscription_id=current_subscription.subscription_id,
                        ),
                    )
                    markup_builder.row(self._buttons.back_to_subscriptions())

                    await self._bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=self._strings.menu.subscription(
                            subscription=current_subscription,
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case ["subscription_config_file" | "subscription_config_copy", _current_subscription_id]:
                    current_subscription_id = int(_current_subscription_id)

                    await getattr(self, call.data.split()[0])(
                        call=call,
                        subscription_id=current_subscription_id,
                    )
                # endregion

                # region view_*
                case ["delete_to_start"]:
                    await self.delete_and_send_start(
                        call=call,
                    )
                case ["just_answer"]:
                    await self._bot.answer_callback_query(
                        callback_query_id=call.id,
                    )
                # endregion

                # region /admin
                case _:
                    if current_user.tg_id in self._config.settings.admin_list:
                        match call.data.split():
                            case ["admin"]:
                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(self._buttons.admin_users(), self._buttons.admin_configs())
                                markup_builder.row(self._buttons.admin_subscriptions(), self._buttons.admin_payments())
                                markup_builder.row(self._buttons.admin_logs, self._buttons.admin_settings)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=self._strings.menu.admin(
                                        tg_full_name=call.from_user.full_name,
                                    ),
                                    reply_markup=markup_builder.as_markup(),
                                )
                            case ["admin_users", _current_page_id]:
                                current_page_id = int(_current_page_id)

                                current_users = self._database.users.get_all_users()

                                if current_users:
                                    user: models.UserValues

                                    page_enter_button, page_buttons = self._buttons.get_page_buttons(
                                        page_items=current_users,
                                        page="admin_users",
                                        page_id=current_page_id,
                                    )

                                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                    markup_builder.row(page_enter_button)
                                    markup_builder.row(
                                        *[
                                            self._buttons.page_item_user(
                                                page="admin_user",
                                                user=user,
                                            ) for user in list(
                                                itertools.batched(
                                                    current_users,
                                                    constants.ITEMS_PER_PAGE,
                                                )
                                            )[current_page_id]
                                        ],
                                        width=constants.ITEMS_PER_ROW,
                                    )
                                    markup_builder.row(*page_buttons)
                                    markup_builder.row(self._buttons.back_to_admin)

                                    await self._bot.edit_message_text(
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        text=self._strings.menu.admin_users(
                                            users_count=len(current_users),
                                        ),
                                        reply_markup=markup_builder.as_markup(),
                                    )
                            case ["admin_user", _current_user_id]:
                                current_user_id = int(_current_user_id)

                                current_user = self._database.users.get_user(
                                    tg_id=current_user_id,
                                )

                                referrer_user = self._database.users.get_user(
                                    tg_id=current_user.referrer_id,
                                ) if current_user.referrer_id else None

                                current_referrer_model = self._config.referral.get_referrer_model(
                                    referrer=self._data.referrers.get_referrer_by_id(
                                        tg_id=current_user.tg_id,
                                    ),
                                )

                                current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                                    tg_id=current_user.tg_id,
                                )

                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(
                                    self._buttons.admin_user_balance_enter(
                                        tg_id=current_user.tg_id,
                                    ),
                                )
                                markup_builder.row(
                                    self._buttons.admin_subscriptions(
                                        tg_id=current_user.tg_id,
                                    ),
                                )
                                markup_builder.row(
                                    self._buttons.admin_payments(
                                        tg_id=current_user.tg_id,
                                    ),
                                )
                                if referrer_user:
                                    markup_builder.row(
                                        self._buttons.admin_user_referrer(
                                            tg_id=referrer_user.tg_id,
                                        ),
                                    )
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=self._strings.menu.profile(
                                        user=current_user,
                                        referrer_model=current_referrer_model,
                                        referrer_user=referrer_user,
                                        subscriptions_count=len(current_subscriptions),
                                        friends_count=self._database.users.get_ref_count(
                                            tg_id=current_user.tg_id,
                                        ),
                                    ),
                                    reply_markup=markup_builder.as_markup(),
                                )
                            case ["admin_user_balance_enter", _current_user_id]:
                                current_user_id = int(_current_user_id)

                                current_user = self._database.users.get_user(
                                    tg_id=current_user_id,
                                )

                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=self._strings.menu.admin_user_balance_enter(
                                        current_user=current_user,
                                        max_balance=self._get_max_balance(
                                            tg_id=current_user.tg_id,
                                        ),
                                    ),
                                    reply_markup=markup_builder.as_markup(),
                                )

                                await state.set_state(self._states.admin_user_balance_enter)
                                await state.set_data(
                                    {
                                        "tg_id": current_user.tg_id,
                                    }
                                )
                            # TODO: `case ["admin_configs", current_page_id]:` (DATABASE)
                            case ["admin_logs"]:
                                if self._config.settings.file_logging:
                                    logs_file = self._logger.get_logs_file()

                                    await self._bot.send_document(
                                        chat_id=call.message.chat.id,
                                        message_thread_id=self._get_message_thread_id(call.message),
                                        document=aiogram.types.BufferedInputFile(
                                            file=logs_file.read(),
                                            filename=logs_file.name,
                                        ),
                                    )

                                    logs_file.close()
                                else:
                                    await self._bot.answer_callback_query(
                                        callback_query_id=call.id,
                                        text=self._strings.alert.admin_logs_unavailable,
                                        show_alert=True,
                                    )
                            case [
                                "admin_subscriptions",
                                _current_page_id,
                                *_current_user_id,
                            ] if len(_current_user_id) <= 1:
                                current_page_id = int(_current_page_id)
                                current_user_id = int(_current_user_id[0]) if _current_user_id else None

                                current_subscriptions = self._database.subscriptions.get_user_subscriptions(
                                    tg_id=current_user_id,
                                ) if current_user_id else self._database.subscriptions.get_all_subscriptions()

                                if current_subscriptions:
                                    subscription: models.SubscriptionValues

                                    page_enter_button, page_buttons = self._buttons.get_page_buttons(
                                        page_items=current_subscriptions,
                                        page="admin_subscriptions",
                                        page_id=current_page_id,
                                        tg_id=current_user_id,
                                    )

                                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                    markup_builder.row(page_enter_button)
                                    markup_builder.row(
                                        *[
                                            self._buttons.page_item_subscription(
                                                page="admin_subscription",
                                                plan_name=self._data.plans.get_plan_by_id(subscription.plan_id).name,
                                                subscription_id=subscription.subscription_id,
                                            ) for subscription in list(
                                                itertools.batched(
                                                    current_subscriptions,
                                                    constants.ITEMS_PER_PAGE,
                                                )
                                            )[current_page_id]
                                        ],
                                        width=constants.ITEMS_PER_ROW,
                                    )
                                    markup_builder.row(*page_buttons)
                                    markup_builder.row(self._buttons.back_to_admin)

                                    await self._bot.edit_message_text(
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        text=self._strings.menu.admin_subscriptions(
                                            subscriptions_count=len(current_subscriptions),
                                        ),
                                        reply_markup=markup_builder.as_markup(),
                                    )
                                else:
                                    await self._bot.answer_callback_query(
                                        callback_query_id=call.id,
                                        text=self._strings.alert.admin_subscriptions_unavailable,
                                        show_alert=True,
                                    )
                            case ["admin_subscription" | "admin_subscription_expire", _current_subscription_id]:
                                current_subscription_id = int(_current_subscription_id)

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

                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                if not current_subscription.is_expired:
                                    markup_builder.row(
                                        self._buttons.subscription_config(
                                            subscription_id=current_subscription.subscription_id,
                                        ),
                                    )
                                    markup_builder.row(
                                        self._buttons.admin_subscription_expire(
                                            subscription_id=current_subscription.subscription_id,
                                        ),
                                    )
                                markup_builder.row(
                                    self._buttons.admin_user(
                                        tg_id=current_user.tg_id,
                                    ),
                                )
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=self._strings.menu.subscription(
                                        subscription=current_subscription,
                                        user=current_user,
                                    ),
                                    reply_markup=markup_builder.as_markup(),
                                )
                            case [
                                "admin_payments",
                                _current_page_id,
                                *_current_user_id,
                            ] if len(_current_user_id) <= 1:
                                current_page_id = int(_current_page_id)
                                current_user_id = int(_current_user_id[0]) if _current_user_id else None

                                current_payments = self._database.payments.get_user_payments(
                                    tg_id=current_user_id,
                                ) if current_user_id else self._database.payments.get_all_payments()

                                if current_payments:
                                    payment: models.PaymentValues

                                    page_enter_button, page_buttons = self._buttons.get_page_buttons(
                                        page_items=current_payments,
                                        page="admin_payments",
                                        page_id=current_page_id,
                                        tg_id=current_user_id,
                                    )

                                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                    markup_builder.row(page_enter_button)
                                    markup_builder.row(
                                        *[
                                            self._buttons.page_item_payment(
                                                page="admin_payment",
                                                payment_amount=payment.payment_amount,
                                                payment_id=payment.payment_id,
                                            ) for payment in list(
                                                itertools.batched(
                                                    current_payments,
                                                    constants.ITEMS_PER_PAGE,
                                                )
                                            )[current_page_id]
                                        ],
                                        width=constants.ITEMS_PER_ROW,
                                    )
                                    markup_builder.row(*page_buttons)
                                    markup_builder.row(self._buttons.back_to_admin)

                                    await self._bot.edit_message_text(
                                        chat_id=call.message.chat.id,
                                        message_id=call.message.message_id,
                                        text=self._strings.menu.admin_payments(
                                            payments_count=len(current_payments),
                                        ),
                                        reply_markup=markup_builder.as_markup(),
                                    )
                                else:
                                    await self._bot.answer_callback_query(
                                        callback_query_id=call.id,
                                        text=self._strings.alert.admin_payments_unavailable,
                                        show_alert=True,
                                    )
                            case ["admin_payment", _current_payment_id]:
                                current_payment_id = int(_current_payment_id)

                                current_payment = self._database.payments.get_payment(
                                    payment_id=current_payment_id,
                                )

                                current_user = self._database.users.get_user(
                                    tg_id=current_payment.tg_id,
                                )

                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(
                                    self._buttons.admin_user(
                                        tg_id=current_user.tg_id,
                                    ),
                                )
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=self._strings.menu.admin_payment(
                                        payment=current_payment,
                                        user=current_user,
                                    ),
                                    reply_markup=markup_builder.as_markup(),
                                )
                            case ["admin_users_enter" | "admin_subscriptions_enter" | "admin_payments_enter"]:
                                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                                markup_builder.row(self._buttons.back_to_admin)

                                await self._bot.edit_message_text(
                                    chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text=self._strings.menu.admin_page_enter(),
                                    reply_markup=markup_builder.as_markup(),
                                )

                                await state.set_state(getattr(self._states, call.data))
                            # TODO: `case ["admin_settings"]:`
                            case _:
                                await self._bot.answer_callback_query(
                                    callback_query_id=call.id,
                                    text=self._strings.alert.button_unavailable,
                                    show_alert=True,
                                )
                    else:
                        await self._bot.answer_callback_query(
                            callback_query_id=call.id,
                            text=self._strings.alert.button_unavailable,
                            show_alert=True,
                        )
                # endregion

        except Exception as e:
            if type(e) not in [aiogram.exceptions.TelegramBadRequest, aiogram.exceptions.TelegramRetryAfter]:
                self._logger.log_exception(e)
        finally:
            await self._bot.answer_callback_query(
                callback_query_id=call.id,
            )

    async def pre_add_funds_handler(self, pre_checkout_query: aiogram.types.PreCheckoutQuery) -> None:
        payment_amount = int(pre_checkout_query.total_amount / self._config.payments.currency_multiplier)

        self._logger.log_user_interaction(
            user=pre_checkout_query.from_user,
            interaction=f"{self.pre_add_funds_handler.__name__} ({payment_amount=})",
        )

        self._database.users.add_user(
            tg_id=pre_checkout_query.from_user.id,
            tg_username=pre_checkout_query.from_user.username,
            balance=int(),
            referrer_id=None,
        )

        current_user = self._database.users.get_user(
            tg_id=pre_checkout_query.from_user.id,
        )

        await pre_checkout_query.answer(
            ok=self._data.plans.minimum_plan.cost <= current_user.balance + payment_amount <= self._get_max_balance(
                tg_id=current_user.tg_id,
            ),
            error_message=self._strings.alert.add_funds_unavailable,
        )

    async def success_add_funds_handler(self, message: aiogram.types.Message) -> None:
        payment_amount = int(message.successful_payment.total_amount / self._config.payments.currency_multiplier)
        successful_payment_date = int(datetime.datetime.now().timestamp())

        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{self.success_add_funds_handler.__name__} ({payment_amount=})",
        )

        current_user = self._database.users.get_user(
            tg_id=message.from_user.id,
        )

        referrer_user = self._database.users.get_user(
            tg_id=current_user.referrer_id,
        ) if current_user.referrer_id else None

        is_first_payment = not self._database.payments.check_payments(
            tg_id=current_user.tg_id,
        )

        self._database.payments.add_payment(
            tg_id=current_user.tg_id,
            payment_amount=payment_amount,
            payment_currency=message.successful_payment.currency,
            payment_payload=message.successful_payment.invoice_payload,
            payment_provider_id=message.successful_payment.provider_payment_charge_id,
            payment_date=successful_payment_date,
        )

        self._database.users.add_balance(
            tg_id=current_user.tg_id,
            amount=payment_amount
        )

        if referrer_user:
            referrer_model = self._config.referral.get_referrer_model(
                referrer=self._data.referrers.get_referrer_by_id(
                    tg_id=referrer_user.tg_id,
                ),
            )

            referrer_multiplier = referrer_model.get_referrer_multiplier(is_first_payment)

            referrer_bonus_amount = int(payment_amount * referrer_multiplier)

            self._database.payments.add_payment(
                tg_id=referrer_user.tg_id,
                payment_amount=referrer_bonus_amount,
                payment_currency=self._config.payments.currency,
                payment_payload=f"referral {current_user.tg_id} {payment_amount} ({is_first_payment=})",
                payment_provider_id=None,
                payment_date=successful_payment_date,
            )

            self._database.users.add_balance(
                tg_id=referrer_user.tg_id,
                amount=referrer_bonus_amount,
            )

            try:
                markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                markup_builder.row(self._buttons.view_start)

                await self._bot.send_message(
                    chat_id=referrer_user.tg_id,
                    text=self._strings.menu.add_funds_referrer(
                        user=current_user,
                        amount=payment_amount,
                        referrer_bonus_amount=referrer_bonus_amount,
                        referrer_multiplier=referrer_multiplier,
                    ),
                    reply_markup=markup_builder.as_markup(),
                )
            except Exception as e:
                if type(e) not in [aiogram.exceptions.TelegramBadRequest, aiogram.exceptions.TelegramRetryAfter]:
                    self._logger.log_exception(e)

        try:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.view_plans)
            markup_builder.row(self._buttons.view_start)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=self._strings.menu.add_funds_success(
                    amount=payment_amount,
                ),
                reply_markup=markup_builder.as_markup(),
            )
        except Exception as e:
            if type(e) not in [aiogram.exceptions.TelegramBadRequest, aiogram.exceptions.TelegramRetryAfter]:
                self._logger.log_exception(e)

    async def add_funds_enter_handler(
            self,
            message: aiogram.types.Message,
            state: aiogram.fsm.context.FSMContext,
    ) -> None:
        _amount = message.text

        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{self.add_funds_enter_handler.__name__} ({_amount=})",
        )

        self._database.users.add_user(
            tg_id=message.from_user.id,
            tg_username=message.from_user.username,
            balance=int(),
            referrer_id=None,
        )

        current_user = self._database.users.get_user(
            tg_id=message.from_user.id,
        )

        try:
            amount = int(_amount)

            if self._data.plans.minimum_plan.cost <= current_user.balance + amount <= self._get_max_balance(
                    tg_id=current_user.tg_id,
            ):
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
                text=self._strings.menu.add_funds_enter(
                    min_amount=self._data.plans.minimum_plan.cost,
                    max_amount=self._get_max_balance(tg_id=current_user.tg_id) - current_user.balance,
                    error=True,
                ),
                reply_markup=markup_builder.as_markup(),
            )

    async def admin_user_balance_enter_handler(
            self,
            message: aiogram.types.Message,
            state: aiogram.fsm.context.FSMContext,
    ) -> None:
        _amount = message.text
        current_user_id = (await state.get_data())["tg_id"]

        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{self.admin_user_balance_enter_handler.__name__} ({current_user_id=}, {_amount=})",
        )

        current_user = self._database.users.get_user(
            tg_id=current_user_id,
        )

        try:
            amount = int(_amount)

            self._database.users.edit_balance(
                tg_id=current_user.tg_id,
                balance=amount,
            )

            current_user = self._database.users.get_user(
                tg_id=current_user.tg_id,
            )

            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.back_to_admin)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=self._strings.menu.admin_user_balance_enter_success(
                    current_user=current_user,
                ),
                reply_markup=markup_builder.as_markup(),
            )

            await state.clear()
        except:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.back_to_admin)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=self._strings.menu.admin_user_balance_enter(
                    current_user=current_user,
                    max_balance=self._get_max_balance(
                        tg_id=current_user.tg_id,
                    ),
                    error=True,
                ),
                reply_markup=markup_builder.as_markup(),
            )

    async def admin_page_enter_handler(
            self,
            message: aiogram.types.Message,
            state: aiogram.fsm.context.FSMContext,
    ):
        _element_id = message.text
        current_state = await state.get_state()

        self._logger.log_user_interaction(
            user=message.from_user,
            interaction=f"{self.admin_page_enter_handler.__name__} ({current_state=}, {_element_id=})",
        )

        try:
            match current_state:
                case self._states.admin_users_enter:
                    current_user_id = int(_element_id)

                    current_user = self._database.users.get_user(
                        tg_id=current_user_id,
                    )

                    referrer_user = self._database.users.get_user(
                        tg_id=current_user.referrer_id,
                    ) if current_user.referrer_id else None

                    current_referrer_model = self._config.referral.get_referrer_model(
                        referrer=self._data.referrers.get_referrer_by_id(
                            tg_id=current_user.tg_id,
                        ),
                    )

                    current_subscriptions = self._database.subscriptions.get_user_active_subscriptions(
                        tg_id=current_user.tg_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(
                        self._buttons.admin_user_balance_enter(
                            tg_id=current_user.tg_id,
                        ),
                    )
                    markup_builder.row(
                        self._buttons.admin_subscriptions(
                            tg_id=current_user.tg_id,
                        ),
                    )
                    markup_builder.row(
                        self._buttons.admin_payments(
                            tg_id=current_user.tg_id,
                        ),
                    )
                    if referrer_user:
                        markup_builder.row(
                            self._buttons.admin_user_referrer(
                                tg_id=referrer_user.tg_id,
                            ),
                        )
                    markup_builder.row(self._buttons.back_to_admin)

                    await self._bot.send_message(
                        chat_id=message.chat.id,
                        message_thread_id=self._get_message_thread_id(message),
                        text=self._strings.menu.profile(
                            user=current_user,
                            referrer_model=current_referrer_model,
                            referrer_user=referrer_user,
                            subscriptions_count=len(current_subscriptions),
                            friends_count=self._database.users.get_ref_count(
                                tg_id=current_user.tg_id,
                            ),
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case self._states.admin_subscriptions_enter:
                    current_subscription_id = int(_element_id)

                    current_subscription = self._database.subscriptions.get_subscription(
                        subscription_id=current_subscription_id,
                    )

                    current_user = self._database.users.get_user(
                        tg_id=current_subscription.tg_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    if not current_subscription.is_expired:
                        markup_builder.row(
                            self._buttons.subscription_config(
                                subscription_id=current_subscription.subscription_id,
                            ),
                        )
                        markup_builder.row(
                            self._buttons.admin_subscription_expire(
                                subscription_id=current_subscription.subscription_id,
                            ),
                        )
                    markup_builder.row(
                        self._buttons.admin_user(
                            tg_id=current_user.tg_id,
                        ),
                    )
                    markup_builder.row(self._buttons.back_to_admin)

                    await self._bot.send_message(
                        chat_id=message.chat.id,
                        message_thread_id=self._get_message_thread_id(message),
                        text=self._strings.menu.subscription(
                            subscription=current_subscription,
                            user=current_user,
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
                case self._states.admin_payments_enter:
                    current_payment_id = int(_element_id)

                    current_payment = self._database.payments.get_payment(
                        payment_id=current_payment_id,
                    )

                    current_user = self._database.users.get_user(
                        tg_id=current_payment.tg_id,
                    )

                    markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
                    markup_builder.row(
                        self._buttons.admin_user(
                            tg_id=current_user.tg_id,
                        ),
                    )
                    markup_builder.row(self._buttons.back_to_admin)

                    await self._bot.send_message(
                        chat_id=message.chat.id,
                        message_thread_id=self._get_message_thread_id(message),
                        text=self._strings.menu.admin_payment(
                            payment=current_payment,
                            user=current_user,
                        ),
                        reply_markup=markup_builder.as_markup(),
                    )
            await state.clear()
        except:
            markup_builder = aiogram.utils.keyboard.InlineKeyboardBuilder()
            markup_builder.row(self._buttons.back_to_admin)

            await self._bot.send_message(
                chat_id=message.chat.id,
                message_thread_id=self._get_message_thread_id(message),
                text=self._strings.menu.admin_page_enter(
                    error=True,
                ),
                reply_markup=markup_builder.as_markup(),
            )

    # endregion
