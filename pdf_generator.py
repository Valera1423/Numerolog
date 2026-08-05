# pdf_generator.py
import os
import logging
import jinja2
from weasyprint import HTML
from datetime import datetime
from typing import Dict, Any, Optional
import base64

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

TEMPLATE_FILE = 'pdf_template.html'

def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от недопустимых символов."""
    forbidden = r'[\\/*?:"<>|]'
    for ch in forbidden:
        filename = filename.replace(ch, '_')
    return filename.replace(' ', '_')

def get_user_directory(user_data: Dict[str, Any]) -> str:
    """Создает директорию для хранения отчетов пользователя."""
    user_name = user_data.get('fio', f"user_{user_data.get('id', 'unknown')}")
    user_dir = os.path.join(PDF_STORAGE_PATH, sanitize_filename(user_name))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def format_date(date_value):
    """Форматирует дату в ДД.ММ.ГГГГ."""
    if not date_value:
        return ''
    if isinstance(date_value, str):
        for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
            try:
                date_obj = datetime.strptime(date_value, fmt)
                return date_obj.strftime('%d.%m.%Y')
            except ValueError:
                continue
        return date_value
    elif hasattr(date_value, 'strftime'):
        return date_value.strftime('%d.%m.%Y')
    return str(date_value)

def get_jinja_template():
    """Получает объект шаблона Jinja2."""
    try:
        template_loader = jinja2.FileSystemLoader(searchpath="./")
        template_env = jinja2.Environment(loader=template_loader)
        return template_env.get_template(TEMPLATE_FILE)
    except jinja2.exceptions.TemplateNotFound:
        logger.warning(f"Шаблон {TEMPLATE_FILE} не найден, используется базовый.")
        basic_template = """
        <!DOCTYPE html>
        <html><head><meta charset="UTF-8"><title>Отчет</title></head>
        <body><h1>Отчет для {{ user_name }}</h1><p>{{ introduction }}</p></body></html>
        """
        return jinja2.Template(basic_template)

def generate_pdf(user_data: Dict[str, Any], 
                 numerology_data: Dict[str, Any], 
                 interpretation_data: Dict[str, Any], 
                 matrix_image_bytes: Optional[bytes] = None,
                 report_type: str = 'full') -> Optional[str]:
    """
    Генерирует PDF-отчет. 
    Принимает:
    - user_data: ФИО, дата рождения и т.д.
    - numerology_data: словарь с базовыми числами, матрицей и блокировками.
    - interpretation_data: интерпретации от ИИ/локальных файлов.
    - matrix_image_bytes: байты PNG-изображения Матрицы (необязательно).
    - report_type: 'full', 'compatibility' и т.д.
    """
    try:
        user_dir = get_user_directory(user_data)
        
        # Базовые данные
        template_data = {
            'user_name': user_data.get('fio', 'Пользователь'),
            'birthdate': format_date(user_data.get('birthdate', '')),
            'current_date': datetime.now().strftime('%d.%m.%Y'),
            'current_year': datetime.now().year,
        }
        
        # 1. Заполнение нумерологических чисел
        for key in ['life_path', 'expression', 'soul_urge', 'personality']:
            template_key = key.replace('soul_urge', 'soul')
            template_data[f'{template_key}_number'] = numerology_data.get(key, '')
        
        # 2. Обработка Матрицы Судьбы
        matrix = numerology_data.get('matrix', {})
        if matrix:
            template_data['matrix'] = matrix
            if matrix_image_bytes:
                # Конвертируем байты PNG в base64 для вставки в HTML
                b64_img = base64.b64encode(matrix_image_bytes).decode('utf-8')
                template_data['matrix_image_base64'] = f"data:image/png;base64,{b64_img}"
        
        # 3. Обработка блокировок (если есть)
        block = numerology_data.get('block', {})
        if block:
            template_data['block_sphere'] = block.get('sphere_name', 'Жизни')
            template_data['block_number'] = block.get('number', '')
            template_data['block_text'] = block.get('text', '')
        
        # 4. Интерпретации от ИИ/локальных файлов
        if isinstance(interpretation_data, dict):
            # Если это JSON с разделами
            template_data['introduction'] = interpretation_data.get('introduction', '')
            template_data['life_path_interpretation'] = interpretation_data.get('life_path_interpretation', '')
            template_data['expression_interpretation'] = interpretation_data.get('expression_interpretation', '')
            template_data['soul_interpretation'] = interpretation_data.get('soul_interpretation', '')
            template_data['personality_interpretation'] = interpretation_data.get('personality_interpretation', '')
            template_data['life_path_detailed'] = interpretation_data.get('life_path_detailed', '')
            template_data['expression_detailed'] = interpretation_data.get('expression_detailed', '')
            template_data['soul_detailed'] = interpretation_data.get('soul_detailed', '')
            template_data['personality_detailed'] = interpretation_data.get('personality_detailed', '')
            template_data['forecast'] = interpretation_data.get('forecast', '')
            template_data['recommendations'] = interpretation_data.get('recommendations', '')
            
            # 5. Совместимость (если есть)
            if report_type == 'compatibility':
                compat = interpretation_data.get('compatibility_report', {})
                template_data['compatibility_score'] = compat.get('score', 75)
                template_data['compatibility_strengths'] = compat.get('strengths', '')
                template_data['compatibility_challenges'] = compat.get('challenges', '')
                template_data['compatibility_recommendations'] = compat.get('recommendations', '')
        else:
            # Если интерпретация пришла как чистый текст
            template_data['introduction'] = str(interpretation_data)
        
        # Заполнение дефолтных значений
        default_texts = {
            'introduction': 'Ваш персональный нумерологический отчет.',
            'life_path_interpretation': 'Интерпретация числа жизненного пути.',
            'expression_interpretation': 'Интерпретация числа выражения.',
            'soul_interpretation': 'Интерпретация числа души.',
            'personality_interpretation': 'Интерпретация числа личности.',
            'life_path_detailed': 'Подробный анализ числа жизненного пути.',
            'expression_detailed': 'Подробный анализ числа выражения.',
            'soul_detailed': 'Подробный анализ числа души.',
            'personality_detailed': 'Подробный анализ числа личности.',
            'forecast': 'Прогноз на ближайшее время.',
            'recommendations': 'Рекомендации для вашего развития.'
        }
        for key, default in default_texts.items():
            if key not in template_data or not template_data[key]:
                template_data[key] = default
        
        # Генерация PDF
        template = get_jinja_template()
        html_content = template.render(**template_data)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"{report_type}_{timestamp}.pdf"
        pdf_path = os.path.join(user_dir, pdf_filename)
        
        # Сохраняем HTML для отладки
        with open(pdf_path.replace('.pdf', '.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Генерация PDF
        HTML(string=html_content).write_pdf(pdf_path)
        logger.info(f"PDF отчет успешно сгенерирован: {pdf_path}")
        
        return pdf_path
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        # Создание текстового отчета как запасной вариант (код опущен для краткости)
        return None