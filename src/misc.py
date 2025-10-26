from __future__ import annotations
import math
import aiogram
import models, data


class ButtonsContainer:
    def __init__(self) -> None:
        self._data = data.DataProvider()
        self._config = data.ConfigProvider()

    # region /start

    @property
    def plans(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Тарифные планы",
            callback_data="plans",
        )

    @property
    def add_funds(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Пополнить баланс",
            callback_data="add_funds",
        )

    @staticmethod
    def invite_friend(bot_username: str, tg_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Пригласить друга",
            copy_text=aiogram.types.CopyTextButton(
                text=f"https://t.me/{bot_username}?start={tg_id}",
            )
        )

    @staticmethod
    def subscriptions(page_id: int = data.Constants.FIRST_PAGE_ID) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Мои подписки",
            callback_data=f"subscriptions {page_id}",
        )

    @property
    def profile(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Профиль",
            callback_data="profile",
        )

    # endregion

    # region /admin

    @staticmethod
    def admin_users(page_id: int = data.Constants.FIRST_PAGE_ID) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Пользователи",
            callback_data=f"admin_users {page_id}",
        )

    @staticmethod
    def admin_configs(page_id: int = data.Constants.FIRST_PAGE_ID) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Конфигурации",
            callback_data=f"admin_configs {page_id}",
        )

    @staticmethod
    def admin_subscriptions(
            page_id: int = data.Constants.FIRST_PAGE_ID,
            tg_id: int = None,
    ) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Подписки",
            callback_data=" ".join(
                i for i in [
                    "admin_subscriptions",
                    str(page_id),
                    str(tg_id) if tg_id else None,
                ] if i
            ),
        )

    @staticmethod
    def admin_payments(
            page_id: int = data.Constants.FIRST_PAGE_ID,
            tg_id: int = None,
    ) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Платежи",
            callback_data=" ".join(
                i for i in [
                    "admin_payments",
                    str(page_id),
                    str(tg_id) if tg_id else None,
                ] if i
            ),
        )

    @property
    def admin_logs(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Логи",
            callback_data="admin_logs",
        )

    @property
    def admin_settings(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Настройки",
            callback_data="admin_settings",
        )

    @staticmethod
    def admin_user_balance_enter(tg_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Изменить баланс",
            callback_data=f"admin_user_balance_enter {tg_id}",
        )

    @staticmethod
    def admin_user_referrer(tg_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Реферер",
            callback_data=f"admin_user {tg_id}",
        )

    @staticmethod
    def admin_user(tg_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Пользователь",
            callback_data=f"admin_user {tg_id}",
        )

    @staticmethod
    def admin_subscription_expire(subscription_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Завершить подписку",
            callback_data=f"admin_subscription_expire {subscription_id}",
        )

    # endregion

    # region plans

    def plan_add_funds(self, amount: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=f"Пополнить на {self._config.payments.get_amount_with_currency(amount)}",
            callback_data=f"add_funds {amount}",
        )

    def _plan(self, plan_type: models.PlansType) -> aiogram.types.InlineKeyboardButton:
        current_plan = self._data.plans.get_plan_by_id(plan_type.value)

        return aiogram.types.InlineKeyboardButton(
            text=current_plan.name,
            callback_data=f"plan {plan_type.value}",
        )

    @property
    def plan_buttons(self) -> list[aiogram.types.InlineKeyboardButton]:
        return [
            self._plan(
                plan_type=plan_type,
            ) for plan_type in models.PlansType
        ]

    def _plan_subscribe(self, plan_type: models.PlansType) -> aiogram.types.InlineKeyboardButton:
        current_plan = self._data.plans.get_plan_by_id(plan_type.value)

        return aiogram.types.InlineKeyboardButton(
            text=f"Подписаться за {self._config.payments.get_amount_with_currency(current_plan.cost)}",
            callback_data=f"plan_subscribe {plan_type.value}",
        )

    @property
    def plan_subscribe_buttons(self) -> list[aiogram.types.InlineKeyboardButton]:
        return [
            self._plan_subscribe(
                plan_type=plan_type,
            ) for plan_type in models.PlansType
        ]

    # endregion

    # region add_funds

    @property
    def add_funds_enter(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Ввести сумму",
            callback_data="add_funds_enter",
        )

    def _add_funds(self, amount: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=self._config.payments.get_amount_with_currency(amount),
            callback_data=f"add_funds {amount}",
        )

    @property
    def add_funds_buttons(self) -> list[aiogram.types.InlineKeyboardButton]:
        return [
            self._add_funds(
                amount=self._data.plans.get_plan_by_id(plan_type.value).cost,
            ) for plan_type in models.PlansType
        ]

    # endregion

    # region subscriptions

    @staticmethod
    def subscription_config(subscription_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Данные для подключения",
            callback_data=f"subscription_config_file {subscription_id}",
        )

    @staticmethod
    def subscription_config_file(subscription_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Файл конфигурации",
            callback_data=f"subscription_config_file {subscription_id}",
        )

    @staticmethod
    def subscription_config_copy(subscription_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Ключ для подключения",
            callback_data=f"subscription_config_copy {subscription_id}",
        )

    @property
    def subscription_config_download(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Скачать AmneziaVPN",
            url="https://storage.googleapis.com/amnezia/amnezia.org",
        )

    @staticmethod
    def subscription_switch_active(status_text: str, subscription_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=status_text,
            callback_data=f"subscription_switch_active {subscription_id}",
        )

    # endregion

    # region TODO: page

    @staticmethod
    def _page_enter(page: str) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Ввести ID элемента",
            callback_data=f"{page}_enter",
        )

    @staticmethod
    def _page_previous(
            page: str,
            page_id: int,
            tg_id: int = None,
            is_just_answer: bool = False,
    ) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="<",
            callback_data="just_answer" if is_just_answer else " ".join(
                i for i in [
                    page,
                    str(page_id),
                    str(tg_id) if tg_id else None,
                ] if i
            ),
        )

    @staticmethod
    def _page_info(
            page: str,
            page_id: int,
            page_count: int,
            tg_id: int = None,
            is_just_answer: bool = False,
    ) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=f"{page_id} / {page_count}",
            callback_data="just_answer" if is_just_answer else " ".join(
                i for i in [
                    page,
                    str(data.Constants.FIRST_PAGE_ID),
                    str(tg_id) if tg_id else None,
                ] if i
            ),
        )

    @staticmethod
    def _page_next(
            page: str,
            page_id: int,
            tg_id: int = None,
            is_just_answer: bool = False,
    ) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=">",
            callback_data="just_answer" if is_just_answer else " ".join(
                i for i in [
                    page,
                    str(page_id),
                    str(tg_id) if tg_id else None,
                ] if i
            ),
        )

    @staticmethod
    def page_item_user(page: str, tg_username: str | None, tg_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=f"{tg_username} ({tg_id})" if tg_username else tg_id,
            callback_data=f"{page} {tg_id}",
        )

    @staticmethod
    def page_item_subscription(page: str, plan_name: str, subscription_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=f"#{subscription_id} «{plan_name}»",
            callback_data=f"{page} {subscription_id}",
        )

    def page_item_payment(self, page: str, payment_amount: int, payment_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text=f"#{payment_id} ({self._config.payments.get_amount_with_currency(payment_amount)})",
            callback_data=f"{page} {payment_id}",
        )

    # endregion

    # region back_to_*

    @property
    def delete_to_start(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Главное меню",
            callback_data="delete_to_start",
        )

    @property
    def back_to_start(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="start",
        )

    @property
    def back_to_plans(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="plans",
        )

    @property
    def back_to_add_funds(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Отмена",
            callback_data="add_funds",
        )

    @staticmethod
    def back_to_subscriptions(page_id: int = data.Constants.FIRST_PAGE_ID) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data=f"subscriptions {page_id}",
        )

    @property
    def back_to_admin(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data="admin",
        )

    @staticmethod
    def back_to_plan(plan_id: int) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Назад",
            callback_data=f"plan {plan_id}",
        )

    # endregion

    # region view_*

    @property
    def view_start(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Главное меню",
            callback_data="start",
        )

    @property
    def view_plans(self) -> aiogram.types.InlineKeyboardButton:
        return aiogram.types.InlineKeyboardButton(
            text="Перейти к тарифам",
            callback_data="plans",
        )

    # endregion

    # region Helpers

    def get_page_buttons(
            self,
            page_items: list,
            page: str,
            page_id: int,
            tg_id: int | None = None,
    ) -> tuple[
        aiogram.types.InlineKeyboardButton,
        tuple[
            aiogram.types.InlineKeyboardButton,
            aiogram.types.InlineKeyboardButton,
            aiogram.types.InlineKeyboardButton,
        ],
    ]:
        previous_page_id = page_id - 1
        next_page_id = page_number = page_id + 1
        pages_count = math.ceil(len(page_items) / data.Constants.ITEMS_PER_PAGE)

        return (
            self._page_enter(
                page=page,
            ),
            (
                self._page_previous(
                    page=page,
                    page_id=previous_page_id,
                    is_just_answer=previous_page_id < data.Constants.FIRST_PAGE_ID,
                    tg_id=tg_id,
                ),
                self._page_info(
                    page=page,
                    page_id=page_number,
                    page_count=pages_count,
                    tg_id=tg_id,
                    is_just_answer=page_id == data.Constants.FIRST_PAGE_ID,
                ),
                self._page_next(
                    page=page,
                    page_id=next_page_id,
                    tg_id=tg_id,
                    is_just_answer=next_page_id >= pages_count,
                ),
            ),
        )

    # endregion
