import logging
import client


def main():
    while True:
        try:
            client.vpn_bot.polling()
        except:
            logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
