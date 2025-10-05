# AI Competitor Insight Hub (shot-news)

**Версия:** 0.1.0  
**Статус:** В разработке  

Интеллектуальная платформа для мониторинга новостей из мира ИИ-индустрии с персонализированными дайджестами.

## 🚀 Быстрый старт

### Предварительные требования
- Python 3.11+
- Node.js 20 LTS
- Docker & Docker Compose
- Git

### Установка

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
poetry install
poetry run alembic upgrade head
poetry run uvicorn main:app --reload
```

4. **Настройте frontend:**
```bash
cd frontend
npm install
npm run dev
```

## 🏗️ Архитектура

```
shot-news/
├── backend/           # FastAPI backend
├── frontend/          # React frontend
├── docs/             # Документация
├── docker-compose.yml # Инфраструктура
└── README.md
```

## 📋 Функциональность

### MVP (v0.1.0)
- [x] Структура проекта
- [ ] Агрегация данных из 20+ источников
- [ ] Классификация новостей (OpenAI API)
- [ ] Персонализированные дайджесты
- [ ] Веб-интерфейс
- [ ] Система аутентификации

### Roadmap
- [ ] Telegram-бот
- [ ] Аналитический модуль
- [ ] API для интеграций

## 🔧 Технологический стек

**Backend:**
- FastAPI 0.115.0
- PostgreSQL 16.0
- Redis 7.4.0
- Celery 5.4.0
- SQLAlchemy 2.0

**Frontend:**
- React 18.3.0
- TypeScript 5.6.0
- Tailwind CSS 3.4.0
- TanStack Query 5.56.0

## 📊 Источники данных

- OpenAI Blog
- Anthropic News
- Google AI Blog
- Meta AI Blog
- Twitter/X API
- GitHub API
- Reddit API

## 🧪 Тестирование

```bash
# Backend tests
cd backend && poetry run pytest

# Frontend tests
cd frontend && npm test

# E2E tests
npm run test:e2e
```

## 📈 Производительность

- Время загрузки страницы: < 2 сек
- API response time: < 500 мс
- Uptime: 99.5%

## 🔐 Безопасность

- HTTPS only
- JWT authentication
- Rate limiting
- GDPR compliance

## 📝 Лицензия

MIT License

## 🤝 Контрибьюция

1. Fork репозиторий
2. Создайте feature branch
3. Commit изменения
4. Push в branch
5. Создайте Pull Request

## 📞 Поддержка

- GitHub Issues
- Email: support@shot-news.com

---

**Статус разработки:** 🟡 В активной разработке  
**Следующий релиз:** v0.1.0 (Q1 2025)
