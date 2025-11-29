# Отчет о состоянии Docker сервисов

**Дата проверки:** 2025-11-29 02:40 UTC (обновлено)

## Общее состояние

Все основные сервисы запущены и работают стабильно. Общее время работы: **17 минут** (после последнего перезапуска).

---

## Статус контейнеров

| Сервис | Статус | Порты | Health Check |
|--------|--------|-------|---------------|
| **shot-news-backend** | ✅ Up | 0.0.0.0:8000->8000/tcp | - |
| **shot-news-frontend** | ✅ Up | 0.0.0.0:5173->5173/tcp | - |
| **shot-news-postgres** | ✅ Up (healthy) | 0.0.0.0:5432->5432/tcp | ✅ Healthy |
| **shot-news-redis** | ✅ Up (healthy) | 0.0.0.0:6379->6379/tcp | ✅ Healthy |
| **shot-news-telegram-bot** | ✅ Up (healthy) | - | ✅ Healthy |
| **shot-news-scraper** | ✅ Up (healthy) | 8001/tcp | ✅ Healthy |
| **shot-news-celery-worker** | ✅ Up | - | - |
| **shot-news-celery-beat** | ✅ Up | - | - |
| **shot-news-migration** | ✅ Exited (0) | - | - |

---

## Использование ресурсов

| Сервис | CPU % | Память | Сеть I/O | Диск I/O |
|--------|-------|--------|----------|----------|
| **backend** | 13.36% | 163.8 MiB | 458kB / 558kB | 40MB / 0B |
| **frontend** | 1.03% | 115 MiB | 130kB / 269kB | 105MB / 381kB |
| **postgres** | 2.65% | 293.2 MiB | 23.5MB / 35.3MB | 148MB / 183MB |
| **redis** | 0.52% | 12.35 MiB | 1.6MB / 938kB | 15.1MB / 5.96MB |
| **celery-worker** | 2.84% | **1.39 GiB** ⚠️ | 64.4MB / 26.5MB | 25.3MB / 73.7kB |
| **celery-beat** | 0.00% | 115.2 MiB | 15.5kB / 40.9kB | 19.5MB / 49.2kB |
| **telegram-bot** | 0.00% | 67.02 MiB | 502kB / 184kB | 41.3MB / 0B |
| **scraper** | 9.11% | 247.9 MiB | 36.7MB / 1.27MB | 50MB / 578kB |

**⚠️ Внимание:** Celery worker использует много памяти (1.39 GiB). Это может быть нормально при активной обработке задач, но стоит мониторить. Использование памяти немного снизилось с предыдущей проверки.

---

## Детальный анализ сервисов

### 1. Backend (shot-news-backend)

**Статус:** ✅ Работает нормально

**Логи:**
- API запросы обрабатываются успешно
- SQL запросы выполняются корректно
- Нет критических ошибок

**Проблемы:**
- ⚠️ Некоторые запросы к `/api/v1/companies/{company_id}/monitoring/matrix` возвращают 404
  - Компании: `94649cdd-0ab2-4fa8-998f-d34851c43938`, `f44bb60b-93d3-4e02-93b8-934a3cdfd393`
  - Причина: Компании не найдены или пользователь не имеет к ним доступа
  - Решение: Проверить принадлежность компаний пользователю через `check_company_access`

**Последние запросы:**
- `GET /api/v1/notifications/unread` - 200 OK
- `GET /api/v1/news/?limit=5` - 200 OK
- `GET /api/v1/companies/monitoring/status` - 200 OK
- `GET /api/v1/companies/{id}/monitoring/matrix` - 200 OK (для некоторых компаний)

---

### 2. Frontend (shot-news-frontend)

**Статус:** ✅ Работает нормально

**Логи:**
- Vite dev server запущен на порту 5173
- Нет ошибок компиляции

**Предупреждения:**
- ⚠️ 7 moderate severity vulnerabilities в npm пакетах
  - Рекомендация: Выполнить `npm audit fix` (с осторожностью)

---

### 3. PostgreSQL (shot-news-postgres)

**Статус:** ✅ Работает нормально

**Логи:**
- Checkpoint операции выполняются успешно
- Нет критических ошибок

**Проблемы:**
- ✅ **SQL синтаксическая ошибка** (исправлена):
  ```
  ERROR: syntax error at or near ":" at character 104
  STATEMENT: SELECT id FROM user_preferences 
             WHERE interested_categories @> ARRAY[:category::newscategory]
  ```
  - Файл: `backend/app/domains/notifications/repositories/preferences_repository.py:39`
  - Исправление: Изменено `:category::newscategory` на `CAST(:category AS newscategory)`
  - Статус: ✅ Исправлено
  - Проверка: Последняя ошибка была в 02:24:07, новых ошибок нет после исправления

**Последние операции:**
- Checkpoint завершен успешно
- WAL файлы обрабатываются корректно

---

### 4. Redis (shot-news-redis)

**Статус:** ✅ Работает нормально

**Логи:**
- Нет ошибок
- Health check проходит успешно

---

### 5. Celery Worker (shot-news-celery-worker)

**Статус:** ✅ Работает нормально

**Логи:**
- Задачи выполняются успешно
- Scraping операции работают

**Проблемы:**
- ⚠️ Некоторые источники возвращают 404:
  - `https://www.megafon.ru/news` → 404 Not Found
  - `https://www.megaline.ru/company/news` → DNS resolution failure
  - Это нормально для источников, которые изменили структуру или недоступны
  - Система корректно обрабатывает такие случаи и записывает результат в health tracking

- ❌ **Ошибка в UniversalBlogScraper** (исправлена):
  - Ошибка: `UniversalBlogScraper._extract_articles() missing 1 required positional argument: 'selectors'`
  - Файл: `backend/app/scrapers/universal_scraper.py:312`
  - Причина: Вызов метода без обязательного параметра `selectors`
  - Исправление: Добавлен параметр `DEFAULT_ARTICLE_SELECTORS` при вызове
  - Статус: ✅ Исправлено

**Активность:**
- Обработка scraping задач
- Обновление source_profiles
- Запись результатов health checks

---

### 6. Celery Beat (shot-news-celery-beat)

**Статус:** ✅ Работает нормально

**Логи:**
- Scheduler настроен с 16 задачами
- Периодические задачи отправляются корректно

**Активные задачи:**
- `generate-weekly-digests` - генерация еженедельных дайджестов
- `check-company-activity` - проверка активности компаний
- `scrape-ai-blogs` - скрапинг AI блогов
- `recompute-analytics-daily` - пересчет аналитики
- `monitor-github` - мониторинг GitHub
- `dispatch-notification-deliveries` - отправка уведомлений
- `fetch-social-media` - получение данных из соцсетей
- `check-daily-trends` - проверка ежедневных трендов
- `generate-daily-digests` - генерация ежедневных дайджестов

---

### 7. Telegram Bot (shot-news-telegram-bot)

**Статус:** ✅ Работает нормально

**Логи:**
- Bot token настроен
- Health check пройден: `@short_news_bot_test_bot`
- Polling запущен успешно

**История:**
- 2025-11-28 19:51:34 - Была ошибка "Server disconnected" (восстановлено)
- Текущий статус: стабильная работа

---

### 8. News Scraper (shot-news-scraper)

**Статус:** ✅ Работает нормально

**Логи:**
- Health check проходит успешно
- Scraping операции выполняются

---

## Исправленные проблемы

### ✅ SQL синтаксическая ошибка в preferences_repository.py

**Проблема:**
```sql
WHERE interested_categories @> ARRAY[:category::newscategory]
```

**Исправление:**
```sql
WHERE interested_categories @> ARRAY[CAST(:category AS newscategory)]
```

**Файл:** `backend/app/domains/notifications/repositories/preferences_repository.py:39`

**Статус:** ✅ Исправлено, новых ошибок нет после 02:24:07

---

### ✅ Ошибка вызова метода в UniversalBlogScraper

**Проблема:**
```python
articles = self._extract_articles(soup, final_url)  # Отсутствует параметр selectors
```

**Ошибка:**
```
UniversalBlogScraper._extract_articles() missing 1 required positional argument: 'selectors'
```

**Исправление:**
```python
articles = self._extract_articles(soup, final_url, DEFAULT_ARTICLE_SELECTORS)
```

**Файл:** `backend/app/scrapers/universal_scraper.py:312`

**Статус:** ✅ Исправлено

---

## Рекомендации

### 1. Мониторинг памяти Celery Worker
- Celery worker использует 1.44 GiB памяти
- Рекомендуется мониторить использование памяти и при необходимости оптимизировать задачи

### 2. Обновление npm пакетов
- Выполнить `npm audit fix` для исправления уязвимостей (с осторожностью, может потребоваться тестирование)

### 3. Обработка 404 для monitoring/matrix
- Проверить логику доступа к компаниям в `check_company_access`
- Убедиться, что компании принадлежат пользователю или являются глобальными
- Добавить более детальное логирование для отладки

### 4. Мониторинг недоступных источников
- Некоторые источники (например, megafon.ru) возвращают 404
- Система корректно обрабатывает такие случаи, но стоит периодически проверять список недоступных источников

---

## Заключение

Все сервисы работают стабильно. Основные проблемы:
1. ✅ Исправлена SQL синтаксическая ошибка (новых ошибок нет)
2. ✅ Исправлена ошибка вызова метода в UniversalBlogScraper
3. ⚠️ Некоторые запросы к monitoring/matrix возвращают 404 (требует проверки доступа к компаниям)
4. ⚠️ Высокое использование памяти Celery Worker (1.39 GiB, требует мониторинга)

**Текущее состояние:**
- Все контейнеры работают стабильно
- Backend обрабатывает запросы успешно
- Monitoring endpoints работают для доступных компаний
- SQL ошибки устранены
- Scraper ошибки исправлены

Система готова к работе. Рекомендуется периодически проверять логи и мониторить использование ресурсов.
