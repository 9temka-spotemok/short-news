# План реализации Фазы 2: Система подписок и монетизация

**Дата создания:** 2025-01-27  
**Статус:** Готов к реализации  
**Ориентировочное время:** 8-13 рабочих дней

---

## 📋 Обзор

Реализация системы подписок для монетизации платформы:
- **Одна подписка на $29/месяц**
- **Триал на 3 дня** после завершения онбординга
- Автоматическое создание триала после онбординга
- Проверка доступа к функциям на основе подписки
- Управление жизненным циклом подписки (активация, отмена, истечение)

---

## 🎯 Цели

1. Создать модель данных для подписок
2. Реализовать сервис управления подписками
3. Создать API endpoints для работы с подписками
4. Интегрировать создание триала в процесс онбординга
5. Реализовать периодические задачи для проверки истечения триалов/подписок
6. Создать Frontend компоненты для отображения статуса подписки
7. Добавить проверку доступа к функциям на основе подписки

---

## 📊 Текущее состояние

### ✅ Что уже есть:
- Система аутентификации (JWT, User модель)
- Онбординг полностью реализован
- API endpoints для онбординга
- Frontend компоненты онбординга

### ❌ Что нужно реализовать:
- Модель Subscription
- SubscriptionService
- API endpoints для подписок
- Celery задачи для проверки истечения
- Frontend компоненты для подписок
- Интеграция создания триала в онбординг

---

## 🏗️ Детальный план реализации

### ЭТАП 1: Backend — Модели и миграции (1-2 дня)

#### 1.1. Создание модели Subscription

**Файл:** `backend/app/models/subscription.py`

**Структура модели:**

```python
from enum import Enum
from sqlalchemy import Column, String, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.models.base import BaseModel


class SubscriptionStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Subscription(BaseModel):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Статус и план
    status = Column(String(20), nullable=False, default=SubscriptionStatus.TRIAL.value, index=True)
    plan_type = Column(String(20), nullable=False, default="monthly")
    price = Column(Numeric(10, 2), nullable=False, default=Decimal("29.00"))
    currency = Column(String(3), nullable=False, default="USD")
    
    # Даты триала
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Даты подписки
    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Платежи
    payment_provider = Column(String(50), nullable=True)  # stripe, paypal, etc.
    payment_subscription_id = Column(String(255), nullable=True)  # ID в платежной системе
    
    # Метаданные
    metadata = Column(JSON, nullable=True, default=dict)
    
    # Relationships
    user = relationship("User", backref="subscription")
    
    __table_args__ = (
        {"comment": "User subscriptions and trials"}
    )
    
    def is_active(self) -> bool:
        """Проверяет, активна ли подписка или триал"""
        if self.status == SubscriptionStatus.EXPIRED:
            return False
        if self.status == SubscriptionStatus.CANCELLED:
            return False
        
        now = datetime.now(timezone.utc)
        
        # Проверка триала
        if self.status == SubscriptionStatus.TRIAL:
            if self.trial_ends_at and self.trial_ends_at < now:
                return False
            return True
        
        # Проверка активной подписки
        if self.status == SubscriptionStatus.ACTIVE:
            if self.expires_at and self.expires_at < now:
                return False
            return True
        
        return False
    
    def days_remaining(self) -> int:
        """Возвращает количество дней до окончания триала или подписки"""
        if not self.is_active():
            return 0
        
        now = datetime.now(timezone.utc)
        
        if self.status == SubscriptionStatus.TRIAL and self.trial_ends_at:
            delta = self.trial_ends_at - now
            return max(0, delta.days)
        
        if self.status == SubscriptionStatus.ACTIVE and self.expires_at:
            delta = self.expires_at - now
            return max(0, delta.days)
        
        return 0
```

**Задачи:**
- [ ] Создать файл `backend/app/models/subscription.py`
- [ ] Добавить enum `SubscriptionStatus`
- [ ] Реализовать модель `Subscription` со всеми полями
- [ ] Добавить методы `is_active()` и `days_remaining()`
- [ ] Добавить relationship к User (one-to-one)
- [ ] Добавить индексы для оптимизации запросов

#### 1.2. Обновление модели User

**Файл:** `backend/app/models/user.py`

**Изменения:**

```python
# Добавить relationship (уже будет через backref, но можно явно указать)
subscription = relationship("Subscription", back_populates="user", uselist=False)

# Добавить метод проверки доступа
def has_active_subscription(self) -> bool:
    """Проверяет, есть ли у пользователя активная подписка или триал"""
    if not self.subscription:
        return False
    return self.subscription.is_active()
```

**Задачи:**
- [ ] Добавить relationship к Subscription (опционально, если нужен явный)
- [ ] Добавить метод `has_active_subscription()` в модель User
- [ ] Обновить импорты

#### 1.3. Создание миграции

**Файл:** `backend/alembic/versions/XXXX_add_subscriptions_table.py`

**Миграция должна:**
- Создать enum тип `subscriptionstatus` в PostgreSQL
- Создать таблицу `subscriptions` со всеми полями
- Добавить индексы: `user_id`, `status`, `trial_ends_at`, `expires_at`
- Добавить foreign key на `users.id` с CASCADE
- Добавить unique constraint на `user_id`

**Задачи:**
- [ ] Создать миграцию через `alembic revision --autogenerate`
- [ ] Проверить SQL миграции
- [ ] Протестировать миграцию на dev окружении

---

### ЭТАП 2: Backend — Сервис подписок (2-3 дня)

#### 2.1. Создание SubscriptionService

**Файл:** `backend/app/services/subscription_service.py`

**Методы:**

```python
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User


class SubscriptionService:
    """Сервис для управления подписками и триалами"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_trial_subscription(self, user_id: UUID) -> Subscription:
        """
        Создает подписку с триалом на 3 дня
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Subscription объект с триалом
        """
        # Проверить, нет ли уже подписки
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"Subscription already exists for user {user_id}")
            return existing
        
        now = datetime.now(timezone.utc)
        trial_ends_at = now + timedelta(days=3)
        
        subscription = Subscription(
            user_id=user_id,
            status=SubscriptionStatus.TRIAL,
            plan_type="monthly",
            price=Decimal("29.00"),
            currency="USD",
            trial_started_at=now,
            trial_ends_at=trial_ends_at,
            metadata={}
        )
        
        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Created trial subscription for user {user_id}, expires at {trial_ends_at}")
        
        return subscription
    
    async def check_subscription_access(self, user_id: UUID) -> bool:
        """
        Проверяет, есть ли у пользователя активная подписка или триал
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если есть активная подписка/триал, False иначе
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False
        
        return subscription.is_active()
    
    async def activate_subscription(
        self, 
        subscription_id: UUID, 
        payment_data: dict
    ) -> Subscription:
        """
        Активирует подписку после оплаты
        
        Args:
            subscription_id: ID подписки
            payment_data: Данные платежа (provider, payment_subscription_id)
            
        Returns:
            Обновленный Subscription объект
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=30)  # Месячная подписка
        
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.started_at = now
        subscription.expires_at = expires_at
        subscription.payment_provider = payment_data.get("provider")
        subscription.payment_subscription_id = payment_data.get("payment_subscription_id")
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Activated subscription {subscription_id} for user {subscription.user_id}")
        
        return subscription
    
    async def cancel_subscription(self, subscription_id: UUID) -> Subscription:
        """
        Отменяет подписку
        
        Args:
            subscription_id: ID подписки
            
        Returns:
            Обновленный Subscription объект
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(subscription)
        
        logger.info(f"Cancelled subscription {subscription_id} for user {subscription.user_id}")
        
        return subscription
    
    async def get_user_subscription(self, user_id: UUID) -> Optional[Subscription]:
        """
        Получает текущую подписку пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Subscription объект или None
        """
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def expire_trials(self) -> int:
        """
        Помечает истекшие триалы как EXPIRED
        
        Returns:
            Количество обновленных подписок
        """
        now = datetime.now(timezone.utc)
        
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.TRIAL,
                Subscription.trial_ends_at < now
            )
        )
        expired_trials = result.scalars().all()
        
        count = 0
        for subscription in expired_trials:
            subscription.status = SubscriptionStatus.EXPIRED
            count += 1
        
        if count > 0:
            await self.db.commit()
            logger.info(f"Expired {count} trial subscriptions")
        
        return count
    
    async def expire_subscriptions(self) -> int:
        """
        Помечает истекшие подписки как EXPIRED
        
        Returns:
            Количество обновленных подписок
        """
        now = datetime.now(timezone.utc)
        
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at < now
            )
        )
        expired_subscriptions = result.scalars().all()
        
        count = 0
        for subscription in expired_subscriptions:
            subscription.status = SubscriptionStatus.EXPIRED
            count += 1
        
        if count > 0:
            await self.db.commit()
            logger.info(f"Expired {count} active subscriptions")
        
        return count
```

**Задачи:**
- [ ] Создать файл `backend/app/services/subscription_service.py`
- [ ] Реализовать все методы сервиса
- [ ] Добавить обработку ошибок
- [ ] Добавить логирование
- [ ] Написать unit тесты

---

### ЭТАП 3: Backend — API endpoints (1-2 дня)

#### 3.1. Создание API endpoints

**Файл:** `backend/app/api/v1/endpoints/subscriptions.py`

**Эндпоинты:**

```python
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import User
from app.services.subscription_service import SubscriptionService

router = APIRouter()


@router.get("/current")
async def get_current_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Получает текущую подписку пользователя
    
    Returns:
        Subscription данные или null если нет подписки
    """
    service = SubscriptionService(db)
    subscription = await service.get_user_subscription(current_user.id)
    
    if not subscription:
        return {"subscription": None}
    
    return {
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status.value,
            "plan_type": subscription.plan_type,
            "price": float(subscription.price),
            "currency": subscription.currency,
            "trial_started_at": subscription.trial_started_at.isoformat() if subscription.trial_started_at else None,
            "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "days_remaining": subscription.days_remaining(),
            "is_active": subscription.is_active()
        }
    }


@router.post("/create")
async def create_subscription(
    request: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Создает подписку после оплаты
    
    Request body:
        - payment_provider: str (stripe, paypal, etc.)
        - payment_subscription_id: str
        - subscription_id: UUID (опционально, если обновляем существующую)
    
    Returns:
        Subscription данные
    """
    service = SubscriptionService(db)
    
    payment_data = {
        "provider": request.get("payment_provider"),
        "payment_subscription_id": request.get("payment_subscription_id")
    }
    
    subscription_id = request.get("subscription_id")
    
    if subscription_id:
        # Активируем существующую подписку
        subscription = await service.activate_subscription(UUID(subscription_id), payment_data)
    else:
        # Создаем новую подписку (если нет триала)
        existing = await service.get_user_subscription(current_user.id)
        if existing:
            subscription = await service.activate_subscription(existing.id, payment_data)
        else:
            # Сначала создаем триал, потом активируем (необычный сценарий)
            trial = await service.create_trial_subscription(current_user.id)
            subscription = await service.activate_subscription(trial.id, payment_data)
    
    return {
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status.value,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
        }
    }


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Отменяет подписку пользователя
    
    Returns:
        Подтверждение отмены
    """
    service = SubscriptionService(db)
    subscription = await service.get_user_subscription(current_user.id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    await service.cancel_subscription(subscription.id)
    
    return {"status": "cancelled", "message": "Subscription cancelled successfully"}


@router.get("/check-access")
async def check_subscription_access(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Проверяет доступ пользователя к функциям
    
    Returns:
        has_access: bool
        reason: str (если нет доступа)
    """
    service = SubscriptionService(db)
    has_access = await service.check_subscription_access(current_user.id)
    
    if has_access:
        subscription = await service.get_user_subscription(current_user.id)
        days_remaining = subscription.days_remaining() if subscription else 0
        
        return {
            "has_access": True,
            "days_remaining": days_remaining,
            "status": subscription.status.value if subscription else None
        }
    else:
        subscription = await service.get_user_subscription(current_user.id)
        
        if not subscription:
            reason = "No subscription found. Please complete onboarding to start trial."
        elif subscription.status == SubscriptionStatus.EXPIRED:
            reason = "Your trial/subscription has expired. Please subscribe to continue."
        elif subscription.status == SubscriptionStatus.CANCELLED:
            reason = "Your subscription was cancelled. Please subscribe to continue."
        else:
            reason = "Access denied. Please check your subscription status."
        
        return {
            "has_access": False,
            "reason": reason,
            "status": subscription.status.value if subscription else None
        }
```

**Задачи:**
- [ ] Создать файл `backend/app/api/v1/endpoints/subscriptions.py`
- [ ] Реализовать все 4 эндпоинта
- [ ] Добавить валидацию запросов
- [ ] Добавить обработку ошибок
- [ ] Зарегистрировать router в `backend/app/api/v1/api.py`

---

### ЭТАП 4: Backend — Интеграция с онбордингом (1 день)

#### 4.1. Обновление complete_onboarding

**Файл:** `backend/app/api/v1/endpoints/onboarding.py`

**Изменения в методе `complete_onboarding`:**

```python
# После создания UserPreferences и добавления компаний в subscribed_companies
# Добавить создание триала:

from app.services.subscription_service import SubscriptionService

# После строки: await db.commit() (после обновления user_prefs)

# 6. Create trial subscription
subscription_service = SubscriptionService(db)
try:
    trial_subscription = await subscription_service.create_trial_subscription(final_user_id)
    logger.info(f"Created trial subscription for user {final_user_id}, expires at {trial_subscription.trial_ends_at}")
except Exception as e:
    # Не критично, если не удалось создать триал - можно создать позже
    logger.warning(f"Failed to create trial subscription for user {final_user_id}: {e}")
```

**Задачи:**
- [ ] Добавить импорт `SubscriptionService`
- [ ] Добавить вызов `create_trial_subscription()` после завершения онбординга
- [ ] Добавить обработку ошибок (не критично, если не удалось создать триал)
- [ ] Обновить логирование

---

### ЭТАП 5: Backend — Celery задачи (1 день)

#### 5.1. Создание Celery задач

**Файл:** `backend/app/tasks/subscriptions.py`

**Задачи:**

```python
"""
Celery tasks for subscription management
"""

from loguru import logger
from app.celery_app import celery_app
from app.core.celery_async import run_async_task
from app.core.celery_database import CelerySessionLocal
from app.services.subscription_service import SubscriptionService


@celery_app.task(name="subscriptions.check_expired_trials")
def check_expired_trials():
    """
    Периодическая задача для проверки истечения триалов
    
    Запускается каждый час через Celery Beat
    """
    async def _check_expired_trials():
        async with CelerySessionLocal() as db:
            service = SubscriptionService(db)
            count = await service.expire_trials()
            return count
    
    try:
        count = run_async_task(_check_expired_trials())
        logger.info(f"Checked expired trials: {count} subscriptions expired")
        return {"expired_count": count}
    except Exception as e:
        logger.error(f"Error checking expired trials: {e}", exc_info=True)
        raise


@celery_app.task(name="subscriptions.check_expired_subscriptions")
def check_expired_subscriptions():
    """
    Периодическая задача для проверки истечения подписок
    
    Запускается каждый час через Celery Beat
    """
    async def _check_expired_subscriptions():
        async with CelerySessionLocal() as db:
            service = SubscriptionService(db)
            count = await service.expire_subscriptions()
            return count
    
    try:
        count = run_async_task(_check_expired_subscriptions())
        logger.info(f"Checked expired subscriptions: {count} subscriptions expired")
        return {"expired_count": count}
    except Exception as e:
        logger.error(f"Error checking expired subscriptions: {e}", exc_info=True)
        raise
```

#### 5.2. Настройка Celery Beat

**Файл:** `backend/app/celery_app.py`

**Добавить в расписание:**

```python
from celery.schedules import crontab

beat_schedule = {
    # ... существующие задачи ...
    
    'check-expired-trials': {
        'task': 'subscriptions.check_expired_trials',
        'schedule': crontab(minute=0),  # Каждый час
    },
    'check-expired-subscriptions': {
        'task': 'subscriptions.check_expired_subscriptions',
        'schedule': crontab(minute=0),  # Каждый час
    },
}
```

**Задачи:**
- [ ] Создать файл `backend/app/tasks/subscriptions.py`
- [ ] Реализовать задачи `check_expired_trials` и `check_expired_subscriptions`
- [ ] Добавить задачи в Celery Beat расписание
- [ ] Протестировать запуск задач

---

### ЭТАП 6: Frontend — Типы и API сервис (0.5 дня)

#### 6.1. Добавление TypeScript типов

**Файл:** `frontend/src/types/index.ts`

**Добавить типы:**

```typescript
export enum SubscriptionStatus {
  TRIAL = "trial",
  ACTIVE = "active",
  CANCELLED = "cancelled",
  EXPIRED = "expired"
}

export interface Subscription {
  id: string
  status: SubscriptionStatus
  plan_type: string
  price: number
  currency: string
  trial_started_at?: string
  trial_ends_at?: string
  started_at?: string
  expires_at?: string
  days_remaining: number
  is_active: boolean
}

export interface SubscriptionAccessResponse {
  has_access: boolean
  days_remaining?: number
  reason?: string
  status?: SubscriptionStatus
}
```

**Задачи:**
- [ ] Добавить типы в `frontend/src/types/index.ts`
- [ ] Экспортировать типы

#### 6.2. Обновление API сервиса

**Файл:** `frontend/src/services/api.ts`

**Добавить методы:**

```typescript
// В класс ApiService

async getCurrentSubscription(): Promise<{ subscription: Subscription | null }> {
  const response = await this.api.get<{ subscription: Subscription | null }>('/subscriptions/current')
  return response.data
}

async checkSubscriptionAccess(): Promise<SubscriptionAccessResponse> {
  const response = await this.api.get<SubscriptionAccessResponse>('/subscriptions/check-access')
  return response.data
}

async createSubscription(paymentData: {
  payment_provider: string
  payment_subscription_id: string
  subscription_id?: string
}): Promise<{ subscription: Subscription }> {
  const response = await this.api.post<{ subscription: Subscription }>('/subscriptions/create', paymentData)
  return response.data
}

async cancelSubscription(): Promise<{ status: string; message: string }> {
  const response = await this.api.post<{ status: string; message: string }>('/subscriptions/cancel')
  return response.data
}
```

**Задачи:**
- [ ] Добавить методы в `ApiService`
- [ ] Добавить обработку ошибок
- [ ] Протестировать методы

---

### ЭТАП 7: Frontend — Компоненты (2-3 дня)

#### 7.1. Компонент статуса подписки

**Файл:** `frontend/src/components/subscription/SubscriptionStatus.tsx`

**Компонент:**

```typescript
import { useEffect, useState } from 'react'
import { ApiService } from '@/services/api'
import { Subscription, SubscriptionStatus } from '@/types'
import { Calendar, CreditCard, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'

export default function SubscriptionStatusCard() {
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSubscription()
  }, [])

  const loadSubscription = async () => {
    try {
      const response = await ApiService.getCurrentSubscription()
      setSubscription(response.subscription)
    } catch (err: any) {
      toast.error(err.message || 'Ошибка при загрузке подписки')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="animate-pulse bg-gray-200 h-24 rounded-lg" />
  }

  if (!subscription) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center gap-2 text-yellow-800">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Подписка не найдена</span>
        </div>
        <p className="text-sm text-yellow-700 mt-2">
          Завершите онбординг, чтобы начать триал на 3 дня
        </p>
      </div>
    )
  }

  const getStatusColor = () => {
    switch (subscription.status) {
      case SubscriptionStatus.TRIAL:
        return 'bg-blue-50 border-blue-200 text-blue-800'
      case SubscriptionStatus.ACTIVE:
        return 'bg-green-50 border-green-200 text-green-800'
      case SubscriptionStatus.EXPIRED:
        return 'bg-red-50 border-red-200 text-red-800'
      case SubscriptionStatus.CANCELLED:
        return 'bg-gray-50 border-gray-200 text-gray-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getStatusText = () => {
    switch (subscription.status) {
      case SubscriptionStatus.TRIAL:
        return 'Триал активен'
      case SubscriptionStatus.ACTIVE:
        return 'Подписка активна'
      case SubscriptionStatus.EXPIRED:
        return 'Подписка истекла'
      case SubscriptionStatus.CANCELLED:
        return 'Подписка отменена'
      default:
        return 'Неизвестный статус'
    }
  }

  return (
    <div className={`border rounded-lg p-4 ${getStatusColor()}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <CreditCard className="w-5 h-5" />
          <span className="font-semibold">{getStatusText()}</span>
        </div>
        {subscription.is_active && (
          <span className="text-sm font-medium">
            ${subscription.price}/{subscription.plan_type === 'monthly' ? 'мес' : 'год'}
          </span>
        )}
      </div>

      {subscription.is_active && subscription.days_remaining > 0 && (
        <div className="flex items-center gap-2 text-sm mt-2">
          <Calendar className="w-4 h-4" />
          <span>
            {subscription.days_remaining === 1
              ? 'Остался 1 день'
              : `Осталось ${subscription.days_remaining} дней`}
          </span>
        </div>
      )}

      {subscription.status === SubscriptionStatus.TRIAL && subscription.days_remaining <= 1 && (
        <button
          onClick={() => {
            // TODO: Открыть модальное окно оплаты
            toast('Интеграция с платежной системой в разработке')
          }}
          className="mt-3 w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 transition-colors font-medium"
        >
          Оформить подписку
        </button>
      )}

      {subscription.status === SubscriptionStatus.EXPIRED && (
        <button
          onClick={() => {
            // TODO: Открыть модальное окно оплаты
            toast('Интеграция с платежной системой в разработке')
          }}
          className="mt-3 w-full bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 transition-colors font-medium"
        >
          Продлить подписку
        </button>
      )}
    </div>
  )
}
```

**Задачи:**
- [ ] Создать файл `frontend/src/components/subscription/SubscriptionStatus.tsx`
- [ ] Реализовать компонент с отображением статуса
- [ ] Добавить отображение дней до окончания триала
- [ ] Добавить кнопку "Оформить подписку" (пока заглушка)
- [ ] Добавить стили и иконки

#### 7.2. Хук проверки доступа

**Файл:** `frontend/src/hooks/useSubscriptionAccess.ts`

**Хук:**

```typescript
import { useState, useEffect } from 'react'
import { ApiService } from '@/services/api'
import { SubscriptionAccessResponse } from '@/types'

export function useSubscriptionAccess() {
  const [hasAccess, setHasAccess] = useState<boolean | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [daysRemaining, setDaysRemaining] = useState<number | null>(null)

  useEffect(() => {
    checkAccess()
  }, [])

  const checkAccess = async () => {
    try {
      setLoading(true)
      const response = await ApiService.checkSubscriptionAccess()
      setHasAccess(response.has_access)
      setReason(response.reason || null)
      setDaysRemaining(response.days_remaining || null)
    } catch (err: any) {
      console.error('Error checking subscription access:', err)
      setHasAccess(false)
      setReason('Ошибка при проверке доступа')
    } finally {
      setLoading(false)
    }
  }

  return {
    hasAccess,
    reason,
    loading,
    daysRemaining,
    refetch: checkAccess
  }
}
```

**Задачи:**
- [ ] Создать файл `frontend/src/hooks/useSubscriptionAccess.ts`
- [ ] Реализовать хук с кэшированием результата
- [ ] Добавить метод `refetch` для обновления статуса

#### 7.3. Баннер о необходимости подписки

**Файл:** `frontend/src/components/subscription/SubscriptionBanner.tsx`

**Компонент:**

```typescript
import { useSubscriptionAccess } from '@/hooks/useSubscriptionAccess'
import { AlertCircle, X } from 'lucide-react'
import { useState } from 'react'

export default function SubscriptionBanner() {
  const { hasAccess, reason, loading } = useSubscriptionAccess()
  const [dismissed, setDismissed] = useState(false)

  if (loading || hasAccess || dismissed) {
    return null
  }

  return (
    <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
      <div className="flex items-start">
        <AlertCircle className="w-5 h-5 text-yellow-400 mr-3 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-sm font-medium text-yellow-800">
            Требуется подписка
          </h3>
          <p className="text-sm text-yellow-700 mt-1">
            {reason || 'Для доступа к функциям требуется активная подписка'}
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="ml-4 text-yellow-400 hover:text-yellow-600"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
```

**Задачи:**
- [ ] Создать файл `frontend/src/components/subscription/SubscriptionBanner.tsx`
- [ ] Реализовать компонент баннера
- [ ] Добавить возможность закрыть баннер
- [ ] Интегрировать в защищенные страницы

---

### ЭТАП 8: Интеграция и тестирование (1-2 дня)

#### 8.1. Интеграция компонентов

**Задачи:**
- [ ] Добавить `SubscriptionStatusCard` в Header или Dashboard
- [ ] Добавить `SubscriptionBanner` на защищенные страницы
- [ ] Интегрировать `useSubscriptionAccess` в компоненты, требующие подписку
- [ ] Обновить роутинг (если нужно)

#### 8.2. Тестирование

**Задачи:**
- [ ] Протестировать создание триала после онбординга
- [ ] Протестировать проверку доступа
- [ ] Протестировать истечение триала (вручную изменить дату в БД)
- [ ] Протестировать Celery задачи
- [ ] Протестировать все API endpoints
- [ ] Протестировать Frontend компоненты

---

## 📝 Чек-лист реализации

### Backend:
- [ ] Модель Subscription создана
- [ ] Миграция применена
- [ ] SubscriptionService реализован
- [ ] API подписок работает (4 эндпоинта)
- [ ] Celery задачи настроены
- [ ] Триал создается после онбординга

### Frontend:
- [ ] Компонент статуса подписки работает
- [ ] Проверка доступа к функциям работает
- [ ] Отображение дней до окончания триала
- [ ] Баннер о необходимости подписки
- [ ] Типы TypeScript добавлены
- [ ] API сервис обновлен

### Тестирование:
- [ ] Триал работает корректно
- [ ] Истечение триала обрабатывается
- [ ] Проверка доступа работает
- [ ] Celery задачи выполняются

---

## 🔄 Последовательность выполнения

1. **Этап 1** (1-2 дня) - Модели и миграции
2. **Этап 2** (2-3 дня) - SubscriptionService
3. **Этап 3** (1-2 дня) - API endpoints
4. **Этап 4** (1 день) - Интеграция с онбордингом
5. **Этап 5** (1 день) - Celery задачи
6. **Этап 6** (0.5 дня) - Frontend типы и API
7. **Этап 7** (2-3 дня) - Frontend компоненты
8. **Этап 8** (1-2 дня) - Интеграция и тестирование

**Общее время: 8-13 рабочих дней**

---

## ⚠️ Важные моменты

1. **Создание триала:** Должно быть не критично, если не удалось создать триал при онбординге (можно создать позже через API)

2. **Проверка доступа:** Можно сделать middleware для автоматической проверки доступа к защищенным эндпоинтам

3. **Платежная система:** Пока интеграция с платежными системами (Stripe, PayPal) не реализована - кнопки "Оформить подписку" будут заглушками

4. **Уведомления:** В будущем можно добавить уведомления об окончании триала (через существующую систему уведомлений)

5. **Миграция данных:** Если есть существующие пользователи, нужно решить, создавать ли им триалы автоматически

---

## 📚 Связанные документы

- `docs/ONBOARDING_SUBSCRIPTION_PLAN.md` - Общий план онбординга и подписок
- `docs/ONBOARDING_HOMEPAGE_INTEGRATION_PLAN.md` - План интеграции онбординга

---

**Готово к реализации** ✅



