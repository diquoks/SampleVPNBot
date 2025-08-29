import threading
import client


def main():
    bot = client.Client()
    bot_thread = threading.Thread(target=bot.polling_thread, name="botThread")
    bot_thread.start()


if __name__ == "__main__":
    main()
