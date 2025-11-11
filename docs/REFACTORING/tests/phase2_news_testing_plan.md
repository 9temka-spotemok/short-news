# Phase 2 — News Domain Testing Plan

Дата: 2025-11-10  
Подготовил: GPT-5 Codex

---

## Цели
- Зафиксировать стратегию тестирования после рефакторинга news-домена.
- Обеспечить покрытие критичных сценариев (репозитории, фасад, API, Celery).
- Подготовить чек-лист для выполнения задачи `task-12`.

## 1. Области тестирования
| Область | Что покрываем | Типы тестов |
|---------|---------------|-------------|
| **Репозитории (`news_repository.py`, `company_repository.py`)** | выборки, статистика, recent fetch | unit (SQLite in-memory) |
| **Query/Ingestion Service** | оркестрация, валидация, делегирование | unit |
| **NewsFacade** | публичные методы (list/search/get/statistics/CRUD) | unit/integration |
| **API `/api/v1/news`** | все эндпоинты (GET/POST/PUT/DELETE) | integration (TestClient) |
| **Celery scraping** | `scrape_ai_blogs` → facade ingestion | integration (eager mode) |

## 2. Инструменты и окружение
- **Pytest** + `pytest-asyncio`.
- Фикстуры для `AsyncSessionLocal` (in-memory SQLite).
- Включить `celery.conf.task_always_eager = True` в тестах для задач.
- Для API — `httpx.AsyncClient` или `TestClient` (FastAPI).

## 3. План тестов
### 3.1 Unit tests
- `tests/unit/domains/news/test_news_repository.py`
  - `fetch_by_url`, `fetch_by_id(include_relations)`, `list_news` (фильтры), `count_news`, `fetch_recent`, `aggregate_statistics`, `category_statistics`.
- `tests/unit/domains/news/test_company_repository.py`
  - `fetch_by_name` сценарии (точные/частичные названия).
- `tests/unit/domains/news/test_query_service.py`
  - Мокаем репозитории, проверяем делегирование и сбор результатов.
- `tests/unit/domains/news/test_ingestion_service.py`
  - Валидация (`NewsCreateSchema`), создание дубликатов, ошибки в плане компании.

### 3.2 Integration tests
- `tests/integration/api/test_news_endpoints.py`
  - `/api/v1/news` (фильтры), `/search`, `/stats`, `/stats/by-companies`, `/category/{name}`.
  - CRUD: `POST /news/`, `PUT /news/{id}`, `DELETE /news/{id}`.
  - Позитивные кейсы + ошибки (400/404/500).
- `tests/integration/tasks/test_scraping_task.py`
  - Используем `celery_app.task_always_eager = True`.
  - Подменяем `UniversalBlogScraper` (фейковые данные) → проверяем, что `NewsFacade.create_news` вызывается и новости появляются в БД.
- `tests/integration/tasks/test_nlp_tasks.py`
  - Мокаем `HeuristicNLPProvider`, запускаем Celery-таски `classify_news`, `summarise_news`, `extract_keywords`.  
  - Проверяем обновление `topic/sentiment/summary/keywords` через фасад и `run_in_loop`.

## 4. Подготовка фикстур
- Общий модуль `tests/conftest.py`:
  - ✅ `async_session()` — in-memory БД, миграция минимальных таблиц.
  - ✅ `news_facade(async_session)` — создаёт фасад.
  - ✅ `setup_app_client(async_session)` — FastAPI приложение с зависимостью `get_news_facade`.
  - Моки для external-сервисов (scrapers) через monkeypatch.

## 5. Checklist выполнения `task-12`
1. [x] Создать структуру каталогов `tests/unit/domains/news/`, `tests/integration/api/`.
2. [x] Написать unit-тесты для news/company репозиториев.
3. [x] Добавить unit-тесты для `NewsQueryService`, `NewsIngestionService`.
4. [x] Написать интеграционные тесты для API `/api/v1/news` (`tests/integration/api/test_news_endpoints.py`).
5. [x] Покрыть Celery scraping (eager) и убедиться, что используется фасад (`tests/integration/tasks/test_scraping_task.py`).
6. [x] Добавить интеграционные тесты для NLP задач (`tests/integration/tasks/test_nlp_tasks.py`, `run_in_loop` адаптер).
7. [ ] Обновить CI (добавить запуск новых тестов).
8. [ ] Обновить документацию (`phase2_news_refactor_plan.md`) и README (раздел “Тестирование”).

## 6. Риски
- Отсутствие реальных миграций для in-memory БД (нужны фикстуры для создания таблиц).
- Потенциальные race conditions в Celery тестах — использовать eager режим.
- Обновление зависимостей FastAPI/TestClient при адаптации API.

---

**Ответственный:** Backend QA / Engineers  
**Статус:** draft (10 Nov 2025)

