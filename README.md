# Скриншоты Lofi Girl

Flask-приложение: галерея скриншотов Lofi Girl. Проект продолжает предыдущую работу, но данные теперь хранятся в базе данных SQLite. Добавлены CRUD, связанная таблица стримов и авторизация пользователей.

## Стек

- Flask
- SQLite (стандартный модуль `sqlite3`)
- Flask-Session (серверные сессии в файлах)
- Werkzeug (хеширование паролей)

## Запуск

```
py -m pip install -r requirements.txt
py app.py
```

Открыть в браузере: http://127.0.0.1:5000

Демо-аккаунт: логин `demo`, пароль `lofi1234`. При первом запуске автоматически создаётся файл `gallery.db`, таблицы и начальные данные: 3 стрима, 3 скриншота и демо-пользователь.

## Выполненные задания

### 1. Создание базы данных

Создана SQLite-база `gallery.db`. Основная сущность - скриншот Lofi Girl. Схема:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL
);

CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stream_id INTEGER,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    mood TEXT,
    image TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (stream_id) REFERENCES streams (id) ON DELETE SET NULL
);
```

Типы данных подобраны по смыслу: целые идентификаторы, строки для текста, дата создания, внешние ключи. Для SQLite включён `PRAGMA foreign_keys = ON`.

### 2. Перенос данных в SQLite

Списков с данными в коде больше нет. Все скриншоты читаются из базы. Функция `init_db()` создаёт таблицы и заполняет их начальными данными только при первом запуске, если база пустая.

### 3. CRUD

- Create: форма `/screenshots/add`, отправка POST, вставка через `INSERT`.
- Read: главная страница со списком и страница `/screenshots/<id>`.
- Update: форма `/screenshots/<id>/edit`, обновление через `UPDATE`.
- Delete: кнопка на странице подробностей, POST на `/screenshots/<id>/delete`, удаление через `DELETE`.

Обработка ошибок:

- обязательные поля проверяются на сервере, пустые значения не принимаются;
- при ошибках форма возвращается с сообщениями и ранее введёнными значениями;
- проверяется существование изображения в `static/images` и стрима в базе;
- несуществующая или чужая запись возвращает 404;
- все операции с базой обёрнуты в обработку `sqlite3.Error`, при ошибке выполняется `rollback` и показывается страница ошибки;
- удаление доступно только методом POST, GET возвращает 405.

### 4. Связанная таблица

Добавлена таблица `streams` со стримами Lofi Girl на YouTube. Связь один ко многим: у одного стрима может быть много скриншотов, у скриншота один стрим (`screenshots.stream_id`). Связанные данные получаются через `LEFT JOIN` на главной странице и на странице подробностей. На странице скриншота выводится название стрима и ссылка на YouTube.

Начальные стримы:

| Скриншот | Стрим | Ссылка |
| --- | --- | --- |
| `winter_love.png` | christmas lofi radio 🎄 cozy ambience to relax to | https://www.youtube.com/watch?v=4t4AQ15yj1M |
| `submerge.png` | Study With Me 📚 Pomodoro | https://www.youtube.com/watch?v=qGohtGC5Rtk |
| `sakura_fuji.png` | asian lofi radio ⛩️ beats to relax/study to | https://www.youtube.com/watch?v=1Tl2FtV06qo |

### 5. Пользователи

Реализованы регистрация, вход и выход. Пароли хранятся только в виде хешей: `generate_password_hash` при регистрации и `check_password_hash` при входе. Сессии работают через Flask-Session с хранением на файловой системе. Маршруты галереи закрыты декоратором `login_required`.

Индивидуальность данных: у каждого скриншота есть `user_id`. Все запросы чтения, редактирования и удаления фильтруются по текущему пользователю. Чужие записи недоступны и возвращают 404. Стримы общие, так как это справочник стримов Lofi Girl.

## Маршруты

| Метод | URL | Назначение |
| --- | --- | --- |
| GET | `/` | галерея, поиск и фильтр по настроению |
| GET | `/?q=...&mood=...` | поиск по названию и фильтрация |
| GET | `/screenshots/<id>` | подробности скриншота и стрим через JOIN |
| GET, POST | `/screenshots/add` | добавление скриншота |
| GET, POST | `/screenshots/<id>/edit` | редактирование |
| POST | `/screenshots/<id>/delete` | удаление |
| GET, POST | `/register` | регистрация |
| GET, POST | `/login` | вход |
| POST | `/logout` | выход |

## Структура проекта

```
app.py
requirements.txt
gallery.db              (создаётся при первом запуске)
static/
    images/
templates/
    base.html
    _form.html
    index.html
    detail.html
    add.html
    edit.html
    login.html
    register.html
    error.html
```

## Примечание

База данных создаётся и заполняется автоматически, поэтому проект запускается сразу после клонирования. Файл `gallery.db` и папка `.flask_session/` не попадают в git, так как создаются при запуске.
