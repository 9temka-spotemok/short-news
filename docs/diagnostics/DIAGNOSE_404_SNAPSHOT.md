# Диагностика проблемы 404 для snapshot

## ✅ Подтверждено: запрос доходит до эндпоинта

Если в логах есть `get_latest_snapshot called`, значит:
- ✅ Маршрутизация работает правильно
- ✅ Аутентификация прошла успешно
- ✅ Эндпоинт вызывается

## 🔍 Пошаговая диагностика

### Шаг 1: Проверить логи сервера

После запроса должны быть следующие логи (в порядке появления):

```
INFO: get_latest_snapshot called: company_id=..., period=daily, user_id=...
INFO: Calling analytics.get_latest_snapshot(company_id=..., period=daily)
DEBUG: SnapshotService.get_latest_snapshot: company_id=..., period=AnalyticsPeriod.DAILY (value=daily)
DEBUG: Executing SQL query for get_latest_snapshot...
INFO: SnapshotService.get_latest_snapshot result: found/NOT FOUND (id=...)
INFO: get_latest_snapshot result: snapshot=found/NOT FOUND (id=...)
```

**Если snapshot НЕ найден:**
```
INFO: Snapshot not found, attempting to create automatically...
INFO: Computing snapshot for period_start=..., period=daily
```

**Если создание успешно:**
```
INFO: Successfully computed snapshot: id=...
INFO: Auto-created snapshot for company ... (period=daily, start=..., id=...)
INFO: Converting snapshot to response...
INFO: === get_latest_snapshot SUCCESS: snapshot_id=... ===
```

**Если создание не удалось:**
```
ERROR: Failed to auto-create snapshot for company ...: ...
INFO: compute_snapshot_for_period failed, creating empty snapshot as fallback...
INFO: Creating empty CompanyAnalyticsSnapshot object...
INFO: Adding snapshot to session and committing...
```

**Если даже пустой snapshot не удалось создать:**
```
ERROR: Failed to create empty snapshot for company ...: ...
# Затем выбрасывается HTTPException с 404
```

### Шаг 2: Запустить скрипт диагностики

```bash
cd backend
python -m scripts.diagnose_snapshot_404 75eee989-a419-4220-bdc6-810c4854a1fe daily
```

Скрипт проверит:
1. ✅ Существует ли компания в БД
2. ✅ Есть ли snapshots для указанного периода
3. ✅ Есть ли snapshots вообще для компании
4. ✅ Существует ли таблица `company_analytics_snapshots`
5. ✅ Есть ли индексы

### Шаг 3: Проверить данные в БД напрямую

```sql
-- Проверить компанию
SELECT id, name, created_at 
FROM companies 
WHERE id = '75eee989-a419-4220-bdc6-810c4854a1fe';

-- Проверить snapshots для периода daily
SELECT 
    id, 
    company_id, 
    period, 
    period_start, 
    period_end,
    news_total,
    impact_score
FROM company_analytics_snapshots 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe' 
  AND period = 'daily'
ORDER BY period_start DESC 
LIMIT 5;

-- Проверить все snapshots для компании
SELECT 
    period,
    COUNT(*) as count,
    MIN(period_start) as earliest,
    MAX(period_start) as latest
FROM company_analytics_snapshots 
WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe'
GROUP BY period;
```

### Шаг 4: Проверить ошибки в логах

Ищите в логах:
- `ERROR: Failed to auto-create snapshot` - ошибка при вычислении snapshot
- `ERROR: Failed to create empty snapshot` - ошибка при сохранении в БД
- `IntegrityError` - нарушение ограничений БД (например, дубликат)
- `OperationalError` - проблема с подключением к БД

## 🎯 Типичные причины 404

### 1. Snapshot не существует и не удалось создать автоматически

**Признаки:**
- В логах: `SnapshotService.get_latest_snapshot result: NOT FOUND`
- Затем: `Failed to create empty snapshot`

**Возможные причины:**
- ❌ Компания не существует в БД
- ❌ Ошибка при сохранении в БД (IntegrityError, OperationalError)
- ❌ Проблемы с транзакцией БД

**Решение:**
1. Проверить существование компании
2. Проверить логи на конкретную ошибку
3. Проверить права доступа к БД

### 2. Ошибка при вычислении snapshot

**Признаки:**
- В логах: `Failed to auto-create snapshot for company ...: ...`
- Затем попытка создать пустой snapshot

**Возможные причины:**
- ❌ Ошибка в `compute_snapshot_for_period()`
- ❌ Проблемы с данными (нет новостей, событий и т.д.)

**Решение:**
1. Проверить полный traceback в логах
2. Проверить, есть ли данные для вычисления snapshot

### 3. Проблема с транзакцией БД

**Признаки:**
- В логах: `Adding snapshot to session and committing...`
- Затем ошибка при commit

**Возможные причины:**
- ❌ Нарушение UniqueConstraint (дубликат snapshot)
- ❌ Проблемы с foreign key (company_id не существует)
- ❌ Проблемы с типом данных

**Решение:**
1. Проверить ограничения в таблице
2. Проверить, нет ли уже snapshot с такими же параметрами
3. Проверить формат данных

## 🔧 Что делать дальше

### Если snapshot не найден в БД:

1. **Проверить, есть ли данные для создания snapshot:**
   ```sql
   -- Проверить новости для компании
   SELECT COUNT(*) FROM news_items 
   WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';
   
   -- Проверить события
   SELECT COUNT(*) FROM competitor_change_events 
   WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe';
   ```

2. **Запустить пересчет аналитики:**
   ```bash
   curl -X POST "http://localhost:8000/api/v2/analytics/companies/75eee989-a419-4220-bdc6-810c4854a1fe/recompute?period=daily&lookback=30" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

### Если есть ошибка при создании:

1. **Проверить полный traceback в логах**
2. **Проверить ограничения БД:**
   ```sql
   -- Проверить UniqueConstraint
   SELECT 
       company_id, 
       period_start, 
       period, 
       COUNT(*) 
   FROM company_analytics_snapshots 
   WHERE company_id = '75eee989-a419-4220-bdc6-810c4854a1fe'
   GROUP BY company_id, period_start, period
   HAVING COUNT(*) > 1;
   ```

3. **Проверить foreign key:**
   ```sql
   -- Убедиться, что компания существует
   SELECT id FROM companies WHERE id = '75eee989-a419-4220-bdc6-810c4854a1fe';
   ```

## 📊 Чек-лист диагностики

- [ ] Логи показывают `get_latest_snapshot called`
- [ ] Логи показывают результат `SnapshotService.get_latest_snapshot`
- [ ] Компания существует в БД
- [ ] Таблица `company_analytics_snapshots` существует
- [ ] Нет ошибок при создании snapshot в логах
- [ ] Нет ошибок при сохранении в БД в логах
- [ ] Скрипт диагностики не показывает критических проблем

## 🚀 Следующие шаги

После диагностики:

1. **Если snapshot не существует:**
   - Запустить пересчет аналитики
   - Или дождаться автоматического создания (должно работать)

2. **Если есть ошибка:**
   - Исправить проблему на основе логов
   - Проверить данные в БД
   - Проверить ограничения и constraints

3. **Если все в порядке, но все равно 404:**
   - Проверить, что сервер перезапущен после изменений
   - Проверить, что используется правильный URL
   - Проверить, что токен авторизации валиден




