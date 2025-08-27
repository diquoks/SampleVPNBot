import traceback, logging
import client


def main():
    while True:
        try:
            client.client.polling(non_stop=True)
        except:
            logging.error(traceback.format_exc())


if __name__ == '__main__':
    main()
