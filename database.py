import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple, Optional

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица для хранения обработанных постов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_username TEXT NOT NULL,
                        message_id INTEGER NOT NULL,
                        message_text TEXT,
                        post_date DATETIME,
                        processed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_published BOOLEAN DEFAULT FALSE,
                        summary TEXT,
                        UNIQUE(channel_username, message_id)
                    )
                ''')
                
                # Таблица для хранения настроек каналов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS channel_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        channel_username TEXT UNIQUE NOT NULL,
                        last_message_id INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        added_date DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица для статистики
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date DATE DEFAULT CURRENT_DATE,
                        posts_processed INTEGER DEFAULT 0,
                        posts_published INTEGER DEFAULT 0,
                        posts_filtered INTEGER DEFAULT 0
                    )
                ''')
                
                conn.commit()
                logging.info("База данных инициализирована успешно")
                
        except sqlite3.Error as e:
            logging.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def is_post_processed(self, channel_username: str, message_id: int) -> bool:
        """Проверяет, был ли пост уже обработан"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM processed_posts WHERE channel_username = ? AND message_id = ?",
                    (channel_username, message_id)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logging.error(f"Ошибка проверки обработанного поста: {e}")
            return False
    
    def add_processed_post(self, channel_username: str, message_id: int, 
                          message_text: str, post_date: datetime, 
                          summary: str = None, is_published: bool = False):
        """Добавляет обработанный пост в базу данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_posts 
                    (channel_username, message_id, message_text, post_date, summary, is_published)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (channel_username, message_id, message_text, post_date, summary, is_published))
                conn.commit()
                logging.debug(f"Пост {message_id} из {channel_username} добавлен в базу данных")
        except sqlite3.Error as e:
            logging.error(f"Ошибка добавления поста в базу данных: {e}")
    
    def get_last_message_id(self, channel_username: str) -> int:
        """Получает ID последнего обработанного сообщения для канала"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT last_message_id FROM channel_settings WHERE channel_username = ?",
                    (channel_username,)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as e:
            logging.error(f"Ошибка получения последнего message_id: {e}")
            return 0
    
    def update_last_message_id(self, channel_username: str, message_id: int):
        """Обновляет ID последнего обработанного сообщения для канала"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO channel_settings (channel_username, last_message_id)
                    VALUES (?, ?)
                ''', (channel_username, message_id))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Ошибка обновления последнего message_id: {e}")
    
    def add_channel(self, channel_username: str):
        """Добавляет новый канал для мониторинга"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO channel_settings (channel_username)
                    VALUES (?)
                ''', (channel_username,))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Ошибка добавления канала: {e}")
    
    def get_statistics(self, days: int = 7) -> List[Tuple]:
        """Получает статистику за последние дни"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT date, posts_processed, posts_published, posts_filtered
                    FROM statistics
                    WHERE date >= date('now', '-{} days')
                    ORDER BY date DESC
                '''.format(days))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Ошибка получения статистики: {e}")
            return []
    
    def update_statistics(self, posts_processed: int = 0, posts_published: int = 0, posts_filtered: int = 0):
        """Обновляет статистику за сегодня"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO statistics 
                    (date, posts_processed, posts_published, posts_filtered)
                    VALUES (
                        CURRENT_DATE,
                        COALESCE((SELECT posts_processed FROM statistics WHERE date = CURRENT_DATE), 0) + ?,
                        COALESCE((SELECT posts_published FROM statistics WHERE date = CURRENT_DATE), 0) + ?,
                        COALESCE((SELECT posts_filtered FROM statistics WHERE date = CURRENT_DATE), 0) + ?
                    )
                ''', (posts_processed, posts_published, posts_filtered))
                conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Ошибка обновления статистики: {e}")
