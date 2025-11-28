# План реализации исправлений персонализации

**Дата:** 2025-01-31  
**Версия:** 0.1.0  
**Статус:** Готов к реализации

## 📋 Обзор

Этот документ содержит пошаговый план реализации исправлений персонализации данных в платформе.

**Ключевой принцип:** Персонализация основана на `user_id` в таблице `companies`, а НЕ на `subscribed_companies`!

---

## 🎯 Приоритеты

### Приоритет 1: Критические исправления безопасности (Этап 1-3)
- Создание централизованных функций проверки доступа
- Исправление фильтрации новостей
- Исправление проверки доступа к ресурсам

### Приоритет 2: Улучшение UX (Этап 4)
- Добавление индикации "Ваши данные"
- Подсказки для пустых состояний

### Приоритет 3: Тестирование (Этап 5)
- Тесты изоляции данных
- Тесты защиты от подмены ID

---

## Этап 1: Создание централизованных функций проверки доступа

### Задача 1.1: Создать `backend/app/core/access_control.py`

**Файл:** `backend/app/core/access_control.py` (новый файл)

**Содержимое:**
```python
"""
Centralized access control functions for personalization.

КРИТИЧЕСКИ ВАЖНО: Персонализация основана на user_id компаний, 
а НЕ на subscribed_companies!
"""

from typing import Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models import User, Company, NewsItem


async def check_company_access(
    company_id: UUID | str,
    user: Optional[User],
    db: AsyncSession
) -> Optional[Company]:
    """
    Check if user has access to company and return it.
    Проверяет доступ по user_id компании (НЕ по subscribed_companies!).
    
    Args:
        company_id: Company UUID or string
        user: Current user (None for anonymous)
        db: Database session
        
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
    Проверяет доступ по user_id компании новости (НЕ по subscribed_companies!).
    
    Args:
        news_id: News UUID or string
        user: Current user (None for anonymous)
        db: Database session
        
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


async def get_user_company_ids(
    user: User,
    db: AsyncSession
) -> list[UUID]:
    """
    Get all company IDs that belong to user.
    Получает все ID компаний, принадлежащих пользователю (user_id = user.id).
    
    Args:
        user: Current user
        db: Database session
        
    Returns:
        List of company UUIDs
    """
    result = await db.execute(
        select(Company.id).where(Company.user_id == user.id)
    )
    return [c.id for c in result.scalars().all()]
```

**Проверка:**
- [ ] Файл создан
- [ ] Функции работают корректно
- [ ] Импорты правильные

---

## Этап 2: Исправление фильтрации новостей

### Задача 2.1: Исправить `GET /api/v1/news/`

**Файл:** `backend/app/api/v1/endpoints/news.py`

**Изменения:**

**ДО:**
```python
# Automatic isolation: if user is authenticated and didn't specify company_ids,
# filter by subscribed_companies from UserPreferences
if current_user and not parsed_company_ids:
    try:
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
# Automatic isolation: if user is authenticated and didn't specify company_ids,
# filter by user_id companies (НЕ по subscribed_companies!)
if current_user and not parsed_company_ids:
    try:
        from app.core.access_control import get_user_company_ids
        # ПРАВИЛЬНО: фильтруем по user_id компаний
        user_company_ids = await get_user_company_ids(current_user, db)
        if user_company_ids:
            parsed_company_ids = user_company_ids
            normalised_company_id = None  # Reset single company_id, use list instead
            logger.info(
                f"Auto-filtering news by {len(parsed_company_ids)} user companies "
                f"for user {current_user.id}"
            )
```

**Проверка:**
- [ ] Фильтрация работает по `user_id` компаний
- [ ] Логирование обновлено
- [ ] Тесты проходят

### Задача 2.2: Исправить `GET /api/v1/news/stats`

**Файл:** `backend/app/api/v1/endpoints/news.py`

**Изменения:**

**ДО:**
```python
if user_prefs and user_prefs.subscribed_companies:
    # Filter statistics by subscribed companies
    stats = await facade.get_statistics_for_companies(
        [str(cid) for cid in user_prefs.subscribed_companies]
    )
```

**ПОСЛЕ:**
```python
from app.core.access_control import get_user_company_ids

user_company_ids = await get_user_company_ids(current_user, db)
if user_company_ids:
    # Filter statistics by user companies (user_id)
    stats = await facade.get_statistics_for_companies(
        [str(cid) for cid in user_company_ids]
    )
```

**Проверка:**
- [ ] Статистика фильтруется по `user_id` компаний
- [ ] Тесты проходят

### Задача 2.3: Исправить `GET /api/v1/news/stats/by-companies`

**Файл:** `backend/app/api/v1/endpoints/news.py`

**Изменения:**

**ДО:**
```python
if user_prefs and user_prefs.subscribed_companies:
    subscribed_ids = set(user_prefs.subscribed_companies)
    if requested_ids and not requested_ids.issubset(subscribed_ids):
        raise HTTPException(status_code=403, detail="Access denied")
```

**ПОСЛЕ:**
```python
from app.core.access_control import check_company_access

# Validate that all requested companies belong to user (user_id)
for company_id in parsed_company_ids:
    company = await check_company_access(company_id, current_user, db)
    if not company:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to company {company_id}"
        )
```

**Проверка:**
- [ ] Валидация работает по `user_id`
- [ ] Тесты проходят

---

## Этап 3: Исправление проверки доступа к ресурсам

### Задача 3.1: Исправить `GET /api/v1/news/{news_id}`

**Файл:** `backend/app/api/v1/endpoints/news.py`

**Изменения:**

**ДО:**
```python
@router.get("/{news_id}")
async def get_news_item(
    news_id: str,
    facade: NewsFacade = Depends(get_news_facade),
):
    news_item = await facade.get_news_item(news_id, include_relations=True)
    # НЕТ ПРОВЕРКИ ДОСТУПА
    return serialize_news_item(news_item, include_activities=True)
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
    from app.core.access_control import check_news_access
    
    news_item = await check_news_access(news_id, current_user, db)
    if not news_item:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    return serialize_news_item(news_item, include_activities=True)
```

**Проверка:**
- [ ] Проверка доступа работает
- [ ] Возвращает 403 для недоступных новостей
- [ ] Тесты проходят

### Задача 3.2: Исправить `PUT /api/v1/news/{news_id}`

**Файл:** `backend/app/api/v1/endpoints/news.py`

**Изменения:**

**ДО:**
```python
@router.put("/{news_id}")
async def update_news(
    news_id: str,
    payload: NewsUpdateSchema,
    facade: NewsFacade = Depends(get_news_facade),
):
    # НЕТ ПРОВЕРКИ ДОСТУПА
    news_item = await facade.update_news(news_id, update_data)
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
    from app.core.access_control import check_news_access
    
    # СНАЧАЛА ПРОВЕРЯЕМ ДОСТУП
    news_item = await check_news_access(news_id, current_user, db)
    if not news_item:
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )
    
    # ТОЛЬКО ПОСЛЕ ПРОВЕРКИ ОБНОВЛЯЕМ
    update_data = payload.model_dump(exclude_unset=True)
    news_item = await facade.update_news(news_id, update_data)
```

**Проверка:**
- [ ] Проверка доступа работает
- [ ] Возвращает 403 для недоступных новостей
- [ ] Тесты проходят

### Задача 3.3: Исправить `DELETE /api/v1/news/{news_id}`

**Файл:** `backend/app/api/v1/endpoints/news.py`

**Изменения:** Аналогично задаче 3.2, но для удаления

**Проверка:**
- [ ] Проверка доступа работает
- [ ] Возвращает 403 для недоступных новостей
- [ ] Тесты проходят

### Задача 3.4: Исправить `GET /api/v1/companies/{company_id}`

**Файл:** `backend/app/api/v1/endpoints/companies.py`

**Изменения:**

**ДО:**
```python
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
from app.core.access_control import check_company_access

# ПРОВЕРКА ДОСТУПА В SQL ЗАПРОСЕ (безопасно!)
company = await check_company_access(company_id, current_user, db)

if not company:
    # Всегда 404, не раскрывает информацию
    raise HTTPException(status_code=404, detail="Company not found")
```

**Проверка:**
- [ ] Проверка доступа в SQL запросе
- [ ] Всегда возвращает 404 для недоступных компаний
- [ ] Тесты проходят

### Задача 3.5: Исправить `POST /api/v1/competitors/compare`

**Файл:** `backend/app/api/v1/endpoints/competitors.py`

**Изменения:**

**ДО:**
```python
company_ids = request_data.get('company_ids', [])
# НЕТ ВАЛИДАЦИИ company_ids
comparison_data = await facade.compare_companies(
    company_ids=company_ids,
    ...
)
```

**ПОСЛЕ:**
```python
from app.core.access_control import check_company_access

company_ids = request_data.get('company_ids', [])

# ВАЛИДАЦИЯ: проверяем доступ к каждой компании
for company_id in company_ids:
    company = await check_company_access(company_id, current_user, db)
    if not company:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to company {company_id}"
        )

comparison_data = await facade.compare_companies(
    company_ids=company_ids,
    ...
)
```

**Проверка:**
- [ ] Валидация всех `company_ids` работает
- [ ] Возвращает 403 для недоступных компаний
- [ ] Тесты проходят

### Задача 3.6: Исправить `GET /api/v1/competitors/suggest/{company_id}`

**Файл:** `backend/app/api/v1/endpoints/competitors.py`

**Изменения:**

**ДО:**
```python
company_uuid = uuid_lib.UUID(company_id)
# НЕТ ПРОВЕРКИ ДОСТУПА
suggestions = await facade.suggest_competitors(
    company_id=company_uuid,
    ...
)
```

**ПОСЛЕ:**
```python
from app.core.access_control import check_company_access

# ПРОВЕРКА ДОСТУПА
company = await check_company_access(company_id, current_user, db)
if not company:
    raise HTTPException(status_code=404, detail="Company not found")

company_uuid = uuid_lib.UUID(company_id)
suggestions = await facade.suggest_competitors(
    company_id=company_uuid,
    ...
)
```

**Проверка:**
- [ ] Проверка доступа работает
- [ ] Возвращает 404 для недоступных компаний
- [ ] Тесты проходят

### Задача 3.7: Исправить `GET /api/v1/competitors/activity/{company_id}`

**Файл:** `backend/app/api/v1/endpoints/competitors.py`

**Изменения:** Аналогично задаче 3.6

**Проверка:**
- [ ] Проверка доступа работает
- [ ] Возвращает 404 для недоступных компаний
- [ ] Тесты проходят

### Задача 3.8: Исправить `GET /api/v1/reports/{report_id}`

**Файл:** `backend/app/api/v1/endpoints/reports.py`

**Изменения:**

**ДО:**
```python
report = await report_repo.get_by_id(report_uuid)

if not report:
    raise HTTPException(status_code=404, detail="Report not found")

# ПРОВЕРКА ДОСТУПА ПОСЛЕ ПОЛУЧЕНИЯ
if report.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Access denied")
```

**ПОСЛЕ:**
```python
# ПРОВЕРКА ДОСТУПА В SQL ЗАПРОСЕ
report = await report_repo.get_by_id(report_uuid, user_id=current_user.id)

if not report:
    # Всегда 404, не раскрывает информацию
    raise HTTPException(status_code=404, detail="Report not found")
```

**Проверка:**
- [ ] `ReportRepository.get_by_id()` обновлён
- [ ] Проверка доступа в SQL запросе
- [ ] Тесты проходят

### Задача 3.9: Обновить `ReportRepository.get_by_id()`

**Файл:** `backend/app/domains/reports/repositories/report_repository.py`

**Изменения:**

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

**Проверка:**
- [ ] Параметр `user_id` добавлен
- [ ] Фильтрация работает корректно
- [ ] Обратная совместимость сохранена
- [ ] Тесты проходят

---

## Этап 4: Улучшение UX

### Задача 4.1: Обновить DashboardPage - заголовок и количество

**Файл:** `frontend/src/pages/DashboardPage.tsx`

**Изменения:**

**ДО:**
```tsx
<h2>Competitors</h2>
```

**ПОСЛЕ:**
```tsx
<h2>
  Your Competitors
  {companies.length > 0 && (
    <span className="text-sm text-gray-500 ml-2">
      ({companies.length} companies)
    </span>
  )}
</h2>
```

**Проверка:**
- [ ] Заголовок обновлён
- [ ] Показывается количество компаний
- [ ] UI выглядит корректно

### Задача 4.2: Обновить DashboardPage - подсказки для пустых состояний

**Файл:** `frontend/src/pages/DashboardPage.tsx`

**Изменения:**

**ДО:**
```tsx
{companies.length === 0 && (
  <div>No companies found</div>
)}
```

**ПОСЛЕ:**
```tsx
{companies.length === 0 && (
  <div className="text-center py-12">
    <p className="text-lg text-gray-600 mb-4">
      You don't have any competitors yet
    </p>
    <p className="text-sm text-gray-500 mb-6">
      Add your first competitor to start tracking news and updates
    </p>
    <button
      onClick={handleAddCompetitor}
      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
    >
      Add Your First Competitor
    </button>
  </div>
)}
```

**Проверка:**
- [ ] Подсказки добавлены
- [ ] Кнопка работает
- [ ] UI выглядит корректно

### Задача 4.3: Обновить Header - количество подписок

**Файл:** `frontend/src/components/Header.tsx`

**Изменения:**

**ДО:**
```tsx
<div>{user.full_name}</div>
```

**ПОСЛЕ:**
```tsx
<div>
  <div>{user.full_name}</div>
  {companiesCount > 0 && (
    <div className="text-xs text-gray-500">
      {companiesCount} companies tracked
    </div>
  )}
</div>
```

**Примечание:** Нужно получить количество компаний через API `GET /companies/` (фильтруется по `user_id`)

**Проверка:**
- [ ] Количество компаний показывается
- [ ] Данные загружаются корректно
- [ ] UI выглядит корректно

### Задача 4.4: Обновить NewsPage - индикация фильтрации

**Файл:** `frontend/src/pages/NewsPage.tsx` (или где отображаются новости)

**Изменения:**

**ДО:**
```tsx
<h2>News</h2>
```

**ПОСЛЕ:**
```tsx
<h2>
  Your News Feed
  {isAuthenticated && (
    <span className="text-sm text-gray-500 ml-2">
      (filtered by your companies)
    </span>
  )}
</h2>
```

**Проверка:**
- [ ] Индикация добавлена
- [ ] UI выглядит корректно

---

## Этап 5: Тестирование

### Задача 5.1: Написать тесты для access_control.py

**Файл:** `backend/tests/test_access_control.py` (новый файл)

**Тесты:**
- [ ] `test_check_company_access_user_owns_company()` - пользователь владеет компанией
- [ ] `test_check_company_access_user_does_not_own_company()` - пользователь не владеет компанией
- [ ] `test_check_company_access_global_company()` - глобальная компания
- [ ] `test_check_news_access_user_owns_company()` - новость из компании пользователя
- [ ] `test_check_news_access_user_does_not_own_company()` - новость из чужой компании
- [ ] `test_get_user_company_ids()` - получение ID компаний пользователя

**Проверка:**
- [ ] Все тесты проходят
- [ ] Покрытие > 80%

### Задача 5.2: Написать тесты изоляции данных

**Файл:** `backend/tests/test_personalization_isolation.py` (новый файл)

**Тесты:**
- [ ] `test_user_a_cannot_see_user_b_companies()` - пользователь А не видит компании пользователя Б
- [ ] `test_user_a_cannot_see_user_b_news()` - пользователь А не видит новости пользователя Б
- [ ] `test_user_a_cannot_see_user_b_reports()` - пользователь А не видит отчёты пользователя Б
- [ ] `test_user_sees_all_own_companies()` - пользователь видит все свои компании
- [ ] `test_user_sees_all_own_news()` - пользователь видит все новости своих компаний

**Проверка:**
- [ ] Все тесты проходят
- [ ] Покрытие > 80%

### Задача 5.3: Написать тесты защиты от подмены ID

**Файл:** `backend/tests/test_personalization_security.py` (новый файл)

**Тесты:**
- [ ] `test_cannot_access_other_user_company_by_id()` - нельзя получить чужую компанию по ID
- [ ] `test_cannot_access_other_user_news_by_id()` - нельзя получить чужую новость по ID
- [ ] `test_cannot_access_other_user_report_by_id()` - нельзя получить чужой отчёт по ID
- [ ] `test_cannot_compare_other_user_companies()` - нельзя сравнивать чужие компании
- [ ] `test_cannot_get_suggestions_for_other_user_company()` - нельзя получить предложения для чужой компании

**Проверка:**
- [ ] Все тесты проходят
- [ ] Покрытие > 80%

---

## Чек-лист перед коммитом

### Backend

- [ ] Все эндпоинты используют `check_company_access()` или `check_news_access()`
- [ ] Фильтрация новостей работает по `user_id` компаний (НЕ по `subscribed_companies`)
- [ ] Все проверки доступа выполняются в SQL запросах (не после получения данных)
- [ ] Логирование обновлено с правильными сообщениями
- [ ] Все тесты проходят
- [ ] Нет линтер ошибок

### Frontend

- [ ] Заголовки обновлены ("Your Competitors", "Your News Feed")
- [ ] Показывается количество компаний
- [ ] Подсказки для пустых состояний добавлены
- [ ] Индикация фильтрации добавлена
- [ ] UI выглядит корректно на всех устройствах

### Документация

- [ ] README обновлён с описанием правильной логики персонализации
- [ ] Комментарии в коде обновлены
- [ ] API документация обновлена (если есть)

---

## Порядок выполнения

1. **Этап 1** - Создать `access_control.py` (основа для всех проверок)
2. **Этап 2** - Исправить фильтрацию новостей (критично для правильной работы)
3. **Этап 3** - Исправить проверку доступа к ресурсам (безопасность)
4. **Этап 4** - Улучшить UX (после исправления безопасности)
5. **Этап 5** - Написать тесты (проверка правильности реализации)

---

## Ожидаемые результаты

После выполнения всех задач:

1. ✅ Пользователь видит только новости из своих компаний (`user_id`)
2. ✅ Пользователь не может получить доступ к чужим ресурсам
3. ✅ Единая логика: "List Competitor" и новости используют один источник
4. ✅ Улучшен UX с явной обратной связью
5. ✅ Все тесты проходят
6. ✅ Код легко поддерживать (централизованные функции)

---

## Примечания

- **Важно:** Все проверки доступа должны использовать `user_id` компаний, а НЕ `subscribed_companies`
- **Важно:** Проверка доступа должна выполняться в SQL запросе, а не после получения данных
- **Важно:** Всегда возвращать 404 для недоступных ресурсов (не 403), чтобы не раскрывать информацию


