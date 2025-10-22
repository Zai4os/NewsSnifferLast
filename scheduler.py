import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
import threading
from telegram_client import TelegramNewsClient
from config import Config

class NewsScheduler:
    def __init__(self):
        self.telegram_client = TelegramNewsClient()
        self.is_running = False
        self.scheduler_thread = None
        self.loop = None
        
    async def initialize(self) -> bool:
        """Инициализация планировщика"""
        try:
            # Инициализируем Telegram клиент
            if not await self.telegram_client.initialize():
                logging.error("Не удалось инициализировать Telegram клиент")
                return False
            
            logging.info("Планировщик успешно инициализирован")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка инициализации планировщика: {e}")
            return False
    
    async def run_news_collection(self):
        """Основная функция сбора и пересылки новостей без фильтрации"""
        try:
            logging.info("Начинаем проверку каналов и пересылку новых сообщений...")
            start_time = datetime.now()
            
            # Проверяем соединение
            if not await self.telegram_client.test_connection():
                logging.error("Нет соединения с Telegram")
                return
            
            # Обрабатываем все каналы
            results = await self.telegram_client.process_all_channels()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logging.info(f"Пересылка завершена за {duration:.1f} секунд")
            logging.info(f"Результаты: обработано {results.get('processed', 0)}, "
                        f"переслано {results.get('forwarded', 0)}")
            
            # Отправляем статистику в лог
            await self._send_statistics_if_needed(results)
            
        except Exception as e:
            logging.error(f"Ошибка при сборе новостей: {e}")
    
    async def _send_statistics_if_needed(self, results: dict):
        """Отправляет статистику в канал, если есть активность"""
        try:
            total_activity = results.get('forwarded', 0)
            
            # Логируем статистику только в лог файл, без отправки в канал
            if total_activity > 0:
                logging.info(f"📊 Статистика: обработано {results.get('processed', 0)}, "
                           f"переслано {results.get('forwarded', 0)} постов")
                    
        except Exception as e:
            logging.error(f"Ошибка обработки статистики: {e}")
    
    async def start_daemon(self):
        """Запускает демон с простым циклом"""
        logging.info("🚀 NewsSniffer запущен в режиме демона")
        logging.info(f"📅 Интервал проверки: {Config.CHECK_INTERVAL_MINUTES} минут")
        if Config.CHECK_INTERVAL_MINUTES < 1:
            logging.warning("⚠️ Используется очень частая проверка (менее 1 минуты). Следите за лимитами Telegram API!")
        logging.info(f"📺 Мониторим каналов: {len(Config.SOURCE_CHANNELS)}")
        logging.info(f"📤 Публикуем в: {Config.TARGET_CHANNEL}")
        
        self.is_running = True
        
        while self.is_running:
            try:
                next_run = datetime.now() + timedelta(minutes=Config.CHECK_INTERVAL_MINUTES)
                logging.info(f"⏰ Следующий запуск: {next_run.strftime('%H:%M:%S %d.%m.%Y')}")
                
                # Ждем интервал
                await asyncio.sleep(Config.CHECK_INTERVAL_MINUTES * 60)
                
                if self.is_running:
                    await self.run_news_collection()
                    
            except Exception as e:
                logging.error(f"Ошибка в цикле демона: {e}")
                await asyncio.sleep(60)  # Ждем минуту при ошибке
    
    def _cleanup_database_sync(self):
        """Синхронная версия очистки БД"""
        try:
            logging.info("Начинаем очистку базы данных...")
            import sqlite3
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM processed_posts 
                    WHERE processed_date < datetime('now', '-30 days')
                ''')
                deleted_count = cursor.rowcount
                conn.commit()
            logging.info(f"Удалено {deleted_count} старых записей из базы данных")
        except Exception as e:
            logging.error(f"Ошибка очистки базы данных: {e}")
    
    def _health_check_sync(self):
        """Синхронная версия проверки здоровья"""
        try:
            logging.info("Проверка состояния системы...")
            
            # Проверяем доступность базы данных
            import sqlite3
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
            logging.debug("База данных доступна")
            
        except Exception as e:
            logging.error(f"Ошибка проверки здоровья системы: {e}")
    
    async def _cleanup_database(self):
        """Очищает старые записи в базе данных"""
        try:
            logging.info("Начинаем очистку базы данных...")
            
            # Удаляем записи старше 30 дней
            cleanup_query = '''
                DELETE FROM processed_posts 
                WHERE processed_date < datetime('now', '-30 days')
            '''
            
            import sqlite3
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(cleanup_query)
                deleted_count = cursor.rowcount
                conn.commit()
            
            logging.info(f"Очистка БД завершена. Удалено записей: {deleted_count}")
            
        except Exception as e:
            logging.error(f"Ошибка очистки базы данных: {e}")
    
    async def _health_check(self):
        """Проверяет состояние системы"""
        try:
            # Проверяем соединение с Telegram
            is_connected = await self.telegram_client.test_connection()
            
            if not is_connected:
                logging.warning("Потеряно соединение с Telegram")
                # Пытаемся переподключиться
                await self.telegram_client.initialize()
            
            # Проверяем доступность базы данных
            try:
                import sqlite3
                with sqlite3.connect(Config.DATABASE_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                logging.debug("База данных доступна")
            except Exception as e:
                logging.error(f"Проблемы с базой данных: {e}")
            
        except Exception as e:
            logging.error(f"Ошибка проверки здоровья системы: {e}")
    
    async def start(self):
        """Запускает планировщик в асинхронном режиме"""
        if self.is_running:
            logging.warning("Планировщик уже запущен")
            return
        
        await self.start_daemon()
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
        except Exception as e:
            logging.error(f"Ошибка в планировщике: {e}")
    
    async def stop(self):
        """Останавливает планировщик"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Закрываем Telegram клиент
        try:
            await self.telegram_client.close()
        except Exception as e:
            logging.error(f"Ошибка закрытия Telegram клиента: {e}")
        
        logging.info("Планировщик остановлен")
    
    async def run_once(self):
        """Запускает сбор новостей один раз (для тестирования)"""
        try:
            if not await self.initialize():
                return False
            
            await self.run_news_collection()
            await self.telegram_client.close()
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при однократном запуске: {e}")
            return False
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Возвращает время следующего запуска"""
        try:
            jobs = schedule.get_jobs()
            if jobs:
                next_run = min(job.next_run for job in jobs)
                return next_run
        except Exception as e:
            logging.error(f"Ошибка получения времени следующего запуска: {e}")
        
        return None
    
    def get_status(self) -> dict:
        """Возвращает статус планировщика"""
        return {
            'is_running': self.is_running,
            'next_run': self.get_next_run_time(),
            'scheduled_jobs': len(schedule.get_jobs()),
            'thread_alive': self.scheduler_thread.is_alive() if self.scheduler_thread else False
        }
