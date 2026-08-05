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
        
        # Таблица reports — с новыми полями для матрицы и блокировок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                report_type TEXT,
                core_json TEXT,
                matrix_json TEXT,          -- данные матрицы (арканы)
                block_json TEXT,           -- данные блокировки
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.connection.commit()
    
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
    
    async def save_report(self, user_id: int, report_type: str, core_json: Dict[str, Any],
                          matrix_json: Dict[str, Any] = None, block_json: Dict[str, Any] = None) -> int:
        """Сохраняет отчет с дополнительными данными матрицы и блокировки"""
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
    
    # Остальные методы (create_order, update_order_status, get_order, get_user_subscription, create_subscription, update_subscription_status, get_active_subscribers) остаются без изменений из предыдущей версии.
    # Для краткости я не повторяю их здесь, они есть в коде Бота №2.
    # Вы можете скопировать их из ранее предоставленного database_sqlite.py.