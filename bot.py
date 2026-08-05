# bot.py (полный с дополнениями)
import logging
import os
import json
from datetime import datetime, date

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery,
    LabeledPrice, FSInputFile, BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Импорт модулей (все ваши существующие)
try:
    from database_sqlite import Database
except ImportError:
    from database import Database

from numerology_core import (
    calculate_numerology, calculate_compatibility,
    money_block_number, relations_block_number, health_block_number, personal_year,
    get_karmic_lessons, get_pythagoras_matrix
)

from matrix_calculator import calculate_shadow_matrix
from image_generator import generate_matrix_image
from blocks import get_block_text, get_personal_year_text
from interpret import send_to_n8n_for_interpretation, get_arcana_interpretation
from money_triangle_pdf import generate_money_triangle_pdf

# Импорт нового PDF-генератора (Playwright)
from pdf_generator_playwright import generate_full_pdf

# Импорт планировщика (если используете)
from scheduler import start_scheduler

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "./pdfs")
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# База данных
db = Database()

# ============================
# FSM СОСТОЯНИЯ
# ============================
class UserStates(StatesGroup):
    waiting_for_birthdate = State()
    waiting_for_name = State()
    waiting_for_partner_birthdate = State()
    waiting_for_partner_name = State()
    waiting_for_matrix_birth = State()
    # Для расшифровки матрицы (платной) можно не создавать отдельное состояние, используем дату из БД.

# ============================
# КОМАНДА /START (обновлённое меню)
# ============================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not await db.get_user_by_tg_id(user_id):
        await db.create_user(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✨ Сделать расчёт", callback_data="start_calculation")],
        [InlineKeyboardButton("🔮 Теневая Матрица Судьбы", callback_data="cmd_matrix")],
        [InlineKeyboardButton("💰 Денежный треугольник", callback_data="cmd_money_triangle")],
        [InlineKeyboardButton("🔍 Узнать блокировки", callback_data="cmd_blocks")],
        [InlineKeyboardButton("👥 Совместимость", callback_data="cmd_compatibility")],
        [InlineKeyboardButton("📞 Консультация", callback_data="cmd_consultation")],  # НОВОЕ
        [InlineKeyboardButton("⚙️ Настройки", callback_data="cmd_settings")]
    ])

    await message.answer(
        "👋 Добро пожаловать в Супер-Нумеролог!\n\n"
        "Я помогу вам рассчитать:\n"
        "• Ваш базовый нумерологический профиль\n"
        "• Теневую Матрицу Судьбы (22 аркана) с картинкой\n"
        "• Денежный треугольник\n"
        "• Блокировки в деньгах, отношениях и здоровье\n"
        "• Совместимость с партнёром\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )
    await state.clear()

# ============================
# ОБРАБОТЧИК КНОПКИ КОНСУЛЬТАЦИИ
# ============================
@router.callback_query(F.data == "cmd_consultation")
async def process_consultation(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📞 Для записи на индивидуальную консультацию напишите @smirnovamarina_n\n"
        "Стоимость: 5 000 ₽ / час.\n"
        "Разберем ваш полный нумерологический портрет, блокировки и пути их преодоления."
    )

# ============================
# ОБРАБОТЧИК КНОПКИ "РАСШИФРОВКА МАТРИЦЫ" (новая платная услуга)
# ============================
@router.callback_query(F.data == "cmd_matrix_full")
async def process_matrix_full(callback: types.CallbackQuery):
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user or not user.get("birthdate"):
        await callback.answer("❗ Сначала введите свои данные через /start.")
        return
    # Предложение купить расшифровку
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Купить расшифровку (199 ₽)", callback_data="buy_matrix_decoding"))
    if TEST_MODE:
        builder.add(InlineKeyboardButton(text="🔍 Бесплатно (тест)", callback_data="test_matrix_decoding"))
    await callback.message.edit_text(
        "🔮 Вы можете получить детальную расшифровку всех 22 арканов вашей Матрицы Судьбы.\n"
        "В расшифровку входят: таланты, предназначение, блокировки, места силы, эзотерические ключи и многое другое.\n"
        "Стоимость: 199 ₽",
        reply_markup=builder.as_markup()
    )

# Обработчики покупки расшифровки
@router.callback_query(F.data == "buy_matrix_decoding")
async def buy_matrix_decoding(callback: types.CallbackQuery):
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback.answer("⚠️ Платежи не настроены. Используйте тестовый режим.")
        return
    user_id = callback.from_user.id
    order_id = await db.create_order(user_id, "matrix_decoding", 199.0, "RUB", {"type": "matrix"})
    if not order_id:
        await callback.message.edit_text("❌ Ошибка создания заказа.")
        return
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Расшифровка Матрицы Судьбы",
        description="Полная расшифровка всех 22 арканов с интерпретациями",
        payload=f"matrix_decoding:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Расшифровка", amount=19900)]
    )

@router.callback_query(F.data == "test_matrix_decoding")
async def test_matrix_decoding(callback: types.CallbackQuery):
    if not TEST_MODE:
        await callback.answer("⚠️ Тестовый режим отключен.")
        return
    await callback.answer()
    # Генерация расшифровки бесплатно
    await generate_matrix_decoding_report(callback.message, callback.from_user.id, test=True)

async def generate_matrix_decoding_report(message: Message, user_id: int, test: bool = False):
    user = await db.get_user_by_tg_id(user_id)
    if not user or not user.get("birthdate"):
        await message.answer("❌ Данные не найдены.")
        return
    birthdate = datetime.strptime(user["birthdate"], "%Y-%m-%d").date()
    matrix = calculate_shadow_matrix(birthdate, user["fio"])
    # Генерируем PDF с расшифровкой (используем новый генератор)
    pdf_path = generate_full_pdf(
        user_data=user,
        numerology_data={"matrix": matrix},
        interpretation_data={"full_report": {"introduction": "Расшифровка Матрицы Судьбы"}},
        matrix_image_bytes=generate_matrix_image(matrix, user["fio"], user["birthdate"]),
        report_type="matrix_decoding"
    )
    if pdf_path:
        await message.answer_document(FSInputFile(pdf_path, filename="matrix_decoding.pdf"))

# ============================
# ОБРАБОТЧИК УСПЕШНОГО ПЛАТЕЖА (дополнен)
# ============================
@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    if ":" not in payload:
        logger.error(f"Invalid payload: {payload}")
        await message.answer("❌ Ошибка обработки платежа.")
        return

    payload_type, order_id_str = payload.split(":", 1)
    try:
        order_id = int(order_id_str)
    except ValueError:
        await message.answer("❌ Ошибка обработки платежа.")
        return

    order = await db.get_order(order_id)
    if not order:
        await message.answer("❌ Заказ не найден.")
        return

    await db.update_order_status(order_id, "paid")

    if payload_type == "subscription":
        await db.create_subscription(order["user_id"], "active")
        await message.answer("✅ Подписка успешно оформлена!")
    elif payload_type == "full_report":
        await process_full_report_payment(message, order)
    elif payload_type == "compatibility":
        await process_compatibility_payment(message, order)
    elif payload_type == "matrix_decoding":   # НОВОЕ
        await process_matrix_decoding_payment(message, order)

# ============================
# ОБРАБОТЧИКИ ПЛАТЕЖЕЙ (MATRIX DECODING, COMPATIBILITY)
# ============================
async def process_matrix_decoding_payment(message: Message, order: dict):
    # Используем данные пользователя из заказа
    user_id = order["user_id"]
    user = await db.get_user_by_id(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return
    await generate_matrix_decoding_report(message, user_id, test=False)

async def process_compatibility_payment(message: Message, order: dict):
    report_id = order["payload"].get("report_id")
    if not report_id:
        await message.answer("❌ Не указан ID отчета.")
        return
    report = await db.get_report(report_id)
    if not report:
        await message.answer("❌ Отчёт не найден.")
        return
    user = await db.get_user_by_id(order["user_id"])
    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    wait = await message.answer("⏳ Генерирую отчёт о совместимости...")
    # Получаем данные совместимости
    compatibility_data = report["core_json"]
    # Генерируем PDF (используем новый генератор)
    pdf_path = generate_full_pdf(
        user_data=user,
        numerology_data=compatibility_data,
        interpretation_data={"compatibility_report": compatibility_data.get("compatibility", {})},
        matrix_image_bytes=None,
        report_type="compatibility"
    )
    if pdf_path:
        await db.update_report_pdf(report_id, pdf_path)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait.message_id)
        await message.answer_document(FSInputFile(pdf_path, filename="compatibility_report.pdf"))
    else:
        await message.answer("❌ Ошибка генерации отчета.")

# ============================
# КОМАНДА /MONEY_TRIANGLE
# ============================
@router.message(Command("money_triangle"))
async def cmd_money_triangle(message: Message):
    user = await db.get_user_by_tg_id(message.from_user.id)
    if not user or not user.get("birthdate"):
        await message.answer("❗ Сначала введите свои данные через /start.")
        return
    # Рассчитываем числа (можно сделать динамически, например, на основе даты)
    # Здесь для примера фиксированные, но вы можете заменить на реальный расчёт.
    user_numbers = ['1', '2', '5', '8', '7']  # Замените на логику
    await generate_and_send_money_triangle(message, user_numbers)

async def generate_and_send_money_triangle(message: Message, user_numbers: list):
    await message.answer("🔮 Генерирую ваш Денежный треугольник...")
    try:
        pdf_path = generate_money_triangle_pdf(user_numbers, output_dir=PDF_STORAGE_PATH)
        await message.answer_document(
            document=FSInputFile(pdf_path, filename="money_triangle.pdf"),
            caption="✨ Ваш Денежный треугольник готов!"
        )
    except Exception as e:
        logger.error(f"Ошибка генерации Money Triangle: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

# ============================
# ЗАПУСК ПЛАНИРОВЩИКА ЕЖЕНЕДЕЛЬНЫХ ПРОГНОЗОВ
# ============================
# В функции main добавляем запуск планировщика
async def main():
    await db.init()
    # Запускаем планировщик
    start_scheduler(bot)
    logger.info("🚀 Бот запущен. Тестовый режим: %s", TEST_MODE)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())