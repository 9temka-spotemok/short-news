# Анализ рисков при исправлении персонализации

**Дата:** 2025-01-31  
**Версия:** 0.1.0  
**Статус:** Требуется внимание

## 📋 Содержание

1. [Обзор проблемы](#обзор-проблемы)
2. [Модули, использующие subscribed_companies](#модули-использующие-subscribed_companies)
3. [Анализ рисков по модулям](#анализ-рисков-по-модулям)
4. [Рекомендации по исправлению](#рекомендации-по-исправлению)
5. [План миграции](#план-миграции)

---

## Обзор проблемы

**Ключевая проблема:** Персонализация должна быть основана на `user_id` компаний, а НЕ на `subscribed_companies`. Однако `subscribed_companies` используется в нескольких модулях для других целей.

**Два разных понятия:**
1. **"My Competitors" (List Competitor)** = компании с `Company.user_id = current_user.id` (основа персонализации)
2. **"Tracked companies"** = компании из `UserPreferences.subscribed_companies` (используются для дайджестов и уведомлений)

**Важно:** `subscribed_companies` может быть подмножеством компаний пользователя, но не должно использоваться для базовой персонализации новостей.

---

## Модули, использующие subscribed_companies

### 1. ✅ DigestService (дайджесты)
**Файл:** `backend/app/domains/notifications/services/digest_service.py`

**Использование:**
- `_fetch_news()` - фильтрует новости по `subscribed_companies` когда `tracked_only=True`
- `_filter_news_by_preferences()` - дополнительная фильтрация по `subscribed_companies`
- `_rank_news_by_relevance()` - повышает релевантность новостей из `subscribed_companies`

**Проблема:** 
- При `tracked_only=False` дайджест показывает ВСЕ новости (не фильтрует по `user_id` компаний)
- При `tracked_only=True` дайджест фильтрует по `subscribed_companies`, но это может быть подмножеством

**Риск:** 🔴 **ВЫСОКИЙ**
- Дайджест может показывать новости из чужих компаний (если `tracked_only=False`)
- Несоответствие: дайджест использует `subscribed_companies`, а основной API новостей должен использовать `user_id`

### 2. ✅ NotificationService (уведомления)
**Файл:** `backend/app/domains/notifications/services/notification_service.py`

**Использование:**
- `_evaluate_news_match()` - проверяет, находится ли `news_item.company_id` в `preferences.subscribed_companies`
- Отправляет уведомления только для компаний из `subscribed_companies`

**Проблема:**
- Уведомления отправляются только для компаний из `subscribed_companies`
- Если пользователь удалил компанию из "Tracked companies", но она осталась в "List Competitor", уведомления не будут приходить

**Риск:** 🟡 **СРЕДНИЙ**
- Это может быть правильным поведением (пользователь явно отписался)
- Но нужно убедиться, что это соответствует ожиданиям пользователя

### 3. ✅ CompetitorNotificationService (уведомления о конкурентах)
**Файл:** `backend/app/domains/competitors/services/notification_service.py`

**Использование:**
- `_load_watchers()` - находит всех пользователей, у которых `company_id` в `subscribed_companies`
- Используется для отправки уведомлений о изменениях в компаниях

**Проблема:**
- Ищет watchers по `subscribed_companies`, а не по `user_id` компаний
- Если пользователь удалил компанию из "Tracked companies", но она осталась в "List Competitor", он не получит уведомления

**Риск:** 🟡 **СРЕДНИЙ**
- Это может быть правильным поведением (пользователь явно отписался)
- Но нужно убедиться, что это соответствует ожиданиям пользователя

### 4. ✅ Telegram бот (дайджесты)
**Файлы:** 
- `backend/app/api/v1/endpoints/telegram.py`
- `backend/scripts/telegram_polling.py`

**Использование:**
- Использует `telegram_digest_mode` ('all' или 'tracked')
- При `tracked=True` передаёт `tracked_only=True` в `DigestService`
- `DigestService` фильтрует по `subscribed_companies` когда `tracked_only=True`

**Проблема:**
- Зависит от `DigestService`, который использует `subscribed_companies`
- Несоответствие с основной логикой персонализации

**Риск:** 🟡 **СРЕДНИЙ**
- Зависит от исправления `DigestService`

### 5. ✅ Frontend (TrackedCompaniesManager)
**Файл:** `frontend/src/components/TrackedCompaniesManager.tsx`

**Использование:**
- Управляет `subscribed_companies` через `updateUserPreferences`
- Показывает компании из `subscribed_companies`

**Проблема:**
- Компонент управляет "Tracked companies", но не синхронизирован с "List Competitor"
- Пользователь может удалить компанию из "Tracked companies", но она останется в "List Competitor"

**Риск:** 🟢 **НИЗКИЙ**
- Это UI проблема, не критична для безопасности

### 6. ✅ Onboarding (создание компаний)
**Файл:** `backend/app/api/v1/endpoints/onboarding.py`

**Использование:**
- При завершении онбординга создаёт компании с `user_id = current_user.id`
- Добавляет эти компании в `subscribed_companies`

**Проблема:**
- После онбординга `subscribed_companies` = все компании пользователя
- Но потом пользователь может удалить некоторые из "Tracked companies"

**Риск:** 🟢 **НИЗКИЙ**
- Это начальное состояние, не критично

---

## Анализ рисков по модулям

### 🔴 Критические риски

#### 1. DigestService - показывает новости из чужих компаний

**Проблема:**
```python
# Текущий код в _fetch_news()
if tracked_only and user_prefs.subscribed_companies:
    query = query.where(NewsItem.company_id.in_(user_prefs.subscribed_companies))
# Если tracked_only=False, фильтрация НЕ применяется!
```

**Последствия:**
- При `tracked_only=False` дайджест показывает ВСЕ новости из БД (включая чужие компании)
- Нарушение изоляции данных

**Решение:**
```python
# ВСЕГДА фильтровать по user_id компаний
user_company_ids = await get_user_company_ids(user, db)
query = query.where(NewsItem.company_id.in_(user_company_ids))

# Дополнительно фильтровать по subscribed_companies если tracked_only=True
if tracked_only and user_prefs.subscribed_companies:
    subscribed_ids = set(user_prefs.subscribed_companies)
    user_company_ids = [cid for cid in user_company_ids if cid in subscribed_ids]
    query = query.where(NewsItem.company_id.in_(user_company_ids))
```

### 🟡 Средние риски

#### 2. NotificationService - уведомления только для subscribed_companies

**Проблема:**
- Уведомления отправляются только для компаний из `subscribed_companies`
- Если пользователь удалил компанию из "Tracked companies", но она осталась в "List Competitor", уведомления не будут приходить

**Вопрос:** Это правильное поведение?

**Варианты решения:**

**Вариант A: Уведомления для всех компаний пользователя (user_id)**
```python
# Проверять, что компания принадлежит пользователю
company = await check_company_access(news_item.company_id, user, db)
if company:
    should_notify = True
```

**Вариант B: Уведомления только для subscribed_companies (текущее поведение)**
```python
# Оставить как есть - пользователь явно отписался
if news_item.company_id in preferences.subscribed_companies:
    should_notify = True
```

**Рекомендация:** Вариант B (оставить как есть), но добавить проверку, что компания принадлежит пользователю:
```python
# Проверяем, что компания принадлежит пользователю
company = await check_company_access(news_item.company_id, user, db)
if not company:
    return  # Не отправляем уведомления о чужих компаниях

# Проверяем, что компания в subscribed_companies
if settings.company_alerts and preferences.subscribed_companies:
    if news_item.company_id in preferences.subscribed_companies:
        should_notify = True
```

#### 3. CompetitorNotificationService - поиск watchers

**Проблема:**
- Ищет watchers по `subscribed_companies`, а не по `user_id` компаний
- Может не найти всех пользователей, которые должны получить уведомление

**Решение:**
```python
async def _load_watchers(self, company_id: UUID) -> List[UUID]:
    # Сначала проверяем, что компания принадлежит кому-то (user_id)
    company_result = await self._session.execute(
        select(Company).where(Company.id == company_id)
    )
    company = company_result.scalar_one_or_none()
    
    if not company:
        return []
    
    watchers: List[UUID] = []
    
    # Если компания принадлежит пользователю (user_id), он должен получить уведомление
    if company.user_id:
        watchers.append(company.user_id)
    
    # Также ищем пользователей, у которых компания в subscribed_companies
    result = await self._session.execute(select(UserPreferences))
    company_token = str(company_id)
    for preferences in result.scalars().all():
        companies = self._normalized_company_ids(preferences.subscribed_companies or [])
        if company_token in companies:
            if preferences.user_id not in watchers:
                watchers.append(preferences.user_id)
    
    return watchers
```

### 🟢 Низкие риски

#### 4. Frontend - TrackedCompaniesManager

**Проблема:**
- Не синхронизирован с "List Competitor"
- Пользователь может удалить компанию из "Tracked companies", но она останется в "List Competitor"

**Решение:**
- Это ожидаемое поведение (два разных списка)
- Можно добавить подсказку: "Компания останется в 'My Competitors', но вы перестанете получать уведомления"

---

## Рекомендации по исправлению

### Приоритет 1: Критические исправления

#### 1. Исправить DigestService._fetch_news()

**Файл:** `backend/app/domains/notifications/services/digest_service.py`

**Изменения:**
```python
async def _fetch_news(
    self,
    user_prefs: UserPreferences,
    date_from: datetime,
    date_to: datetime,
    tracked_only: bool,
) -> List[NewsItem]:
    from app.core.access_control import get_user_company_ids
    from app.models import User
    
    # ВСЕГДА получаем компании пользователя (user_id)
    user = await self._session.get(User, user_prefs.user_id)
    user_company_ids = await get_user_company_ids(user, self._session)
    
    if not user_company_ids:
        logger.info("User has no companies, returning empty digest")
        return []
    
    query = select(NewsItem).where(
        and_(
            NewsItem.published_at >= date_from,
            NewsItem.published_at <= date_to,
            NewsItem.company_id.in_(user_company_ids)  # ВСЕГДА фильтруем по user_id
        )
    )
    
    # Дополнительно фильтруем по subscribed_companies если tracked_only=True
    if tracked_only and user_prefs.subscribed_companies:
        subscribed_ids = set(user_prefs.subscribed_companies)
        # Пересечение: только компании, которые и в user_id, и в subscribed_companies
        filtered_ids = [cid for cid in user_company_ids if cid in subscribed_ids]
        if filtered_ids:
            query = query.where(NewsItem.company_id.in_(filtered_ids))
        else:
            # Если нет пересечения, возвращаем пустой список
            return []
    
    if tracked_only and user_prefs.interested_categories:
        query = query.where(NewsItem.category.in_(user_prefs.interested_categories))
    
    query = query.order_by(desc(NewsItem.published_at))
    result = await self._session.execute(query)
    news_items = list(result.scalars().all())
    logger.info("Fetched %s news items", len(news_items))
    return news_items
```

#### 2. Исправить NotificationService._evaluate_news_match()

**Файл:** `backend/app/domains/notifications/services/notification_service.py`

**Изменения:**
```python
async def _evaluate_news_match(
    self,
    *,
    news_item: NewsItem,
    settings: NotificationSettings,
    preferences: UserPreferences,
) -> tuple[NotificationType, NotificationPriority, bool]:
    from app.core.access_control import check_company_access
    from app.models import User
    
    should_notify = False
    notification_type = NotificationType.NEW_NEWS
    priority = NotificationPriority.MEDIUM
    
    # СНАЧАЛА проверяем, что компания принадлежит пользователю (user_id)
    user = await self._session.get(User, preferences.user_id)
    company = await check_company_access(news_item.company_id, user, self._session)
    
    if not company:
        # Компания не принадлежит пользователю - не отправляем уведомление
        return notification_type, priority, False
    
    # Company-based alerts (только для subscribed_companies)
    if settings.company_alerts and preferences.subscribed_companies:
        if news_item.company_id in preferences.subscribed_companies:
            should_notify = True
            # ... остальная логика
```

#### 3. Исправить CompetitorNotificationService._load_watchers()

**Файл:** `backend/app/domains/competitors/services/notification_service.py`

**Изменения:**
```python
async def _load_watchers(self, company_id: UUID) -> List[UUID]:
    watchers: List[UUID] = []
    
    # Сначала проверяем, кому принадлежит компания (user_id)
    company_result = await self._session.execute(
        select(Company).where(Company.id == company_id)
    )
    company = company_result.scalar_one_or_none()
    
    if company and company.user_id:
        # Владелец компании должен получить уведомление
        watchers.append(company.user_id)
    
    # Также ищем пользователей, у которых компания в subscribed_companies
    result = await self._session.execute(select(UserPreferences))
    company_token = str(company_id)
    for preferences in result.scalars().all():
        companies = self._normalized_company_ids(preferences.subscribed_companies or [])
        if company_token in companies:
            # Проверяем, что компания действительно принадлежит пользователю или является глобальной
            if company and (company.user_id == preferences.user_id or company.user_id is None):
                if preferences.user_id not in watchers:
                    watchers.append(preferences.user_id)
    
    # Удаляем дубликаты
    seen: Set[UUID] = set()
    unique_watchers: List[UUID] = []
    for watcher_id in watchers:
        if watcher_id not in seen:
            unique_watchers.append(watcher_id)
            seen.add(watcher_id)
    
    return unique_watchers
```

### Приоритет 2: Улучшения

#### 4. Обновить DigestService._rank_news_by_relevance()

**Файл:** `backend/app/domains/notifications/services/digest_service.py`

**Изменения:**
```python
def _rank_news_by_relevance(
    self,
    news_items: List[NewsItem],
    user_prefs: UserPreferences,
) -> List[NewsItem]:
    def calculate_score(news: NewsItem) -> float:
        score = news.priority_score or 0.5
        
        # Повышаем релевантность для компаний из subscribed_companies
        # (но все новости уже отфильтрованы по user_id компаний)
        if user_prefs.subscribed_companies and news.company_id in user_prefs.subscribed_companies:
            score += 0.3
        
        # ... остальная логика
```

---

## План миграции

### Этап 1: Критические исправления (1-2 дня)

1. ✅ Создать `access_control.py` с функциями проверки доступа
2. ✅ Исправить `DigestService._fetch_news()` - ВСЕГДА фильтровать по `user_id`
3. ✅ Исправить `NotificationService._evaluate_news_match()` - проверять `user_id`
4. ✅ Исправить `CompetitorNotificationService._load_watchers()` - искать по `user_id`

### Этап 2: Тестирование (1 день)

1. ✅ Написать тесты для `DigestService` с разными сценариями
2. ✅ Написать тесты для `NotificationService`
3. ✅ Написать тесты для `CompetitorNotificationService`
4. ✅ Проверить интеграцию с Telegram ботом

### Этап 3: Мониторинг (непрерывно)

1. ✅ Логировать все случаи, когда фильтрация применяется
2. ✅ Мониторить количество уведомлений до/после изменений
3. ✅ Собрать обратную связь от пользователей

---

## Чек-лист перед деплоем

### Backend

- [ ] `DigestService._fetch_news()` всегда фильтрует по `user_id` компаний
- [ ] `DigestService._fetch_news()` дополнительно фильтрует по `subscribed_companies` если `tracked_only=True`
- [ ] `NotificationService._evaluate_news_match()` проверяет `user_id` перед отправкой уведомления
- [ ] `CompetitorNotificationService._load_watchers()` ищет watchers по `user_id` и `subscribed_companies`
- [ ] Все тесты проходят
- [ ] Нет линтер ошибок

### Тестирование

- [ ] Дайджест с `tracked_only=False` показывает только новости из компаний пользователя
- [ ] Дайджест с `tracked_only=True` показывает только новости из `subscribed_companies` (которые также принадлежат пользователю)
- [ ] Уведомления отправляются только для компаний пользователя
- [ ] Уведомления отправляются только для компаний из `subscribed_companies` (если включены company_alerts)
- [ ] Telegram бот работает корректно

### Документация

- [ ] Обновлена документация API
- [ ] Обновлены комментарии в коде
- [ ] Создан документ с описанием изменений для пользователей

---

## Выводы

### ✅ Что нужно исправить

1. **DigestService** - критично: всегда фильтровать по `user_id`, дополнительно по `subscribed_companies` если `tracked_only=True`
2. **NotificationService** - важно: проверять `user_id` перед отправкой уведомлений
3. **CompetitorNotificationService** - важно: искать watchers по `user_id` и `subscribed_companies`

### ✅ Что можно оставить

1. **TrackedCompaniesManager** - UI компонент, не критично
2. **Onboarding** - начальное состояние, не критично
3. **Логика subscribed_companies** - правильная для дайджестов и уведомлений (подмножество компаний пользователя)

### ✅ Итоговая логика

1. **Персонализация новостей (основной API):** по `user_id` компаний ✅
2. **Дайджесты (tracked_only=False):** по `user_id` компаний ✅
3. **Дайджесты (tracked_only=True):** по пересечению `user_id` компаний и `subscribed_companies` ✅
4. **Уведомления:** только для компаний из `subscribed_companies`, которые принадлежат пользователю (`user_id`) ✅

---

## Примечания

- `subscribed_companies` остается полезным для дайджестов и уведомлений (подмножество компаний пользователя)
- Основная персонализация (новости) должна быть по `user_id` компаний
- Все проверки доступа должны включать проверку `user_id` для безопасности


