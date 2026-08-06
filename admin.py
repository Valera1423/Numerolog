# admin.py
import os
import logging
import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_sqlite import Database

# Импорт бота не нужен - используем message.bot или callback.bot

router = Router()
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
logger = logging.getLogger(__name__)


# ========== FSM для рассылки ==========
class BroadcastState(StatesGroup):
    waiting_for_text = State()


# ========== Вспомогательные функции ==========
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


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


# ========== Команда /admin ==========
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.add(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    builder.add(InlineKeyboardButton(text="🛒 Заказы", callback_data="admin_orders"))
    builder.add(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    # Кнопка меню
    builder.add(InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"))
    # Располагаем в 2 колонки
    builder.adjust(2)
    await message.answer(
        "👑 Админ-панель\nВыберите действие:",
        reply_markup=builder.as_markup()
    )


# ========== Обработчики callback'ов админки ==========
@router.callback_query(F.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.")
        return
    action = callback.data.split("_")[1]
    db = Database()
    await db.init()
    
    if action == "stats":
        stats = await db.get_stats()
        text = (
            f"📊 Статистика:\n"
            f"👤 Пользователей: {stats['users']}\n"
            f"💳 Оплаченных заказов: {stats['paid_orders']}\n"
            f"💎 Активных подписок: {stats['active_subscriptions']}"
        )
        await callback.message.edit_text(
            text,
            reply_markup=back_keyboard("admin_panel")  # возврат к админ-панели
        )
        await callback.answer()
    
    elif action == "users":
        users = await db.get_all_users(limit=20)
        text = "👥 Последние 20 пользователей:\n\n"
        for u in users:
            text += f"• {u['id']} | {u['tg_id']} | {u['fio'] or '-'} | {u['birthdate'] or '-'}\n"
        await callback.message.edit_text(
            text,
            reply_markup=back_keyboard("admin_panel")
        )
        await callback.answer()
    
    elif action == "orders":
        orders = await db.get_all_orders(limit=20)
        text = "🛒 Последние 20 заказов:\n\n"
        for o in orders:
            text += f"• {o['id']} | {o['product']} | {o['status']} | {o['price']} {o['currency']}\n"
        await callback.message.edit_text(
            text,
            reply_markup=back_keyboard("admin_panel")
        )
        await callback.answer()
    
    elif action == "broadcast":
        # Переход в режим ввода текста рассылки
        await callback.message.edit_text(
            "📢 Введите текст рассылки (одно сообщение).\n"
            "Оно будет отправлено всем пользователям с включёнными уведомлениями.\n"
            "Отправьте /cancel для отмены.",
            reply_markup=back_keyboard("admin_panel")
        )
        await callback.answer()
        # Устанавливаем состояние
        await callback.message.answer("✏️ Введите текст:")
        await callback.message.state.set_state(BroadcastState.waiting_for_text)
    
    else:
        await callback.message.edit_text("❌ Неизвестное действие.", reply_markup=back_keyboard("admin_panel"))
        await callback.answer()


# ========== Обработчик для ввода текста рассылки ==========
@router.message(BroadcastState.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    text = message.text
    if not text:
        await message.answer("❌ Текст не может быть пустым. Отправьте /cancel для отмены.")
        return
    
    db = Database()
    await db.init()
    tg_ids = await db.get_all_active_users()
    await message.answer(f"📢 Начинаю рассылку для {len(tg_ids)} пользователей...")
    
    success = 0
    for tg_id in tg_ids:
        try:
            await message.bot.send_message(tg_id, text)
            success += 1
            await asyncio.sleep(0.05)  # избегаем превышения лимитов Telegram
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {tg_id}: {e}")
    
    await message.answer(f"✅ Рассылка завершена. Успешно: {success}/{len(tg_ids)}")
    await state.clear()


# ========== Обработчик для возврата в админ-панель ==========
@router.callback_query(F.data == "admin_panel")
async def back_to_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.")
        return
    await admin_panel(callback.message)
    await callback.answer()


# ========== Обработчик для кнопки "Меню" ==========
@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    # Возвращаем пользователя в главное меню (этот хендлер также определён в bot.py)
    # Чтобы не дублировать логику, можно вызвать команду /start через бота или просто отправить сообщение.
    # Проще: отправить новое сообщение с меню.
    await callback.answer()
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
    # Если это сообщение из админки, редактируем его же
    await callback.message.edit_text(
        "👋 Добро пожаловать в Супер-Нумеролог!\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )


# ========== Обработчик /cancel для выхода из состояния ==========
@router.message(Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == BroadcastState.waiting_for_text:
        await state.clear()
        await message.answer("❌ Отправка рассылки отменена.", reply_markup=menu_keyboard())
    else:
        # Если не в этом состоянии, просто игнорируем или говорим, что нечего отменять
        await message.answer("Нет активных действий для отмены.", reply_markup=menu_keyboard())
