import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    """
    Конфигурация NewsSnifferLast
    Приложение работает в режиме простой пересылки (ретрансляции)
    Все новые сообщения пересылаются без фильтрации
    """
    # Telegram API настройки
    TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Канал для публикации
    TARGET_CHANNEL = os.getenv('TARGET_CHANNEL')  # @your_channel или chat_id
    
    # Список каналов для мониторинга
    SOURCE_CHANNELS = [
        '@the_club_100',
        '@zaichos11',
        '@underworld_dev',
        '@gift_newstg',
        '@just',
        '@AIKaleidoscope',
        '@cryptoattack24',
        '@tonmonitoring',
        '@giftnews',
        '@baoanri',
        '@TON_Cabal',
        '@China77',
        '@sticker_community',
        '@suterTV',
        '@roxtalk',
        '@PudgyPenguins',
        '@ScamSnifferAlert',
        '@peskarbrain',
        '@michaelgiftblog',
        '@getgems',
        '@toncoin',
        '@OfficialBAYC',
        '@luchathoughts',
        '@fuse_stickers',
        '@MyTonWalletRu',
        '@lunasundesign',
        '@lucanetztg',
        '@durov',
        '@azukihq',
        '@dogs',
        '@founder',
        '@officialopensea',
        '@tonwallet_news_cis',
        '@Gift_Alerts',
        '@limitedstickers',
        '@notcoin',
        '@not_base',
        '@whackdoor',
        '@DeCenter',
        '@telelakel',
        '@WatcherGuru',
        '@markettwits',
        '@aid_crypto',
        '@CryptSoap',
        # Добавьте свои каналы здесь
    ]
    
    # Настройки времени
    CHECK_INTERVAL_MINUTES = 1  # 1 минута
    
    # База данных
    DATABASE_PATH = 'news_sniffer.db'
    
    # Логирование
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'news_sniffer.log'
