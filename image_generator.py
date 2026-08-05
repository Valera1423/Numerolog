# image_generator.py
from PIL import Image, ImageDraw, ImageFont
import io
import os

def generate_matrix_image(matrix: dict, name: str, birthdate_str: str) -> bytes:
    """
    Создаёт PNG-изображение Теневой Матрицы Судьбы с кругами и числами.
    Размер: 800x800, тёмно-красный фон.
    Возвращает байты изображения.
    """
    # Настройки
    width, height = 800, 800
    bg_color = (26, 11, 13)          # тёмно-красный
    circle_color = (215, 176, 106)   # золотой
    text_color = (255, 255, 255)     # белый
    title_color = (215, 176, 106)    # золотой

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Загрузка шрифта (если нет, используется стандартный)
    try:
        font_path = os.path.join(os.path.dirname(__file__), "static", "arial.ttf")
        title_font = ImageFont.truetype(font_path, 32)
        num_font = ImageFont.truetype(font_path, 48)
        label_font = ImageFont.truetype(font_path, 20)
    except IOError:
        title_font = ImageFont.load_default()
        num_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    # Заголовок
    draw.text((width//2, 40), "Теневая Матрица Судьбы", fill=title_color, font=title_font, anchor="mt")
    draw.text((width//2, 80), f"{name} | {birthdate_str}", fill=text_color, font=label_font, anchor="mt")

    # Координаты позиций (крест)
    positions = {
        "day": (200, 250),
        "month": (600, 250),
        "year": (400, 450),   # год внизу центра
        "day_month": (200, 550),
        "month_year": (600, 550),
        "center": (400, 400),
        # дополнительные (можно расширить)
    }

    # Рисуем круги и числа
    for key, pos in positions.items():
        if key in matrix:
            val = matrix[key]
            # Рисуем круг
            draw.ellipse(
                [pos[0]-35, pos[1]-35, pos[0]+35, pos[1]+35],
                outline=circle_color, width=3
            )
            # Пишем число
            draw.text(pos, str(val), fill=text_color, font=num_font, anchor="mm")

    # Добавим подписи к кругам (опционально)
    labels = {
        "day": "День",
        "month": "Месяц",
        "year": "Год",
        "day_month": "Д+М",
        "month_year": "М+Г",
        "center": "Судьба",
    }
    for key, pos in positions.items():
        if key in labels and key in matrix:
            draw.text((pos[0], pos[1]+50), labels[key], fill=circle_color, font=label_font, anchor="mt")

    # Сохраняем в буфер
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()