# Исправление ошибки UI при переключении на вкладку Digest

## Проблема
При переключении на вкладку Digest возникала ошибка:
```
Uncaught TypeError: Cannot read properties of undefined (reading 'map')
at DashboardPage.tsx:597
```

## Причина
Код пытался вызвать `Object.entries(digest.categories).map()` без проверки на существование `digest.categories`. Когда digest только загружается или когда API возвращает пустой ответ, поле `categories` может быть `undefined`.

## Исправления

### 1. Обновлен интерфейс DigestData
Сделали поля `categories` и `statistics` необязательными:

```typescript
interface DigestData {
  date_from: string
  date_to: string
  news_count: number
  categories?: Record<string, NewsItem[]>  // <- добавлен ?
  statistics?: {                            // <- добавлен ?
    total_news: number
    by_category: Record<string, number>
    by_source: Record<string, number>
    avg_priority: number
  }
  format: string
}
```

### 2. Добавлена проверка перед .map()
**Строка 604:**
```typescript
// Было:
{Object.entries(digest.categories).map(([category, items]) => (

// Стало:
{digest.categories && Object.entries(digest.categories).map(([category, items]) => (
```

### 3. Добавлена проверка для пустого состояния
**Строка 643:**
```typescript
// Было:
{Object.keys(digest.categories).length === 0 && (

// Стало:
{(!digest.categories || Object.keys(digest.categories).length === 0) && (
```

## Результат
✅ Ошибка исправлена
✅ UI корректно обрабатывает случаи когда:
  - digest еще не загружен (null)
  - digest загружен, но categories undefined
  - digest загружен, но categories пустой объект {}
  - digest загружен с данными

## Тестирование
Теперь можно безопасно:
1. Переключаться на вкладку Digest
2. Нажимать кнопки Daily/Weekly/Custom Digest
3. Получать пустые результаты без ошибок

## Файлы изменены
- `frontend/src/pages/DashboardPage.tsx`
  - Обновлен интерфейс DigestData (строки 31-43)
  - Добавлена проверка на строке 604
  - Добавлена проверка на строке 643



