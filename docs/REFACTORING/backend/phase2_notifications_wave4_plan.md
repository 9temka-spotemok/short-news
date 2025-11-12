# Phase 2 — Wave 4 Notifications & Digests Plan (B-201-Notifications)

**Дата:** 2025-11-12  
**Подготовил:** GPT-5 Codex  
**Статус:** Draft → Ready for execution

---

## 1. Цель волны

Сконцентрировать логику уведомлений и дайджестов в домене `notifications`, обеспечив:
- единый фасад для событий (Competitor/Analytics → Notifications);
- унифицированные каналы доставки (telegram/email/webhook);
- тестируемость и наблюдаемость пайплайнов генерации дайджестов.

## 2. Целевая структура

```
app/domains/notifications/
  __init__.py
  facade.py
  dto.py
  repositories/
    notification_repository.py
    delivery_repository.py
    preference_repository.py
  services/
    dispatcher_service.py
    channel_service.py
    digest_service.py
    template_renderer.py
  channels/
    telegram.py
    email.py
    webhook.py
  pipelines/
    delivery_runner.py
    digest_runner.py
  tasks.py
```

- **facade.py** — точка входа для API, Celery, других доменов (competitors/analytics).
- **dto.py** — структуры `NotificationEventDTO`, `DeliveryDTO`, `DigestDTO`.
- **repositories/** — взаимодействие с `Notification`, `NotificationEvent`, `DeliveryAttempt`, настройками пользователя.
- **services/** — бизнес-правила по маршрутизации, генерации содержимого, фильтрации по предпочтениям.
- **channels/** — адаптеры отправки (теплые обёртки над SendGrid, Telegram, webhook HTTP).
- **pipelines/** — orchestration Celery задач и ретраев, дедуп ключей.

## 3. План шагов

| Шаг | Deliverable | Примечания |
|-----|-------------|------------|
| 4.1 | Создать пакет `app/domains/notifications` и `facade.py` | Определить API `notify_event`, `trigger_digest`, `refresh_preferences` |
| 4.2 | Репозитории & DTO | Вынести SQL/ORM слои из `notification_dispatcher.py`, `notification_service.py`, `digest_service.py` |
| 4.3 | Dispatcher & channel services | Разделить маршрутизацию, сериализацию сообщений и доставку по каналам |
| 4.4 | Pipelines & Celery | Перенести `app/tasks/notifications.py`, `app/tasks/digest.py` в `pipelines/` + обёртки |
| 4.5 | API & интеграции | Обновить API `/api/v1/notifications/*`, интеграцию с Competitor/Analytics фасадами |
| 4.6 | Тесты | Unit для dispatcher/channel/digest, integration для Celery eager |
| 4.7 | Документация | Обновить README, `phase2_bounded_contexts.md`, backlog |

## 4. Тестовая стратегия

- **Unit:**  
  - `tests/unit/domains/notifications/test_dispatcher_service.py`  
  - `tests/unit/domains/notifications/test_channel_service.py`  
  - `tests/unit/domains/notifications/test_digest_service.py`
- **Integration:**  
  - Celery eager тесты `tests/integration/tasks/test_notifications_tasks.py`, `test_digest_tasks.py`  
  - API `/api/v1/notifications` smoke-тесты
- **Contract:**  
  - Проверка webhook payload (snapshot)  
  - Telegram/email шаблоны (render snapshot)

## 5. Документация

- `docs/REFACTORING/backend/phase2_bounded_contexts.md` — Wave 4 «In progress».
- README — раздел «Мультиканальные уведомления» → новые файлы и фасад.
- `docs/REFACTORING/tests/phase2_news_testing_plan.md` → добавить раздел для notifications.

## 6. Риски / зависимости

- Требуется согласование payload’ов с Productivity/Frontend (UI подсказки, линк на настройки).
- Необходимо учесть Celery observability (B-302) — каналы должны отдавать метрики ретраев/успехов.
- Email/Telegram токены хранить через secrets manager (обновить SETUP).

## 7. Критерии готовности

- Competitor/Analytics домены публикуют события через `notifications.facade`.
- `notification_dispatcher.py`, `notification_service.py`, `digest_service.py` превращены в thin adapters или удалены.
- Celery задачи используют `TaskExecutionContext` + новые pipelines.
- Тесты и документация обновлены, backlog B-201-Wave4 закрыт.

## 8. Прогресс (12 Nov 2025)

- Создан пакет `app/domains/notifications/` с фасадом, объединяющим legacy-эндоинты и Celery.
- Репозитории для каналов, событий, доставок, настроек и предпочтений вынесены в `app/domains/notifications/repositories/*`, доступ к БД из сервисов/тасков теперь проходит через них.
- `DispatcherService` переписан на использование репозиториев, обработку статусов/дедуплицирования и работает поверх `EventRepository`.
- Логика `notification_service.py` и `digest_service.py` перенесена в доменные сервисы; legacy-файлы стали адаптерами.
- API `/api/v1/notifications/*` и таски `app/tasks/notifications.py` продолжают работать через фасад без изменений контрактов.
- Следующий шаг — мигрировать Celery пайплайны (`notifications.py`, `digest.py`) на доменный слой и реализовать channel/pipeline сервисы.

