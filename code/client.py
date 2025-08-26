from __future__ import annotations
import traceback, logging, telebot, sys
import data


class VPNBot(telebot.TeleBot):
    # TODO: добавить класс для сохранения и взаимодействия с логами
    class ExceptionHandler(telebot.ExceptionHandler):
        def handle(self, _):
            logging.error(traceback.format_exc())
            return True

    def __init__(self):
        self._config = data.BotConfig()
        logging.basicConfig(level=logging.INFO)
        super().__init__(
            token=self._config.settings.token,
            exception_handler=self.ExceptionHandler(),
        )


vpn_bot = VPNBot()


@vpn_bot.message_handler(commands=["start"])
def start(message: telebot.types.Message):
    logging.info(f"{sys._getframe().f_code.co_name}: {message.from_user.id} - \"{message.text}\"")
    vpn_bot.send_message(chat_id=message.chat.id, text="Привет, мир!")
