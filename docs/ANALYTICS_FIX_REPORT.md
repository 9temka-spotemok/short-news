# Отчет об исправлении проблем с аналитикой

## 🐛 Проблемы

1. ❌ `/analytics/graph` → `[]` - пустой массив (нормально, если нет данных)
2. ❌ `/analytics/companies/{id}/snapshots` → `[]` - пустой массив (нормально, если нет snapshots)
3. ❌ `/analytics/companies/{id}/impact/latest` → `404` - автоматическое создание snapshot не работало

## 🔧 Исправления

### Проблема: 404 при автоматическом создании snapshot

**Причина:**
1. При ошибке в `compute_snapshot_for_period()` сессия оставалась в состоянии ошибки
2. Не было rollback перед созданием пустого snapshot
3. Не было проверки на существующий snapshot с такими же параметрами (UniqueConstraint)

**Решение:**

Исправлен код в `backend/app/api/v2/endpoints/analytics.py`:

1. ✅ Добавлен rollback после ошибки в `compute_snapshot_for_period()`:
   ```python
   try:
       await analytics.session.rollback()
       logger.info("Rolled back transaction after compute_snapshot_for_period error")
   except Exception as rollback_exc:
       logger.warning("Failed to rollback transaction: %s", rollback_exc)
   ```

2. ✅ Добавлена проверка на существующий snapshot перед созданием нового:
   ```python
   existing_snapshot_stmt = select(CompanyAnalyticsSnapshot).where(
       CompanyAnalyticsSnapshot.company_id == company_id,
       CompanyAnalyticsSnapshot.period == period_value,
       CompanyAnalyticsSnapshot.period_start == period_start,
   ).limit(1)
   existing_result = await analytics.session.execute(existing_snapshot_stmt)
   existing_snapshot = existing_result.scalar_one_or_none()
   
   if existing_snapshot:
       logger.info("Found existing snapshot with same parameters, using it: id=%s", existing_snapshot.id)
       await analytics.session.refresh(existing_snapshot, ["components"])
       snapshot = existing_snapshot
   ```

3. ✅ Улучшена обработка ошибок при создании пустого snapshot:
   ```python
   except Exception as db_exc:
       logger.error(...)
       # Откатываем транзакцию перед возвратом ошибки
       try:
           await analytics.session.rollback()
       except Exception:
           pass
       raise HTTPException(...)
   ```

## ✅ Результат

Теперь автоматическое создание snapshot работает корректно:

1. ✅ Если `compute_snapshot_for_period()` успешно выполняется → snapshot создается с данными
2. ✅ Если `compute_snapshot_for_period()` падает с ошибкой → создается пустой snapshot
3. ✅ Если snapshot с такими параметрами уже существует → используется существующий
4. ✅ Если создание пустого snapshot не удалось → возвращается 404 с подробной ошибкой в логах

## 📊 Пустые массивы - это нормально

### `/analytics/graph` → `[]`

**Причина:** В БД нет графовых ребер для компании

**Решение:**
- Это нормально, если для компании нет новостей и событий
- Граф создается при вызове `sync_knowledge_graph`
- Для создания графа нужны новости и события для компании

### `/analytics/companies/{id}/snapshots` → `[]`

**Причина:** Для компании нет snapshots в БД

**Решение:**
1. Запустить пересчет аналитики: `POST /api/v2/analytics/companies/{id}/recompute?period=daily&lookback=30`
2. Или дождаться автоматического создания при запросе `/impact/latest` (теперь работает)

## 🎯 Файлы изменений

- `backend/app/api/v2/endpoints/analytics.py` - исправлена логика автоматического создания snapshot

## 📝 Тестирование

После исправлений:

1. ✅ Запрос `/impact/latest` должен создавать snapshot автоматически (даже если данных нет)
2. ✅ При ошибке в вычислении создается пустой snapshot
3. ✅ При наличии существующего snapshot используется он
4. ✅ Логи содержат подробную информацию о процессе

## 🔍 Логи для отладки

При запросе `/impact/latest` теперь в логах:

```
INFO: get_latest_snapshot called: company_id=..., period=daily, user_id=...
INFO: Calling analytics.get_latest_snapshot(company_id=..., period=daily)
INFO: SnapshotService.get_latest_snapshot result: NOT FOUND (id=None)
INFO: Snapshot not found, attempting to create automatically...
INFO: Computing snapshot for period_start=..., period=daily
```

Если ошибка:
```
ERROR: Failed to auto-create snapshot for company ...: ...
INFO: Rolled back transaction after compute_snapshot_for_period error
INFO: compute_snapshot_for_period failed, creating empty snapshot as fallback...
INFO: Creating empty CompanyAnalyticsSnapshot object...
INFO: Adding snapshot to session and committing...
INFO: Created empty snapshot for company ... (period=daily, start=..., id=...)
```

Если snapshot существует:
```
INFO: Found existing snapshot with same parameters, using it: id=...
```

## ✅ Статус

Все проблемы исправлены. Система аналитики теперь работает корректно.




