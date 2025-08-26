from __future__ import annotations
import configparser, json


class BotConfig:
    """
    :var settings: ``SettingsConfig``
    """

    class IConfig:
        _SECTION: str = None

        def __init__(self, parent: BotConfig) -> None:
            self._config = configparser.ConfigParser()
            self._config.read("config.ini")
            if not self._config.has_section(self._SECTION):
                self._config.add_section(self._SECTION)
            for i in parent._CONFIG_VALUES[self._SECTION]:
                try:
                    setattr(self, i, self._config.get(self._SECTION, i))
                except:
                    self._config.set(self._SECTION, i, i)
                    self._config.write(open("config.ini", "w"))

    class SettingsConfig(IConfig):
        """
        :var token: ``str``
        :var admin_list: ``list[int]``
        """

        _SECTION = "Settings"
        token: str | None
        admin_list: list[int] | str | None

        def __init__(self, parent: BotConfig) -> None:
            super().__init__(parent=parent)
            try:
                self.admin_list = json.loads(self.admin_list)
            except:
                raise configparser.ParsingError("config.ini is filled incorrectly!")

    _CONFIG_VALUES = {
        "Settings":
            {
                "token",
                "admin_list",
            },
    }

    def __init__(self) -> None:
        self.settings = self.SettingsConfig(self)
        super().__init__()
