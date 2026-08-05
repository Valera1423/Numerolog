# pdf_generator_playwright.py
import os
import base64
from playwright.sync_api import sync_playwright
from jinja2 import Template
from datetime import datetime
from typing import Dict, Any, Optional

PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

def generate_full_pdf(user_data: Dict[str, Any],
                      numerology_data: Dict[str, Any],
                      interpretation_data: Dict[str, Any],
                      matrix_image_bytes: Optional[bytes] = None,
                      report_type: str = 'full') -> Optional[str]:
    """
    Генерирует красивый PDF с использованием Playwright.
    Включает базовые числа, Матрицу Судьбы (с картинкой), блокировки.
    """
    # Подготовка данных
    template_data = {
        'user_name': user_data.get('fio', 'Пользователь'),
        'birthdate': user_data.get('birthdate', ''),
        'current_date': datetime.now().strftime('%d.%m.%Y'),
        'current_year': datetime.now().year,
    }
    # Добавляем числа
    for key in ['life_path', 'expression', 'soul_urge', 'personality']:
        template_data[f'{key}_number'] = numerology_data.get(key, '')
    # Добавляем матрицу
    matrix = numerology_data.get('matrix', {})
    if matrix:
        template_data['matrix'] = matrix
        if matrix_image_bytes:
            b64 = base64.b64encode(matrix_image_bytes).decode('utf-8')
            template_data['matrix_image_base64'] = f"data:image/png;base64,{b64}"
    # Добавляем блокировки (если есть)
    block = numerology_data.get('block', {})
    if block:
        template_data['block_sphere'] = block.get('sphere_name', 'Жизни')
        template_data['block_number'] = block.get('number', '')
        template_data['block_text'] = block.get('text', '')
    # Добавляем интерпретации
    if isinstance(interpretation_data, dict):
        for key, val in interpretation_data.items():
            if isinstance(val, str):
                template_data[key] = val
    # Шаблон HTML (можно вынести в отдельный файл)
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Нумерологический отчёт</title>
        <style>
            body { font-family: 'Arial', sans-serif; background: #0a0304; color: #d4ccc5; margin: 0; padding: 0; }
            .page { width: 210mm; min-height: 297mm; padding: 20mm; background: radial-gradient(circle at center, #1c0a0e 0%, #0a0304 100%); }
            h1, h2, h3 { color: #d7b06a; }
            .matrix-img { max-width: 100%; border: 2px solid #d7b06a; }
            .block-box { background: rgba(179,40,40,0.1); border-left: 4px solid #b32828; padding: 10px; }
        </style>
    </head>
    <body>
        <div class="page">
            <h1>Нумерологический отчёт для {{ user_name }}</h1>
            <p>Дата рождения: {{ birthdate }}</p>
            <p>Дата отчёта: {{ current_date }}</p>
            <hr>
            <h2>Ключевые числа</h2>
            <p>Жизненный путь: <strong>{{ life_path_number }}</strong></p>
            <p>Выражение: {{ expression_number }}</p>
            <p>Душа: {{ soul_number }}</p>
            <p>Личность: {{ personality_number }}</p>
            {% if matrix %}
            <h2>Теневая Матрица Судьбы</h2>
            <p>Центр: {{ matrix.center }}</p>
            <p>КРТ: {{ matrix.key_talent }}</p>
            <p>КРП: {{ matrix.key_destiny }}</p>
            {% if matrix_image_base64 %}
            <img src="{{ matrix_image_base64 }}" class="matrix-img" alt="Матрица">
            {% endif %}
            {% endif %}
            {% if block_sphere %}
            <h2>Блокировка в {{ block_sphere }}</h2>
            <div class="block-box">{{ block_text }}</div>
            {% endif %}
            <hr>
            <p><small>© Супер-Нумеролог {{ current_year }}</small></p>
        </div>
    </body>
    </html>
    """
    template = Template(html_template)
    html_output = template.render(**template_data)

    # Генерация PDF
    output_path = os.path.join(PDF_STORAGE_PATH, f"{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_output, wait_until="networkidle")
        page.pdf(path=output_path, format="A4", print_background=True, margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"})
        browser.close()
    return output_path