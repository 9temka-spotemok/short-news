# Phase 1 — Endpoint Catalog Template

Назначение: зафиксировать связь между backend эндпоинтами и клиентскими вызовами, контролировать контракты и покрытие.

---

## 1. Общая информация
- **Дата:** _YYYY-MM-DD_
- **Составители:** _Backend Lead, Frontend Lead_
- **Источник схемы:** `openapi.json` (commit: _hash_)

## 2. Легенда
- **Scope:** требуется ли авторизация (auth / public / admin и т.д.)
- **Client Usage:** где используется на фронтенде (файл + функция/хук)
- **Tests:** наличие тестов (unit / integration / e2e)
- **Notes:** TODO, технический долг, расхождения в типах

## 3. Каталог (примерная структура)

### API v1

| Endpoint | Method | Scope | Client Usage | Tests | Notes |
|----------|--------|-------|--------------|-------|-------|
| `/api/v1/news/` | GET | auth | `ApiService.getNews` | `tests/test_news.py` |  |
| `/api/v1/companies/scan` | POST | auth | `ApiService.scanCompany` | `tests/test_companies.py` |  |
| ... | ... | ... | ... | ... | ... |

### API v2

| Endpoint | Method | Scope | Client Usage | Tests | Notes |
|----------|--------|-------|--------------|-------|-------|
| `/api/v2/analytics/companies/{id}/impact/latest` | GET | auth | `ApiService.getImpactSnapshot` | `tests/test_analytics_v2.py` |  |
| `/api/v2/analytics/export` | POST | auth | `ApiService.exportAnalysis` | Playwright `analytics.spec.ts` |  |
| ... | ... | ... | ... | ... | ... |

### Webhooks / Callbacks / WebSocket (если есть)

| Endpoint | Тип | Scope | Client/Integrations | Tests | Notes |
|----------|-----|-------|----------------------|-------|-------|
| `/api/v1/telegram/webhook` | POST | public | Telegram | `tests/test_telegram_bot.py` |  |

### Внутренние сервисы / Cron

| Task / Endpoint | Описание | Клиентский вызов | Tests | Notes |
|-----------------|----------|------------------|-------|-------|
| `celery.tasks.analytics.recompute_all_analytics` | Периодический пересчёт | UI кнопка Recompute | `tests/test_analytics_v2.py` |  |

## 4. Обнаруженные пробелы
- _Список эндпоинтов без клиентов_
- _Клиенты, обращающиеся к отсутствующим эндпоинтам_
- _Не задокументированные ручки_

## 5. Рекомендации / Следующие шаги
- _Например: добавить контрактный тест / обновить типы / вынести Feature Flag_

---

**Утверждено:** _Имена лидов, дата_



