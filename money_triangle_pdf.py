# money_triangle_pdf.py
import os
from playwright.sync_api import sync_playwright
from jinja2 import Template
from typing import List, Dict, Any

# ====================== ДАННЫЕ (можно вынести в отдельный файл) ======================
INNER_DESCRIPTIONS = {
    "1": "Ты первооткрыватель, и рожден(а) создавать то, чего никто ещё не создавал... Твоя самая слабая сторона – страх проявляться...",
    "2": "Это значит, что ты рожден(а) объединять других людей... Твоя самая слабая сторона – внутренняя недолюбленность...",
    "5": "Это значит, что ты рожден(а) быть духовным наставником и учителем для других... Твоя самая слабая сторона – распыленность...",
    "7": "Это значит, что ты тот человек, который способен на революции... Твоя самая слабая сторона — страх распространяться и расширяться...",
    "8": "Это значит, что ты рожден(а) увеличивать денежный потенциал этого мира... Твоя самая слабая сторона — обостренное чувство справедливости...",
}

TRIANGLE_DESCRIPTIONS = {
    "5": {"title": "5 АРКАН", "professions": "Всё, что связано с порядком, деньгами, счётом...", "blocks": "Хаос в делах и в жизни, если у вас незакрытые вопросы...", "spending": "В путешествия, в постоянные обучения..."},
    "7": {"title": "7 АРКАН", "professions": "Всё, что связано с движением: турагентства, работа с машинами...", "blocks": "Отсутствие движения и цели...", "spending": "В найм финансовых советников..."},
    "4": {"title": "4 АРКАН", "professions": "Руководящие должности... Физический труд...", "blocks": "Позиция подчинённого... Злоупотребление властью...", "spending": "В долгосрочные инвестиции (2-5 лет)..."},
    "3": {"title": "3 АРКАН", "professions": "Бьюти-индустрия, женщины, дети...", "blocks": "Формулировка «всё сама», отрицание помощи...", "spending": "В своё творчество и хобби..."},
    "9": {"title": "9 АРКАН", "professions": "Мудрость и духовность: учёные, врачи, целители...", "blocks": "Сомнения в своём профессионализме...", "spending": "В благотворительность..."},
    "2": {"title": "2 АРКАН", "professions": "Деятельность, связанная с женщинами и детьми...", "blocks": "Неискренность, обсуждение других за спиной...", "spending": "Посещение гонг-медитаций, ретритов..."}
}

PURPOSE_TABLE = [
    {"digit": "5", "who": "Учёный / учитель", "talents": "Аналитика", "blocks": "Распыляться", "energy": "Путешествие", "purpose": "Физики, учителя"},
    {"digit": "3", "who": "Актёр / творчество", "talents": "Артистизм", "blocks": "Меркантильность", "energy": "Творчество", "purpose": "Работа с женщинами"},
    {"digit": "9", "who": "Лекарь / мудрец", "talents": "Считывать знаки", "blocks": "Отшельничество", "energy": "Духовность", "purpose": "Эзотерика, медицина"},
    {"digit": "7", "who": "Воин / интуит", "talents": "Проницательность", "blocks": "Ограничения", "energy": "Движение", "purpose": "Политика, путешествия"},
    {"digit": "2", "who": "Оратор / медиатор", "talents": "Находить подход", "blocks": "Сплетни", "energy": "Ораторское искусство", "purpose": "Психолог, ведущий"},
    {"digit": "4", "who": "Трудолюбив", "talents": "Быстрая адаптация", "blocks": "Лень", "energy": "Стабильность", "purpose": "Спорт, строительство"}
]

# ====================== ГЕНЕРАЦИЯ PDF ======================

def generate_money_triangle_pdf(user_numbers: List[str], output_dir: str = "./pdfs") -> str:
    """
    Генерирует PDF с денежным треугольником.
    user_numbers: список из 5 строк (например, ['1','2','5','8','7'])
    output_dir: папка для сохранения PDF
    Возвращает путь к созданному файлу.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Фиксированные цифры для внешнего треугольника (по методике)
    triangle_numbers = ['5', '3', '9', '7', '2', '4']
    
    page_data = []
    for num in user_numbers:
        if num in INNER_DESCRIPTIONS:
            page_data.append({"type": "inner", "digit": num, "content": INNER_DESCRIPTIONS[num]})
            
    for num in triangle_numbers:
        if num in TRIANGLE_DESCRIPTIONS:
            item = TRIANGLE_DESCRIPTIONS[num]
            page_data.append({
                "type": "triangle", "digit": num, "title": item["title"],
                "professions": item["professions"], "blocks": item["blocks"], "spending": item["spending"]
            })

    # HTML Шаблон (тот же, что в тесте)
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Денежный код</title>
        <link href="https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Open+Sans:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Cinzel', serif; background: #0a0304; color: #f2e2d4; }
            .page { width: 210mm; height: 297mm; position: relative; page-break-after: always; background: radial-gradient(circle at center, #1c0a0e 0%, #0a0304 100%); overflow: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center;}
            .bg-smoke { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background-image: radial-gradient(circle at 10% 10%, rgba(200, 50, 50, 0.2) 0%, transparent 60%); z-index: 1; pointer-events: none; }
            .cover-title { font-size: 48px; text-transform: uppercase; text-align: center; z-index: 10; }
            .cover-subtitle { font-size: 30px; color: #d7b06a; text-align: center; z-index: 10; letter-spacing: 4px; }
            .pentagram-svg { z-index: 10; margin-bottom: 20px; width: 200px; height: 200px; }
            .bars-container { display: flex; gap: 20px; z-index: 10; margin-top: 100px; }
            .gold-bar { width: 70px; height: 180px; background: linear-gradient(90deg, #5e3a18 0%, #fceabb 25%, #e6c37a 50%, #a87e2e 80%, #402b12 100%); border-radius: 12px; box-shadow: 0 15px 30px rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; font-size: 56px; color: #2e1b0b; font-weight: 700; border: 2px solid #fcd48a; }
            .text-page { justify-content: flex-start; padding: 50px 70px; }
            .text-header { color: #b32828; font-size: 48px; border-bottom: 2px solid #d7b06a; padding-bottom: 15px; width: 100%; margin-bottom: 30px; text-align: center; }
            .text-body { font-family: 'Open Sans', sans-serif; font-size: 16px; line-height: 1.6; color: #d4ccc5; margin-bottom: 20px; width: 100%; }
            .purpose-table { width: 100%; border-collapse: collapse; margin-top: 20px; font-family: 'Open Sans', sans-serif; font-size: 12px; }
            .purpose-table th { background: #1d0a0b; color: #d7b06a; border: 1px solid #d7b06a; padding: 10px; }
            .purpose-table td { border: 1px solid #5e3a18; padding: 10px; text-align: center; color: #d4ccc5; }
        </style>
    </head>
    <body>
        <div class="page"><div class="bg-smoke"></div>
            <svg class="pentagram-svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" /><circle cx="50" cy="50" r="30" style="stroke: #b32828; fill: rgba(179, 40, 40, 0.1);" /><path d="M50 10 L65 40 L95 40 L70 55 L80 85 L50 65 L20 85 L30 55 L5 40 L35 40 Z" /></svg>
            <div class="cover-title">КОД ДЕНЕГ</div><div class="cover-subtitle">ПО 9 АРКАНАМ</div>
        </div>
        
        <div class="page"><div class="bg-smoke"></div>
            <h1 style="z-index: 10; margin-top: -50px; font-size: 28px; letter-spacing: 3px;">Твой код успеха</h1>
            <div class="bars-container">
                {% for num in user_numbers %}<div class="gold-bar">{{ num }}</div>{% endfor %}
            </div>
        </div>

        {% for page in pages %}
        <div class="page text-page"><div class="bg-smoke"></div>
            {% if page.type == 'inner' %}
                <div class="text-header">ЦИФРА — {{ page.digit }}</div>
                <div class="text-body">{{ page.content }}</div>
            {% elif page.type == 'triangle' %}
                <div class="text-header">{{ page.title }}</div>
                <div class="text-body"><b>Профессии:</b><br>{{ page.professions }}</div>
                <div class="text-body"><b>Блоки:</b><br>{{ page.blocks }}</div>
                <div class="text-body"><b>Траты:</b><br>{{ page.spending }}</div>
            {% endif %}
        </div>
        {% endfor %}

        <div class="page text-page"><div class="bg-smoke"></div>
            <div class="text-header">ПРЕДНАЗНАЧЕНИЕ</div>
            <table class="purpose-table">
                <tr><th>Код</th><th>Кто я?</th><th>Таланты</th><th>Блоки</th><th>Энергия</th><th>Предназначение</th></tr>
                {% for row in purpose_table %}
                <tr><td><b>{{ row.digit }}</b></td><td>{{ row.who }}</td><td>{{ row.talents }}</td><td>{{ row.blocks }}</td><td>{{ row.energy }}</td><td>{{ row.purpose }}</td></tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    """

    template = Template(html_template)
    html_output = template.render(user_numbers=user_numbers, pages=page_data, purpose_table=PURPOSE_TABLE)

    # Сохраняем результат
    filename = f"money_triangle_{'_'.join(user_numbers)}.pdf"
    output_path = os.path.join(output_dir, filename)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_output, wait_until="networkidle")
        page.pdf(path=output_path, format="A4", print_background=True, margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"})
        browser.close()

    return output_path