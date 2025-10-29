# Анализ запроса Save Settings из DigestSettingsPage

## Что отправляет фронтенд

### Тип DigestSettings (frontend/src/types/index.ts):
```typescript
export interface DigestSettings {
  digest_enabled: boolean
  digest_frequency: DigestFrequency  // 'daily' | 'weekly' | 'custom'
  digest_custom_schedule: CustomSchedule | null  // {time: string, days: number[], timezone: string} | null
  digest_format: DigestFormat  // 'short' | 'detailed'
  digest_include_summaries: boolean
  telegram_chat_id: string | null
  telegram_enabled: boolean
  timezone?: string
  week_start_day?: number
}
```

### Пример JSON запроса:
```json
{
  "digest_enabled": true,
  "digest_frequency": "daily",
  "digest_custom_schedule": {
    "time": "09:00",
    "days": [1, 2, 3, 4, 5],
    "timezone": "UTC"
  },
  "digest_format": "short",
  "digest_include_summaries": true,
  "telegram_chat_id": null,
  "telegram_enabled": false,
  "timezone": "UTC",
  "week_start_day": 0
}
```

**Важно:** `telegram_digest_mode` НЕ отправляется фронтендом!

---

## Что ожидает backend

### Модель DigestSettingsUpdate (backend/app/api/v1/endpoints/users.py):
```python
class DigestSettingsUpdate(BaseModel):
    digest_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    digest_custom_schedule: Optional[dict] = None
    digest_format: Optional[str] = None
    digest_include_summaries: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    telegram_digest_mode: Optional[str] = None  # НЕ отправляется фронтендом
    timezone: Optional[str] = None
    week_start_day: Optional[int] = None
```

---

## Типы в базе данных

### Таблица user_preferences:
```sql
digest_enabled          BOOLEAN
digest_frequency        digestfrequency ENUM('daily', 'weekly', 'custom')
digest_custom_schedule  JSONB           -- Хранит {"time": "09:00", "days": [1,2,3,4,5], "timezone": "UTC"}
digest_format           digestformat ENUM('short', 'detailed')
digest_include_summaries BOOLEAN
telegram_chat_id        VARCHAR(255)
telegram_enabled        BOOLEAN
telegram_digest_mode    telegramdigestmode ENUM('all', 'tracked')  -- НЕ обновляется через этот endpoint
timezone                VARCHAR(50)
week_start_day          INTEGER
```

**Важно:** Enum типы в базе данных используют старые имена БЕЗ подчеркиваний:
- `digestfrequency` (не `digest_frequency`)
- `digestformat` (не `digest_format`)
- `telegramdigestmode` (не `telegram_digest_mode`)

---

## Endpoint обработки

**PUT `/api/v1/users/preferences/digest`**

**Функция:** `update_digest_settings()`

**Обработка:**
1. Получает `DigestSettingsUpdate` из запроса
2. Проверяет существование `UserPreferences`
3. Строит динамический SQL UPDATE запрос
4. Использует позиционные параметры `$1, $2, ...`
5. Конвертирует в именованные `:param_1, :param_2, ...` для SQLAlchemy
6. Применяет CAST для enum типов к старым именам

---

## Потенциальные проблемы

### 1. digest_custom_schedule = null
**Проблема:** Если фронтенд отправляет `null`, backend НЕ обновит поле (т.к. `if settings.digest_custom_schedule is not None`).

**Текущий код:**
```python
if settings.digest_custom_schedule is not None:
    updates.append(f"digest_custom_schedule = ${len(param_values) + 1}::jsonb")
    param_values.append(json.dumps(settings.digest_custom_schedule))
```

**Результат:** Если `null`, поле не обновится.

### 2. telegram_digest_mode не отправляется
**Проблема:** Frontend не отправляет `telegram_digest_mode`, но backend ожидает.

**Результат:** Поле не обновится через этот endpoint (но это нормально, т.к. это Optional).

### 3. digest_custom_schedule при frequency != 'custom'
**Вопрос:** Что происходит, если `digest_frequency = 'daily'`, но `digest_custom_schedule` не null?

**Текущее поведение:** Обновляется и `digest_frequency`, и `digest_custom_schedule` независимо.

---

## Рекомендации

### Исправление для digest_custom_schedule = null:
```python
if settings.digest_custom_schedule is not None:
    # Если отправлен объект или null
    if settings.digest_custom_schedule is not None:
        updates.append(f"digest_custom_schedule = ${len(param_values) + 1}::jsonb")
        param_values.append(json.dumps(settings.digest_custom_schedule))
    # Или использовать специальное значение для удаления:
    # else:
    #     updates.append("digest_custom_schedule = NULL")
```

**Но:** В текущей реализации, если `frequency != 'custom'`, `digest_custom_schedule` не используется, поэтому это не критично.

---

## Проверка запроса

### Что нужно проверить:
1. ✅ Все поля отправляются корректно
2. ✅ Типы соответствуют ожидаемым
3. ⚠️ `digest_custom_schedule = null` не обновит поле
4. ⚠️ `telegram_digest_mode` не отправляется (но это OK, т.к. Optional)
5. ✅ Enum значения валидируются
6. ✅ JSON правильно сериализуется для `digest_custom_schedule`

