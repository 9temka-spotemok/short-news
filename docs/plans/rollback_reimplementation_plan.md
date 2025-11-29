## План восстановления функционала после отката

После отката текущих изменений нужно вернуть следующие блоки. Группируй работу и проверяй по чек-листу.

### Документация (`README.md`, `docs/PARSER_IMPROVEMENT_TODO.md`, `docs/file1.md`, `docs/file2.md`)
- Описать, как включать Playwright-фолбэк и зачем он нужен.
- Задокументировать историю багфиксов: `feedparser`, быстрый предпросмотр конкурентов, поддержка Next.js.
- Обновить описание `UniversalBlogScraper` и список ответственных файлов.

### Эндпоинт предпросмотра конкурента (`backend/app/api/v1/endpoints/companies.py`)
- Восстановить «быстрый режим»: лимиты `max_requests`, `max_duration`, уменьшенный HTTP таймаут, обёртку `asyncio.wait_for`.
- Вернуть fallback-сканер, который срабатывает, если основной превысил бюджет.
- Прокинуть уменьшенный таймаут в `extract_company_info`.

### Универсальный скрапер (`backend/app/scrapers/universal_scraper.py`)
- Вернуть конструктор с параметрами `max_requests`, `request_timeout`, `max_duration` и выбор `lxml` по умолчанию.
- Восстановить контроль бюджета запросов (`_request_allowed`, `_fetch`), остановку по дедлайну и расширенное логирование.
- Оставить безопасный фолбэк на встроенный `html.parser`, если `lxml` недоступен.

### Извлечение информации о компании (`backend/app/services/company_info_extractor.py`)
- Поддержать настраиваемый `timeout`, чтобы предпросмотр не зависал на медленных сайтах.

### Зависимости (`backend/pyproject.toml`, `backend/poetry.lock`, `backend/requirements.txt`)
- Добавить `feedparser` — без него backend/Celery снова упадут с `ModuleNotFoundError`.

### Тесты и фикстуры (`backend/tests/...`)
- Вернуть юнит-тесты на RSS, JSON Feed, JSON-LD и дедупликацию `UniversalBlogScraper`.
- Оставить реальные фикстуры RSS/JSON/HTML для регрессионной проверки.

### Прочее
- Удалить случайные артефакты (`"4 import BeautifulSoup"`, `"ubprocess, os"`, `"uccess' if success else 'compile failed')"`) и убедиться, что они не попадут обратно.


