# Phase 2 — Scraper Interface Extraction Plan

Дата: 2025-11-10  
Подготовил: GPT-5 Codex

---

## 1. Контекст и мотивация
- **Текущее состояние:**  
  - `app/scrapers/universal_scraper.py` содержит универсальный сборщик с httpx, headless fallback и конфигурациями через `ScraperConfigRegistry`.  
  - Celery задачи (`app/tasks/scraping.py`) напрямую создают `UniversalBlogScraper` и работают с `AsyncSessionLocal`.  
  - Специализированные скраперы (AINews, OpenAI blog) находятся в `app/scrapers/real_scrapers.py`, используют разные API и стратегии ретраев.  
  - Конфигурации источников не связаны с news-доменом: нет явного интерфейса, чтобы доменные сервисы могли подменять scraping-реализации (например, для интеграционных тестов или внешних провайдеров).

- **Проблемы:**  
  1. Сильная связанность между Celery задачами, универсальным скрапером и инфраструктурой (httpx, rate limiter).  
  2. Сложно расширять источники (нужно модифицировать `UniversalBlogScraper`), отсутствуют интерфейсы/адаптеры для сторонних провайдеров.  
  3. Тестирование ограничено: сложно подменить скрапер/источник без monkeypatch.  
  4. Отсутствует версия, совместимая с доменным фасадом (`NewsFacade`) для запуска ingestion в других сценариях (CLI, ad-hoc).

## 2. Цели
- Выделить явные интерфейсы scraping-провайдеров, совместимые с доменным слоем (`NewsFacade`, `NewsIngestionService`).  
- Минимизировать прямые зависимости Celery задач от конкретных реализаций.  
- Подготовить возможность расширения (подключение новых источников, смена движка), упрощённого тестирования и reuse в других bounded contexts (например, Competitor Intelligence).

## 3. Предлагаемая структура
```
app/
  domains/
    news/
      scrapers/
        interfaces.py        # Протоколы / абстрактные классы для провайдеров
        adapters.py          # Обёртки над существующими реализациями (Universal, AINews и т.д.)
        registry.py          # Регистрация и выбор стратегии (DI контейнер)
        tasks.py             # Вызовы из Celery → фасад (shared с ingestion)
      services/
        ingestion_service.py # Уже использует facade; будет вызываться из адаптера
```

Дополнительно:
- Внедрить зависимости через `get_news_facade` или аналогичный DI helper, чтобы Celery/CLI могли получать скрапер из реестра.

## 4. План миграции (итерации)
1. **Инвентаризация источников (B-203-1)**  
   - Просмотреть `app/scrapers/*` и задокументировать реализованные стратегии (универсальный, AINews, OpenAI).  
   - Оценить зависимости (rate limiter, headless, config loader).  
   - Зафиксировать результаты в разделе 5.

2. **Абстракции и интерфейсы (B-203-2)** — ✅  
   - Созданы `interfaces.py` (`CompanyContext`, `ScrapedNewsItem`, `ScraperProvider`).  
   - Определены методы `scrape_company`, `close`.

3. **Адаптеры и реализация (B-203-3)** — ✅ (первая итерация)  
   - `UniversalScraperProvider` адаптирует `UniversalBlogScraper`.  
   - `AINewsScraperProvider` покрывает curated источники (OpenAI, Anthropic, Google).  
   - Реестр `NewsScraperRegistry` позволяет регистрировать провайдеры и имеет built-in правила.  
   - Celery задача `scraping._scrape_ai_blogs_async` использует фасадный `NewsScraperService`.
4. **Интеграция CLI/скриптов (B-203-6)** — ✅  
   - Скрипты `scrape_all_companies.py`, `run_full_import.py`, `import_from_docker.py` используют `NewsFacade`/`NewsScraperService`.  
   - API `companies.scan_company` строит превью через реестр провайдеров.
   - Unit-тесты для адаптера (`tests/unit/domains/news/test_scraper_provider.py`).

4. **Интеграция с фасадом (B-203-4)**  
   - Организовать ingestion через `NewsFacade` (уже сделано для создания новостей).  
   - Добавить команду/CLI (или функцию) для ручного запуска scraping через доменный слой.

5. **Тесты и документация (B-203-5)**  
   - Добавить unit-тесты для адаптеров (моки httpx/headless).  
   - Обновить интеграционный тест `tests/integration/tasks/test_scraping_task.py` на использование нового реестра.  
   - Обновить README и `phase2_news_refactor_plan.md` (раздел Scraping/NLP).

## 5. Инвентаризация текущих реализаций
| Файл | Реализация | Особенности | Риск |
|------|------------|-------------|------|
| `scrapers/universal_scraper.py` | UniversalBlogScraper | httpx, heuristics, headless fallback, config registry | Средний (сложность модификаций) |
| `scrapers/real_scrapers.py` | `AINewsScraper`, др. | Используют API/HTML конкретных сайтов | Средний |
| `scrapers/headless.py` | Playwright fallback | Требует внешние зависимости, может быть тяжёлым | Средний |
| `scrapers/config_loader.py` | Загрузка yaml-конфигураций | Связь через FS и settings | Низкий |
| `scrapers/rate_limiter.py` | RateLimiter | Независимая утилита | Низкий |

## 6. Риски и меры
- **Playwright зависит от окружения:** предусмотреть конфигурацию в CI, описать fallback.  
- **Изменение API провайдеров:** задокументировать адаптеры, добавить мониторинг.  
- **Качество данных:** обеспечить пост-валидацию через `NewsIngestionService` (уже реализована).  
- **Тестирование:** обеспечить мок-слой (поставляемый rate limiter, headless fetch) для unit-тестов.

## 7. Статус и deliverables
- **Статус:** план утверждён, ожидает декомпозиции (B-203-1 … B-203-5).  
- **Deliverables:**  
  - Новый пакет `app/domains/news/scrapers/` с интерфейсами и адаптерами.  
  - Обновлённые Celery задачи и документация.  
  - Тестовое покрытие для основных провайдеров и интеграционные сценарии.

---

**Подпись:** GPT-5 Codex — 10 Nov 2025

