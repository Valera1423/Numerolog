# text_report_generator.py
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PDF_STORAGE_PATH = os.environ.get('PDF_STORAGE_PATH', './pdfs')
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

def sanitize_filename(filename: str) -> str:
    for ch in r'[\\/*?:"<>|]':
        filename = filename.replace(ch, '_')
    return filename.replace(' ', '_')

def get_user_directory(user_data: Dict[str, Any]) -> str:
    user_name = user_data.get('fio', f"user_{user_data.get('id', 'unknown')}")
    user_dir = os.path.join(PDF_STORAGE_PATH, sanitize_filename(user_name))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir

def format_date(date_value):
    if not date_value:
        return ''
    if isinstance(date_value, str):
        for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_value, fmt).strftime('%d.%m.%Y')
            except:
                continue
        return date_value
    elif hasattr(date_value, 'strftime'):
        return date_value.strftime('%d.%m.%Y')
    return str(date_value)

def generate_pdf(user_data: Dict[str, Any], 
                 numerology_data: Dict[str, Any], 
                 interpretation_data: Dict[str, Any], 
                 matrix_image_bytes: Optional[bytes] = None,
                 report_type: str = 'full') -> Optional[str]:
    try:
        user_dir = get_user_directory(user_data)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        txt_path = os.path.join(user_dir, f"{report_type}_{timestamp}.txt")

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("="*50 + "\n")
            f.write(f"ТЕСТОВЫЙ ОТЧЁТ (замена PDF)\n")
            f.write("="*50 + "\n\n")
            f.write(f"Пользователь: {user_data.get('fio', 'Неизвестный')}\n")
            f.write(f"Дата рождения: {format_date(user_data.get('birthdate', ''))}\n")
            f.write(f"Дата отчёта: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n")

            f.write("--- Нумерологические числа ---\n")
            for key in ['life_path', 'expression', 'soul_urge', 'personality']:
                val = numerology_data.get(key, '')
                f.write(f"{key}: {val}\n")

            # Матрица
            matrix = numerology_data.get('matrix', {})
            if matrix:
                f.write("\n--- Теневая Матрица Судьбы ---\n")
                for k, v in matrix.items():
                    f.write(f"{k}: {v}\n")

            # Блокировки
            block = numerology_data.get('block', {})
            if block:
                f.write("\n--- Блокировка ---\n")
                f.write(f"Сфера: {block.get('sphere_name', '')}\n")
                f.write(f"Число: {block.get('number', '')}\n")
                f.write(f"Текст: {block.get('text', '')}\n")

            # Интерпретации
            if isinstance(interpretation_data, dict):
                f.write("\n--- Интерпретация ---\n")
                for key, val in interpretation_data.items():
                    if isinstance(val, str):
                        f.write(f"{key}: {val[:200]}...\n")

        logger.info(f"Текстовый отчёт сохранён: {txt_path}")
        return txt_path
    except Exception as e:
        logger.error(f"Ошибка генерации отчёта: {e}")
        return None