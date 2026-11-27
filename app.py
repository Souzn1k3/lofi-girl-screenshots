import functools
import os
import sqlite3

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "lofi-girl-dev-secret-key")
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, ".flask_session")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
Session(app)

DB_PATH = os.environ.get("LOFI_DB", os.path.join(app.root_path, "gallery.db"))
IMAGES_DIR = os.path.join(app.static_folder, "images")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS screenshots (
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
"""

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "lofi1234"

STREAMS = [
    (
        "christmas lofi radio 🎄 cozy ambience to relax to",
        "https://www.youtube.com/watch?v=4t4AQ15yj1M",
    ),
    (
        "Study With Me 📚 Pomodoro",
        "https://www.youtube.com/watch?v=qGohtGC5Rtk",
    ),
    (
        "asian lofi radio ⛩️ beats to relax/study to",
        "https://www.youtube.com/watch?v=1Tl2FtV06qo",
    ),
]

DEMO_SCREENSHOTS = [
    (
        "A Winter's Love",
        "Праздничный вечер: гирлянды, подарки, снежный город за окном и тёплый свет лампы. Атмосфера новогоднего уюта.",
        "зимний вечер",
        "winter_love.png",
        "christmas lofi radio 🎄 cozy ambience to relax to",
    ),
    (
        "Submerge",
        "Тихая библиотека, стопки книг, чашка кофе и рыжий кот на стуле. Идеальный фон для учёбы и работы.",
        "учёба",
        "submerge.png",
        "Study With Me 📚 Pomodoro",
    ),
    (
        "Sakura and Fuji",
        "Весенняя Япония: цветущая сакура, гора Фудзи и тетрадь с записями. Спокойствие и вдохновение.",
        "весна",
        "sakura_fuji.png",
        "asian lofi radio ⛩️ beats to relax/study to",
    ),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)

    demo = db.execute(
        "SELECT id FROM users WHERE username = ?", (DEMO_USERNAME,)
    ).fetchone()
    if demo is None:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (DEMO_USERNAME, generate_password_hash(DEMO_PASSWORD)),
        )
        demo_id = cursor.lastrowid
    else:
        demo_id = demo["id"]

    if db.execute("SELECT COUNT(*) AS count FROM streams").fetchone()["count"] == 0:
        db.executemany(
            "INSERT INTO streams (title, url) VALUES (?, ?)",
            STREAMS,
        )

    if db.execute("SELECT COUNT(*) AS count FROM screenshots").fetchone()["count"] == 0:
        streams_by_title = {
            row["title"]: row["id"]
            for row in db.execute("SELECT id, title FROM streams").fetchall()
        }
        db.executemany(
            """
            INSERT INTO screenshots (user_id, stream_id, title, description, mood, image)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    demo_id,
                    streams_by_title.get(stream_title),
                    title,
                    description,
                    mood,
                    image,
                )
                for title, description, mood, image, stream_title in DEMO_SCREENSHOTS
            ],
        )

    db.commit()
    db.close()


def get_available_images():
    if not os.path.isdir(IMAGES_DIR):
        return []
    return sorted(
        name
        for name in os.listdir(IMAGES_DIR)
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    )


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def read_screenshot_form(db):
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    mood = request.form.get("mood", "").strip()
    image = request.form.get("image", "").strip()
    stream_raw = request.form.get("stream_id", "").strip()

    errors = []
    stream_id = None

    if not title:
        errors.append("Укажите название скриншота.")
    elif len(title) > 120:
        errors.append("Название не должно быть длиннее 120 символов.")

    if not description:
        errors.append("Укажите описание скриншота.")
    elif len(description) > 1000:
        errors.append("Описание не должно быть длиннее 1000 символов.")

    if len(mood) > 60:
        errors.append("Настроение не должно быть длиннее 60 символов.")

    if image and image not in get_available_images():
        errors.append("Выбранное изображение не найдено в папке static/images.")

    if stream_raw:
        try:
            stream_id = int(stream_raw)
        except ValueError:
            errors.append("Некорректный стрим.")
        else:
            stream = db.execute(
                "SELECT 1 FROM streams WHERE id = ?", (stream_id,)
            ).fetchone()
            if stream is None:
                errors.append("Выбранный стрим не найден.")
                stream_id = None

    values = {
        "title": title,
        "description": description,
        "mood": mood,
        "image": image,
        "stream_id": stream_id,
    }
    return values, errors


@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")

    if user_id is None:
        g.user = None
        return

    g.user = get_db().execute(
        "SELECT id, username FROM users WHERE id = ?", (user_id,)
    ).fetchone()

    if g.user is None:
        session.clear()


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", message="Страница или запись не найдены."), 404


@app.errorhandler(sqlite3.Error)
def database_error(error):
    app.logger.exception("Ошибка базы данных: %s", error)
    db = g.get("db")
    if db is not None:
        db.rollback()
    return (
        render_template(
            "error.html",
            message="Произошла ошибка при работе с базой данных. Попробуйте ещё раз.",
        ),
        500,
    )


@app.route("/")
@login_required
def index():
    db = get_db()
    user_id = g.user["id"]

    query = request.args.get("q", "").strip()
    selected_mood = request.args.get("mood", "").strip()

    sql = """
        SELECT s.*, st.title AS stream_title, st.url AS stream_url
        FROM screenshots AS s
        LEFT JOIN streams AS st ON st.id = s.stream_id
        WHERE s.user_id = ?
    """
    params = [user_id]

    if query:
        sql += " AND LOWER(s.title) LIKE LOWER(?)"
        params.append("%" + query + "%")

    if selected_mood:
        sql += " AND s.mood = ?"
        params.append(selected_mood)

    sql += " ORDER BY s.id DESC"

    screenshots = db.execute(sql, params).fetchall()

    moods = [
        row["mood"]
        for row in db.execute(
            """
            SELECT DISTINCT mood
            FROM screenshots
            WHERE user_id = ? AND mood != ''
            ORDER BY mood
            """,
            (user_id,),
        ).fetchall()
    ]

    total_count = db.execute(
        "SELECT COUNT(*) AS count FROM screenshots WHERE user_id = ?",
        (user_id,),
    ).fetchone()["count"]

    return render_template(
        "index.html",
        screenshots=screenshots,
        total_count=total_count,
        query=query,
        selected_mood=selected_mood,
        moods=moods,
    )


@app.route("/screenshots/<int:screenshot_id>")
@login_required
def detail(screenshot_id):
    screenshot = get_db().execute(
        """
        SELECT s.*, st.title AS stream_title, st.url AS stream_url
        FROM screenshots AS s
        LEFT JOIN streams AS st ON st.id = s.stream_id
        WHERE s.id = ? AND s.user_id = ?
        """,
        (screenshot_id, g.user["id"]),
    ).fetchone()

    if screenshot is None:
        abort(404)

    return render_template("detail.html", screenshot=screenshot)


@app.route("/screenshots/add", methods=["GET", "POST"])
@login_required
def add_screenshot():
    db = get_db()
    streams = db.execute("SELECT id, title FROM streams ORDER BY title").fetchall()

    if request.method == "POST":
        values, errors = read_screenshot_form(db)

        if errors:
            return render_template(
                "add.html",
                errors=errors,
                streams=streams,
                available_images=get_available_images(),
                title=values["title"],
                description=values["description"],
                mood=values["mood"],
                selected_image=values["image"],
                selected_stream=values["stream_id"] or 0,
            )

        db.execute(
            """
            INSERT INTO screenshots
                (user_id, stream_id, title, description, mood, image)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                values["stream_id"],
                values["title"],
                values["description"],
                values["mood"],
                values["image"],
            ),
        )
        db.commit()

        flash("Скриншот добавлен.", "success")
        return redirect(url_for("index"))

    return render_template(
        "add.html",
        streams=streams,
        available_images=get_available_images(),
    )


@app.route("/screenshots/<int:screenshot_id>/edit", methods=["GET", "POST"])
@login_required
def edit_screenshot(screenshot_id):
    db = get_db()
    screenshot = db.execute(
        "SELECT * FROM screenshots WHERE id = ? AND user_id = ?",
        (screenshot_id, g.user["id"]),
    ).fetchone()

    if screenshot is None:
        abort(404)

    streams = db.execute("SELECT id, title FROM streams ORDER BY title").fetchall()

    if request.method == "POST":
        values, errors = read_screenshot_form(db)

        if errors:
            return render_template(
                "edit.html",
                screenshot=screenshot,
                errors=errors,
                streams=streams,
                available_images=get_available_images(),
                title=values["title"],
                description=values["description"],
                mood=values["mood"],
                selected_image=values["image"],
                selected_stream=values["stream_id"] or 0,
            )

        db.execute(
            """
            UPDATE screenshots
            SET title = ?, description = ?, mood = ?, image = ?, stream_id = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                values["title"],
                values["description"],
                values["mood"],
                values["image"],
                values["stream_id"],
                screenshot_id,
                g.user["id"],
            ),
        )
        db.commit()

        flash("Изменения сохранены.", "success")
        return redirect(url_for("detail", screenshot_id=screenshot_id))

    return render_template(
        "edit.html",
        screenshot=screenshot,
        streams=streams,
        available_images=get_available_images(),
        selected_stream=screenshot["stream_id"] or 0,
    )


@app.route("/screenshots/<int:screenshot_id>/delete", methods=["POST"])
@login_required
def delete_screenshot(screenshot_id):
    db = get_db()
    screenshot = db.execute(
        "SELECT id FROM screenshots WHERE id = ? AND user_id = ?",
        (screenshot_id, g.user["id"]),
    ).fetchone()

    if screenshot is None:
        abort(404)

    db.execute(
        "DELETE FROM screenshots WHERE id = ? AND user_id = ?",
        (screenshot_id, g.user["id"]),
    )
    db.commit()

    flash("Скриншот удалён.", "success")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        errors = []

        if len(username) < 3:
            errors.append("Имя пользователя должно содержать минимум 3 символа.")
        elif len(username) > 50:
            errors.append("Имя пользователя не должно быть длиннее 50 символов.")

        if len(password) < 6:
            errors.append("Пароль должен содержать минимум 6 символов.")

        if password != password_confirm:
            errors.append("Пароли не совпадают.")

        if not errors:
            db = get_db()
            exists = db.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            ).fetchone()

            if exists is not None:
                errors.append("Пользователь с таким именем уже существует.")
            else:
                try:
                    cursor = db.execute(
                        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)),
                    )
                    db.commit()
                except sqlite3.IntegrityError:
                    db.rollback()
                    errors.append("Пользователь с таким именем уже существует.")
                else:
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    flash("Регистрация прошла успешно.", "success")
                    return redirect(url_for("index"))

        if errors:
            return render_template("register.html", errors=errors, username=username)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        errors = []
        user = None

        if not username or not password:
            errors.append("Введите имя пользователя и пароль.")
        else:
            user = get_db().execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()

        if not errors and (
            user is None or not check_password_hash(user["password_hash"], password)
        ):
            errors.append("Неверное имя пользователя или пароль.")

        if errors:
            return render_template("login.html", errors=errors, username=username)

        session.clear()
        session["user_id"] = user["id"]
        flash("Вы вошли в систему.", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Вы вышли из системы.", "success")
    return redirect(url_for("login"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
