# admin.py
import os
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database_sqlite import Database

router = Router()
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

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
    await message.answer(
        "👑 Админ-панель\nВыберите действие:",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data.startswith("admin_"))
async def admin_callback(callback: types.CallbackQuery):
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
        await callback.message.edit_text(text)
    
    elif action == "users":
        users = await db.get_all_users(limit=20)
        text = "👥 Последние 20 пользователей:\n\n"
        for u in users:
            text += f"• {u['id']} | {u['tg_id']} | {u['fio'] or '-'} | {u['birthdate'] or '-'}\n"
        await callback.message.edit_text(text)
    
    elif action == "orders":
        orders = await db.get_all_orders(limit=20)
        text = "🛒 Последние 20 заказов:\n\n"
        for o in orders:
            text += f"• {o['id']} | {o['product']} | {o['status']} | {o['price']} {o['currency']}\n"
        await callback.message.edit_text(text)
    
    elif action == "broadcast":
        await callback.message.edit_text(
            "📢 Введите текст рассылки (одно сообщение).\n"
            "Оно будет отправлено всем пользователям с включёнными уведомлениями."
        )
        # Здесь можно использовать FSM для ввода текста, но для простоты мы используем следующее сообщение
        # В реальном боте лучше использовать FSM
    else:
        await callback.message.edit_text("❌ Неизвестное действие.")

# Обработчик для рассылки (упрощённо, без FSM)
@router.message(lambda msg: msg.text and not msg.text.startswith("/"))
async def broadcast_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    # Проверим, что админ в режиме рассылки — мы можем использовать состояние, но для упрощения предположим, что последнее сообщение после нажатия "admin_broadcast" — это текст рассылки.
    # В реальном проекте используйте FSM.
    db = Database()
    await db.init()
    tg_ids = await db.get_all_active_users()
    await message.answer(f"📢 Начинаю рассылку для {len(tg_ids)} пользователей...")
    from bot import bot
    success = 0
    for tg_id in tg_ids:
        try:
            await bot.send_message(tg_id, message.text)
            success += 1
            await asyncio.sleep(0.05)  # чтобы не превысить лимиты Telegram
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю {tg_id}: {e}")
    await message.answer(f"✅ Рассылка завершена. Успешно: {success}/{len(tg_ids)}")
