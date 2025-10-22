#!/bin/bash

# 🚀 Простой установщик NewsSniffer
# Быстрая настройка агрегатора новостей

set -e

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Установка NewsSniffer${NC}"
echo "=========================="

# Проверка Python
echo -e "${BLUE}Проверка Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 не найден!${NC}"
    echo "Установите Python: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi
echo -e "${GREEN}✅ Python найден${NC}"

# Создание виртуального окружения
echo -e "${BLUE}Создание виртуального окружения...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Виртуальное окружение создано${NC}"
else
    echo -e "${YELLOW}⚠️  Виртуальное окружение уже существует${NC}"
fi

# Активация и установка зависимостей
echo -e "${BLUE}Установка зависимостей...${NC}"
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    echo -e "${GREEN}✅ Зависимости установлены${NC}"
else
    echo -e "${RED}❌ Файл requirements.txt не найден!${NC}"
    exit 1
fi

# Настройка конфигурации
echo -e "${BLUE}Настройка конфигурации...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✅ Создан файл .env${NC}"
    else
        echo -e "${RED}❌ Файл .env.example не найден!${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Файл .env уже существует${NC}"
fi

# Создание скриптов управления
echo -e "${BLUE}Создание скриптов...${NC}"

# Скрипт запуска
cat > run.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено. Запустите ./install.sh"
    exit 1
fi

source venv/bin/activate

echo "🔥 NewsSniffer - Управление"
echo "========================="
echo "1) Тест подключения"
echo "2) Запуск один раз"
echo "3) Запуск в фоне"
echo "4) Показать статус"
echo "5) Остановить"
echo ""

read -p "Выберите (1-5): " choice

case $choice in
    1) python3 main.py --test ;;
    2) python3 main.py --once ;;
    3) 
        echo "🚀 Запуск в фоновом режиме..."
        nohup python3 main.py --daemon > daemon.log 2>&1 &
        echo "✅ Запущено! Логи: tail -f daemon.log"
        ;;
    4) python3 main.py --status ;;
    5) 
        pkill -f "main.py --daemon"
        echo "🛑 Остановлено"
        ;;
    *) echo "❌ Неверный выбор" ;;
esac
EOF

chmod +x run.sh

echo -e "${GREEN}✅ Скрипт run.sh создан${NC}"

# Проверка файлов
echo -e "${BLUE}Проверка файлов проекта...${NC}"
MISSING_FILES=()

for file in "main.py" "config.py" "telegram_client.py"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ Все файлы найдены${NC}"
else
    echo -e "${RED}❌ Отсутствуют файлы: ${MISSING_FILES[*]}${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Установка завершена!${NC}"
echo ""
echo -e "${YELLOW}⚠️  ВАЖНО: Настройте конфигурацию!${NC}"
echo ""
echo "Следующие шаги:"
echo "1️⃣  Настройте .env файл:"
echo "   nano .env"
echo ""
echo "2️⃣  Получите Telegram данные:"
echo "   • API: https://my.telegram.org/apps"
echo "   • Bot: @BotFather в Telegram"
echo ""
echo "3️⃣  Запустите программу:"
echo "   ./run.sh"
echo ""
echo -e "${BLUE}📚 Документация: README.md${NC}"
