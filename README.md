# Букинист

Учебный совместный проект онлайн-библиотеки / книжного магазина на Django с каталогом книг, корзиной, отзывами, личным кабинетом, подтверждением email, восстановлением пароля и системой чатов.

## Что умеет проект

- регистрация, вход и выход пользователя;
- личный кабинет с редактированием профиля и загрузкой аватарки;
- подтверждение email через код, отправленный на почту;
- восстановление пароля по коду из письма;
- каталог книг с:
  - поиском;
  - фильтрацией по жанру, автору и издательству;
  - сортировкой по цене;
  - страницами книги, жанра, автора и издательства;
- чтение электронной книги из каталога;
- корзина и оформление заказов;
- отзывы и рейтинг книг;
- пользовательские диалоги;
- чат поддержки;
- CI с прогоном тестов и coverage в GitHub Actions;
- deploy через self-hosted runner.

## Стек

- Python 3.13
- Django 5.2.12
- Django Channels
- Daphne
- SQLite
- Pillow
- Stripe
- HTML, Tailwind CSS, JavaScript
- SMTP (Gmail) для отправки писем
- GitHub Actions

## Структура проекта

```text
config/            # настройки проекта, главные urls, стартовые view
catalog/           # каталог книг, поиск, фильтры, сортировки, reader
cart_order/        # корзина, позиции корзины, заказы
users/             # регистрация, логин, профиль, email-верификация, reset password
review_rating/     # отзывы и оценки
chat/              # обычные диалоги между пользователями
support_chat/      # чат поддержки
service_entities/  # платежи, история статусов, доступ к файлам книг
frontend/          # шаблоны, статические файлы, JS и CSS
.github/workflows/ # CI и deploy workflow
```

## Основные приложения

### `catalog`
Отвечает за книги и каталог.

Содержит:
- авторов;
- жанры;
- издательства;
- книги;
- остатки на складе.

Реализованы:
- каталог;
- детальная страница книги;
- поиск;
- фильтры;
- сортировка;
- просмотр электронной книги.

### `users`
Отвечает за пользователей и профиль.

Реализованы:
- регистрация;
- вход / выход;
- профиль;
- редактирование профиля;
- загрузка аватарки;
- подтверждение почты;
- восстановление пароля по email.

### `cart_order`
Отвечает за корзину и заказы.

Реализованы:
- добавление книги в корзину;
- обновление количества;
- удаление из корзины;
- сущности заказа и позиций заказа.

### `review_rating`
Реализованы отзывы пользователей с рейтингом книги.

### `chat`
Обычные пользовательские диалоги и сообщения.

### `support_chat`
Отдельный чат поддержки между пользователем и оператором.

Особенность текущей реализации:
- оператор определяется через роль пользователя `support`;
- обычный пользователь подключается к одному из доступных операторов;
- если пользователь сам является оператором, ему показывается список диалогов поддержки.

### `service_entities`
Служебные сущности:
- платежи;
- история изменения статусов заказа;
- сообщения поддержки по заказу;
- доступ к файлам книг.

## Основные маршруты

### HTML-страницы
- `/` — главная страница
- `/catalog/` — каталог
- `/catalog/book/<slug>/` — страница книги
- `/catalog/reader/<slug>/` — чтение электронной книги
- `/cart/` — корзина
- `/cart/checkout/` — оформление заказа
- `/login/` — HTML-страница входа
- `/register/` — HTML-страница регистрации
- `/profile/` — HTML-страница профиля
- `/profile/edit/` — редактирование профиля
- `/profile/verify-email/` — подтверждение email
- `/reviews/my-reviews/` — мои отзывы
- `/chat/` — чат поддержки
- `/messages/` — пользовательские сообщения

### JSON / служебные маршруты
- `/users/register/` — регистрация пользователя через JSON
- `/users/login/` — вход пользователя через JSON
- `/users/logout/` — выход пользователя
- `/users/profile/` — JSON-профиль текущего пользователя
- `/users/password-reset/` — запрос сброса пароля
- `/users/password-reset/code/` — ввод кода сброса
- `/users/password-reset/new/` — установка нового пароля
- `/users/password-reset/resend/` — повторная отправка кода

### Платежи
- `/cart/checkout/create-session/` — создание Stripe Checkout Session
- `/cart/order/<order_id>/success/` — страница успешного заказа
- `/cart/stripe/webhook/` — Stripe webhook
## Установка и запуск

### 1. Клонировать репозиторий
```bash
git clone https://github.com/obratno123/library.git
cd library
```

### 2. Установить зависимости

```bash
pip install -r requirements.txt
```

### 3. Настроить переменные окружения

Минимально для локального запуска понадобятся:

```bash
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
```

### 4. Проверить локальные настройки
```md
Сейчас в `config/settings.py` часть путей настроена под Windows-deploy:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path("C:/deploy/shared/db/db.sqlite3"),
    }
}

MEDIA_ROOT = Path("C:/deploy/shared/media")
```

Для локального запуска удобнее временно заменить на:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

MEDIA_ROOT = BASE_DIR / "media"
```

## 5. Добавить отдельный раздел про оплату
Этого реально не хватает.

После блока `SMTP` добавь:

```md
## Оплата

Проект использует Stripe Checkout для оформления и подтверждения оплаты.

Логика работы:
- пользователь переходит на страницу оформления заказа;
- сервер создаёт `Order` и `Payment`;
- затем создаётся Stripe Checkout Session;
- после успешной оплаты Stripe отправляет webhook;
- webhook помечает заказ как оплаченный;
- для электронных книг создаётся доступ через `BookFileAccess`;
- корзина пользователя очищается.

Для работы оплаты нужно заполнить в настройках:
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
```

### 6. Применить миграции

```bash
python manage.py migrate
```

### 7. Создать суперпользователя

```bash
python manage.py createsuperuser
```

### 8. Запустить сервер

```bash
python manage.py runserver
```

После этого проект будет доступен по адресу:

```text
http://127.0.0.1:8000/
```

## Настройка email / SMTP

Для отправки писем проект использует SMTP.

В `settings.py` уже есть настройки под Gmail:

```python
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
```

Нужно задать переменные окружения:

```bash
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

Если используется Gmail, лучше применять **app password**, а не обычный пароль.

## WebSocket / чаты

Проект использует `channels` и `daphne`.

В настройках сейчас подключён:

```python
ASGI_APPLICATION = "config.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
```

Для локальной разработки этого достаточно.

## Тесты

Запуск тестов:

```bash
python manage.py test
```

Запуск с coverage:

```bash
coverage erase
coverage run --branch manage.py test
coverage report -m
coverage html
```

HTML-отчёт появится в папке `htmlcov/`.

## GitHub Actions

В проекте есть два workflow:

### `tests.yml`
- запускает тесты и coverage;
- срабатывает на `push` в ветки `tests` и `main`;
- срабатывает на `pull_request` в `main`.

### `deploy.yml`
- срабатывает на `push` в `main`;
- запускает deploy через self-hosted runner на Windows.

## Импорт книг

В проекте есть management command для импорта книг из CSV:

```bash
python manage.py import_books_csv
```

## Особенности текущей реализации

- для WebSocket используется `InMemoryChannelLayer`, что подходит для локальной разработки;
- часть путей в `settings.py` сейчас ориентирована на Windows-deploy;
- приложение `books` пока является заготовкой;
- часть бизнес-логики оплаты и доступа к электронным книгам реализована через служебные модели `service_entities`.

## Авторы

Совместный проект Бориса (`@obratno123`) и Григория (`@bl1nchik2287`).
