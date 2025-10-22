#!/usr/bin/env python3
"""
NewsSniffer - Telegram News Forwarder
Автоматическая пересылка новостей из Telegram каналов без фильтрации
"""

import asyncio
import logging
import signal
import sys
import argparse
from datetime import datetime
import os

from config import Config
from scheduler import NewsScheduler
from telegram_client import TelegramNewsClient

def setup_logging():
    """Настройка логирования"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Настройка логирования в файл
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Уменьшаем уровень логирования для внешних библиотек
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

def check_config():
    """Проверяет конфигурацию"""
    missing_vars = []
    
    if not Config.TELEGRAM_API_ID:
        missing_vars.append('TELEGRAM_API_ID')
    if not Config.TELEGRAM_API_HASH:
        missing_vars.append('TELEGRAM_API_HASH')
    if not Config.TELEGRAM_BOT_TOKEN:
        missing_vars.append('TELEGRAM_BOT_TOKEN')
    if not Config.TARGET_CHANNEL:
        missing_vars.append('TARGET_CHANNEL')
    
    if missing_vars:
        logging.error(f"Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
        logging.error("Создайте файл .env на основе .env.example и заполните все необходимые поля")
        return False
    
    if not Config.SOURCE_CHANNELS:
        logging.warning("Список каналов для мониторинга пуст. Добавьте каналы в config.py")
        return False
    
    return True

async def test_connection():
    """Тестирует подключение к Telegram"""
    logging.info("Тестируем подключение к Telegram...")
    
    client = TelegramNewsClient()
    try:
        if await client.initialize():
            logging.info("✅ Подключение к Telegram успешно")
            
            # Проверяем доступность каналов
            for channel in Config.SOURCE_CHANNELS:
                info = await client.get_channel_info(channel)
                if info:
                    logging.info(f"✅ Канал {channel}: {info['title']} ({info.get('participants_count', 'N/A')} участников)")
                else:
                    logging.warning(f"⚠️ Канал {channel} недоступен")
            
            # Проверяем целевой канал
            target_info = await client.get_channel_info(Config.TARGET_CHANNEL)
            if target_info:
                logging.info(f"✅ Целевой канал {Config.TARGET_CHANNEL}: {target_info['title']}")
            else:
                logging.warning(f"⚠️ Целевой канал {Config.TARGET_CHANNEL} недоступен")
            
            await client.close()
            return True
        else:
            logging.error("❌ Не удалось подключиться к Telegram")
            return False
            
    except Exception as e:
        logging.error(f"❌ Ошибка тестирования подключения: {e}")
        return False

async def run_once():
    """Запускает сбор новостей один раз"""
    logging.info("Запуск однократного сбора новостей...")
    
    scheduler = NewsScheduler()
    success = await scheduler.run_once()
    
    if success:
        logging.info("✅ Однократный сбор новостей завершен успешно")
    else:
        logging.error("❌ Ошибка при однократном сборе новостей")
    
    return success

def run_daemon():
    """Запускает планировщик в режиме демона"""
    logging.info("Запуск в режиме демона...")
    
    scheduler = NewsScheduler()
    
    # Обработчики сигналов для корректного завершения
    def signal_handler(signum, frame):
        logging.info(f"Получен сигнал {signum}. Завершаем работу...")
        scheduler.is_running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_scheduler():
        if await scheduler.initialize():
            await scheduler.start()
        else:
            logging.error("❌ Не удалось инициализировать планировщик")
            sys.exit(1)
    
    # Запускаем асинхронный планировщик
    try:
        asyncio.run(start_scheduler())
    except KeyboardInterrupt:
        logging.info("Программа прервана пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        sys.exit(1)

def show_status():
    """Показывает статус системы"""
    logging.info("📊 Статус NewsSniffer:")
    
    # Проверяем конфигурацию
    if check_config():
        logging.info("✅ Конфигурация корректна")
    else:
        logging.error("❌ Проблемы с конфигурацией")
        return
    
    # Проверяем базу данных
    try:
        import sqlite3
        with sqlite3.connect(Config.DATABASE_PATH) as conn:
            cursor = conn.cursor()
            
            # Статистика обработанных постов
            cursor.execute("SELECT COUNT(*) FROM processed_posts")
            total_posts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM processed_posts WHERE is_published = 1")
            published_posts = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM channel_settings WHERE is_active = 1")
            active_channels = cursor.fetchone()[0]
            
            logging.info(f"📊 Всего обработано постов: {total_posts}")
            logging.info(f"📰 Опубликовано: {published_posts}")
            logging.info(f"📺 Активных каналов: {active_channels}")
            
    except Exception as e:
        logging.error(f"❌ Ошибка доступа к базе данных: {e}")

def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(description='NewsSniffer - Telegram News Aggregator')
    parser.add_argument('--test', action='store_true', help='Тестировать подключение')
    parser.add_argument('--once', action='store_true', help='Запустить сбор новостей один раз')
    parser.add_argument('--daemon', action='store_true', help='Запустить в режиме демона')
    parser.add_argument('--status', action='store_true', help='Показать статус системы')
    parser.add_argument('--config', action='store_true', help='Показать текущую конфигурацию')
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging()
    
    logging.info("🔥 NewsSniffer - Telegram News Forwarder")
    logging.info(f"📅 Запуск: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")
    
    # Проверяем конфигурацию
    if not check_config():
        sys.exit(1)
    
    try:
        if args.test:
            # Тестирование подключения
            success = asyncio.run(test_connection())
            sys.exit(0 if success else 1)
            
        elif args.once:
            # Однократный запуск
            success = asyncio.run(run_once())
            sys.exit(0 if success else 1)
            
        elif args.status:
            # Показать статус
            show_status()
            
        elif args.config:
            # Показать конфигурацию
            logging.info("⚙️ Текущая конфигурация:")
            logging.info(f"📺 Каналы для мониторинга: {Config.SOURCE_CHANNELS}")
            logging.info(f"📤 Целевой канал: {Config.TARGET_CHANNEL}")
            logging.info(f"⏰ Интервал проверки: {Config.CHECK_INTERVAL_MINUTES} минут")
            logging.info(f"🗄️ База данных: {Config.DATABASE_PATH}")
            logging.info(f"📝 Лог файл: {Config.LOG_FILE}")
            
        elif args.daemon:
            # Режим демона
            run_daemon()
            
        else:
            # По умолчанию показываем помощь
            parser.print_help()
            
    except KeyboardInterrupt:
        logging.info("👋 Программа завершена пользователем")
    except Exception as e:
        logging.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
