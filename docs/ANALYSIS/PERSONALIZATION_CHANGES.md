# Что изменится после выполнения плана исправлений персонализации

**Дата:** 2025-01-31  
**Версия:** 0.1.0

## 📋 Содержание

1. [Изменения в безопасности](#изменения-в-безопасности)
2. [Изменения в поведении API](#изменения-в-поведении-api)
3. [Изменения в пользовательском интерфейсе](#изменения-в-пользовательском-интерфейсе)
4. [Новые файлы и функции](#новые-файлы-и-функции)
5. [Влияние на производительность](#влияние-на-производительность)
6. [Миграция и обратная совместимость](#миграция-и-обратная-совместимость)

---

## ⚠️ КРИТИЧЕСКИ ВАЖНО: Основная суть персонализации

**Персонализация основана на `user_id` в таблице `companies`, а НЕ на `subscribed_companies`!**

- **"List Competitor" (My Competitors)** = компании с `Company.user_id = current_user.id`
- **"Tracked companies"** = компании из `UserPreferences.subscribed_companies` (используются для фильтрации новостей, но это НЕПРАВИЛЬНО!)

**Проблема текущей реализации:**
- При онбординге создаются компании с `user_id = current_user.id` (5 компаний)
- Эти компании также добавляются в `subscribed_companies`
- Когда пользователь убирает 2 компании из "Tracked companies" (удаляет из `subscribed_companies`), они остаются в "List Competitor" (потому что `user_id` не изменяется)
- Новости фильтруются по `subscribed_companies`, но должны фильтроваться по компаниям с `user_id = current_user.id`

**Правильная логика после исправлений:**
- Компании: фильтруются по `Company.user_id = current_user.id` ✅
- Новости: должны фильтроваться по `NewsItem.company_id IN (SELECT id FROM companies WHERE user_id = current_user.id)` ✅
- Единая логика: "List Competitor" и новости используют один источник - `user_id` компаний ✅

---

## Изменения в безопасности

### 🔒 До исправлений

**Текущее состояние:**
- ❌ Пользователь может получить любую новость по ID, даже если она не относится к его компаниям (`user_id`)
- ❌ Пользователь может редактировать/удалять чужие новости
- ❌ Пользователь может узнать о существовании чужих компаний (разные ответы 404 vs 403)
- ❌ Пользователь может сравнивать чужие компании
- ❌ Пользователь может получить предложения конкурентов для чужих компаний
- ⚠️ **КРИТИЧНО:** Новости фильтруются по `subscribed_companies`, но должны фильтроваться по компаниям с `user_id = current_user.id`
- ⚠️ **Проблема:** При удалении компании из "Tracked companies" (`subscribed_companies`) она остаётся в "List Competitor" (потому что `user_id` не изменяется)

**Примеры уязвимостей:**

```python
# ДО: Любой пользователь может получить любую новость
GET /api/v1/news/{news_id}
# Ответ: 200 OK с данными новости (даже если она не относится к подпискам пользователя)

# ДО: Пользователь может узнать о существовании чужих компаний
GET /api/v1/companies/{company_id}
# Если компания существует, но принадлежит другому пользователю:
# Ответ: 403 Forbidden (раскрывает информацию о существовании)
# Если компания не существует:
# Ответ: 404 Not Found
# → Пользователь может различать эти случаи!
```

### ✅ После исправлений

**Новое состояние:**
- ✅ Пользователь может получить только новости из своих компаний (`user_id = current_user.id`)
- ✅ Пользователь может редактировать/удалять только новости из своих компаний
- ✅ Пользователь не может узнать о существовании чужих компаний (всегда 404)
- ✅ Пользователь может сравнивать только свои компании (`user_id = current_user.id`)
- ✅ Пользователь может получить предложения только для своих компаний
- ✅ Новости фильтруются по компаниям с `user_id = current_user.id` (НЕ по `subscribed_companies`!)
- ✅ Единая логика: "List Competitor" и новости используют один источник - `user_id` компаний

**Примеры исправлений:**

```python
# ПОСЛЕ: Проверка доступа в SQL запросе
GET /api/v1/companies/{company_id}
# Если компания существует, но принадлежит другому пользователю:
# Ответ: 404 Not Found (не раскрывает информацию)
# Если компания не существует:
# Ответ: 404 Not Found
# → Пользователь не может различить эти случаи (безопасно!)

# ПОСЛЕ: Проверка доступа к новости
GET /api/v1/news/{news_id}
# Если новость не относится к подпискам пользователя:
# Ответ: 403 Forbidden
# Если новость относится к подпискам:
# Ответ: 200 OK с данными
```

---

## Изменения в поведении API

### 0. `GET /api/v1/news/` - Фильтрация списка новостей

**ДО:**
```python
# В GET /news/
if current_user and not parsed_company_ids:
    prefs_result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == current_user.id)
    )
    user_prefs = prefs_result.scalar_one_or_none()
    
    if user_prefs and user_prefs.subscribed_companies:
        # НЕПРАВИЛЬНО: фильтруем по subscribed_companies
        parsed_company_ids = user_prefs.subscribed_companies
```

**ПОСЛЕ:**
```python
# В GET /news/
if current_user and not parsed_company_ids:
    # ПРАВИЛЬНО: фильтруем по user_id компаний
    companies_result = await db.execute(
        select(Company.id).where(Company.user_id == current_user.id)
    )
    user_company_ids = [c.id for c in companies_result.scalars().all()]
    parsed_company_ids = user_company_ids
```

**Изменения в поведении:**
- ✅ Новости фильтруются по компаниям с `user_id = current_user.id` (НЕ по `subscribed_companies`!)
- ✅ Единая логика: "List Competitor" и новости используют один источник - `user_id` компаний
- ✅ Если пользователь удалил компанию из "Tracked companies", она всё равно остаётся в новостях (потому что `user_id` не изменяется)

### 1. `GET /api/v1/news/{news_id}`

**ДО:**
```python
@router.get("/{news_id}")
async def get_news_item(
    news_id: str,
    facade: NewsFacade = Depends(get_news_facade),
):
    news_item = await facade.get_news_item(news_id)
    # НЕТ ПРОВЕРКИ ДОСТУПА
    return serialize_news_item(news_item)
```

**ПОСЛЕ:**
```python
@router.get("/{news_id}")
async def get_news_item(
    news_id: str,
    current_user: User = Depends(get_current_user),
    facade: NewsFacade = Depends(get_news_facade),
    db: AsyncSession = Depends(get_db),
):
    news_item = await facade.get_news_item(news_id)
    
    # НОВАЯ ПРОВЕРКА ДОСТУПА (по user_id компании, НЕ по subscribed_companies!)
    if current_user:
        # Проверяем, что компания новости принадлежит пользователю
        company_result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == news_item.company_id,
                    Company.user_id == current_user.id
                )
            )
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return serialize_news_item(news_item)
```

**Изменения в поведении:**
- ✅ Теперь требуется аутентификация (`current_user`)
- ✅ Проверяется, что компания новости принадлежит пользователю (`Company.user_id == current_user.id`)
- ✅ Если новость не относится к компаниям пользователя → 403 Forbidden
- ✅ Если новость относится к компаниям пользователя → 200 OK

### 2. `PUT /api/v1/news/{news_id}` и `DELETE /api/v1/news/{news_id}`

**ДО:**
```python
@router.put("/{news_id}")
async def update_news(
    news_id: str,
    payload: NewsUpdateSchema,
    facade: NewsFacade = Depends(get_news_facade),
):
    # НЕТ ПРОВЕРКИ ДОСТУПА
    news_item = await facade.update_news(news_id, payload.model_dump())
    return serialize_news_item(news_item)
```

**ПОСЛЕ:**
```python
@router.put("/{news_id}")
async def update_news(
    news_id: str,
    payload: NewsUpdateSchema,
    current_user: User = Depends(get_current_user),
    facade: NewsFacade = Depends(get_news_facade),
    db: AsyncSession = Depends(get_db),
):
    # СНАЧАЛА ПРОВЕРЯЕМ ДОСТУП (по user_id компании, НЕ по subscribed_companies!)
    news_item = await facade.get_news_item(news_id)
    if current_user:
        company_result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == news_item.company_id,
                    Company.user_id == current_user.id
                )
            )
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # ТОЛЬКО ПОСЛЕ ПРОВЕРКИ ОБНОВЛЯЕМ
    news_item = await facade.update_news(news_id, payload.model_dump())
    return serialize_news_item(news_item)
```

**Изменения в поведении:**
- ✅ Добавлена проверка доступа перед обновлением/удалением
- ✅ Пользователь может редактировать/удалять только новости из своих компаний (`user_id = current_user.id`)
- ✅ Попытка редактировать чужую новость → 403 Forbidden

### 3. `GET /api/v1/companies/{company_id}`

**ДО:**
```python
@router.get("/{company_id}")
async def get_company(
    company_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    # СНАЧАЛА ПОЛУЧАЕМ КОМПАНИЮ
    result = await db.execute(
        select(Company).where(Company.id == uuid_obj)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # ПРОВЕРКА ДОСТУПА ПОСЛЕ ПОЛУЧЕНИЯ (раскрывает информацию!)
    if company.user_id is not None:
        if not current_user or company.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
```

**ПОСЛЕ:**
```python
@router.get("/{company_id}")
async def get_company(
    company_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    # ПРОВЕРКА ДОСТУПА В SQL ЗАПРОСЕ (безопасно!)
    query = select(Company).where(Company.id == uuid_obj)
    
    if current_user:
        query = query.where(
            or_(
                Company.user_id == current_user.id,
                Company.user_id.is_(None)  # Глобальные компании
            )
        )
    else:
        query = query.where(Company.user_id.is_(None))
    
    result = await db.execute(query)
    company = result.scalar_one_or_none()
    
    if not company:
        # Всегда 404, не раскрывает информацию о существовании
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {...}
```

**Изменения в поведении:**
- ✅ Проверка доступа выполняется в SQL запросе, а не после получения
- ✅ Если компания существует, но недоступна → 404 (не 403)
- ✅ Пользователь не может различить "компания не существует" и "компания недоступна"
- ✅ Улучшена безопасность (не раскрывается информация о существовании чужих ресурсов)

### 4. `POST /api/v1/competitors/compare`

**ДО:**
```python
@router.post("/compare")
async def compare_companies(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    company_ids = request_data.get('company_ids', [])
    # НЕТ ВАЛИДАЦИИ company_ids
    comparison_data = await facade.compare_companies(
        company_ids=company_ids,
        user_id=str(current_user.id),
        ...
    )
    return comparison_data
```

**ПОСЛЕ:**
```python
@router.post("/compare")
async def compare_companies(
    request_data: dict = Body(...),
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
    db: AsyncSession = Depends(get_db),
):
    company_ids = request_data.get('company_ids', [])
    
    # НОВАЯ ВАЛИДАЦИЯ: проверяем доступ к каждой компании (по user_id, НЕ по subscribed_companies!)
    for company_id in company_ids:
        # Проверяем, что компания принадлежит пользователю (user_id = current_user.id)
        company = await check_company_access(company_id, current_user, db)
        if not company:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to company {company_id}"
            )
    
    comparison_data = await facade.compare_companies(
        company_ids=company_ids,
        user_id=str(current_user.id),
        ...
    )
    return comparison_data
```

**Изменения в поведении:**
- ✅ Добавлена валидация всех `company_ids` перед сравнением
- ✅ Пользователь может сравнивать только свои компании (`user_id = current_user.id`)
- ✅ Попытка сравнить чужую компанию → 403 Forbidden с указанием проблемного ID

### 5. `GET /api/v1/competitors/suggest/{company_id}`

**ДО:**
```python
@router.get("/suggest/{company_id}")
async def suggest_competitors(
    company_id: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
):
    # НЕТ ПРОВЕРКИ ДОСТУПА К company_id
    suggestions = await facade.suggest_competitors(
        company_id=company_uuid,
        limit=limit,
        ...
    )
    return {"suggestions": suggestions}
```

**ПОСЛЕ:**
```python
@router.get("/suggest/{company_id}")
async def suggest_competitors(
    company_id: str,
    limit: int = 5,
    current_user: User = Depends(get_current_user),
    facade: CompetitorFacade = Depends(get_competitor_facade),
    db: AsyncSession = Depends(get_db),
):
    # НОВАЯ ПРОВЕРКА ДОСТУПА
    company = await check_company_access(company_id, current_user, db)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    suggestions = await facade.suggest_competitors(
        company_id=company_uuid,
        limit=limit,
        ...
    )
    return {"suggestions": suggestions}
```

**Изменения в поведении:**
- ✅ Добавлена проверка доступа к `company_id` перед получением предложений
- ✅ Пользователь может получить предложения только для своих компаний
- ✅ Попытка получить предложения для чужой компании → 404 Not Found

### 6. `GET /api/v1/reports/{report_id}`

**ДО:**
```python
@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report_repo = ReportRepository(db)
    # СНАЧАЛА ПОЛУЧАЕМ ОТЧЁТ
    report = await report_repo.get_by_id(report_uuid)
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # ПРОВЕРКА ДОСТУПА ПОСЛЕ ПОЛУЧЕНИЯ (раскрывает информацию!)
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
```

**ПОСЛЕ:**
```python
@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    report_repo = ReportRepository(db)
    # ПРОВЕРКА ДОСТУПА В SQL ЗАПРОСЕ (безопасно!)
    report = await report_repo.get_by_id(
        report_uuid,
        user_id=current_user.id  # Фильтр по user_id в запросе
    )
    
    if not report:
        # Всегда 404, не раскрывает информацию
        raise HTTPException(status_code=404, detail="Report not found")
```

**Изменения в поведении:**
- ✅ Проверка доступа выполняется в SQL запросе через `get_by_id(user_id=...)`
- ✅ Если отчёт существует, но принадлежит другому пользователю → 404 (не 403)
- ✅ Улучшена безопасность (не раскрывается информация о существовании чужих отчётов)

---

## Изменения в пользовательском интерфейсе

### 1. DashboardPage - Индикация "Ваши конкуренты"

**ДО:**
```tsx
// Просто заголовок "Competitors"
<h2>Competitors</h2>
```

**ПОСЛЕ:**
```tsx
// Явная индикация принадлежности
<h2>
  Your Competitors
  {subscribedCompaniesCount > 0 && (
    <span className="text-sm text-gray-500">
      ({subscribedCompaniesCount} companies)
    </span>
  )}
</h2>
```

**Изменения:**
- ✅ Заголовок изменён на "Your Competitors" (Ваши конкуренты)
- ✅ Показывается количество подписок
- ✅ Улучшена обратная связь для пользователя

### 2. DashboardPage - Подсказки для пустых состояний

**ДО:**
```tsx
// Пустая таблица без подсказок
{companies.length === 0 && (
  <div>No companies found</div>
)}
```

**ПОСЛЕ:**
```tsx
// Подсказки для новых пользователей
{companies.length === 0 && (
  <div className="text-center py-12">
    <p className="text-lg text-gray-600 mb-4">
      You don't have any competitors yet
    </p>
    <p className="text-sm text-gray-500 mb-6">
      Add your first competitor to start tracking news and updates
    </p>
    <button onClick={handleAddCompetitor}>
      Add Your First Competitor
    </button>
  </div>
)}
```

**Изменения:**
- ✅ Добавлены подсказки для пустых состояний
- ✅ Кнопка "Add Your First Competitor" для новых пользователей
- ✅ Улучшен UX для пользователей без данных

### 3. Header - Количество подписок

**ДО:**
```tsx
// Только имя пользователя
<div>{user.full_name}</div>
```

**ПОСЛЕ:**
```tsx
// Имя пользователя + количество подписок
<div>
  <div>{user.full_name}</div>
  {subscribedCount > 0 && (
    <div className="text-xs text-gray-500">
      {subscribedCount} companies tracked
    </div>
  )}
</div>
```

**Изменения:**
- ✅ Показывается количество отслеживаемых компаний
- ✅ Улучшена обратная связь о состоянии аккаунта

### 4. NewsPage - Индикация фильтрации

**ДО:**
```tsx
// Нет индикации фильтрации
<h2>News</h2>
```

**ПОСЛЕ:**
```tsx
// Индикация фильтрации по подпискам
<h2>
  Your News Feed
  {isFiltered && (
    <span className="text-sm text-gray-500">
      (filtered by your subscriptions)
    </span>
  )}
</h2>
```

**Изменения:**
- ✅ Добавлена индикация, что новости фильтруются по подпискам
- ✅ Пользователь понимает, почему видит только определённые новости

---

## Новые файлы и функции

### 1. `backend/app/core/access_control.py` (новый файл)

**Создаётся новый модуль для централизованной проверки доступа:**

```python
"""
Centralized access control functions
"""

from typing import Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models import User, Company, NewsItem
from app.models.preferences import UserPreferences


async def check_company_access(
    company_id: UUID | str,
    user: Optional[User],
    db: AsyncSession
) -> Optional[Company]:
    """
    Check if user has access to company and return it.
    
    Returns:
        Company if accessible, None otherwise
    """
    if isinstance(company_id, str):
        try:
            company_id = UUID(company_id)
        except ValueError:
            return None
    
    query = select(Company).where(Company.id == company_id)
    
    if user:
        query = query.where(
            or_(
                Company.user_id == user.id,
                Company.user_id.is_(None)  # Global companies
            )
        )
    else:
        query = query.where(Company.user_id.is_(None))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def check_news_access(
    news_id: UUID | str,
    user: Optional[User],
    db: AsyncSession
) -> Optional[NewsItem]:
    """
    Check if user has access to news item and return it.
    Проверяет доступ по user_id компании (НЕ по subscribed_companies!).
    
    Returns:
        NewsItem if accessible, None otherwise
    """
    if isinstance(news_id, str):
        try:
            news_id = UUID(news_id)
        except ValueError:
            return None
    
    result = await db.execute(
        select(NewsItem).where(NewsItem.id == news_id)
    )
    news_item = result.scalar_one_or_none()
    
    if not news_item:
        return None
    
    # Check if company belongs to user (user_id = user.id)
    if user:
        company_result = await db.execute(
            select(Company).where(
                and_(
                    Company.id == news_item.company_id,
                    Company.user_id == user.id
                )
            )
        )
        company = company_result.scalar_one_or_none()
        if not company:
            return None
    
    return news_item


async def get_user_preferences(
    user_id: UUID,
    db: AsyncSession
) -> UserPreferences:
    """
    Get user preferences, creating default if not exists.
    """
    result = await db.execute(
        select(UserPreferences).where(UserPreferences.user_id == user_id)
    )
    prefs = result.scalar_one_or_none()
    
    if not prefs:
        # Create default preferences
        prefs = UserPreferences(
            user_id=user_id,
            subscribed_companies=[],
            interested_categories=[],
            keywords=[],
            ...
        )
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    
    return prefs
```

**Преимущества:**
- ✅ Единый подход к проверке доступа
- ✅ Переиспользование кода
- ✅ Легче тестировать
- ✅ Легче поддерживать

### 2. Обновление `ReportRepository.get_by_id()`

**ДО:**
```python
async def get_by_id(
    self,
    report_id: UUID | str,
    *,
    include_relations: bool = False
) -> Optional[Report]:
    stmt = select(Report).where(Report.id == report_id)
    # НЕТ ФИЛЬТРА ПО user_id
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**ПОСЛЕ:**
```python
async def get_by_id(
    self,
    report_id: UUID | str,
    *,
    user_id: Optional[UUID] = None,  # НОВЫЙ ПАРАМЕТР
    include_relations: bool = False
) -> Optional[Report]:
    stmt = select(Report).where(Report.id == report_id)
    
    # НОВЫЙ ФИЛЬТР ПО user_id
    if user_id:
        stmt = stmt.where(Report.user_id == user_id)
    
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**Изменения:**
- ✅ Добавлен опциональный параметр `user_id` для фильтрации
- ✅ Если `user_id` указан, отчёт возвращается только если принадлежит пользователю
- ✅ Обратная совместимость: если `user_id` не указан, работает как раньше

---

## Влияние на производительность

### Положительные изменения

1. **Оптимизация SQL запросов:**
   - Проверка доступа в SQL запросе вместо Python кода
   - Меньше запросов к БД (один запрос вместо двух)
   - Использование индексов БД для фильтрации

2. **Кэширование UserPreferences:**
   - `UserPreferences` можно кэшировать на уровне запроса
   - Меньше повторных запросов к БД

### Негативные изменения (минимальные)

1. **Дополнительные запросы:**
   - Для проверки доступа к новостям нужен запрос `UserPreferences`
   - Компенсируется кэшированием и оптимизацией SQL

2. **Валидация company_ids:**
   - При сравнении компаний нужна проверка каждого ID
   - Можно оптимизировать батч-проверкой

**Общий вывод:** Влияние на производительность минимальное, безопасность значительно улучшена.

---

## Миграция и обратная совместимость

### Обратная совместимость API

**✅ Сохраняется:**
- Все существующие эндпоинты работают как раньше
- Формат запросов и ответов не изменяется
- Только добавляются проверки доступа

**⚠️ Изменения в поведении:**
- Некоторые запросы, которые раньше возвращали 200, теперь возвращают 403/404
- Это ожидаемое поведение для исправления уязвимостей

### Миграция данных

**Не требуется:**
- Все данные уже имеют правильные `user_id`
- `UserPreferences` уже существуют для всех пользователей
- Нет необходимости в миграции данных

### Миграция кода

**Порядок внедрения:**

1. **Этап 1: Создание access_control.py**
   - Создать новый файл с функциями проверки доступа
   - Добавить тесты

2. **Этап 2: Исправление критических эндпоинтов**
   - `GET /news/{news_id}`
   - `PUT /news/{news_id}`
   - `DELETE /news/{news_id}`
   - `GET /companies/{company_id}`
   - `GET /reports/{report_id}`

3. **Этап 3: Исправление эндпоинтов competitors**
   - `POST /competitors/compare`
   - `GET /competitors/suggest/{company_id}`
   - `GET /competitors/activity/{company_id}`

4. **Этап 4: Улучшение UX**
   - Добавить индикацию "Ваши конкуренты"
   - Добавить подсказки для пустых состояний
   - Показывать количество подписок

5. **Этап 5: Тестирование**
   - Тесты изоляции данных
   - Тесты защиты от подмены ID
   - E2E тесты персонализации

---

## Итоговые изменения

### Безопасность

| Параметр | До | После |
|----------|-----|-------|
| Доступ к новостям | ❌ Любой пользователь может получить любую новость | ✅ Только новости из своих компаний (`user_id`) |
| Фильтрация новостей | ⚠️ По `subscribed_companies` (неправильно) | ✅ По `user_id` компаний (правильно) |
| Доступ к компаниям | ⚠️ Раскрывается информация о существовании | ✅ Безопасная проверка в SQL |
| Доступ к отчётам | ⚠️ Раскрывается информация о существовании | ✅ Безопасная проверка в SQL |
| Сравнение компаний | ❌ Можно сравнивать чужие компании | ✅ Только свои компании (`user_id`) |
| Редактирование новостей | ❌ Можно редактировать чужие новости | ✅ Только новости из своих компаний (`user_id`) |
| Синхронизация | ⚠️ "List Competitor" и новости используют разные источники | ✅ Единая логика: все по `user_id` компаний |

### Пользовательский опыт

| Параметр | До | После |
|----------|-----|-------|
| Индикация принадлежности | ⚠️ Нет явной индикации | ✅ "Ваши конкуренты", количество подписок |
| Пустые состояния | ⚠️ Пустая таблица без подсказок | ✅ Подсказки и кнопки действий |
| Фильтрация новостей | ⚠️ Неочевидно, что новости фильтруются | ✅ Индикация фильтрации по подпискам |

### Код

| Параметр | До | После |
|----------|-----|-------|
| Проверка доступа | ⚠️ Разбросана по коду, неконсистентна | ✅ Централизованные функции в `access_control.py` |
| SQL запросы | ⚠️ Проверка после получения данных | ✅ Проверка в SQL запросе |
| Тесты | ❌ Нет тестов персонализации | ✅ Тесты изоляции и безопасности |

---

## Заключение

После выполнения плана исправлений:

1. **Безопасность значительно улучшится:**
   - Устранены все критические уязвимости
   - Пользователи не могут получить доступ к чужим данным
   - Информация о существовании ресурсов не раскрывается

2. **UX улучшится:**
   - Пользователи понимают, что видят свои данные
   - Есть подсказки для новых пользователей
   - Показывается количество подписок

3. **Код станет лучше:**
   - Единый подход к проверке доступа
   - Легче поддерживать и тестировать
   - Оптимизированные SQL запросы

**Рекомендуемый порядок внедрения:** Сначала критические исправления безопасности (Этапы 1-3), затем улучшения UX (Этап 4), затем тесты (Этап 5).

