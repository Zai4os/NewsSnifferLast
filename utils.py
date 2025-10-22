#!/usr/bin/env python3
"""
Утилиты для управления NewsSniffer
"""

import sqlite3
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse
import sys

from config import Config
from database import DatabaseManager

class NewsSnifferUtils:
    def __init__(self):
        self.db = DatabaseManager(Config.DATABASE_PATH)
    
    def export_statistics(self, days: int = 30, format: str = 'json') -> str:
        """Экспортирует статистику в JSON или CSV"""
        stats = self.db.get_statistics(days)
        
        if format.lower() == 'json':
            return self._export_to_json(stats)
        elif format.lower() == 'csv':
            return self._export_to_csv(stats)
        else:
            raise ValueError("Поддерживаются форматы: json, csv")
    
    def _export_to_json(self, stats: List) -> str:
        """Экспорт в JSON"""
        data = []
        for row in stats:
            data.append({
                'date': row[0],
                'posts_processed': row[1],
                'posts_published': row[2],
                'posts_filtered': row[3]
            })
        
        filename = f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filename
    
    def _export_to_csv(self, stats: List) -> str:
        """Экспорт в CSV"""
        filename = f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Дата', 'Обработано', 'Опубликовано', 'Отфильтровано'])
            writer.writerows(stats)
        
        return filename
    
    def cleanup_old_posts(self, days: int = 30) -> int:
        """Удаляет старые посты из базы данных"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM processed_posts 
                    WHERE processed_date < datetime('now', '-{} days')
                '''.format(days))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                print(f"✅ Удалено {deleted_count} старых записей (старше {days} дней)")
                return deleted_count
                
        except sqlite3.Error as e:
            print(f"❌ Ошибка очистки базы данных: {e}")
            return 0
    
    def get_channel_statistics(self) -> Dict[str, Dict]:
        """Получает статистику по каналам"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # Статистика по каналам
                cursor.execute('''
                    SELECT 
                        channel_username,
                        COUNT(*) as total_posts,
                        SUM(CASE WHEN is_published = 1 THEN 1 ELSE 0 END) as published_posts,
                        MAX(processed_date) as last_processed
                    FROM processed_posts 
                    GROUP BY channel_username
                    ORDER BY total_posts DESC
                ''')
                
                results = cursor.fetchall()
                
                stats = {}
                for row in results:
                    channel, total, published, last_processed = row
                    stats[channel] = {
                        'total_posts': total,
                        'published_posts': published,
                        'filtered_posts': total - published,
                        'last_processed': last_processed,
                        'publish_rate': round((published / total) * 100, 1) if total > 0 else 0
                    }
                
                return stats
                
        except sqlite3.Error as e:
            print(f"❌ Ошибка получения статистики каналов: {e}")
            return {}
    
    def reset_channel(self, channel_username: str) -> bool:
        """Сбрасывает статистику канала (удаляет все обработанные посты)"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # Удаляем обработанные посты
                cursor.execute(
                    "DELETE FROM processed_posts WHERE channel_username = ?",
                    (channel_username,)
                )
                
                # Сбрасываем last_message_id
                cursor.execute(
                    "UPDATE channel_settings SET last_message_id = 0 WHERE channel_username = ?",
                    (channel_username,)
                )
                
                conn.commit()
                
                print(f"✅ Канал {channel_username} сброшен")
                return True
                
        except sqlite3.Error as e:
            print(f"❌ Ошибка сброса канала: {e}")
            return False
    
    def add_channel(self, channel_username: str) -> bool:
        """Добавляет новый канал для мониторинга"""
        if not channel_username.startswith('@'):
            channel_username = '@' + channel_username
        
        try:
            self.db.add_channel(channel_username)
            print(f"✅ Канал {channel_username} добавлен")
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления канала: {e}")
            return False
    
    def remove_channel(self, channel_username: str) -> bool:
        """Удаляет канал из мониторинга"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                # Деактивируем канал
                cursor.execute(
                    "UPDATE channel_settings SET is_active = 0 WHERE channel_username = ?",
                    (channel_username,)
                )
                
                conn.commit()
                
                print(f"✅ Канал {channel_username} деактивирован")
                return True
                
        except sqlite3.Error as e:
            print(f"❌ Ошибка удаления канала: {e}")
            return False
    
    def list_channels(self) -> List[Dict]:
        """Список всех каналов"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        cs.channel_username,
                        cs.last_message_id,
                        cs.is_active,
                        cs.added_date,
                        COUNT(pp.id) as posts_count
                    FROM channel_settings cs
                    LEFT JOIN processed_posts pp ON cs.channel_username = pp.channel_username
                    GROUP BY cs.channel_username
                    ORDER BY cs.added_date DESC
                ''')
                
                results = cursor.fetchall()
                
                channels = []
                for row in results:
                    username, last_msg_id, is_active, added_date, posts_count = row
                    channels.append({
                        'username': username,
                        'last_message_id': last_msg_id,
                        'is_active': bool(is_active),
                        'added_date': added_date,
                        'posts_count': posts_count
                    })
                
                return channels
                
        except sqlite3.Error as e:
            print(f"❌ Ошибка получения списка каналов: {e}")
            return []
    
    def backup_database(self) -> str:
        """Создает резервную копию базы данных"""
        import shutil
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"news_sniffer_backup_{timestamp}.db"
        
        try:
            shutil.copy2(Config.DATABASE_PATH, backup_filename)
            print(f"✅ Резервная копия создана: {backup_filename}")
            return backup_filename
        except Exception as e:
            print(f"❌ Ошибка создания резервной копии: {e}")
            return ""
    
    def restore_database(self, backup_filename: str) -> bool:
        """Восстанавливает базу данных из резервной копии"""
        import shutil
        import os
        
        if not os.path.exists(backup_filename):
            print(f"❌ Файл резервной копии не найден: {backup_filename}")
            return False
        
        try:
            # Создаем резервную копию текущей БД
            current_backup = self.backup_database()
            
            # Восстанавливаем из резервной копии
            shutil.copy2(backup_filename, Config.DATABASE_PATH)
            
            print(f"✅ База данных восстановлена из {backup_filename}")
            print(f"📁 Текущая БД сохранена как {current_backup}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка восстановления базы данных: {e}")
            return False
    
    def show_recent_posts(self, limit: int = 10) -> None:
        """Показывает последние обработанные посты"""
        try:
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        channel_username,
                        message_id,
                        LEFT(message_text, 100) as preview,
                        processed_date,
                        is_published
                    FROM processed_posts 
                    ORDER BY processed_date DESC 
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                
                if not results:
                    print("📭 Нет обработанных постов")
                    return
                
                print(f"📰 Последние {len(results)} обработанных постов:")
                print("-" * 80)
                
                for row in results:
                    channel, msg_id, preview, processed_date, is_published = row
                    status = "✅ Опубликован" if is_published else "🚫 Отфильтрован"
                    
                    print(f"📺 {channel} | ID: {msg_id} | {status}")
                    print(f"📅 {processed_date}")
                    print(f"📝 {preview}...")
                    print("-" * 80)
                    
        except sqlite3.Error as e:
            print(f"❌ Ошибка получения постов: {e}")

def main():
    """CLI интерфейс для утилит"""
    parser = argparse.ArgumentParser(description='NewsSniffer Utilities')
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Экспорт статистики
    export_parser = subparsers.add_parser('export', help='Экспорт статистики')
    export_parser.add_argument('--days', type=int, default=30, help='Количество дней')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Формат экспорта')
    
    # Очистка старых постов
    cleanup_parser = subparsers.add_parser('cleanup', help='Очистка старых постов')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Удалить посты старше N дней')
    
    # Статистика каналов
    subparsers.add_parser('channels', help='Статистика по каналам')
    
    # Управление каналами
    add_parser = subparsers.add_parser('add-channel', help='Добавить канал')
    add_parser.add_argument('channel', help='Username канала')
    
    remove_parser = subparsers.add_parser('remove-channel', help='Удалить канал')
    remove_parser.add_argument('channel', help='Username канала')
    
    reset_parser = subparsers.add_parser('reset-channel', help='Сбросить канал')
    reset_parser.add_argument('channel', help='Username канала')
    
    # Резервное копирование
    subparsers.add_parser('backup', help='Создать резервную копию БД')
    
    restore_parser = subparsers.add_parser('restore', help='Восстановить БД')
    restore_parser.add_argument('backup_file', help='Файл резервной копии')
    
    # Просмотр постов
    posts_parser = subparsers.add_parser('recent', help='Показать последние посты')
    posts_parser.add_argument('--limit', type=int, default=10, help='Количество постов')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    utils = NewsSnifferUtils()
    
    try:
        if args.command == 'export':
            filename = utils.export_statistics(args.days, args.format)
            print(f"✅ Статистика экспортирована в {filename}")
            
        elif args.command == 'cleanup':
            utils.cleanup_old_posts(args.days)
            
        elif args.command == 'channels':
            stats = utils.get_channel_statistics()
            if stats:
                print("📊 Статистика по каналам:")
                print("-" * 80)
                for channel, data in stats.items():
                    print(f"📺 {channel}")
                    print(f"   Всего постов: {data['total_posts']}")
                    print(f"   Опубликовано: {data['published_posts']}")
                    print(f"   Отфильтровано: {data['filtered_posts']}")
                    print(f"   Процент публикации: {data['publish_rate']}%")
                    print(f"   Последняя обработка: {data['last_processed']}")
                    print("-" * 80)
            else:
                print("📭 Нет данных по каналам")
                
        elif args.command == 'add-channel':
            utils.add_channel(args.channel)
            
        elif args.command == 'remove-channel':
            utils.remove_channel(args.channel)
            
        elif args.command == 'reset-channel':
            utils.reset_channel(args.channel)
            
        elif args.command == 'backup':
            utils.backup_database()
            
        elif args.command == 'restore':
            utils.restore_database(args.backup_file)
            
        elif args.command == 'recent':
            utils.show_recent_posts(args.limit)
            
    except Exception as e:
        print(f"❌ Ошибка выполнения команды: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
