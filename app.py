import os

from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

IMAGES_DIR = os.path.join(app.static_folder, "images")

screenshots = [
    {
        "id": 1,
        "title": "A Winter's Love",
        "description": "Праздничный вечер: гирлянды, подарки, снежный город за окном и тёплый свет лампы. Атмосфера новогоднего уюта.",
        "mood": "зимний вечер",
        "image": "winter_love.png",
    },
    {
        "id": 2,
        "title": "Submerge",
        "description": "Тихая библиотека, стопки книг, чашка кофе и рыжий кот на стуле. Идеальный фон для учёбы и работы.",
        "mood": "учёба",
        "image": "submerge.png",
    },
    {
        "id": 3,
        "title": "Sakura and Fuji",
        "description": "Весенняя Япония: цветущая сакура, гора Фудзи и тетрадь с записями. Спокойствие и вдохновение.",
        "mood": "весна",
        "image": "sakura_fuji.png",
    },
]


def get_available_images():
    if not os.path.isdir(IMAGES_DIR):
        return []
    return sorted(
        name
        for name in os.listdir(IMAGES_DIR)
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
    )


def find_screenshot(screenshot_id):
    for item in screenshots:
        if item["id"] == screenshot_id:
            return item
    return None


def read_screenshot_form():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    mood = request.form.get("mood", "").strip()
    image = request.form.get("image", "").strip()

    errors = []

    if not title:
        errors.append("Укажите название скриншота.")

    if not description:
        errors.append("Укажите описание скриншота.")

    if image and image not in get_available_images():
        errors.append("Выбранное изображение не найдено в папке static/images.")

    return title, description, mood, image, errors


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    selected_mood = request.args.get("mood", "").strip()

    filtered = list(screenshots)

    if query:
        filtered = [
            item for item in filtered
            if query.lower() in item["title"].lower()
        ]

    if selected_mood:
        filtered = [
            item for item in filtered
            if item.get("mood", "") == selected_mood
        ]

    moods = sorted({item["mood"] for item in screenshots if item.get("mood")})

    return render_template(
        "index.html",
        screenshots=filtered,
        total_count=len(screenshots),
        query=query,
        selected_mood=selected_mood,
        moods=moods,
    )


@app.route("/screenshots/<int:screenshot_id>")
def detail(screenshot_id):
    screenshot = find_screenshot(screenshot_id)

    if screenshot is None:
        return "Скриншот не найден", 404

    return render_template("detail.html", screenshot=screenshot)


@app.route("/screenshots/add", methods=["GET", "POST"])
def add_screenshot():
    if request.method == "POST":
        title, description, mood, image, errors = read_screenshot_form()

        if errors:
            return render_template(
                "add.html",
                errors=errors,
                title=title,
                description=description,
                mood=mood,
                selected_image=image,
                available_images=get_available_images(),
            )

        new_screenshot = {
            "id": max((item["id"] for item in screenshots), default=0) + 1,
            "title": title,
            "description": description,
            "mood": mood,
            "image": image,
        }

        screenshots.append(new_screenshot)
        return redirect(url_for("index"))

    return render_template("add.html", available_images=get_available_images())


@app.route("/screenshots/<int:screenshot_id>/edit", methods=["GET", "POST"])
def edit_screenshot(screenshot_id):
    screenshot = find_screenshot(screenshot_id)

    if screenshot is None:
        return "Скриншот не найден", 404

    if request.method == "POST":
        title, description, mood, image, errors = read_screenshot_form()

        if errors:
            return render_template(
                "edit.html",
                screenshot=screenshot,
                errors=errors,
                title=title,
                description=description,
                mood=mood,
                selected_image=image,
                available_images=get_available_images(),
            )

        screenshot["title"] = title
        screenshot["description"] = description
        screenshot["mood"] = mood
        screenshot["image"] = image

        return redirect(url_for("detail", screenshot_id=screenshot_id))

    return render_template(
        "edit.html",
        screenshot=screenshot,
        available_images=get_available_images(),
    )


@app.route("/screenshots/<int:screenshot_id>/delete", methods=["POST"])
def delete_screenshot(screenshot_id):
    screenshot = find_screenshot(screenshot_id)

    if screenshot is None:
        return "Скриншот не найден", 404

    screenshots.remove(screenshot)
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
