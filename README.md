# SampleVPNBot

#### Заготовка Telegram-бота для продажи VPN-конфигураций

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

- [Telegram-канал с новостями](https://t.me/diquoks_channel)

---

## Сборка и запуск

### Необходимые компоненты

- [Docker Desktop](https://docs.docker.com/desktop)
- [Git](https://git-scm.com/downloads)
- [Python 3.13.8](https://www.python.org/downloads)

### Первоначальная настройка

##### Клонируйте репозиторий git

```bash
git clone https://github.com/diquoks/SampleVPNBot.git
```

##### Перейдите в корневую директорию

```bash
cd SampleVPNBot
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

##### Заполните `SampleVPNBot/src/config.ini` и следуйте инструкциям для [Docker](#docker)

### Docker

##### Перейдите в корневую директорию

```bash
cd ../
```

##### Создайте образ

```bash
docker build -t samplevpnbot .
```

##### Запустите контейнер

```bash
docker run -it -d --name SampleVPNBot samplevpnbot
```
