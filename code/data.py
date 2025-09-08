from __future__ import annotations
import configparser, datetime, logging, json, sys, os
import aiogram
import utils


class ConfigProvider:
    """
    :var settings: ``SettingsConfig``
    """

    class IConfig:
        _SECTION: str = None
        _CONFIG_VALUES: dict = None

        def __init__(self, parent: ConfigProvider = None) -> None:
            if isinstance(parent, ConfigProvider):
                self._CONFIG_VALUES = parent._CONFIG_VALUES[self._SECTION]
                self._incorrect_content_exception = configparser.ParsingError("config.ini is filled incorrectly!")
                self._config = configparser.ConfigParser()
                self._config.read(utils.get_path("config.ini"))
                if not self._config.has_section(self._SECTION):
                    self._config.add_section(self._SECTION)
                for k, v in self._CONFIG_VALUES.items():
                    try:
                        setattr(self, k, self._config.get(self._SECTION, k))
                    except:
                        self._config.set(self._SECTION, k, v.__name__)
                        with open(utils.get_path("config.ini"), "w") as file:
                            self._config.write(fp=file)
                for k, v in self._CONFIG_VALUES.items():
                    try:
                        if v == int:
                            setattr(self, k, int(getattr(self, k)))
                        elif v == bool:
                            if getattr(self, k) not in [str(True), str(False)]:
                                setattr(self, k, None)
                                raise self._incorrect_content_exception
                            else:
                                setattr(self, k, getattr(self, k) == str(True))
                        elif v in [dict, list]:
                            setattr(self, k, json.loads(getattr(self, k)))
                    except:
                        setattr(self, k, None)
                        raise self._incorrect_content_exception
                if not self.values:
                    raise self._incorrect_content_exception

        @property
        def values(self) -> dict | None:
            try:
                return {i: getattr(self, i) for i in self._CONFIG_VALUES}
            except:
                return None

    class SettingsConfig(IConfig):
        """
        :var admin_list: ``list[int]``
        :var bot_token: ``str``
        """

        _SECTION = "Settings"
        admin_list: list[int] | str | None
        bot_token: str | None

    _CONFIG_VALUES = {
        "Settings":
            {
                "admin_list": list,
                "bot_token": str,
            },
    }
    settings: SettingsConfig

    def __init__(self) -> None:
        self.settings = self.SettingsConfig(self)
        super().__init__()


class LoggerService(logging.Logger):
    def __init__(self, name: str, file_handling: bool = True, filename: str = datetime.datetime.now().strftime("%d-%m-%y-%H-%M-%S"), level: int = logging.NOTSET, folder_name: str = "logs") -> None:
        super().__init__(name, level)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(fmt="$levelname $asctime $name - $message", datefmt="%d-%m-%y %H:%M:%S", style="$"))
        self.addHandler(stream_handler)
        if file_handling:
            os.makedirs(utils.get_path(folder_name, only_abspath=True), exist_ok=True)
            file_handler = logging.FileHandler(utils.get_path(f"{folder_name}/{filename}-{name}.log", only_abspath=True), encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(fmt="$levelname $asctime - $message", datefmt="%d-%m-%y %H:%M:%S", style="$"))
            self.addHandler(file_handler)

    def log_user_interaction(self, user: aiogram.types.User, interaction: str) -> None:
        user_info = f"@{user.username} ({user.id})" if user.username else user.id
        self.info(f"{user_info} - \"{interaction}\"")

    def log_exception(self, e: Exception) -> None:
        self.error(msg=e, exc_info=True)
