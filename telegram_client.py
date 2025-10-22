import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from telethon import TelegramClient, events
from telethon.tl.types import Message, Channel
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import time

from config import Config
from database import DatabaseManager

class TelegramNewsClient:
    def __init__(self):
        self.client = None
        self.db = DatabaseManager(Config.DATABASE_PATH)
        self.is_running = False
        self.start_time = None  # Время запуска программы
        
        # Статистика
        self.stats = {
            'posts_processed': 0,
            'posts_forwarded': 0
        }
    
    async def initialize(self):
        """Инициализация Telegram клиента"""
        try:
            self.client = TelegramClient(
                'news_sniffer_session',
                Config.TELEGRAM_API_ID,
                Config.TELEGRAM_API_HASH
            )
            
            await self.client.start()
            
            # Проверяем авторизацию
            if not await self.client.is_user_authorized():
                logging.error("Пользователь не авторизован")
                return False
            
            me = await self.client.get_me()
            logging.info(f"Авторизован как: {me.first_name} {me.last_name or ''}")
            
            # Устанавливаем время запуска (только новые сообщения после этого времени)
            if self.start_time is None:
                from datetime import timezone
                self.start_time = datetime.now(timezone.utc)
                logging.info(f"Установлено время запуска: {self.start_time.strftime('%H:%M:%S %d.%m.%Y')}")
                logging.info("Будут обрабатываться только новые сообщения после запуска")
            
            # Добавляем каналы в базу данных
            for channel in Config.SOURCE_CHANNELS:
                self.db.add_channel(channel)
            
            return True
            
        except Exception as e:
            logging.error(f"Ошибка инициализации Telegram клиента: {e}")
            return False
    
    async def get_channel_messages(self, channel_username: str, limit: int = 50) -> List[Message]:
        """Получает сообщения из канала после времени запуска программы"""
        try:
            messages = []
            
            # Если время запуска не установлено, не получаем старые сообщения
            if self.start_time is None:
                logging.info(f"Время запуска не установлено, пропускаем получение сообщений из {channel_username}")
                return messages
            
            # Получаем последние сообщения и фильтруем по времени
            async for message in self.client.iter_messages(channel_username, limit=limit):
                # Проверяем, что сообщение после времени запуска
                if message.date and message.date > self.start_time:
                    if message.text and not message.text.startswith('/'):
                        messages.append(message)
                        logging.info(f"Найдено новое сообщение {message.id} от {message.date.strftime('%H:%M:%S %d.%m.%Y')}")
                elif message.date and message.date <= self.start_time:
                    # Если дошли до сообщений старше времени запуска, прекращаем поиск
                    break
            
            logging.info(f"Получено {len(messages)} новых сообщений из {channel_username} после {self.start_time.strftime('%H:%M:%S')}")
            return messages
            
        except FloodWaitError as e:
            logging.warning(f"Flood wait для {channel_username}: {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
            return []
        except Exception as e:
            logging.error(f"Ошибка получения сообщений из {channel_username}: {e}")
            return []
    
    async def forward_message(self, message: Message, channel_username: str) -> bool:
        """Пересылает сообщение в целевой канал без фильтрации"""
        try:
            # Пересылаем сообщение напрямую
            await self.client.forward_messages(
                Config.TARGET_CHANNEL,
                message,
                from_peer=channel_username
            )
            
            # Сохраняем в базу данных как переслано
            self.db.add_processed_post(
                channel_username, 
                message.id, 
                message.text or "[Медиа сообщение]", 
                message.date,
                summary="Переслано",
                is_published=True
            )
            
            self.stats['posts_processed'] += 1
            self.stats['posts_forwarded'] += 1
            logging.info(f"Сообщение {message.id} из {channel_username} успешно переслано")
            
            return True
            
        except Exception as e:
            logging.error(f"Ошибка пересылки сообщения {message.id}: {e}")
            return False
    
    async def send_message(self, message: str) -> bool:
        """Отправляет простое сообщение в целевой канал"""
        try:
            await self.client.send_message(
                Config.TARGET_CHANNEL,
                message,
                parse_mode='html'
            )
            logging.info("Сообщение успешно отправлено")
            return True
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    async def process_all_channels(self) -> Dict[str, int]:
        """Обрабатывает все каналы из конфигурации и пересылает все новые сообщения"""
        results = {
            'processed': 0,
            'forwarded': 0
        }
        
        for channel_username in Config.SOURCE_CHANNELS:
            try:
                logging.info(f"Проверяем канал: {channel_username}")
                
                messages = await self.get_channel_messages(channel_username)
                
                if not messages:
                    continue
                
                # Обновляем последний message_id
                if messages:
                    max_message_id = max(msg.id for msg in messages)
                    self.db.update_last_message_id(channel_username, max_message_id)
                
                # Пересылаем новые сообщения
                for message in messages:
                    if self.db.is_post_processed(channel_username, message.id):
                        continue
                    
                    if await self.forward_message(message, channel_username):
                        results['forwarded'] += 1
                        # Небольшая пауза между пересылками
                        await asyncio.sleep(1)
                
                results['processed'] += len(messages)
                
                # Небольшая пауза между каналами
                await asyncio.sleep(2)
                
            except Exception as e:
                logging.error(f"Ошибка обработки канала {channel_username}: {e}")
                continue
        
        # Обновляем статистику в базе данных
        self.db.update_statistics(
            self.stats['posts_processed'],
            self.stats['posts_forwarded'],
            0  # filtered = 0, так как мы не фильтруем
        )
        
        # Сбрасываем статистику
        self.stats = {'posts_processed': 0, 'posts_forwarded': 0}
        
        return results
    
    async def get_channel_info(self, channel_username: str) -> Optional[Dict]:
        """Получает информацию о канале"""
        try:
            entity = await self.client.get_entity(channel_username)
            if isinstance(entity, Channel):
                return {
                    'title': entity.title,
                    'username': entity.username,
                    'participants_count': entity.participants_count,
                    'id': entity.id
                }
        except Exception as e:
            logging.error(f"Ошибка получения информации о канале {channel_username}: {e}")
        
        return None
    
    async def test_connection(self) -> bool:
        """Тестирует соединение с Telegram"""
        try:
            me = await self.client.get_me()
            logging.info(f"Соединение активно. Пользователь: {me.first_name}")
            return True
        except Exception as e:
            logging.error(f"Ошибка соединения: {e}")
            return False
    
    async def close(self):
        """Закрывает соединение"""
        if self.client:
            await self.client.disconnect()
            logging.info("Telegram клиент отключен")
