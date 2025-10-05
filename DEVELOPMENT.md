# Руководство по разработке

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.11+
- Node.js 20 LTS
- Docker & Docker Compose
- Git

### Установка и запуск

1. **Клонируйте репозиторий:**
```bash
git clone <repository-url>
cd short-news
```

2. **Запустите инфраструктуру:**
```bash
docker-compose up -d postgres redis
```

3. **Настройте backend:**
```bash
cd backend

# Установите Poetry (если не установлен)
curl -sSL https://install.python-poetry.org | python3 -

# Установите зависимости
poetry install

# Скопируйте файл окружения
cp env.example .env

# Создайте миграции
poetry run alembic revision --autogenerate -m "Initial migration"

# Примените миграции
poetry run alembic upgrade head

# Запустите сервер
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. **Настройте frontend:**
```bash
cd frontend

# Установите зависимости
npm install

# Запустите dev сервер
npm run dev
```

5. **Проверьте работу:**
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Database: localhost:5432

## 🧪 Тестирование

### Backend тесты
```bash
cd backend
poetry run pytest
```

### Frontend тесты
```bash
cd frontend
npm test
```

### E2E тесты
```bash
npm run test:e2e
```

## 📊 Мониторинг

### Логи
```bash
# Backend логи
docker-compose logs -f backend

# Database логи
docker-compose logs -f postgres

# Redis логи
docker-compose logs -f redis
```

### Запуск scrapers
```bash
# Запуск всех scrapers
curl -X POST http://localhost:8000/api/v1/admin/scrapers/run-all

# Запуск конкретного scraper
curl -X POST http://localhost:8000/api/v1/admin/scrapers/openai_blog/run

# Статус scrapers
curl http://localhost:8000/api/v1/admin/scrapers
```

## 🗄️ База данных

### Миграции
```bash
# Создать новую миграцию
poetry run alembic revision --autogenerate -m "Description"

# Применить миграции
poetry run alembic upgrade head

# Откат миграции
poetry run alembic downgrade -1
```

### Подключение к БД
```bash
# Через Docker
docker-compose exec postgres psql -U shot_news -d shot_news

# Или через psql
psql postgresql://shot_news:shot_news_dev@localhost:5432/shot_news
```

## 🔧 Разработка

### Структура проекта
```
short-news/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core functionality
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   ├── scrapers/       # Web scrapers
│   │   └── utils/          # Utilities
│   ├── alembic/            # Database migrations
│   └── tests/              # Backend tests
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API services
│   │   ├── store/          # State management
│   │   └── utils/          # Utilities
│   └── tests/              # Frontend tests
└── docs/                   # Documentation
```

### Добавление нового scraper

1. Создайте класс в `backend/app/scrapers/`
2. Наследуйтесь от `BaseScraper`
3. Реализуйте метод `scrape()`
4. Добавьте в `ScrapingService`

```python
# backend/app/scrapers/new_scraper.py
from .base import BaseScraper

class NewScraper(BaseScraper):
    def __init__(self):
        super().__init__("new_source", "https://example.com")
    
    async def scrape(self):
        # Implementation
        pass
```

### Добавление нового API endpoint

1. Создайте endpoint в `backend/app/api/v1/endpoints/`
2. Добавьте в `backend/app/api/v1/api.py`
3. Создайте сервис в `backend/app/services/` если нужно

### Добавление нового React компонента

1. Создайте компонент в `frontend/src/components/`
2. Добавьте типы в `frontend/src/types/`
3. Создайте сервис в `frontend/src/services/` если нужно

## 🐛 Отладка

### Backend
```bash
# Запуск с отладкой
poetry run uvicorn main:app --reload --log-level debug

# Проверка синтаксиса
poetry run ruff check .

# Форматирование кода
poetry run black .
```

### Frontend
```bash
# Проверка типов
npm run type-check

# Линтинг
npm run lint

# Форматирование
npm run format
```

## 📦 Production

### Сборка
```bash
# Backend
cd backend
poetry build

# Frontend
cd frontend
npm run build
```

### Docker
```bash
# Сборка всех образов
docker-compose build

# Запуск в production
docker-compose -f docker-compose.prod.yml up -d
```

## 🔐 Безопасность

### Переменные окружения
- Никогда не коммитьте `.env` файлы
- Используйте `env.example` как шаблон
- В production используйте секретные менеджеры

### API ключи
- Храните API ключи в переменных окружения
- Используйте разные ключи для dev/prod
- Регулярно ротируйте ключи

## 📚 Полезные команды

### Docker
```bash
# Пересоздать контейнеры
docker-compose down && docker-compose up -d

# Очистить volumes
docker-compose down -v

# Просмотр логов
docker-compose logs -f [service]
```

### Git
```bash
# Создать feature branch
git checkout -b feature/new-feature

# Синхронизация с main
git checkout main && git pull && git checkout feature/new-feature && git rebase main
```

### База данных
```bash
# Сброс базы данных
docker-compose down -v
docker-compose up -d postgres
poetry run alembic upgrade head

# Создание бэкапа
docker-compose exec postgres pg_dump -U shot_news shot_news > backup.sql
```

## 🤝 Contributing

1. Создайте issue для новой функции
2. Создайте feature branch
3. Сделайте изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📞 Поддержка

- GitHub Issues для багов и предложений
- Discord для обсуждений
- Email для критических проблем

---

**Удачной разработки! 🚀**
