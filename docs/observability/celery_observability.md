# Celery Observability Playbook

Обновлено: 12 ноября 2025.

Документ описывает, как включить метрики Celery, собрать baseline, завести алерты и проверить deduplication guards по задаче **B-302**.

---

## 1. Быстрый старт локально

1. Скопируйте `.env.example` в `.env` и установите:
   ```bash
   SECRET_KEY=dev-secret
   DATABASE_URL=sqlite+aiosqlite:///./celery_baseline.db
   REDIS_URL=redis://localhost:6379/0           # или fake:// для локального мока
   CELERY_METRICS_EXPOSE_SERVER=true
   CELERY_METRICS_HOST=0.0.0.0
   CELERY_METRICS_PORT=9464
   CELERY_OTEL_ENABLED=false
   ```
   > При отсутствии Redis можно переопределить backend на InMemory (см. `configure_dedup_backend`).

2. Запустите приложение:
   ```bash
   poetry run uvicorn app.main:app --reload
   ```

3. Поднимите воркер:
   ```bash
   CELERY_METRICS_EXPOSE_SERVER=false \
   poetry run celery -A app.celery_app worker -l info
   ```
   (когда воркеров несколько, HTTP-экспортёр оставляют только на одном инстансе).

4. Выполните smoke-таск:
   ```bash
   poetry run python scripts/observability/celery_metrics_baseline.py
   ```
   Скрипт триггерит несколько `TaskExecutionContext` сценариев и печатает аггрегированные метрики/дедуп-статистику в консоль, а также формирует `artifacts/celery_metrics_baseline.txt` для отчётов.

5. Проверьте Prometheus:
   ```bash
   curl http://localhost:9464/metrics | grep celery_task
   ```

---

## 2. Prometheus / Alertmanager

Правила в `observability/prometheus/celery_rules.yml`:

- `CeleryTaskFailuresHigh` — алерт, если `failure`-метрики > 0 в течение 5 минут.
- `CeleryDuplicateSpike` — срабатывает при >5 дубликатов за 5 минут (помогает поймать невалидные ключи).
- `CeleryTaskStalled` — если `celery_task_in_progress` > 0 более 15 минут.

### Развёртывание

1. Добавьте файл в Prometheus конфигурацию:
   ```yaml
   rule_files:
     - "celery_rules.yml"
   ```
2. Настройте job для воркеров:
   ```yaml
   scrape_configs:
     - job_name: "celery-workers"
       static_configs:
         - targets: ["celery-worker-1:9464", "celery-worker-2:9464"]
   ```
3. Передайте Alertmanager route в Slack/Email.

---

## 3. Grafana Dashboard

- JSON панель лежит в `observability/grafana/celery_dashboard.json`.
- Основные графики:
  - Throughput и среднее время задач (`celery_task_total`, `celery_task_duration_seconds`).
  - Карта дубликатов (`celery_task_duplicates_total`).
  - Gauge активных задач (`celery_task_in_progress`).
- Включены аннотации на основе Alertmanager.

Загрузите дашборд через **Dashboards → Import → Upload JSON file**.

---

## 4. Baseline и артефакты

- Скрипт `scripts/observability/celery_metrics_baseline.py` генерирует:
  - `artifacts/celery_metrics_baseline.txt` — snapshot метрик.
  - `artifacts/celery_metrics_summary.json` — агрегированные показатели (среднее/максимум/дубликаты).
- Запишите результаты в `docs/REFACTORING/metrics/phase0_baseline_metrics.md`.

---

## 5. Smoke / E2E

### 5.1. Код
- Тест `tests/integration/tasks/test_celery_metrics.py` проверяет:
  - учёт `success/failure` статусов,
  - работу дедупликации и duplicate counter.

### 5.2. Практика
- Перед релизом прогоняйте:
  ```bash
  poetry run pytest tests/integration/tasks/test_celery_metrics.py
  ```
- После выката QA запускает `scripts/observability/celery_metrics_baseline.py` и прикладывает артефакты к релизному отчёту.

---

## 6. Рекомендации

- **Retriable ошибки**: на проде используйте Celery `autoretry_for` / `retry_backoff`. Метрики по ретраям можно расширить (см. TODO в `celery_metrics.py`).
- **Dedup TTL**: для аналитики TTL 15 минут (`settings.CELERY_DEDUP_TTL_SECONDS=900`). Для «единоразовых» задач лучше ставить TTL >= сроку SLA.
- **OTel**: при `CELERY_OTEL_ENABLED=true` и корректном OTLP-экспортёре метрики автоматически уйдут в Grafana Cloud / Tempo.
- **Разделение очередей**: добавляйте label `queue=<name>` при вызовах `TaskExecutionContext` — это попадёт в метрики и облегчит фильтрацию.

---

### Контакты
- Ответственный: Backend Team (@backend-platform)
- Канал: `#observability` (для алертов и операционных вопросов)


