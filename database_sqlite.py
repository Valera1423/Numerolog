# database_sqlite.py
import os
import json
import sqlite3
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Union

class Database:
    def __init__(self):
        self.db_file = "numerology_bot.db"
        self.connection = None
        
    async def init(self):
        """Инициализация соединения с базой данных"""
        self.connection = sqlite3.connect(self.db_file)
        self.connection.row_factory = sqlite3.Row
        await self._create_tables_if_not_exist()
        return True
    
    async def _create_tables_if_not_exist(self):
        """Создаёт таблицы, если они не существуют"""
        cursor = self.connection.cursor()
        
        # Таблица users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                fio TEXT,
                birthdate DATE,
                lang TEXT DEFAULT 'ru',
                push_enabled INTEGER DEFAULT 1,
                state TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица orders
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product TEXT,
                price REAL,
                currency TEXT,
                status TEXT,
                paid_at TIMESTAMP,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                report_type TEXT,
                core_json TEXT,
                matrix_json TEXT,
                block_json TEXT,
                pdf_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица subscriptions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT,
                trial_end DATE,
                next_charge DATE,
                provider_id TEXT,
                delivery_day INTEGER DEFAULT 0,  -- день недели для прогноза (0=воскресенье, 1=понедельник...)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица request_history (история запросов)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS request_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                request_type TEXT,
                params TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица feedback (отзывы)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица forecast_history (история отправленных прогнозов)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS forecast_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                forecast_text TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.connection.commit()
    
    # ========== Пользователи ==========
    async def get_user_by_tg_id(self, tg_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    async def create_user(self, tg_id: int) -> int:
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_user(self, tg_id: int, fio: str, birthdate: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE users SET fio = ?, birthdate = ? WHERE tg_id = ?",
            (fio, birthdate, tg_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def update_user_settings(self, tg_id: int, lang: str = None, push_enabled: bool = None) -> bool:
        query_parts = []
        params = []
        if lang is not None:
            query_parts.append("lang = ?")
            params.append(lang)
        if push_enabled is not None:
            query_parts.append("push_enabled = ?")
            params.append(1 if push_enabled else 0)
        if not query_parts:
            return False
        params.append(tg_id)
        cursor = self.connection.cursor()
        cursor.execute(f"UPDATE users SET {', '.join(query_parts)} WHERE tg_id = ?", params)
        self.connection.commit()
        return cursor.rowcount > 0
    
    # ========== Отчёты ==========
    async def save_report(self, user_id: int, report_type: str, core_json: Dict[str, Any],
                          matrix_json: Dict[str, Any] = None, block_json: Dict[str, Any] = None) -> int:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            """
            INSERT INTO reports (user_id, report_type, core_json, matrix_json, block_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, report_type, json.dumps(core_json),
             json.dumps(matrix_json) if matrix_json else None,
             json.dumps(block_json) if block_json else None)
        )
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_report_pdf(self, report_id: int, pdf_url: str) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("UPDATE reports SET pdf_url = ? WHERE id = ?", (pdf_url, report_id))
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        if row:
            report = dict(row)
            if report["core_json"]:
                report["core_json"] = json.loads(report["core_json"])
            if report["matrix_json"]:
                report["matrix_json"] = json.loads(report["matrix_json"])
            if report["block_json"]:
                report["block_json"] = json.loads(report["block_json"])
            return report
        return None
    
    async def get_latest_user_report(self, user_id: int, report_type: str) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            """
            SELECT * FROM reports
            WHERE user_id = ? AND report_type = ? AND pdf_url IS NOT NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, report_type)
        )
        row = cursor.fetchone()
        if row:
            report = dict(row)
            if report["core_json"]:
                report["core_json"] = json.loads(report["core_json"])
            if report["matrix_json"]:
                report["matrix_json"] = json.loads(report["matrix_json"])
            if report["block_json"]:
                report["block_json"] = json.loads(report["block_json"])
            return report
        return None
    
    # ========== Заказы ==========
    async def create_order(self, user_id: int, product: str, price: float,
                          currency: str, payload: Dict[str, Any]) -> int:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            """
            INSERT INTO orders (user_id, product, price, currency, status, payload)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, product, price, currency, json.dumps(payload))
        )
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_order_status(self, order_id: int, status: str) -> bool:
        cursor = self.connection.cursor()
        paid_at = datetime.now().isoformat() if status == 'paid' else None
        cursor.execute(
            "UPDATE orders SET status = ?, paid_at = ? WHERE id = ?",
            (status, paid_at, order_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if row:
            order = dict(row)
            if order["payload"]:
                order["payload"] = json.loads(order["payload"])
            return order
        return None
    
    # ========== Подписки ==========
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    async def create_subscription(self, user_id: int, status: str, provider_id: str = None) -> int:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        now = datetime.now().date()
        trial_end = (now + timedelta(days=7)).isoformat() if status == "trial" else None
        next_charge = (now + timedelta(days=30)).isoformat() if status in ["active", "trial"] else None
        cursor.execute(
            """
            INSERT INTO subscriptions (user_id, status, trial_end, next_charge, provider_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, status, trial_end, next_charge, provider_id, datetime.now().isoformat())
        )
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_subscription_status(self, subscription_id: int, status: str) -> bool:
        cursor = self.connection.cursor()
        now = datetime.now().date()
        next_charge = (now + timedelta(days=30)).isoformat() if status == "active" else None
        cursor.execute(
            "UPDATE subscriptions SET status = ?, next_charge = ?, updated_at = ? WHERE id = ?",
            (status, next_charge, datetime.now().isoformat(), subscription_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def update_subscription_delivery_day(self, subscription_id: int, day: int) -> bool:
        cursor = self.connection.cursor()
        cursor.execute("UPDATE subscriptions SET delivery_day = ? WHERE id = ?", (day, subscription_id))
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def get_active_subscribers(self) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT u.*, s.id as subscription_id, s.delivery_day
            FROM users u
            JOIN subscriptions s ON u.id = s.user_id
            WHERE s.status IN ('active', 'trial')
            AND (s.trial_end IS NULL OR date(s.trial_end) >= date('now'))
            AND u.push_enabled = 1
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========== История запросов ==========
    async def save_request_history(self, user_id: int, request_type: str, params: dict):
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            "INSERT INTO request_history (user_id, request_type, params) VALUES (?, ?, ?)",
            (user_id, request_type, json.dumps(params))
        )
        self.connection.commit()
    
    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            "SELECT * FROM request_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========== Отзывы ==========
    async def save_feedback(self, user_id: int, text: str, rating: int = 0):
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            "INSERT INTO feedback (user_id, text, rating) VALUES (?, ?, ?)",
            (user_id, text, rating)
        )
        self.connection.commit()
    
    # ========== История прогнозов ==========
    async def save_forecast_history(self, user_id: int, forecast_text: str):
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            "INSERT INTO forecast_history (user_id, forecast_text) VALUES (?, ?)",
            (user_id, forecast_text)
        )
        self.connection.commit()
    
    async def get_forecast_history(self, user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        cursor.execute(
            "SELECT * FROM forecast_history WHERE user_id = ? ORDER BY sent_at DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========== Статистика (для админа) ==========
    async def get_stats(self) -> Dict[str, Any]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'paid'")
        orders_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
        subscriptions_active = cursor.fetchone()[0]
        return {
            "users": users_count,
            "paid_orders": orders_count,
            "active_subscriptions": subscriptions_active
        }
    
    # ========== Получить всех пользователей (для админа) ==========
    async def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM users ORDER BY id LIMIT ? OFFSET ?",
            (limit, offset)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========== Получить все заказы (для админа) ==========
    async def get_all_orders(self, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    # ========== Рассылка сообщений (для админа) ==========
    async def get_all_active_users(self) -> List[int]:
        cursor = self.connection.cursor()
        cursor.execute("SELECT tg_id FROM users WHERE push_enabled = 1")
        rows = cursor.fetchall()
        return [row[0] for row in rows]
