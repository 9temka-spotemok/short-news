# План интеграции онбординга в HomePage.tsx

## Общая цель
Интегрировать весь онбординг прямо в главную страницу (HomePage.tsx) вместо отдельной страницы. После завершения онбординга пользователь должен зарегистрироваться/авторизоваться, чтобы данные перенеслись на платформу.

---

## Задачи

### 1. Создать компонент AuthModal.tsx
**Файл:** `frontend/src/components/onboarding/AuthModal.tsx`

**Функционал:**
- Переключение между режимами "Login" и "Sign Up" (табы или ссылки)
- Форма авторизации (email, password)
- Форма регистрации (full_name, email, password, confirmPassword)
- Стиль как у `OnboardingRegisterModal` (белый фон, стандартные кнопки системы)
- После успешной авторизации/регистрации → вызывать `onSuccess(user.id)`

**Props:**
```typescript
interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (userId: string) => void
}
```

**Зависимости:**
- Использовать `authService.login()` и `authService.register()`
- Использовать `useAuthStore().login()` для обновления состояния
- Обработка ошибок через toast

---

### 2. Интегрировать логику онбординга в HomePage.tsx
**Файл:** `frontend/src/pages/HomePage.tsx`

**Что сделать:**
- Перенести всю логику из `OnboardingPage.tsx`:
  - Состояния: `sessionToken`, `currentStep`, `company`, `competitors`, `observationTaskId`, `isLoading`, `isProcessing`
  - Обработчики: `handleAnalyzeCompany`, `handleSelectCompetitors`, `handleReplaceCompetitor`, `handleObservationSetup`, `handleObservationComplete`
  - Инициализация сессии в `useEffect`
- Добавить состояние `showAuthModal`
- Импортировать все компоненты онбординга

**Структура:**
```typescript
// Условный рендеринг
if (isAuthenticated) {
  return <LandingContent /> // Hero + Features + Stats + CTA
}

// Онбординг (заменяет Hero Section)
return (
  <div>
    <OnboardingSection />
    <FeaturesSection />
    <StatsSection />
    <CTASection />
    <AuthModal ... />
  </div>
)
```

---

### 3. Добавить условный рендеринг в HomePage
**Файл:** `frontend/src/pages/HomePage.tsx`

**Логика:**
- Если `isAuthenticated === true` → показать полный лендинг (Hero + Features + Stats + CTA)
- Если `isAuthenticated === false` → показать онбординг вместо Hero Section
- Остальные секции (Features, Stats, CTA) можно оставить или скрыть

**Важно:**
- При загрузке показывать лоадер, пока инициализируется сессия онбординга
- Progress indicator для онбординга должен быть виден

---

### 4. Обновить OnboardingCompleteStep
**Файл:** `frontend/src/components/onboarding/OnboardingCompleteStep.tsx`

**Изменения:**
- Убрать `navigate('/dashboard')` из `handleStart`
- Убрать импорт `useNavigate`
- Добавить prop `onAuthRequired: () => void`
- Заменить кнопку "Начать" на "Зарегистрироваться" или "Войти"
- При нажатии на кнопку → вызывать `onAuthRequired()`

**Новый интерфейс:**
```typescript
interface OnboardingCompleteStepProps {
  company: OnboardingCompanyData
  competitors: OnboardingCompetitor[]
  onAuthRequired: () => void
}
```

**Текст кнопки:**
- "Зарегистрироваться" или "Войти в систему"
- Можно сделать две кнопки: "Войти" и "Зарегистрироваться"

---

### 5. Добавить обработчик handleAuthSuccess
**Файл:** `frontend/src/pages/HomePage.tsx`

**Функционал:**
- После успешной авторизации/регистрации в `AuthModal`
- Вызвать `ApiService.completeOnboarding(sessionToken, userId)`
- После успешного вызова → редирект на `/dashboard`
- Обработка ошибок через toast

**Код:**
```typescript
const handleAuthSuccess = async (userId: string) => {
  if (!sessionToken) {
    toast.error('Сессия онбординга не найдена')
    return
  }
  
  setIsProcessing(true)
  try {
    await ApiService.completeOnboarding(sessionToken, userId)
    toast.success('Онбординг завершен! Перенаправляем на платформу...')
    navigate('/dashboard')
  } catch (err: any) {
    toast.error(err.message || 'Ошибка при завершении онбординга')
  } finally {
    setIsProcessing(false)
  }
}
```

---

### 6. Обновить backend complete_onboarding
**Файл:** `backend/app/api/v1/endpoints/onboarding.py`

**Что добавить:**
- После создания компаний (родительской и конкурентов)
- Получить или создать `UserPreferences` для пользователя
- Добавить ID всех конкурентов в `subscribed_companies`
- Сохранить изменения в БД

**Код:**
```python
from app.models import UserPreferences
from app.models.preferences import DigestFrequency

# После создания competitor_companies:

# Get or create user preferences
result = await db.execute(
    select(UserPreferences).where(UserPreferences.user_id == final_user_id)
)
user_prefs = result.scalar_one_or_none()

if not user_prefs:
    user_prefs = UserPreferences(
        user_id=final_user_id,
        subscribed_companies=[],
        digest_enabled=True,
        digest_frequency=DigestFrequency.DAILY
    )
    db.add(user_prefs)
    await db.flush()

# Add competitor IDs to subscribed_companies
competitor_ids = [str(comp.id) for comp in competitor_companies]
existing_subscriptions = user_prefs.subscribed_companies or []
new_subscriptions = list(set(existing_subscriptions + competitor_ids))
user_prefs.subscribed_companies = new_subscriptions

await db.commit()
```

**Важно:**
- Проверить, что `final_user_id` не `None`
- Использовать `set()` для исключения дубликатов
- Обновить TODO комментарий в коде

---

### 7. Протестировать полный флоу
**Тестирование:**

1. **Неавторизованный пользователь:**
   - Заходит на `/` → видит онбординг
   - Проходит все шаги: company_input → company_card → competitor_selection → observation_setup → completed
   - Видит `OnboardingCompleteStep` с информацией о компании и конкурентах
   - Нажимает "Зарегистрироваться" → открывается `AuthModal`
   - Регистрируется → вызывается `completeOnboarding` → редирект на `/dashboard`
   - Проверяет, что конкуренты добавлены в подписки

2. **Авторизованный пользователь:**
   - Заходит на `/` → видит полный лендинг (Hero + Features + Stats + CTA)

3. **Ошибки:**
   - Проверить обработку ошибок при авторизации
   - Проверить обработку ошибок при `completeOnboarding`
   - Проверить, что сессия онбординга сохраняется при перезагрузке страницы

---

### 8. Обновить роутинг (опционально)
**Файл:** `frontend/src/App.tsx`

**Изменения:**
- Убрать роут `/onboarding` (если `OnboardingPage.tsx` больше не используется)
- Или оставить для обратной совместимости

**Опционально:**
- Можно удалить `frontend/src/pages/OnboardingPage.tsx` после успешной интеграции

---

## Порядок выполнения

1. ✅ Создать `AuthModal.tsx` (задача 1)
2. ✅ Обновить `OnboardingCompleteStep.tsx` (задача 4)
3. ✅ Интегрировать логику в `HomePage.tsx` (задачи 2, 3, 5)
4. ✅ Обновить backend `complete_onboarding` (задача 6)
5. ✅ Протестировать флоу (задача 7)
6. ✅ Обновить роутинг (задача 8, опционально)

---

## Важные моменты

1. **Сохранение сессии:** `session_token` хранится в БД, не в localStorage
2. **Авторизация:** После регистрации пользователь автоматически авторизован через `authStore.login()`
3. **Подписки:** Конкуренты добавляются в `UserPreferences.subscribed_companies` после `completeOnboarding`
4. **Редирект:** После успешного `completeOnboarding` → редирект на `/dashboard`
5. **Стили:** Использовать существующие стили системы (`btn btn-primary`, стандартные модалки)

---

## Файлы для изменения

**Создать:**
- `frontend/src/components/onboarding/AuthModal.tsx`

**Изменить:**
- `frontend/src/pages/HomePage.tsx` (полная переработка)
- `frontend/src/components/onboarding/OnboardingCompleteStep.tsx`
- `backend/app/api/v1/endpoints/onboarding.py` (метод `complete_onboarding`)

**Опционально:**
- `frontend/src/App.tsx` (убрать роут `/onboarding`)
- Удалить `frontend/src/pages/OnboardingPage.tsx` (если больше не нужен)

---

## Готово к реализации ✅

После просмотра плана можно приступать к реализации.











