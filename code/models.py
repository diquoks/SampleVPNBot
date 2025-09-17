from __future__ import annotations
import enum


# Abstract classes
class IModel:
    _ATTRIBUTES: dict | set | None = None
    _OBJECTS: dict | None = None
    data: dict

    def __init__(self, data: dict):
        setattr(self, "data", data)
        if isinstance(self._ATTRIBUTES, set):
            for i in self._ATTRIBUTES:
                try:
                    setattr(self, i, data[i])
                except:
                    setattr(self, i, None)
        if isinstance(self._ATTRIBUTES, dict):
            for k, v in self._ATTRIBUTES.items():
                if isinstance(v, set):
                    for i in v:
                        try:
                            setattr(self, i, data[k][i])
                        except:
                            setattr(self, i, None)
        if isinstance(self._OBJECTS, dict):
            for k, v in self._OBJECTS.items():
                try:
                    setattr(self, k, v(data=data[k]))
                except:
                    setattr(self, k, None)


# Enums
class PlansType(enum.IntEnum):
    MONTH = 0
    QUARTER = 1
    HALF = 2
    YEAR = 3


# Utils and containers
class PlansContainer:
    data: dict
    max_balance: int | None
    plans: list[Plan] | None

    def __init__(self, data: dict):
        setattr(self, "data", data)
        setattr(self, "max_balance", data["max_balance"])
        setattr(self, "plans", [Plan(data=i) for i in data["plans"]])


# Models
class Plan(IModel):
    _ATTRIBUTES = {
        "months",
        "price",
    }
    data: dict
    months: int | None
    price: int | None
