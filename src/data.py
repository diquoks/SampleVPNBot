from __future__ import annotations
import aiogram
import pyquoks.data, pyquoks.utils
import models


# Named classes
class DataProvider(pyquoks.data.IDataProvider):
    _PATH = pyquoks.utils.get_path("data/{0}.json")
    _DATA_VALUES = {
        "plans": models.PlansContainer,
    }
    plans: models.PlansContainer


class ConfigProvider(pyquoks.data.IConfigProvider):
    class SettingsConfig(pyquoks.data.IConfigProvider.IConfig):
        _SECTION = "Settings"
        admin_list: list[int]
        bot_token: str
        file_logging: bool
        skip_updates: bool
        provider_token: str

    class TestConfig(pyquoks.data.IConfigProvider.IConfig):  # TODO: удалить после интеграции базы данных (DATABASE)
        _SECTION = "Test"
        balance: int

    _CONFIG_VALUES = {
        "Settings":
            {
                "admin_list": list,
                "bot_token": str,
                "file_logging": bool,
                "skip_updates": bool,
                "provider_token": str,
            },
        "Test":
            {
                "balance": int,
            },
    }
    _CONFIG_OBJECTS = {
        "settings": SettingsConfig,
        "test": TestConfig,
    }
    settings: SettingsConfig
    test: TestConfig


class LoggerService(pyquoks.data.LoggerService):
    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - «{interaction}»")
