# Инструкция по настройке и запуску проекта AI Competitor Insight Hub

**Дата:** 7 октября 2025  
**Версия:** 0.1.0

---

## 📋 Предварительные требования

### Обязательное ПО
- [Docker Desktop](https://www.docker.com/products/docker-desktop) - для Windows/Mac
- [Git](https://git-scm.com/downloads) - система контроля версий
- [Python 3.11+](https://www.python.org/downloads/) - для разработки backend
- [Node.js 20 LTS](https://nodejs.org/) - для разработки frontend

### Опциональные инструменты
- [VS Code](https://code.visualstudio.com/) - рекомендуемый редактор
- [Postman](https://www.postman.com/downloads/) - для тестирования API
- [PostgreSQL Client](https://www.postgresql.org/download/) - для работы с БД

---

## 🚀 Быстрый старт (Docker)

### 1. Клонирование репозитория
```bash
git clone <repository-url>
cd short-news
```

### 2. Запуск Docker Desktop
**Windows:**
- Запустите Docker Desktop из меню Пуск
- Дождитесь, пока Docker полностью запустится (значок в трее будет зеленым)

**Mac:**
- Запустите Docker Desktop из Applications
- Убедитесь, что Docker запущен (значок кита в строке меню)

### 3. Запуск всех сервисов
```bash
docker-compose up -d
```

Это запустит:
- ✅ PostgreSQL (порт 5432)
- ✅ Redis (порт 6379)
- ✅ Backend API (порт 8000)
- ✅ Frontend (порт 5173)
- ✅ Celery Worker
- ✅ Celery Beat

### 4. Проверка статуса
```bash
# Посмотреть логи всех сервисов
docker-compose logs -f

# Проверить работу API
curl http://localhost:8000/health

# Проверить frontend
# Откройте в браузере: http://localhost:5173
```

### 5. Инициализация базы данных
```bash
# Применить миграции
docker-compose exec backend alembic upgrade head

# Создать тестового пользователя (опционально)
docker-compose exec backend python -c "from app.tasks.seed_competitors import seed_data; seed_data()"
```

---

## 🛠️ Разработка (без Docker)

### Backend

#### 1. Установка зависимостей
```bash
cd backend

# С использованием Poetry (рекомендуется)
poetry install

# Или с использованием pip
pip install -r requirements.txt
```

#### 2. Настройка переменных окружения
Файл `.env` уже создан с настройками по умолчанию. Для работы необходимо:

```bash
# Обязательно установить SECRET_KEY в production
SECRET_KEY=your-secret-key-here

# Опционально (для полной функциональности):
OPENAI_API_KEY=sk-...  # Для классификации новостей
GITHUB_TOKEN=ghp_...   # Для GitHub scraping
```

#### 3. Запуск PostgreSQL и Redis
```bash
# Только PostgreSQL и Redis
docker-compose up -d postgres redis
```

#### 4. Применение миграций
```bash
# С Poetry
poetry run alembic upgrade head

# С pip
alembic upgrade head
```

#### 5. Запуск backend сервера
```bash
# С Poetry
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# С pip
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступно на: http://localhost:8000
Документация: http://localhost:8000/docs

#### 6. Запуск Celery (опционально)
```bash
# В отдельном терминале - Worker
poetry run celery -A celery_app worker --loglevel=info

# В отдельном терминале - Beat (планировщик)
poetry run celery -A celery_app beat --loglevel=info
```

### Frontend

#### 1. Установка зависимостей
```bash
cd frontend
npm install
```

#### 2. Настройка переменных окружения
Файл `.env` уже создан со значениями по умолчанию:
```env
VITE_API_URL=http://localhost:8000
```

#### 3. Запуск dev сервера
```bash
npm run dev
```

Frontend будет доступен на: http://localhost:5173

#### 4. Сборка для production
```bash
npm run build
npm run preview  # Предпросмотр production сборки
```

---

## 📦 Структура проекта

```
short-news/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Конфигурация, БД
│   │   ├── models/         # SQLAlchemy модели
│   │   ├── scrapers/       # Web scrapers
│   │   ├── services/       # Бизнес-логика
│   │   └── tasks/          # Celery tasks
│   ├── alembic/            # Миграции БД
│   ├── .env               # ✅ Переменные окружения
│   ├── requirements.txt    # Python зависимости
│   ├── pyproject.toml      # Poetry конфигурация
│   └── main.py            # Точка входа
│
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React компоненты
│   │   ├── pages/          # Страницы приложения
│   │   ├── services/       # API клиенты
│   │   ├── store/          # Zustand store
│   │   └── types/          # TypeScript типы
│   ├── .env               # ✅ Переменные окружения
│   ├── package.json        # npm зависимости
│   └── vite.config.ts      # Vite конфигурация
│
├── docs/                   # Документация
│   └── competitor-analysis.md  # ✅ Анализ 123 конкурентов
│
├── docker-compose.yml      # Docker orchestration
├── README.md              # Основная документация
└── SETUP.md              # ✅ Эта инструкция
```

---

## 🔧 Конфигурация

### Backend Environment Variables

| Переменная | Описание | Обязательна | Значение по умолчанию |
|-----------|----------|-------------|---------------------|
| `SECRET_KEY` | Ключ для JWT токенов | ✅ Да | dev-secret-key... |
| `DATABASE_URL` | URL PostgreSQL | ✅ Да | postgresql+asyncpg://... |
| `REDIS_URL` | URL Redis | ✅ Да | redis://localhost:6379 |
| `OPENAI_API_KEY` | OpenAI API ключ | ❌ Нет | - |
| `GITHUB_TOKEN` | GitHub API токен | ❌ Нет | - |
| `TWITTER_API_KEY` | Twitter API ключ | ❌ Нет | - |
| `REDDIT_CLIENT_ID` | Reddit API ID | ❌ Нет | - |
| `SENDGRID_API_KEY` | SendGrid для email | ❌ Нет | - |

### Frontend Environment Variables

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|---------------------|
| `VITE_API_URL` | URL backend API | http://localhost:8000 |
| `VITE_APP_NAME` | Название приложения | AI Competitor Insight Hub |

---

## 🧪 Тестирование

### Backend Tests
```bash
cd backend

# Запуск всех тестов
poetry run pytest

# С покрытием кода
poetry run pytest --cov=app --cov-report=html

# Только быстрые тесты (без integration)
poetry run pytest -m "not slow"
```

### Frontend Tests
```bash
cd frontend

# Запуск тестов
npm test

# С UI (интерактивно)
npm run test:ui

# С покрытием кода
npm run test:coverage
```

---

## 📊 Доступные API Endpoints

### Health & Info
- `GET /health` - Проверка здоровья сервиса
- `GET /` - Информация о API
- `GET /docs` - Swagger UI (только в dev)

### Authentication
- `POST /api/v1/auth/register` - Регистрация
- `POST /api/v1/auth/login` - Вход
- `POST /api/v1/auth/logout` - Выход
- `POST /api/v1/auth/refresh` - Обновление токена

### News
- `GET /api/v1/news` - Список новостей
- `GET /api/v1/news/{id}` - Детали новости
- `GET /api/v1/news/search` - Поиск новостей

### Users
- `GET /api/v1/users/me` - Текущий пользователь
- `PUT /api/v1/users/me` - Обновить профиль
- `GET /api/v1/users/preferences` - Настройки

### Admin (Scraping)
- `POST /api/v1/admin/scraping/start` - Запустить scraping
- `GET /api/v1/admin/scraping/status` - Статус scraping

---

## 🐛 Устранение неполадок

### Docker не запускается
**Проблема:** `error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.47/containers/json"`

**Решение:**
1. Запустите Docker Desktop
2. Дождитесь полной инициализации (зеленый значок)
3. Проверьте: `docker ps`

### Backend не подключается к PostgreSQL
**Проблема:** `could not connect to server`

**Решение:**
1. Убедитесь, что PostgreSQL запущен: `docker-compose ps`
2. Проверьте DATABASE_URL в .env
3. Проверьте логи: `docker-compose logs postgres`

### Frontend не видит backend API
**Проблема:** `Network Error` или CORS

**Решение:**
1. Проверьте `VITE_API_URL` в frontend/.env
2. Убедитесь, что backend запущен: `curl http://localhost:8000/health`
3. Проверьте CORS настройки в backend/app/core/config.py

### Celery tasks не выполняются
**Проблема:** Tasks висят в PENDING

**Решение:**
1. Убедитесь, что Redis запущен: `docker-compose ps redis`
2. Проверьте Celery worker: `docker-compose logs celery-worker`
3. Проверьте CELERY_BROKER_URL в .env

### Миграции не применяются
**Проблема:** `alembic upgrade head` fails

**Решение:**
```bash
# Проверить текущую версию
alembic current

# Посмотреть историю
alembic history

# Откатить и применить заново
alembic downgrade -1
alembic upgrade head
```

---

## 📝 Полезные команды

### Docker
```bash
# Запустить все сервисы
docker-compose up -d

# Остановить все сервисы
docker-compose down

# Посмотреть логи
docker-compose logs -f [service_name]

# Пересобрать образы
docker-compose build --no-cache

# Очистить volumes (⚠️ удалит данные БД)
docker-compose down -v
```

### Миграции
```bash
# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1
```

### Linting & Formatting
```bash
# Backend
cd backend
poetry run black app/
poetry run ruff check app/
poetry run mypy app/

# Frontend
cd frontend
npm run lint
npm run lint:fix
npm run format
```

---

## 🌐 URLs после запуска

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs
- **API Docs (ReDoc):** http://localhost:8000/redoc
- **PostgreSQL:** localhost:5432 (username: shot_news, password: shot_news_dev)
- **Redis:** localhost:6379

---

## 📈 Следующие шаги

### MVP Features (To-Do)
- [ ] Реализовать полноценную аутентификацию (JWT)
- [ ] Добавить scrapers для всех 20+ источников
- [ ] Интегрировать OpenAI для классификации новостей
- [ ] Реализовать email digest генерацию
- [ ] Добавить тесты (coverage > 80%)
- [ ] Настроить CI/CD (GitHub Actions)

### Опциональные API ключи
Для полной функциональности рекомендуется настроить:

1. **OpenAI API** - для классификации новостей
   - Получить: https://platform.openai.com/api-keys
   - Добавить в `backend/.env`: `OPENAI_API_KEY=sk-...`

2. **GitHub Token** - для GitHub scraping
   - Получить: https://github.com/settings/tokens
   - Добавить в `backend/.env`: `GITHUB_TOKEN=ghp_...`

3. **Twitter API** - для Twitter scraping
   - Получить: https://developer.twitter.com/
   - Добавить credentials в `backend/.env`

---

## 💡 Дополнительные ресурсы

### Документация
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryq.dev/)

### Анализ конкурентов
- [docs/competitor-analysis.md](docs/competitor-analysis.md) - Детальный анализ 123 конкурентов

### Поддержка
- GitHub Issues: [создать issue]
- Email: team@shot-news.com

---

**Последнее обновление:** 7 октября 2025  
**Автор:** AI Competitor Insight Hub Team

