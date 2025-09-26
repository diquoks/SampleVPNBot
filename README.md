# VastNetVPNBot

#### Ты думал тут что-то будет?

---

## Оглавление

- [Контакты](#контакты)
    - [Связь с разработчиком](#связь-с-разработчиком)
    - [Прочие ссылки](#прочие-ссылки)
- [Сборка и запуск](#сборка-и-запуск)
    - [Необходимые компоненты](#необходимые-компоненты)
    - [Первоначальная настройка](#первоначальная-настройка)
    - [Docker](#docker)

---

## Контакты

#### Связь с разработчиком

- [Telegram для связи](https://t.me/diquoks)
- [Почта для связи](mailto:diquoks@yandex.ru)

#### Прочие ссылки

- [Бот в Telegram](https://t.me/vastnetvpnbot)
- [Telegram-канал с новостями](https://t.me/diquoks_channel)

---

## Сборка и запуск

### Необходимые компоненты

- [Docker Desktop](https://docs.docker.com/desktop)
- [Git](https://git-scm.com/downloads)
- [Python](https://www.python.org/downloads)

### Первоначальная настройка

##### Клонируйте репозиторий git

```bash
git clone https://github.com/diquoks/VastNetVPNBot.git
```

##### Перейдите в корневую директорию

```bash
cd VastNetVPNBot
```

##### Установите зависимости

```bash
pip install -r requirements.txt
```

##### Перейдите в директорию `src`

```bash
cd src
```

##### Сгенерируйте файл `config.ini`

```bash
python main.py
```

##### Заполните `VastNetVPNBot/src/config.ini` и следуйте инструкциям для [Docker](#docker)

### Docker

##### Перейдите в корневую директорию

```bash
cd ../
```

##### Создайте образ

```bash
docker build -t vastnetvpnbot .
```

##### Запустите контейнер

```bash
docker run -it -d --name VastNetVPNBot vastnetvpnbot
```
