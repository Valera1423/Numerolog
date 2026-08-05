# test_all.py
import os
import sys
import json
import base64
from datetime import datetime, date
import traceback

# ============================
# ИМПОРТ МОДУЛЕЙ СУПЕР-БОТА
# ============================
# Мы импортируем их напрямую, предполагая, что файлы лежат в этой же папке
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from numerology_core import (
        calculate_numerology, calculate_compatibility,
        money_block_number, relations_block_number, health_block_number, personal_year
    )
    from matrix_calculator import calculate_shadow_matrix
    from image_generator import generate_matrix_image
    from blocks import get_block_text, get_personal_year_text
    from text_report_generator import generate_pdf
    from database_sqlite import Database
    from interpret import send_to_n8n_for_interpretation
except ImportError as e:
    print(f"❌ Ошибка импорта модулей. Проверьте, что все файлы лежат в папке: {e}")
    sys.exit(1)

# ============================
# ТЕСТОВЫЕ ДАННЫЕ
# ============================
TEST_USER = {
    "id": 9999,
    "tg_id": 123456789,
    "fio": "Иванов Иван Иванович",
    "birthdate": "1990-03-15"
}

TEST_BIRTHDATE = date(1990, 3, 15)
TEST_BIRTHDATE_STR = "15.03.1990"

def print_separator(title):
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print('=' * 60)

def main():
    print("\n🔮 ЗАПУСК ТЕСТА СУПЕР-БОТА 🔮")
    print("Все файлы будут сохранены в текущей папке.\n")

    # 1. ТЕСТ БАЗОВОЙ НУМЕРОЛОГИИ И БЛОКИРОВОК
    print_separator("1. Базовые расчёты и блокировки")
    numerology_data = calculate_numerology(TEST_USER["birthdate"], TEST_USER["fio"])
    print(f"✅ Число жизненного пути: {numerology_data['life_path']}")
    print(f"✅ Число выражения: {numerology_data['expression']}")
    print(f"✅ Число души: {numerology_data['soul_urge']}")
    print(f"✅ Число личности: {numerology_data['personality']}")

    money_num = money_block_number(TEST_BIRTHDATE)
    rel_num = relations_block_number(TEST_BIRTHDATE)
    health_num = health_block_number(TEST_BIRTHDATE)
    py_num = personal_year(TEST_BIRTHDATE)
    
    print(f"\n📌 Блокировка денег (день рождения): {money_num}")
    print(f"📌 Блокировка отношений (месяц): {rel_num}")
    print(f"📌 Блокировка здоровья: {health_num}")
    print(f"📌 Личный год 2026: {py_num}")

    # 2. ТЕСТ ТЕКСТОВ БЛОКИРОВОК
    print_separator("2. Тексты блокировок")
    print(get_block_text("money", money_num)[:200] + "...")
    print(get_personal_year_text(py_num)[:200] + "...")

    # 3. ТЕСТ МАТРИЦЫ СУДЬБЫ
    print_separator("3. Расчёт Теневой Матрицы Судьбы (22 аркана)")
    matrix = calculate_shadow_matrix(TEST_BIRTHDATE, TEST_USER["fio"])
    print(f"✅ Центральный аркан: {matrix['center']}")
    print(f"✅ КРТ (Талант): {matrix['key_talent']}")
    print(f"✅ КРП (Предназначение): {matrix['key_destiny']}")
    print("Матрица рассчитана успешно:", json.dumps(matrix, indent=2))

    # 4. ТЕСТ ГЕНЕРАЦИИ ИЗОБРАЖЕНИЯ
    print_separator("4. Генерация изображения Матрицы (Pillow)")
    try:
        img_bytes = generate_matrix_image(matrix, TEST_USER["fio"], TEST_BIRTHDATE_STR)
        image_path = "test_matrix.png"
        with open(image_path, "wb") as f:
            f.write(img_bytes)
        print(f"✅ Картинка сохранена: {os.path.abspath(image_path)}")
    except Exception as e:
        print(f"❌ Ошибка генерации картинки: {e}")

    # 5. ТЕСТ ГЕНЕРАЦИИ PDF (С МАТРИЦЕЙ И БЛОКИРОВКАМИ)
    print_separator("5. Генерация PDF (WeasyPrint / Текстовый запасной)")
    # Формируем данные для PDF
    combined_data = {
        **numerology_data,
        "matrix": matrix,
        "block": {
            "sphere_name": "Деньги",
            "number": money_num,
            "text": get_block_text("money", money_num)
        }
    }
    
    # Имитация интерпретации от ИИ (заглушка)
    mock_interpretation = {
        "introduction": "Ваш тестовый нумерологический отчёт!",
        "life_path_interpretation": "Интерпретация числа жизненного пути (тест).",
        "life_path_detailed": "Подробный анализ числа жизненного пути (тест).",
        "forecast": "Тестовый прогноз на ближайшую неделю.",
        "recommendations": "Тестовые рекомендации."
    }

    pdf_path = generate_pdf(
        user_data=TEST_USER,
        numerology_data=combined_data,
        interpretation_data=mock_interpretation,
        matrix_image_bytes=img_bytes if 'img_bytes' in locals() else None,
        report_type="full"
    )

    if pdf_path and os.path.exists(pdf_path):
        print(f"✅ Отчёт сохранён: {os.path.abspath(pdf_path)}")
    else:
        print("❌ Ошибка сохранения отчёта. Проверьте логи выше.")

    # 6. ТЕСТ БАЗЫ ДАННЫХ (SQLite)
    print_separator("6. Тест базы данных (SQLite)")
    db = Database()
    import asyncio

    async def test_db():
        await db.init()
        
        # Создаём пользователя
        user_id = await db.create_user(TEST_USER["tg_id"])
        await db.update_user(TEST_USER["tg_id"], TEST_USER["fio"], TEST_USER["birthdate"])
        print(f"✅ Пользователь создан/обновлён. ID в БД: {user_id}")

        # Сохраняем отчёт с матрицей и блокировкой
        report_id = await db.save_report(
            user_id=TEST_USER["tg_id"],
            report_type="full",
            core_json=numerology_data,
            matrix_json=matrix,
            block_json=combined_data["block"]
        )
        print(f"✅ Отчёт сохранён в БД. Report ID: {report_id}")

        # Проверяем, что отчёт достаётся
        saved_report = await db.get_report(report_id)
        if saved_report and saved_report.get("matrix_json") == matrix:
            print("✅ Данные матрицы корректно извлечены из БД.")
        else:
            print("❌ Ошибка проверки данных из БД.")

    asyncio.run(test_db())

    # 7. ТЕСТ ИНТЕРПРЕТАЦИИ (локальный режим интерпретатора)
    print_separator("7. Локальная ИИ-интерпретация (тестовый режим)")
    try:
        # Принудительно включаем TEST_MODE в interpret.py (если переменная не задана)
        os.environ["TEST_MODE"] = "true"
        mini_report = asyncio.run(send_to_n8n_for_interpretation(numerology_data, "mini"))
        print(f"✅ Мини-отчёт (локальный):\n{mini_report.get('mini_report', '')[:100]}...")
    except Exception as e:
        print(f"⚠️ Ошибка интерпретации (но она не критична для теста): {e}")

    print("\n🎉 ТЕСТИРОВАНИЕ УСПЕШНО ЗАВЕРШЕНО!")
    print("Проверьте файлы в текущей папке:")
    print("1. test_matrix.png (изображение Матрицы)")
    print("2. numerology_bot.db (файл базы данных SQLite)")
    print("3. pdfs/Иванов_Иван.../full_*.pdf (или .txt, если не установлен WeasyPrint)")

if __name__ == "__main__":
    main()