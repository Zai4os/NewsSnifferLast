# 📤 Загрузка проекта на GitHub

## ✅ Что уже сделано:
- ✅ Git репозиторий инициализирован
- ✅ Все файлы добавлены в коммит
- ✅ Создан первый коммит
- ✅ Docker файлы удалены (вы развернете сами на сервере)

## 🚀 Шаги для загрузки на GitHub:

### 1. Создайте новый репозиторий на GitHub

Перейдите на https://github.com/new и создайте новый репозиторий:
- **Название:** `NewsSnifferLast` (или любое другое)
- **Описание:** `Telegram News Forwarder - автоматическая пересылка новостей`
- **Приватность:** Выберите Public или Private
- ⚠️ **НЕ создавайте** README, .gitignore или LICENSE (они уже есть)

### 2. Подключите локальный репозиторий к GitHub

После создания репозитория GitHub покажет команды. Выполните их:

```bash
cd /home/tux/Documents/NewsSnifferLast-master

# Добавьте удаленный репозиторий (замените YOUR_USERNAME на ваш логин)
git remote add origin https://github.com/YOUR_USERNAME/NewsSnifferLast.git

# Переименуйте ветку в main (если хотите)
git branch -M main

# Загрузите код на GitHub
git push -u origin main
```

### 3. Альтернативный способ (с SSH ключом)

Если у вас настроен SSH ключ:

```bash
git remote add origin git@github.com:YOUR_USERNAME/NewsSnifferLast.git
git branch -M main
git push -u origin main
```

## 🔐 Важно о безопасности:

### Файл `.env` НЕ будет загружен на GitHub! ✅

Файл `.gitignore` уже настроен и исключает:
- ✅ `.env` - ваши секретные ключи
- ✅ `*.db` - базу данных
- ✅ `*.session` - сессии Telegram
- ✅ `*.log` - логи

### Что БУДЕТ на GitHub:
- ✅ Исходный код программы
- ✅ `.env.example` - шаблон для настройки
- ✅ `README.md` - документация
- ✅ `requirements.txt` - зависимости

## 📥 Клонирование на сервер

После загрузки на GitHub, на сервере выполните:

```bash
# Клонируйте репозиторий
git clone https://github.com/YOUR_USERNAME/NewsSnifferLast.git
cd NewsSnifferLast

# Создайте .env файл
cp .env.example .env
nano .env  # Заполните ваши данные

# Установите зависимости
pip3 install -r requirements.txt

# Запустите
python3 main.py --daemon
```

## 🔄 Обновление кода на сервере

Когда вы обновите код на GitHub:

```bash
cd NewsSnifferLast
git pull origin main
python3 main.py --daemon  # Перезапустите
```

## 📊 Проверка статуса Git

```bash
# Проверить статус
git status

# Посмотреть историю коммитов
git log --oneline

# Проверить удаленные репозитории
git remote -v
```

## 🎉 Готово!

После выполнения этих шагов ваш проект будет на GitHub и вы сможете:
- 📥 Клонировать его на любой сервер
- 🔄 Обновлять код через `git pull`
- 🔐 Хранить код безопасно (без секретных данных)
- 👥 Делиться проектом (если репозиторий публичный)
