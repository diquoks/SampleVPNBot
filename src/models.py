from __future__ import annotations
import enum
import pyquoks.models


# Enums
class PlansType(enum.IntEnum):
    MONTH = 0
    QUARTER = 1
    HALF = 2
    YEAR = 3


# Models & Containers
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


class PlansContainer(pyquoks.models.IContainer):
    _ATTRIBUTES = {
        "currency",
        "currency_sign",
        "max_balance",
        "multiplier",
    }
    _OBJECTS = {
        "plans": Plan,
    }
    currency: str
    currency_sign: str
    max_balance: int
    multiplier: int
    plans: list[Plan]


# Values
class UserValues(pyquoks.models.IValues):
    _ATTRIBUTES = {
        "tg_id",
        "tg_username",
        "balance",
        "ref_id",
    }
    tg_id: int | None
    tg_username: str | None
    balance: int | None
    ref_id: int | None
