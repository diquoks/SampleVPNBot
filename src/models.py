from __future__ import annotations
import datetime, enum
import pyquoks.models


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


class PlansContainer(pyquoks.models.IContainer):
    _DATA = {
        "plans": Plan,
    }
    plans: list[Plan] | None

    def get_plan_by_id(self, plan_id: int) -> Plan:
        return self.plans[plan_id]


class Referrer(pyquoks.models.IModel):
    _ATTRIBUTES = {
        "tg_id",
        "multiplier_common",
        "multiplier_first",
    }
    tg_id: int | None
    multiplier_common: float | None
    multiplier_first: float | None


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

class PaymentValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "payment_id",
        "tg_id",
        "payment_amount",
        "payment_currency",
        "payment_payload",
        "payment_provider_id",
        "payment_date",
    }
    payment_id: int | None
    tg_id: int | None
    payment_amount: int | None
    payment_currency: str | None
    payment_payload: str | None
    payment_provider_id: str | None
    payment_date: int | None


class SubscriptionValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "subscription_id",
        "tg_id",
        "plan_id",
        "payment_amount",
        "subscribed_date",
        "expires_date",
        "is_active",
    }
    subscription_id: int | None
    tg_id: int | None
    plan_id: int | None
    payment_amount: int | None
    subscribed_date: int | None
    expires_date: int | None
    is_active: int | None

    @property
    def status(self) -> str:
        return "Истекла" if datetime.datetime.now().timestamp() > self.expires_date else "Активна" if self.is_active else "Отменена"


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

# endregion
