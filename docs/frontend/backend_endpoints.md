# Backend API Endpoints for Frontend Integration

Актуально на 12 ноября 2025 года. Все маршруты используют префикс `https://<backend-host>/api`. Авторизационные эндпоинты отдают и принимают JWT-токены, остальные требуют заголовок `Authorization: Bearer <token>`.

## Аутентификация (`/v1/auth`)

| Method | Path | Body/Query | Response | Notes |
| --- | --- | --- | --- | --- |
| `POST` | `/v1/auth/login` | `{ "email", "password" }` | `{ "access_token", "token_type" }` | Стандартный логин, выдаёт JWT. |
| `POST` | `/v1/auth/refresh` | Header `Authorization: Bearer <refresh_token>` | Новый `access_token` | Используется для продления сессии. |

## Компании (`/v1/companies`)

| Method | Path | Параметры | Ответ | Notes |
| --- | --- | --- | --- | --- |
| `GET` | `/v1/companies` | `?search`, `?category`, пагинация `limit/offset` | `{ "items": [...], "total": <int> }` | Для автодополнений и списков. |
| `GET` | `/v1/companies/{company_id}` | – | Объект компании | Используется карточками и аналитикой. |

## Новости (`/v1/news`)

| Method | Path | Параметры | Ответ | Notes |
| --- | --- | --- | --- | --- |
| `GET` | `/v1/news` | `?company_id`, `?company_ids[]`, `?category`, `?source_type`, `?limit`, `?offset`, `?search` | `{ "items": [...], "total": <int> }` | Основная выборка новостей. |
| `GET` | `/v1/news/stats` | – | `{ "totals", "by_category", "by_source" }` | Глобальная статистика (дашборд). |
| `GET` | `/v1/news/stats/by-companies` | `?company_ids=uuid1,uuid2` | `{ "totals", "by_category", "by_source" }` | Статистика по конкретным компаниям. |
| `POST` | `/v1/news` | Новостной payload | Созданный объект | Backend-only (скрепперы/админка). |

## Аналитика (`/v2/analytics`)

| Method | Path | Тело/параметры | Ответ | Notes |
| --- | --- | --- | --- | --- |
| `POST` | `/v2/analytics/comparisons` | `ComparisonRequest` (subjects, период, фильтры) | `ComparisonResponse` | Главный источник данных страницы сравнения. |
| `GET` | `/v2/analytics/change-log` | `?company_id`, `?period`, пагинация `cursor/limit`, `?source_types[]` | `AnalyticsChangeLogResponse` | TanStack Query для ленты изменений (topics/sentiments/min_priority пока прокидываются на будущее). |
| `GET` | `/v2/analytics/graph` | `?company_id`, `?relationship`, `?limit` | `[KnowledgeGraphEdge]` | Блок knowledge graph. |
| `GET` | `/v2/analytics/companies/{company_id}/impact/latest` | `?period` | `CompanyAnalyticsSnapshot` | Виджет Impact. |
| `GET` | `/v2/analytics/companies/{company_id}/snapshots` | `?period`, `?limit` | `SnapshotSeriesResponse` | История показателей/трендов. |
| `POST` | `/v2/analytics/reports/presets` | `ReportPresetCreateRequest` | `ReportPreset` | Создание пользовательских пресетов. |
| `GET` | `/v2/analytics/reports/presets` | – | `[ReportPreset]` | Загрузка пресетов (export диалог). |
| `POST` | `/v2/analytics/export` | `AnalyticsExportRequest` | `AnalyticsExportResponse` | Payload для JSON/PDF/CSV экспорта. |
| `POST` | `/v2/analytics/companies/{company_id}/recompute` | `?period`, `?lookback` | `{ "status": "queued", "task_id": ... }` | Кнопка «Recompute» (Celery). |
| `POST` | `/v2/analytics/companies/{company_id}/graph/sync` | `?period`, `period_start` | `{ "status": "queued", "task_id": ... }` | Триггер синхронизации knowledge graph. |

> ⚠️ Тепловые карты активности пока используют наследованный `/v1/competitors/activity/{company_id}`; переход на v2 в планах.

## Конкуренты (`/v1/competitors`)

| Method | Path | Параметры | Ответ | Notes |
| --- | --- | --- | --- | --- |
| `GET` | `/v1/competitors/changes/{company_id}` | `?limit`, `?status` | `{ "events": [...], "total": <int> }` | Legacy-ручка (оставлена для обратной совместимости/админки). |
| `POST` | `/v1/competitors/changes/{event_id}/recompute` | – | Пересчитанное событие | Админ/диагностика. |
| `POST` | `/v1/competitors/compare` | JSON: `{ "company_ids": [...], ... }` | Подробный отчёт сравнения | Старый интерфейс сравнения (v1), поддержан адаптерами. |
| `GET` | `/v1/competitors/suggest/{company_id}` | `?limit`, `?days` | `{ "suggestions": [...] }` | Рекомендации конкурентов. |

## Настройки уведомлений и дайджестов (`/v1/users/preferences`)

| Method | Path | Тело/параметры | Ответ | Notes |
| --- | --- | --- | --- | --- |
| `GET` | `/v1/users/preferences` | – | Полные пользовательские настройки | Экран Notification Settings. |
| `PUT` | `/v1/users/preferences` | Изменённые настройки | Обновлённый объект | Сохранение подписок, частоты, ключевых слов. |
| `GET` | `/v1/users/preferences/digest` | – | Настройки дайджеста | Используется страницей Digest Settings. |
| `PUT` | `/v1/users/preferences/digest` | Payload | Обновлённые параметры дайджеста | Частота, формат, Telegram и т.д. |

> Старые ручки `/v1/notifications/settings` и `/v1/digest/preferences` остаются для обратной совместимости, но фронтенд их больше не вызывает.

## Дополнительные вызовы

- `GET /v1/competitors/activity/{company_id}` — источник тепловых карт активности (до миграции на v2).
- `POST /v1/competitors/themes` — тематический анализ для блока «Themes».
- `POST /v2/analytics/companies/{company_id}/recompute` и `/graph/sync` — триггеры Celery задач (уже перечислены выше, но критичны для UI).
- `GET /openapi.json` — используется для ручной синхронизации типизации (при необходимости генерации TS-моделей).

## Общие замечания

1. **Версионирование**: аналитика живёт в `/v2`, остальные модули пока в `/v1`. Старые маршруты продолжают работать через thin adapters, но фронтенду лучше использовать фасадные v2 там, где они есть.
2. **Авторизация**: все бизнес-эндпоинты требуют действующего access-token. Refresh end-point выдаёт новый access, но работает только с refresh-токеном. Возможность анонимных запросов выключена.
3. **Форматы дат/UUID**: API отдаёт ISO-строки (`YYYY-MM-DDTHH:MM:SSZ`) и строки UUID. Это согласовано с текущими схемами фронтенда.
4. **Метрики/observability**: публичного эндпоинта нет; метрики экспонируются внутренним сервисом (`/metrics`), когда `CELERY_METRICS_ENABLED=true` (Prometheus) или `CELERY_OTEL_ENABLED=true`. Подробный плейбук — в `docs/observability/celery_observability.md`.

Для расширения списка можно использовать автогенерацию OpenAPI (`/openapi.json`) – он обновляется автоматически при запуске приложения. Если нужен TypeScript-генератор, пока его нет в пайплайне, но можно подключить `openapi-typescript` вручную.

