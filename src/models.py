from __future__ import annotations
import datetime, enum
import pyquoks.models
import constants


# region Enums

class PlansType(enum.IntEnum):
    MONTH = 0
    QUARTER = 1
    HALF = 2
    YEAR = 3


# endregion

# region Models & Containers

class Plan(pyquoks.models.IModel):
    _ATTRIBUTES = {
        "description",
        "months",
        "name",
        "price",
    }
    description: str | None
    months: int | None
    name: str | None
    price: int | None

    @property
    def cost(self) -> int:
        return self.price * self.months

    @property
    def days(self) -> int:
        return self.months * constants.DAYS_IN_MONTH


class PlansContainer(pyquoks.models.IContainer):
    _DATA = {
        "plans": Plan,
    }
    plans: list[Plan] | None

    def get_plan_by_id(self, plan_id: int) -> Plan:
        return self.plans[plan_id]

    @property
    def minimum_plan(self) -> Plan:
        return self.get_plan_by_id(
            plan_id=constants.MINIMUM_PLAN_ID,
        )


class Referrer(pyquoks.models.IModel):
    _ATTRIBUTES = {
        "tg_id",
        "multiplier_common",
        "multiplier_first",
    }
    tg_id: int | None
    multiplier_common: float | None
    multiplier_first: float | None

    def get_referrer_multiplier(self, is_first_payment: bool) -> float | None:
        return self.multiplier_first if is_first_payment else self.multiplier_common


class ReferrersContainer(pyquoks.models.IContainer):
    _DATA = {
        "referrers": Referrer,
    }
    referrers: list[Referrer] | None

    def get_referrer_by_id(self, tg_id: int) -> Referrer | None:
        try:
            return list(
                filter(
                    lambda referrer: referrer.tg_id == tg_id,
                    self.referrers,
                )
            )[0]
        except IndexError:
            return None


# endregion

# region Values

class ConfigValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "id",
        "name",
        "data",
        "subscription_id",
    }
    id: int | None
    name: str | None
    data: str | None
    subscription_id: int | None


class PaymentValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "id",
        "provider_id",
        "amount",
        "currency",
        "payload",
        "date",
        "tg_id",
    }
    id: int | None
    provider_id: str | None
    amount: int | None
    currency: str | None
    payload: str | None
    date: int | None
    tg_id: int | None


class SubscriptionValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "id",
        "plan_id",
        "is_active",
        "is_checked",
        "subscribed_at",
        "expires_at",
        "tg_id",
        "config_id",
    }
    id: int | None
    plan_id: int | None
    is_active: int | None
    is_checked: int | None
    subscribed_at: int | None
    expires_at: int | None
    tg_id: int | None
    config_id: int | None

    @property
    def is_expired(self) -> bool:
        return self.expires_at < datetime.datetime.now().timestamp()

    @property
    def status(self) -> str:
        return "Истекла" if self.is_expired else "Активна" if self.is_active else "Отменена"


class UserValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "tg_id",
        "tg_username",
        "balance",
        "referrer_id",
    }
    tg_id: int | None
    tg_username: str | None
    balance: int | None
    referrer_id: int | None

    @property
    def html_text(self) -> str:
        return f"@{self.tg_username} (<code>{self.tg_id}</code>)" if self.tg_username else str(self.tg_id)

    @property
    def text(self) -> str:
        return f"@{self.tg_username} ({self.tg_id})" if self.tg_username else str(self.tg_id)

# endregion
