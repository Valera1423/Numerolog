# bot.py
import logging
import os
import asyncio
import json
from datetime import datetime, date

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery,
    LabeledPrice, FSInputFile, BufferedInputFile, CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Импорт модулей
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

# Генератор отчётов (используем Playwright для красивого PDF)
from pdf_generator_playwright import generate_full_pdf

# Админ-модуль
from admin import router as admin_router

# Логирование и утилиты
from logger import logger, setup_logging
from utils import run_in_background, retry_n8n, validate_date, validate_fio

# Кеширование Redis
from redis_cache import cache_get, cache_set, cache_delete

# Планировщик для еженедельных прогнозов
from scheduler import start_scheduler

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"
PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "./pdfs")
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

# Настройка логирования
setup_logging()
logger.info("Бот инициализируется...")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)
dp.include_router(admin_router)  # Админ-команды

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
    waiting_for_edit_birthdate = State()
    waiting_for_edit_name = State()
    waiting_for_feedback = State()


# ============================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ КЛАВИАТУР
# ============================
def menu_keyboard():
    """Клавиатура с кнопкой 'Меню' для возврата в главное меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
    ])


def back_keyboard(callback_data: str):
    """Клавиатура с кнопкой 'Назад' для возврата на предыдущий шаг."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
    ])


# ============================
# КОМАНДА /START (обновлённое меню)
# ============================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    # Регистрация пользователя
    if not await db.get_user_by_tg_id(user_id):
        await db.create_user(user_id)

    # Главное меню с иконками
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Сделать расчёт", callback_data="start_calculation")],
        [InlineKeyboardButton(text="🔮 Теневая Матрица Судьбы", callback_data="cmd_matrix")],
        [InlineKeyboardButton(text="💰 Денежный треугольник", callback_data="cmd_money_triangle")],
        [InlineKeyboardButton(text="🔍 Узнать блокировки", callback_data="cmd_blocks")],
        [InlineKeyboardButton(text="👥 Совместимость", callback_data="cmd_compatibility")],
        [InlineKeyboardButton(text="📜 История запросов", callback_data="cmd_history")],
        [InlineKeyboardButton(text="📞 Консультация", callback_data="cmd_consultation")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="cmd_settings")]
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
# КОМАНДА /CANCEL
# ============================
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("❌ Действие отменено.", reply_markup=menu_keyboard())
    else:
        await message.answer("Нет активных действий для отмены.", reply_markup=menu_keyboard())


# ============================
# КОМАНДА /HELP
# ============================
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🆘 Помощь\n\n"
        "Используйте /start для главного меню.\n"
        "Для расчётов следуйте инструкциям.\n"
        "Если возникли вопросы – напишите @smirnovamarina_n\n\n"
        "Команды:\n"
        "/start - главное меню\n"
        "/cancel - отменить текущее действие\n"
        "/help - эта справка\n"
        "/report - получить последний купленный отчёт\n"
        "/subscribe - управление подпиской"
    )


# ============================
# ОБРАБОТЧИК ГЛАВНОГО МЕНЮ (callback)
# ============================
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    # Отправляем новое сообщение с меню (редактируем текущее)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Сделать расчёт", callback_data="start_calculation")],
        [InlineKeyboardButton(text="🔮 Теневая Матрица Судьбы", callback_data="cmd_matrix")],
        [InlineKeyboardButton(text="💰 Денежный треугольник", callback_data="cmd_money_triangle")],
        [InlineKeyboardButton(text="🔍 Узнать блокировки", callback_data="cmd_blocks")],
        [InlineKeyboardButton(text="👥 Совместимость", callback_data="cmd_compatibility")],
        [InlineKeyboardButton(text="📜 История запросов", callback_data="cmd_history")],
        [InlineKeyboardButton(text="📞 Консультация", callback_data="cmd_consultation")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="cmd_settings")]
    ])
    await callback.message.edit_text(
        "👋 Добро пожаловать в Супер-Нумеролог!\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


# ============================
# ОБРАБОТЧИКИ КНОПОК ГЛАВНОГО МЕНЮ
# ============================
@router.callback_query(F.data == "start_calculation")
async def process_calculation_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "📅 Введите вашу дату рождения в формате ДД.ММ.ГГГГ (например: 15.03.1990)",
        reply_markup=back_keyboard("main_menu")
    )
    await state.set_state(UserStates.waiting_for_birthdate)


@router.callback_query(F.data == "cmd_matrix")
async def process_matrix_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "📅 Введите дату рождения для построения Теневой Матрицы Судьбы (ДД.ММ.ГГГГ)",
        reply_markup=back_keyboard("main_menu")
    )
    await state.set_state(UserStates.waiting_for_matrix_birth)


@router.callback_query(F.data == "cmd_money_triangle")
async def process_money_triangle_button(callback: CallbackQuery):
    await callback.answer()
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user or not user.get("birthdate"):
        await callback.message.edit_text(
            "❗ Сначала введите свои данные через /start.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    birthdate = datetime.strptime(user["birthdate"], "%Y-%m-%d").date()
    # Расчёт чисел для денежного треугольника (берём арканы из матрицы)
    matrix = calculate_shadow_matrix(birthdate, user.get("fio", ""))
    # Формируем список из ключевых арканов (день, месяц, год, центр, талант, предназначение)
    user_numbers = [
        str(matrix.get("day", 0)),
        str(matrix.get("month", 0)),
        str(matrix.get("year", 0)),
        str(matrix.get("center", 0)),
        str(matrix.get("key_talent", 0)),
        str(matrix.get("key_destiny", 0))
    ]
    # Убираем дубли и нули, оставляем только уникальные числа от 1 до 22
    user_numbers = list(dict.fromkeys([n for n in user_numbers if n and n != "0"]))
    if not user_numbers:
        await callback.message.edit_text(
            "❌ Не удалось рассчитать числа для денежного треугольника.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await generate_and_send_money_triangle(callback.message, user_numbers)


@router.callback_query(F.data == "cmd_blocks")
async def process_blocks_button(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Деньги", callback_data="block_money")],
        [InlineKeyboardButton(text="❤️ Отношения", callback_data="block_relations")],
        [InlineKeyboardButton(text="🌿 Здоровье", callback_data="block_health")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "🔍 Выберите сферу, чтобы узнать свою блокировку:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "cmd_compatibility")
async def process_compatibility_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user or not user.get("birthdate") or not user.get("fio"):
        await callback.message.edit_text(
            "❗ Сначала введите свои данные через /start.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await state.update_data(user_birthdate=user["birthdate"], user_fio=user["fio"])
    await callback.message.edit_text(
        "👥 Введите дату рождения партнёра в формате ДД.ММ.ГГГГ",
        reply_markup=back_keyboard("main_menu")
    )
    await state.set_state(UserStates.waiting_for_partner_birthdate)


@router.callback_query(F.data == "cmd_history")
async def process_history_button(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    history = await db.get_user_history(user_id, limit=10)
    if not history:
        await callback.message.edit_text(
            "📜 У вас пока нет истории запросов.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    text = "📜 Ваши последние запросы:\n\n"
    for item in history:
        text += f"• {item['created_at']} — {item['request_type']}\n"
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("main_menu")
    )


@router.callback_query(F.data == "cmd_consultation")
async def process_consultation(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📞 Для записи на индивидуальную консультацию напишите @smirnovamarina_n\n"
        "Стоимость: 5 000 ₽ / час.\n"
        "Разберем ваш полный нумерологический портрет, блокировки и пути их преодоления.",
        reply_markup=back_keyboard("main_menu")
    )


@router.callback_query(F.data == "cmd_settings")
async def process_settings_button(callback: CallbackQuery):
    await callback.answer()
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.message.edit_text(
            "❗ Сначала введите свои данные через /start.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    lang = user.get("lang", "ru")
    push = user.get("push_enabled", True)
    lang_text = "🇷🇺 Русский" if lang == "ru" else "🇬🇧 English"
    push_text = "Включены ✅" if push else "Отключены ❌"

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"Язык: {lang_text}", callback_data="toggle_lang"))
    builder.add(InlineKeyboardButton(text=f"Уведомления: {push_text}", callback_data="toggle_push"))
    builder.add(InlineKeyboardButton(text="✏️ Редактировать профиль", callback_data="edit_profile"))
    builder.add(InlineKeyboardButton(text="💬 Оставить отзыв", callback_data="feedback"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))
    builder.adjust(2)
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        f"Язык: {lang_text}\n"
        f"Уведомления: {push_text}",
        reply_markup=builder.as_markup()
    )


# ============================
# ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ПРОФИЛЯ И ОТЗЫВОВ
# ============================
@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Изменить дату рождения", callback_data="edit_birthdate")],
        [InlineKeyboardButton(text="✏️ Изменить ФИО", callback_data="edit_name")],
        [InlineKeyboardButton(text="👤 Просмотреть профиль", callback_data="view_profile")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="cmd_settings")],
        [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "Настройка профиля:",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "edit_birthdate")
async def edit_birthdate(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Введите новую дату рождения в формате ДД.ММ.ГГГГ",
        reply_markup=back_keyboard("edit_profile")
    )
    await state.set_state(UserStates.waiting_for_edit_birthdate)


@router.message(UserStates.waiting_for_edit_birthdate)
async def process_edit_birthdate(message: Message, state: FSMContext):
    new_birthdate = validate_date(message.text)
    if not new_birthdate:
        await message.answer(
            "❌ Неверный формат. Попробуйте ещё раз.",
            reply_markup=back_keyboard("edit_profile")
        )
        return
    await db.update_user(message.from_user.id, birthdate=new_birthdate.strftime("%Y-%m-%d"))
    await message.answer("✅ Дата рождения обновлена!", reply_markup=menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "edit_name")
async def edit_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Введите новое полное ФИО",
        reply_markup=back_keyboard("edit_profile")
    )
    await state.set_state(UserStates.waiting_for_edit_name)


@router.message(UserStates.waiting_for_edit_name)
async def process_edit_name(message: Message, state: FSMContext):
    new_fio = message.text.strip()
    if not validate_fio(new_fio):
        await message.answer(
            "❌ ФИО содержит недопустимые символы. Используйте только буквы, пробелы и дефисы.",
            reply_markup=back_keyboard("edit_profile")
        )
        return
    await db.update_user(message.from_user.id, fio=new_fio)
    await message.answer("✅ ФИО обновлено!", reply_markup=menu_keyboard())
    await state.clear()


@router.callback_query(F.data == "view_profile")
async def view_profile(callback: CallbackQuery):
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Профиль не найден.")
        return
    text = (
        f"👤 Ваш профиль:\n"
        f"• ФИО: {user['fio'] or 'не указано'}\n"
        f"• Дата рождения: {user['birthdate'] or 'не указана'}\n"
        f"• Язык: {user['lang']}\n"
        f"• Уведомления: {'включены' if user['push_enabled'] else 'отключены'}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=back_keyboard("edit_profile")
    )
    await callback.answer()


@router.callback_query(F.data == "feedback")
async def feedback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "Напишите ваш отзыв или предложение:",
        reply_markup=back_keyboard("cmd_settings")
    )
    await state.set_state(UserStates.waiting_for_feedback)


@router.message(UserStates.waiting_for_feedback)
async def process_feedback(message: Message, state: FSMContext):
    await db.save_feedback(message.from_user.id, message.text)
    await message.answer("✅ Спасибо за ваш отзыв! Он поможет нам стать лучше.", reply_markup=menu_keyboard())
    await state.clear()


# ============================
# FSM: СБОР ДАННЫХ ДЛЯ БАЗОВОГО РАСЧЁТА
# ============================
@router.message(UserStates.waiting_for_birthdate)
async def process_birthdate(message: Message, state: FSMContext):
    birthdate = validate_date(message.text)
    if not birthdate:
        await message.answer(
            "❌ Неверный формат. Попробуйте ещё раз (ДД.ММ.ГГГГ).",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await state.update_data(birthdate=birthdate.strftime("%Y-%m-%d"))
    await message.answer(
        "✍️ Теперь введите ваше полное ФИО (Фамилия Имя Отчество)",
        reply_markup=back_keyboard("main_menu")
    )
    await state.set_state(UserStates.waiting_for_name)


@router.message(UserStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    fio = message.text.strip()
    if not validate_fio(fio):
        await message.answer(
            "❌ ФИО содержит недопустимые символы. Используйте только буквы, пробелы и дефисы.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await state.update_data(fio=fio)
    data = await state.get_data()
    birthdate = data["birthdate"]
    tg_id = message.from_user.id

    await db.update_user(tg_id, fio, birthdate)
    await db.save_request_history(tg_id, "base_calculation", {"birthdate": birthdate, "fio": fio})

    wait_msg = await message.answer("🔮 Выполняю расчёты... Пожалуйста, подождите.")

    # 1. Базовый расчёт
    numerology_data = calculate_numerology(birthdate, fio)
    numerology_data["karmic_lessons"] = get_karmic_lessons(fio)
    numerology_data["pythagoras_matrix"] = get_pythagoras_matrix(birthdate)
    numerology_data["personal_year"] = personal_year(datetime.strptime(birthdate, "%Y-%m-%d").date())

    # Сохраняем отчёт в БД
    report_id = await db.save_report(tg_id, "mini", numerology_data)

    # 2. ИИ-интерпретация (с кешированием)
    cache_key = f"interpret:mini:{birthdate}:{fio}"
    cached = await cache_get(cache_key)
    if cached:
        mini_text = cached
    else:
        interpretation = await send_to_n8n_for_interpretation(numerology_data, "mini")
        mini_text = interpretation.get('mini_report', "Ваш мини-отчёт готов!")
        await cache_set(cache_key, mini_text, ttl=3600)

    # 3. Кнопки для дальнейших действий
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Полный PDF-отчёт - 149 ₽", callback_data=f"buy_full_report:{report_id}"))
    if TEST_MODE:
        builder.add(InlineKeyboardButton(text="🔍 Получить бесплатно (тест)", callback_data=f"test_full_report:{report_id}"))
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))

    await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)
    await message.answer(
        f"🌟 {mini_text}\n\n"
        f"Дополнительно:\n"
        f"• Кармические уроки: {numerology_data['karmic_lessons']}\n"
        f"• Матрица Пифагора: {dict(numerology_data['pythagoras_matrix'])}\n"
        f"• Личный год: {numerology_data['personal_year']}",
        reply_markup=builder.as_markup()
    )
    await state.clear()


# ============================
# FSM: ТЕНЕВАЯ МАТРИЦА СУДЬБЫ
# ============================
@router.message(UserStates.waiting_for_matrix_birth)
async def process_matrix_birth(message: Message, state: FSMContext):
    birthdate = validate_date(message.text)
    if not birthdate:
        await message.answer(
            "❌ Неверный формат. Попробуйте ещё раз.",
            reply_markup=back_keyboard("main_menu")
        )
        return

    wait_msg = await message.answer("🎨 Рисую вашу Матрицу... Подождите немного.")

    matrix = calculate_shadow_matrix(birthdate, message.from_user.first_name)
    img_bytes = generate_matrix_image(matrix, message.from_user.first_name, message.text)

    await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)

    caption = (
        f"🔮 Твоя Теневая Матрица Судьбы готова!\n\n"
        f"• Центральный аркан (Судьба): {matrix['center']}\n"
        f"• КРТ (Талант): {matrix['key_talent']}\n"
        f"• КРП (Предназначение): {matrix['key_destiny']}\n"
        f"• ЦРП (Родовые программы): {matrix['center_family']}\n\n"
        f"Чтобы получить полную расшифровку всех 22 арканов, закажите полный отчёт или расшифровку."
    )
    await message.answer_photo(
        photo=BufferedInputFile(img_bytes, filename="shadow_matrix.png"),
        caption=caption,
        reply_markup=back_keyboard("main_menu")
    )

    # Предложение купить расшифровку
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Купить расшифровку Матрицы (199 ₽)", callback_data="buy_matrix_decoding"))
    if TEST_MODE:
        builder.add(InlineKeyboardButton(text="🔍 Бесплатно (тест)", callback_data="test_matrix_decoding"))
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))
    await message.answer(
        "📌 Вы можете получить детальную расшифровку всех 22 арканов с интерпретациями.",
        reply_markup=builder.as_markup()
    )
    await state.clear()


# ============================
# ОБРАБОТЧИКИ РАСШИФРОВКИ МАТРИЦЫ
# ============================
@router.callback_query(F.data == "buy_matrix_decoding")
async def buy_matrix_decoding(callback: CallbackQuery):
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback.answer("⚠️ Платежи не настроены. Используйте тестовый режим.")
        return
    user_id = callback.from_user.id
    order_id = await db.create_order(user_id, "matrix_decoding", 199.0, "RUB", {"type": "matrix"})
    if not order_id:
        await callback.message.edit_text(
            "❌ Ошибка создания заказа.",
            reply_markup=back_keyboard("main_menu")
        )
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
    await callback.answer()


@router.callback_query(F.data == "test_matrix_decoding")
async def test_matrix_decoding(callback: CallbackQuery):
    if not TEST_MODE:
        await callback.answer("⚠️ Тестовый режим отключен.")
        return
    await callback.answer()
    await generate_matrix_decoding_report(callback.message, callback.from_user.id, test=True)


async def generate_matrix_decoding_report(message: Message, user_id: int, test: bool = False):
    user = await db.get_user_by_tg_id(user_id)
    if not user or not user.get("birthdate"):
        await message.answer(
            "❌ Данные не найдены.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    birthdate = datetime.strptime(user["birthdate"], "%Y-%m-%d").date()
    matrix = calculate_shadow_matrix(birthdate, user["fio"])
    # Генерируем PDF с расшифровкой
    pdf_path = await generate_full_pdf(
        user_data=user,
        numerology_data={"matrix": matrix},
        interpretation_data={"full_report": {"introduction": "Расшифровка Матрицы Судьбы"}},
        matrix_image_bytes=generate_matrix_image(matrix, user["fio"], user["birthdate"]),
        report_type="matrix_decoding"
    )
    if pdf_path:
        await message.answer_document(
            FSInputFile(pdf_path, filename="matrix_decoding.pdf"),
            reply_markup=menu_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка генерации отчёта.",
            reply_markup=back_keyboard("main_menu")
        )


# ============================
# FSM: СОВМЕСТИМОСТЬ
# ============================
@router.message(UserStates.waiting_for_partner_birthdate)
async def process_partner_birthdate(message: Message, state: FSMContext):
    birthdate = validate_date(message.text)
    if not birthdate:
        await message.answer(
            "❌ Неверный формат. Попробуйте ещё раз.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await state.update_data(partner_birthdate=birthdate.strftime("%Y-%m-%d"))
    await message.answer(
        "✍️ Теперь введите полное ФИО партнёра",
        reply_markup=back_keyboard("main_menu")
    )
    await state.set_state(UserStates.waiting_for_partner_name)


@router.message(UserStates.waiting_for_partner_name)
async def process_partner_name(message: Message, state: FSMContext):
    partner_fio = message.text.strip()
    if not validate_fio(partner_fio):
        await message.answer(
            "❌ ФИО содержит недопустимые символы.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await state.update_data(partner_fio=partner_fio)
    data = await state.get_data()
    user_birthdate = data["user_birthdate"]
    user_fio = data["user_fio"]
    partner_birthdate = data["partner_birthdate"]
    partner_fio = data["partner_fio"]

    wait_msg = await message.answer("🔮 Рассчитываю совместимость... Подождите.")

    compatibility_data = calculate_compatibility(user_birthdate, user_fio, partner_birthdate, partner_fio)
    report_id = await db.save_report(message.from_user.id, "compatibility_mini", compatibility_data)

    # ИИ-интерпретация
    interpretation = await send_to_n8n_for_interpretation(compatibility_data, "compatibility_mini")
    mini_text = interpretation.get('compatibility_mini_report',
        f"🌟 Совместимость: {compatibility_data['compatibility']['total']*10:.0f}%")

    await bot.delete_message(chat_id=message.chat.id, message_id=wait_msg.message_id)

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Полный отчёт о совместимости - 199 ₽", callback_data=f"buy_compatibility:{report_id}"))
    if TEST_MODE:
        builder.add(InlineKeyboardButton(text="🔍 Бесплатно (тест)", callback_data=f"test_compatibility:{report_id}"))
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))

    await message.answer(
        f"{mini_text}\n\n"
        f"Подробнее: жизненный путь: {compatibility_data['compatibility']['life_path']}/10, "
        f"эмоциональная: {compatibility_data['compatibility']['emotional']}/10",
        reply_markup=builder.as_markup()
    )
    await state.clear()


# ============================
# ОБРАБОТЧИКИ БЛОКИРОВОК
# ============================
@router.callback_query(F.data.startswith("block_"))
async def process_block_choice(callback: CallbackQuery):
    sphere = callback.data.split("_")[1]
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user or not user.get("birthdate"):
        await callback.message.edit_text(
            "❗ Сначала введите свою дату рождения через /start.",
            reply_markup=back_keyboard("main_menu")
        )
        return

    birthdate = datetime.strptime(user["birthdate"], "%Y-%m-%d").date()
    if sphere == "money":
        num = money_block_number(birthdate)
        text = get_block_text("money", num)
        title = "Деньгах"
    elif sphere == "relations":
        num = relations_block_number(birthdate)
        text = get_block_text("relations", num)
        title = "Отношениях"
    else:
        num = health_block_number(birthdate)
        text = get_block_text("health", num)
        title = "Здоровье"

    py_num = personal_year(birthdate)
    py_text = get_personal_year_text(py_num)

    await callback.message.edit_text(
        f"📌 *Ваша блокировка в {title} (число {num}):*\n\n"
        f"{text}\n\n"
        f"🎁 *Ваш Личный год {datetime.now().year} (число {py_num}):*\n{py_text}",
        reply_markup=back_keyboard("cmd_blocks")
    )
    await callback.answer()


# ============================
# ГЕНЕРАЦИЯ И ОТПРАВКА ДЕНЕЖНОГО ТРЕУГОЛЬНИКА
# ============================
async def generate_and_send_money_triangle(message: Message, user_numbers: list):
    await message.answer("🔮 Генерирую ваш Денежный треугольник... Это займёт несколько секунд.")
    try:
        pdf_path = await generate_money_triangle_pdf(user_numbers, output_dir=PDF_STORAGE_PATH)
        await message.answer_document(
            document=FSInputFile(pdf_path, filename="money_triangle.pdf"),
            caption="✨ Ваш Денежный треугольник готов!",
            reply_markup=menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка генерации Money Triangle: {e}")
        await message.answer(
            "❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=back_keyboard("main_menu")
        )


# ============================
# ОБРАБОТЧИКИ ОПЛАТЫ
# ============================
@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    user_id = message.from_user.id
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await message.answer("❓ Для начала работы отправьте /start", reply_markup=menu_keyboard())
        return

    subscription = await db.get_user_subscription(user_id)
    if subscription and subscription["status"] in ("active", "trial"):
        # Показываем информацию о подписке
        status = subscription["status"]
        if status == "active":
            next_charge = subscription.get("next_charge")
            next_charge_str = next_charge if isinstance(next_charge, str) else "неизвестно"
            await message.answer(
                f"💎 У вас активная подписка.\n"
                f"Следующее списание: {next_charge_str}\n"
                f"Стоимость: 299 ₽/мес.\n"
                f"Используйте /subscribe для управления.",
                reply_markup=menu_keyboard()
            )
        elif status == "trial":
            trial_end = subscription.get("trial_end")
            trial_end_str = trial_end if isinstance(trial_end, str) else "неизвестно"
            await message.answer(
                f"🔍 У вас пробная подписка до {trial_end_str}.\n"
                f"После окончания пробного периода подписка будет отключена.",
                reply_markup=menu_keyboard()
            )
        return

    builder = InlineKeyboardBuilder()
    if PAYMENT_TOKEN and not TEST_MODE:
        builder.add(InlineKeyboardButton(text="💎 Оформить подписку (299 ₽/мес)", callback_data="subscribe_pay"))
    if TEST_MODE:
        builder.add(InlineKeyboardButton(text="🔔 Активировать бесплатно (тест)", callback_data="test_subscribe"))
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))

    await message.answer(
        "💎 Подписка на еженедельные прогнозы — 299 ₽ в месяц.\n"
        "Вы будете получать персональный нумерологический прогноз каждую неделю.\n"
        "Вы можете выбрать день недели для получения прогноза.",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "subscribe")
async def handle_subscribe_callback(callback: CallbackQuery):
    await callback.answer()
    await cmd_subscribe(callback.message)


@router.callback_query(F.data == "test_subscribe")
async def process_test_subscription(callback: CallbackQuery):
    if not TEST_MODE:
        await callback.answer("⚠️ Тестовый режим отключен")
        return
    await callback.answer()
    user_id = callback.from_user.id
    subscription_id = await db.create_subscription(user_id, "trial")
    if subscription_id:
        await callback.message.edit_text(
            "✅ Тестовая подписка активирована на 7 дней!",
            reply_markup=menu_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка активации подписки.",
            reply_markup=back_keyboard("main_menu")
        )


@router.callback_query(F.data == "subscribe_pay")
async def process_subscription_payment(callback: CallbackQuery):
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback.answer("⚠️ Платежи не настроены. Используйте тестовый режим.")
        return
    user_id = callback.from_user.id
    order_id = await db.create_order(user_id, "subscription_month", 299.0, "RUB", {"type": "subscription"})
    if not order_id:
        await callback.message.edit_text(
            "❌ Ошибка создания заказа.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Подписка на ИИ-Нумеролог",
        description="Еженедельные прогнозы на 1 месяц",
        payload=f"subscription:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=29900)]
    )
    await callback.answer()


# ============================
# ОБРАБОТЧИКИ ПЛАТЕЖЕЙ
# ============================
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    if ":" not in payload:
        logger.error(f"Invalid payload: {payload}")
        await message.answer(
            "❌ Ошибка обработки платежа.",
            reply_markup=menu_keyboard()
        )
        return

    payload_type, order_id_str = payload.split(":", 1)
    try:
        order_id = int(order_id_str)
    except ValueError:
        await message.answer(
            "❌ Ошибка обработки платежа.",
            reply_markup=menu_keyboard()
        )
        return

    order = await db.get_order(order_id)
    if not order:
        await message.answer(
            "❌ Заказ не найден.",
            reply_markup=menu_keyboard()
        )
        return

    await db.update_order_status(order_id, "paid")

    if payload_type == "subscription":
        await db.create_subscription(order["user_id"], "active")
        await message.answer("✅ Подписка успешно оформлена!", reply_markup=menu_keyboard())
    elif payload_type == "full_report":
        await process_full_report_payment(message, order)
    elif payload_type == "compatibility":
        await process_compatibility_payment(message, order)
    elif payload_type == "matrix_decoding":
        await process_matrix_decoding_payment(message, order)


# ============================
# ОБРАБОТЧИКИ ПОКУПКИ ОТЧЁТОВ
# ============================
@router.callback_query(F.data.startswith("buy_full_report:"))
async def process_buy_full_report(callback: CallbackQuery):
    await callback.answer()
    report_id = int(callback.data.split(":")[1])
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback.message.edit_text(
            "⚠️ Тестовый режим. Используйте кнопку 'Получить бесплатно'.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    user_id = callback.from_user.id
    order_id = await db.create_order(user_id, "full_report", 149.0, "RUB", {"report_id": report_id})
    if not order_id:
        await callback.message.edit_text(
            "❌ Ошибка создания заказа.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Полный нумерологический отчёт",
        description="Детальный анализ с Матрицей Судьбы и блокировками",
        payload=f"full_report:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Полный PDF-отчёт", amount=14900)]
    )


@router.callback_query(F.data.startswith("buy_compatibility:"))
async def process_buy_compatibility(callback: CallbackQuery):
    await callback.answer()
    report_id = int(callback.data.split(":")[1])
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback.message.edit_text(
            "⚠️ Тестовый режим. Используйте кнопку 'Получить бесплатно'.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    user_id = callback.from_user.id
    order_id = await db.create_order(user_id, "compatibility", 199.0, "RUB", {"report_id": report_id})
    if not order_id:
        await callback.message.edit_text(
            "❌ Ошибка создания заказа.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Отчёт о совместимости",
        description="Полный анализ совместимости с партнёром",
        payload=f"compatibility:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Отчёт о совместимости", amount=19900)]
    )


async def process_full_report_payment(message: Message, order: dict):
    report_id = order["payload"]["report_id"]
    report = await db.get_report(report_id)
    if not report:
        await message.answer(
            "❌ Отчёт не найден.",
            reply_markup=menu_keyboard()
        )
        return
    user = await db.get_user_by_id(order["user_id"])
    if not user:
        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=menu_keyboard()
        )
        return

    wait = await message.answer("⏳ Генерирую полный отчёт...")
    # Получаем дополнительные данные: матрица и блокировки
    birthdate = datetime.strptime(user["birthdate"], "%Y-%m-%d").date()
    matrix = calculate_shadow_matrix(birthdate, user["fio"])
    img_bytes = generate_matrix_image(matrix, user["fio"], user["birthdate"])
    # Блокировка (например, деньги)
    money_num = money_block_number(birthdate)
    block_text = get_block_text("money", money_num)

    combined_numerology = {
        **report["core_json"],
        "matrix": matrix,
        "block": {"sphere_name": "Деньги", "number": money_num, "text": block_text}
    }

    # ИИ-интерпретация
    interpretation = await send_to_n8n_for_interpretation(combined_numerology, "full")

    # Генерируем PDF в фоне
    pdf_path = await generate_full_pdf(
        user_data=user,
        numerology_data=combined_numerology,
        interpretation_data=interpretation,
        matrix_image_bytes=img_bytes,
        report_type="full"
    )
    if pdf_path:
        await db.update_report_pdf(report_id, pdf_path)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait.message_id)
        await message.answer_document(
            FSInputFile(pdf_path, filename="full_report.pdf"),
            reply_markup=menu_keyboard()
        )
        # Предложение подписки
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="💎 Оформить подписку", callback_data="subscribe"))
        builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))
        await message.answer(
            "🌟 Хотите получать еженедельные прогнозы? Оформите подписку за 299 ₽/мес!",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer(
            "❌ Ошибка генерации отчёта.",
            reply_markup=back_keyboard("main_menu")
        )


async def process_compatibility_payment(message: Message, order: dict):
    report_id = order["payload"]["report_id"]
    report = await db.get_report(report_id)
    if not report:
        await message.answer(
            "❌ Отчёт не найден.",
            reply_markup=menu_keyboard()
        )
        return
    user = await db.get_user_by_id(order["user_id"])
    if not user:
        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=menu_keyboard()
        )
        return

    wait = await message.answer("⏳ Генерирую отчёт о совместимости...")
    compatibility_data = report["core_json"]
    pdf_path = await generate_full_pdf(
        user_data=user,
        numerology_data=compatibility_data,
        interpretation_data={"compatibility_report": compatibility_data.get("compatibility", {})},
        matrix_image_bytes=None,
        report_type="compatibility"
    )
    if pdf_path:
        await db.update_report_pdf(report_id, pdf_path)
        await bot.delete_message(chat_id=message.chat.id, message_id=wait.message_id)
        await message.answer_document(
            FSInputFile(pdf_path, filename="compatibility_report.pdf"),
            reply_markup=menu_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка генерации отчёта.",
            reply_markup=back_keyboard("main_menu")
        )


async def process_matrix_decoding_payment(message: Message, order: dict):
    user_id = order["user_id"]
    user = await db.get_user_by_id(user_id)
    if not user:
        await message.answer(
            "❌ Пользователь не найден.",
            reply_markup=menu_keyboard()
        )
        return
    await generate_matrix_decoding_report(message, user_id, test=False)


# ============================
# ТЕСТОВЫЕ ОБРАБОТЧИКИ (БЕСПЛАТНО)
# ============================
@router.callback_query(F.data.startswith("test_full_report:"))
async def process_test_full_report(callback: CallbackQuery):
    if not TEST_MODE:
        await callback.answer("⚠️ Тестовый режим отключен")
        return
    await callback.answer()
    report_id = int(callback.data.split(":")[1])
    report = await db.get_report(report_id)
    if not report:
        await callback.message.edit_text(
            "❌ Отчёт не найден.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    user = await db.get_user_by_id(report["user_id"])
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await process_full_report_payment(callback.message, {"user_id": user["id"], "payload": {"report_id": report_id}})


@router.callback_query(F.data.startswith("test_compatibility:"))
async def process_test_compatibility(callback: CallbackQuery):
    if not TEST_MODE:
        await callback.answer("⚠️ Тестовый режим отключен")
        return
    await callback.answer()
    report_id = int(callback.data.split(":")[1])
    report = await db.get_report(report_id)
    if not report:
        await callback.message.edit_text(
            "❌ Отчёт не найден.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    user = await db.get_user_by_id(report["user_id"])
    if not user:
        await callback.message.edit_text(
            "❌ Пользователь не найден.",
            reply_markup=back_keyboard("main_menu")
        )
        return
    await process_compatibility_payment(callback.message, {"user_id": user["id"], "payload": {"report_id": report_id}})


# ============================
# КОМАНДА /REPORT (ПОВТОРНАЯ ВЫДАЧА)
# ============================
@router.message(Command("report"))
async def cmd_report(message: Message):
    user_id = message.from_user.id
    report = await db.get_latest_user_report(user_id, "full")
    if not report or not report.get("pdf_url"):
        report = await db.get_latest_user_report(user_id, "compatibility")
    if not report or not report.get("pdf_url"):
        await message.answer(
            "ℹ️ У вас нет купленных отчётов. Используйте /start для расчёта.",
            reply_markup=menu_keyboard()
        )
        return
    await message.answer_document(
        FSInputFile(report["pdf_url"]),
        reply_markup=menu_keyboard()
    )


# ============================
# НАСТРОЙКИ (ПЕРЕКЛЮЧЕНИЕ ЯЗЫКА И УВЕДОМЛЕНИЙ)
# ============================
@router.callback_query(F.data == "toggle_lang")
async def toggle_lang(callback: CallbackQuery):
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("❓ Сначала выполните /start")
        return
    new_lang = "en" if user["lang"] == "ru" else "ru"
    await db.update_user_settings(callback.from_user.id, lang=new_lang)
    await callback.answer(f"Язык изменён на {'🇷🇺 Русский' if new_lang == 'ru' else '🇬🇧 English'}")
    # Обновляем сообщение с настройками
    await process_settings_button(callback)


@router.callback_query(F.data == "toggle_push")
async def toggle_push(callback: CallbackQuery):
    user = await db.get_user_by_tg_id(callback.from_user.id)
    if not user:
        await callback.answer("❓ Сначала выполните /start")
        return
    new_push = not user["push_enabled"]
    await db.update_user_settings(callback.from_user.id, push_enabled=new_push)
    status = "включены ✅" if new_push else "отключены ❌"
    await callback.answer(f"Уведомления {status}")
    # Обновляем сообщение с настройками
    await process_settings_button(callback)


# ============================
# ЗАПУСК БОТА
# ============================
async def main():
    await db.init()
    # Планировщик запускаем с переданным экземпляром бота
    start_scheduler(bot)
    logger.info("🚀 Бот запущен. Тестовый режим: %s", TEST_MODE)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
