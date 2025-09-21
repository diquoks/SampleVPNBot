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
        "months",
        "price",
    }
    months: int | None
    price: int | None


class PlansContainer(pyquoks.models.IContainer):
    _ATTRIBUTES = {
        "max_balance",
    }
    _OBJECTS = {
        "plans": Plan,
    }
    max_balance: int
    plans: list[Plan]
