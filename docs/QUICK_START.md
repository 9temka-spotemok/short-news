# 🚀 Быстрый старт - Решение проблем

## ⚡ Быстрое решение (5 минут)

### 1. Запустить пересчёт аналитики

**Вариант A: Через скрипт (рекомендуется)**
```bash
# Для одной компании
docker exec shot-news-backend python backend/scripts/quick_fix_snapshots.py 75eee989-a419-4220-bdc6-810c4854a1fe

# Для всех компаний (первые 10)
docker exec shot-news-backend python backend/scripts/quick_fix_snapshots.py all daily 30 10
```

**Вариант B: Через UI**
1. Открыть Competitor Analysis → Company Analysis
2. Выбрать компанию
3. Нажать "Analyze Company"
4. Нажать "Recompute" в ImpactPanel

**Вариант C: Через API**
```bash
curl -X POST "http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/recompute?period=daily&lookback=60" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Проверить результат

```bash
# Проверить snapshots
docker exec shot-news-postgres psql -U shot_news -d shot_news -c \
  "SELECT COUNT(*), MAX(period_start) as latest FROM company_analytics_snapshots WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';"
```

### 3. Проверить UI

- Обновить страницу Company Analysis
- Проверить Impact Score
- Проверить графики

---

## 📋 Полное решение (30-40 минут)

См. `docs/ACTION_PLAN.md` для детального плана.

---

## 🆘 Если что-то не работает

### Проверить логи:
```bash
docker logs shot-news-celery-worker --tail=50
```

### Проверить Redis:
```bash
docker exec shot-news-redis redis-cli PING
```

### Проверить Celery:
```bash
docker exec shot-news-celery-worker celery -A app.celery_app inspect active
```

---

**Следующий шаг:** Запустить скрипт `quick_fix_snapshots.py`
