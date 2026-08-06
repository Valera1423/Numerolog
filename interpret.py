# interpret.py
import os
import json
import logging
import aiohttp
from typing import Dict, Any, Optional

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
EXTERNAL_WEBHOOK_URL = os.getenv("EXTERNAL_WEBHOOK_URL", "https://nnikochann.ru/webhook/numero_post_bot")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
EXPECT_TEXT_RESPONSE = os.getenv("EXPECT_TEXT_RESPONSE", "true").lower() == "true"

# ============================
# ЗАГРУЗКА ТЕКСТОВ ИЗ ФАЙЛОВ (Бот №1)
# ============================
import os

def load_text_file(file_path: str) -> Dict[int, str]:
    """
    Загружает файл вида "1: текст\n2: текст..." в словарь.
    Ищет сначала в /app/data, затем в текущей папке (fallback).
    """
    result = {}
    # Возможные пути для поиска
    possible_paths = [
        file_path,  # исходный путь (если абсолютный)
        os.path.join('/app/data', os.path.basename(file_path)),  # внутри контейнера
        os.path.join(os.getcwd(), 'data', os.path.basename(file_path)),  # рядом с ботом
        os.path.join(os.getcwd(), os.path.basename(file_path)),  # в корне бота
    ]
    
    for path in possible_paths:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        key = int(parts[0].strip())
                        value = parts[1].strip()
                        result[key] = value
                logger.info(f"Файл загружен: {path}")
                return result  # успешно загрузили, возвращаем
        except FileNotFoundError:
            continue
        except Exception as e:
            logger.warning(f"Ошибка при загрузке {path}: {e}")
    
    logger.warning(f"Файл {file_path} не найден ни в одном из путей, используется пустой словарь.")
    return result

# Пути к файлам (предполагаем, что они лежат в папке data/)
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Загружаем все интерпретации
TALENTS = load_text_file(os.path.join(DATA_DIR, "talents.txt"))
PLACES = load_text_file(os.path.join(DATA_DIR, "thePlaceOfPower.txt"))
TYPAGE = load_text_file(os.path.join(DATA_DIR, "typage.txt"))
ALTER_EGO = load_text_file(os.path.join(DATA_DIR, "alterEgo.txt"))
ARCANA_PLANETS = load_text_file(os.path.join(DATA_DIR, "arcanaPlanets.txt"))
ASSEMBLAGE_POINT = load_text_file(os.path.join(DATA_DIR, "assemblagePoint.txt"))
CENTER_FAMILY = load_text_file(os.path.join(DATA_DIR, "centerFamilyPrograms.txt"))
DESTINATION_CENTER = load_text_file(os.path.join(DATA_DIR, "destinationCenter.txt"))
ESOTERIC_KEYS = load_text_file(os.path.join(DATA_DIR, "esotericKeys.txt"))
ILLNESSES = load_text_file(os.path.join(DATA_DIR, "illnesses.txt"))
INCARNATION_PROFILE = load_text_file(os.path.join(DATA_DIR, "incarnationProfile.txt"))
INSTRUCTIONS_PLACE = load_text_file(os.path.join(DATA_DIR, "instructionsForThePlaceOfPower.txt"))
KEY_DESTINY = load_text_file(os.path.join(DATA_DIR, "keydestinyrealization.txt"))
MASKS_GREEN = load_text_file(os.path.join(DATA_DIR, "masksgreendescription.txt"))
MASKS_PURPLE = load_text_file(os.path.join(DATA_DIR, "maskspurpedescription.txt"))
MASKS_RED = load_text_file(os.path.join(DATA_DIR, "masksreddescription.txt"))
PERSONALITY_CENTER = load_text_file(os.path.join(DATA_DIR, "personalityCenter.txt"))
QUEST = load_text_file(os.path.join(DATA_DIR, "quest.txt"))
RESOURCE = load_text_file(os.path.join(DATA_DIR, "resource.txt"))
SHADOW1 = load_text_file(os.path.join(DATA_DIR, "shadow1.txt"))
SHADOW2 = load_text_file(os.path.join(DATA_DIR, "shadow2.txt"))
SHADOW3 = load_text_file(os.path.join(DATA_DIR, "shadow3.txt"))
TALENT_KEY = load_text_file(os.path.join(DATA_DIR, "talentKey.txt"))

# Общий словарь для доступа по аркану и категории
ARCANA_DATA = {
    "talents": TALENTS,
    "places": PLACES,
    "typage": TYPAGE,
    "alter_ego": ALTER_EGO,
    "planets": ARCANA_PLANETS,
    "assemblage": ASSEMBLAGE_POINT,
    "family": CENTER_FAMILY,
    "destination": DESTINATION_CENTER,
    "esoteric": ESOTERIC_KEYS,
    "illnesses": ILLNESSES,
    "incarnation": INCARNATION_PROFILE,
    "instructions_place": INSTRUCTIONS_PLACE,
    "key_destiny": KEY_DESTINY,
    "masks_green": MASKS_GREEN,
    "masks_purple": MASKS_PURPLE,
    "masks_red": MASKS_RED,
    "personality": PERSONALITY_CENTER,
    "quest": QUEST,
    "resource": RESOURCE,
    "shadow1": SHADOW1,
    "shadow2": SHADOW2,
    "shadow3": SHADOW3,
    "talent_key": TALENT_KEY,
}

def get_arcana_interpretation(arcana: int, category: str) -> str:
    """
    Возвращает текст интерпретации для аркана по категории.
    Категории: 'talents', 'typage', 'places' и т.д.
    """
    cat_data = ARCANA_DATA.get(category, {})
    return cat_data.get(arcana, f"Интерпретация для аркана {arcana} в категории {category} не найдена.")

# ============================
# ГЕНЕРАЦИЯ ЛОКАЛЬНОГО ОТВЕТА (тестовый режим)
# ============================

def generate_local_interpretation(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Формирует ответ, используя загруженные текстовые файлы.
    Для мини-отчёта – только базовые числа.
    Для полного отчёта – включает матрицу и блокировки.
    """
    if report_type == "mini":
        life_path = data.get("life_path", 0)
        expression = data.get("expression", 0)
        soul = data.get("soul_urge", 0)
        personality = data.get("personality", 0)
        mini_text = (
            f"🔢 Твой мини-отчёт (локальный режим):\n\n"
            f"Число жизненного пути: {life_path}\n"
            f"Число выражения: {expression}\n"
            f"Число души: {soul}\n"
            f"Число личности: {personality}\n\n"
            f"Для полной интерпретации закажи полный PDF-отчёт."
        )
        return {"mini_report": mini_text}

    elif report_type == "full":
        # Если есть данные матрицы, генерируем отчёт по арканам
        matrix = data.get("matrix", {})
        block = data.get("block", {})
        full_report = {}
        # Заполняем разделами
        full_report["introduction"] = "Ваш полный нумерологический отчёт (локальная версия)."
        # Включаем интерпретации арканов
        if matrix:
            center = matrix.get("center", 0)
            full_report["center_arcana"] = get_arcana_interpretation(center, "talents")
            # Можно добавить другие категории
        # Блокировки
        if block:
            sphere = block.get("sphere")
            number = block.get("number")
            if sphere == "money":
                full_report["block_text"] = get_arcana_interpretation(number, "talents")  # пример
        return {"full_report": full_report}

    elif report_type == "compatibility":
        # Генерация текста совместимости
        score = data.get("compatibility", {}).get("total", 75)
        return {
            "compatibility_report": {
                "intro": "Анализ совместимости (локальная версия).",
                "score": score,
                "strengths": "Взаимопонимание и общие цели.",
                "challenges": "Разные подходы к принятию решений.",
                "recommendations": "Больше открытого общения."
            }
        }

    elif report_type == "weekly":
        # Генерация еженедельного прогноза
        return {
            "weekly_forecast": "На этой неделе уделите внимание внутреннему балансу и планированию."
        }

    # По умолчанию
    return {"message": "Интерпретация сгенерирована локально."}

# ============================
# ОТПРАВКА В N8N (режим продакшн)
# ============================

async def send_to_n8n_webhook(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Отправляет данные на внешний webhook (n8n) и возвращает ответ.
    """
    if TEST_MODE:
        return None  # в тестовом режиме не отправляем

    try:
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(EXTERNAL_WEBHOOK_URL, json=data, headers=headers, timeout=30) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        return await resp.json()
                    else:
                        text = await resp.text()
                        return {"raw_text": text}
                else:
                    logger.error(f"Webhook error {resp.status}: {await resp.text()}")
                    return None
    except Exception as e:
        logger.error(f"Error sending to n8n: {e}")
        return None
    
def get_arcana_interpretation(arcana: int, category: str) -> str:
    """
    Возвращает текст интерпретации для аркана по категории.
    Категории: 'talents', 'typage', 'places' и т.д.
    """
    # Загружаем данные из файлов (как мы делали ранее)
    # Пример:
    from blocks import ARCANA_DATA  # если вы храните в blocks.py
    return ARCANA_DATA.get(category, {}).get(arcana, f"Интерпретация для {arcana} не найдена.")
# ============================
# ОСНОВНАЯ ФУНКЦИЯ ДЛЯ БОТА
# ============================

async def send_to_n8n_for_interpretation(data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Основная функция, вызываемая из бота.
    В тестовом режиме использует локальные данные, иначе отправляет в n8n.
    """
    if TEST_MODE:
        logger.info(f"Локальная генерация для {report_type}")
        return generate_local_interpretation(data, report_type)

    # В продакшне отправляем в n8n
    result = await send_to_n8n_webhook(data)
    if result:
        return result
    else:
        # Если ошибка, возвращаем локальную заглушку
        logger.warning("n8n недоступен, используется локальная интерпретация")
        return generate_local_interpretation(data, report_type)
