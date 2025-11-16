# Phase 2 — Wave 5 Shared Services & Auth Plan (B-201-Shared)

**Дата:** 2025-11-12  
**Подготовил:** GPT-5 Codex  
**Статус:** Draft → Ready for execution

---

## 1. Цель волны

Завершить декомпозицию backend, выделив общие домены и инфраструктуру:
- вынести `users/auth` в отдельный домен с фасадом;
- сгруппировать shared-сервисы (security, feature flags, external интеграции);
- подготовить платформу для Phase 4 (feature flags, типы, CI automation).

## 2. Исходное состояние

- Логика пользователей и авторизации разбросана по `app/api/v1/endpoints/auth.py`, `users.py`, `app/services/telegram_service.py`.
- Shared-инфраструктура (`core/security`, `core/database`, `services/api clients`) хранится в `app/core` и `app/services`.
- План Phase 4 требует feature flag middleware и генерацию общих типов.

## 3. Целевая структура

```
app/domains/users/
  facade.py
  repositories/
    user_repository.py
    preference_repository.py
  services/
    auth_service.py
    preference_service.py
  dto.py

app/platform/
  feature_flags/
    facade.py
    repository.py
    middleware.py
  integrations/
    openapi_codegen.py
    celery_instrumentation.py
  security/
    password.py
    tokens.py

app/infrastructure/
  db/
  redis/
  http/
```

- **domains/users** — единая точка для управления пользователями, авторизацией, Telegram/OTP и преференциями.
- **platform/** — cross-cutting сервисы (feature flags, схема генерации, shared security).
- **infrastructure/** — адаптеры к БД/Redis/HTTP.

## 4. План реализации

| Шаг | Deliverable | Примечания |
|-----|-------------|------------|
| 5.1 | Users/Auth фасад | Создать `app/domains/users/facade.py`, перенести CRUD/преференции |
| 5.2 | Telegram & external auth интеграции | Обновить `telegram_service.py`, вынести в domain/service |
| 5.3 | Feature flag platform | Создать `app/platform/feature_flags`, подключить middleware (см. B-401) |
| 5.4 | Shared security/integrations | Перенести `core/security`, подготовить JWT/пароли как сервисы |
| 5.5 | API адаптация | Обновить `/api/v1/auth`, `/api/v1/users` на фасад, закрыть raw SQL |
| 5.6 | Tests/Docs | Unit + integration для users/auth, обновление README и SETUP |

## 5. Тестовая стратегия

- **Unit:**  
  - `tests/unit/domains/users/test_auth_service.py`  
  - `tests/unit/domains/users/test_preference_service.py`  
  - `tests/unit/platform/test_feature_flags.py`
- **Integration:**  
  - `/api/v1/auth`, `/api/v1/users` (token refresh, password reset)  
  - Feature flag middleware (FastAPI lifecyle tests)
- **Contract:**  
  - Snapshot OpenAPI для auth/users  
  - Validate TypeScript генерацию (Phase 4)

## 6. Документация

- `docs/REFACTORING/backend/phase2_bounded_contexts.md` — Wave 5 «In progress».
- README — разделы Auth/Feature Flags.
- SETUP — обновить инструкции по переменным (`FEATURE_FLAGS_URL`, и т.д.).

## 7. Риски / зависимости

- Требуется синхронизация с B-401/B-402 (Phase 4).
- Возможно изменение токенов/протоколов → согласовать с frontend/mobile.
- Нужно обеспечить миграцию текущих пользователей (если меняется структура таблиц).

## 8. Критерии готовности

- Users/Auth домен изолирован, API использует фасад.
- Feature flag middleware работает (можно вкл/выкл фичи без деплоя).
- Shared security и API интеграции оформлены как часть platform.
- Документация обновлена, B-201-Wave5 закрыт.


