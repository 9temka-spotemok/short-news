# Полный анализ Save Settings запроса

## 1. Что отправляет фронтенд (DigestSettingsPage.tsx)

### Запрос: PUT `/api/v1/users/preferences/digest`

### JSON body:
```json
{
  "digest_enabled": boolean,
  "digest_frequency": "daily" | "weekly" | "custom",
  "digest_custom_schedule": {
    "time": "09:00",
    "days": [0-6],  // Массив чисел от 0 до 6
    "timezone": "UTC"
  } | null,
  "digest_format": "short" | "detailed",
  "digest_include_summaries": boolean,
  "telegram_chat_id": string | null,
  "telegram_enabled": boolean,
  "timezone": string,  // Например: "UTC", "America/New_York"
  "week_start_day": 0 | 1  // 0=Sunday, 1=Monday
}
```

### Важные моменты:
- ✅ Все поля отправляются (кроме `telegram_digest_mode`)
- ⚠️ `digest_custom_schedule` может быть `null`
- ⚠️ `telegram_digest_mode` НЕ отправляется (но это OK, т.к. Optional в backend)

---

## 2. Что ожидает backend (DigestSettingsUpdate)

### Модель Pydantic:
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

### Валидация:
- `digest_frequency`: должен быть 'daily', 'weekly', или 'custom'
- `digest_format`: должен быть 'short' или 'detailed'
- `telegram_digest_mode`: должен быть 'all' или 'tracked' (если передан)

---

## 3. Типы в базе данных (user_preferences)

| Поле | Тип в БД | Enum | Nullable | Default |
|------|----------|------|----------|---------|
| `digest_enabled` | BOOLEAN | - | false | false |
| `digest_frequency` | **digestfrequency** ENUM | 'daily', 'weekly', 'custom' | false | 'daily' |
| `digest_custom_schedule` | JSONB | - | true | {} |
| `digest_format` | **digestformat** ENUM | 'short', 'detailed' | false | 'short' |
| `digest_include_summaries` | BOOLEAN | - | false | true |
| `telegram_chat_id` | VARCHAR(255) | - | true | NULL |
| `telegram_enabled` | BOOLEAN | - | false | false |
| `telegram_digest_mode` | **telegramdigestmode** ENUM | 'all', 'tracked' | true | 'all' |
| `timezone` | VARCHAR(50) | - | false | 'UTC' |
| `week_start_day` | INTEGER | - | false | 0 |

**Важно:** Enum типы в PostgreSQL используют старые имена БЕЗ подчеркиваний:
- `digestfrequency` (не `digest_frequency`)
- `digestformat` (не `digest_format`)
- `telegramdigestmode` (не `telegram_digest_mode`)

---

## 4. Обработка запроса (update_digest_settings)

### Шаги:
1. **Получение данных:** `DigestSettingsUpdate` из request body
2. **Проверка preferences:** Запрос `UserPreferences` из БД
3. **Создание defaults:** Если preferences нет, создается с default значениями
4. **Построение SQL:** Динамический UPDATE запрос с позиционными параметрами
5. **Конвертация параметров:** `$1, $2, ...` → `:param_1, :param_2, ...`
6. **CAST для enum:** Явное приведение к старым именам enum типов
7. **Выполнение:** Raw SQL через SQLAlchemy `text()`

### Особенности обработки:

#### digest_custom_schedule:
```python
if settings.digest_custom_schedule is not None:
    updates.append(f"digest_custom_schedule = ${len(param_values) + 1}::jsonb")
    param_values.append(json.dumps(settings.digest_custom_schedule))
```
**⚠️ Проблема:** Если фронтенд отправляет `null`, поле НЕ обновится!

#### Enum типы:
```python
# digest_frequency
updates.append(f"digest_frequency = CAST(${len(param_values) + 1} AS text)::digestfrequency")
param_values.append(settings.digest_frequency)

# digest_format
updates.append(f"digest_format = CAST(${len(param_values) + 1} AS text)::digestformat")
param_values.append(settings.digest_format)

# telegram_digest_mode
updates.append(f"telegram_digest_mode = CAST(${len(param_values) + 1} AS text)::telegramdigestmode")
param_values.append(settings.telegram_digest_mode)
```

---

## 5. Потенциальные проблемы

### 🔴 Проблема 1: digest_custom_schedule = null не обновляет поле
**Ситуация:** Если фронтенд отправляет `digest_custom_schedule: null`, backend НЕ обновит поле.

**Причина:** 
```python
if settings.digest_custom_schedule is not None:  # False для None
    # Не выполнится
```

**Решение:** 
```python
# Разрешить явную установку NULL
if settings.digest_custom_schedule is not None:
    updates.append(f"digest_custom_schedule = ${len(param_values) + 1}::jsonb")
    param_values.append(json.dumps(settings.digest_custom_schedule))
# Добавить обработку None для очистки поля
```

**Текущее поведение:** Если `frequency != 'custom'`, это не критично, т.к. поле не используется.

### 🟡 Проблема 2: telegram_digest_mode не отправляется
**Ситуация:** Фронтенд не отправляет `telegram_digest_mode`, но backend ожидает.

**Результат:** Поле не обновляется через этот endpoint (но это нормально, т.к. Optional).

**Решение:** Добавить поле в фронтенд, если нужно управлять им через UI.

### 🟢 Все остальное работает корректно:
- ✅ Enum значения валидируются
- ✅ JSON правильно сериализуется
- ✅ Типы соответствуют ожидаемым
- ✅ Позиционные параметры корректно конвертируются

---

## 6. Тестирование запроса

### Пример успешного запроса:
```bash
curl -X PUT "http://localhost:8000/api/v1/users/preferences/digest" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "digest_enabled": true,
    "digest_frequency": "daily",
    "digest_custom_schedule": {"time": "09:00", "days": [1,2,3,4,5], "timezone": "UTC"},
    "digest_format": "short",
    "digest_include_summaries": true,
    "telegram_chat_id": null,
    "telegram_enabled": false,
    "timezone": "UTC",
    "week_start_day": 0
  }'
```

### Ожидаемый ответ:
```json
{
  "status": "success",
  "digest_settings": {
    "digest_enabled": true,
    "digest_frequency": "daily",
    "digest_custom_schedule": {"time": "09:00", "days": [1,2,3,4,5], "timezone": "UTC"},
    "digest_format": "short",
    "digest_include_summaries": true,
    "telegram_chat_id": null,
    "telegram_enabled": false,
    "telegram_digest_mode": "all",
    "timezone": "UTC",
    "week_start_day": 0
  }
}
```

---

## 7. Рекомендации

1. **Исправить обработку `digest_custom_schedule = null`:**
   - Разрешить явную установку NULL для очистки поля
   
2. **Добавить `telegram_digest_mode` в фронтенд (опционально):**
   - Если нужно управлять этим полем через UI
   
3. **Валидация `digest_custom_schedule` при `frequency = 'custom'`:**
   - Убедиться, что когда `frequency = 'custom'`, `digest_custom_schedule` не null

---

## Итог

**✅ Запрос работает корректно** для большинства случаев.

**⚠️ Единственная проблема:** `digest_custom_schedule = null` не обновляет поле в БД (но это не критично, т.к. используется только при `frequency = 'custom'`).

