# План переработки Discover Tab

**Дата создания:** 2025-01-XX  
**Статус:** 🔄 В разработке  
**Приоритет:** Высокий

---

## 📋 Обзор

Переработка вкладки Discover для создания системы отчётов о компаниях с асинхронной генерацией через Celery и отображением результатов в виде аккордеонов с табами (News, Sources, Pricing).

---

## 🎯 Цели

1. Упростить UI: убрать модальное окно, сделать простое поле ввода
2. Создать систему отчётов с асинхронной генерацией
3. Использовать polling для отслеживания статуса создания отчёта
4. Отобразить отчёты в виде аккордеонов (аналогично "My competitors")
5. Реализовать табы: News, Sources, Pricing

---

## 📦 Этапы реализации

### Этап 1: Backend - API для отчётов (2-3 дня)

#### 1.1 Создать модель Report в БД
**Файлы:**
- `backend/app/models/report.py` (новый)
- `backend/alembic/versions/XXXX_create_reports_table.py` (новая миграция)

**Структура модели:**
```python
class Report(BaseModel):
    id: UUID (PK)
    user_id: UUID (FK -> users)
    query: str  # Название компании или URL
    status: enum('processing', 'ready', 'error')
    company_id: UUID (FK -> companies, nullable)
    error_message: str (nullable)
    created_at: datetime
    completed_at: datetime (nullable)
    # Связи
    user: relationship -> User
    company: relationship -> Company
```

**Действия:**
- [x] Создать модель `Report`
- [ ] Создать миграцию Alembic
- [ ] Применить миграцию

#### 1.2 Создать репозиторий ReportRepository
**Файл:**
- `backend/app/domains/reports/repositories/report_repository.py` (новый)

**Методы:**
- `create(report_data: dict) -> Report`
- `get_by_id(report_id: UUID) -> Report | None`
- `get_by_user(user_id: UUID, limit: int, offset: int) -> List[Report]`
- `update_status(report_id: UUID, status: str, error_message: str | None = None) -> Report`
- `get_by_status(status: str) -> List[Report]`

#### 1.3 Создать Celery задачу для генерации отчёта
**Файл:**
- `backend/app/tasks/reports.py` (новый)

**Задача:**
```python
@celery_app.task(bind=True)
def generate_company_report(self, report_id: str, query: str, user_id: str):
    """
    Генерирует отчёт о компании асинхронно.
    
    Шаги:
    1. Разрешить query (URL или название компании)
    2. Найти/создать компанию через существующую логику scan_company
    3. Собрать данные:
       - Новости компании
       - Категории новостей с количеством
       - Источники с количеством новостей
       - Pricing информация из description
    4. Сохранить отчёт в БД
    5. Обновить статус: processing -> ready / error
    """
```

**Важно:**
- Использовать существующую логику из `/companies/scan`
- Обрабатывать ошибки и обновлять статус при ошибках
- Логировать прогресс выполнения

#### 1.4 Создать API endpoints
**Файл:**
- `backend/app/api/v1/endpoints/reports.py` (новый)

**Endpoints:**

1. **POST `/api/v1/reports/create`**
   - Создаёт новый отчёт со статусом `processing`
   - Запускает Celery задачу
   - Возвращает `report_id` и `status`
   ```python
   Request: { "query": "openai.com" }
   Response: { 
     "report_id": "uuid", 
     "status": "processing",
     "created_at": "2025-01-XX..."
   }
   ```

2. **GET `/api/v1/reports/{report_id}/status`**
   - Проверяет статус отчёта
   - Возвращает текущий статус и ошибку (если есть)
   ```python
   Response: { 
     "status": "processing" | "ready" | "error",
     "error": null | "error message"
   }
   ```

3. **GET `/api/v1/reports/{report_id}`**
   - Возвращает полные данные отчёта (только для `status='ready'`)
   ```python
   Response: {
     "id": "uuid",
     "query": "openai.com",
     "status": "ready",
     "company": {...},
     "categories": [...],
     "news": [...],
     "sources": [...],
     "pricing": {...},
     "created_at": "...",
     "completed_at": "..."
   }
   ```

4. **GET `/api/v1/reports/`**
   - Список отчётов пользователя
   - Query params: `limit`, `offset`
   ```python
   Response: {
     "items": [...],
     "total": 10,
     "limit": 10,
     "offset": 0
   }
   ```

**Действия:**
- [ ] Создать роутер
- [ ] Подключить к `backend/app/api/v1/router.py`
- [ ] Добавить валидацию и обработку ошибок
- [ ] Добавить rate limiting (опционально)

---

### Этап 2: Frontend - Типы и API сервис (0.5 дня)

#### 2.1 Определить TypeScript интерфейсы
**Файл:**
- `frontend/src/types/index.ts`

**Добавить:**
```typescript
export interface Report {
  id: string
  query: string
  status: 'processing' | 'ready' | 'error'
  company_id?: string
  company?: Company
  error_message?: string
  created_at: string
  completed_at?: string
  // Данные отчёта (только для status='ready')
  categories?: CategoryStats[]
  news?: NewsItem[]
  sources?: SourceStats[]
  pricing?: PricingInfo
}

export interface CategoryStats {
  category: string
  technicalCategory: string
  count: number
}

export interface SourceStats {
  url: string
  type: string
  count: number
}

export interface PricingInfo {
  description?: string
  news?: NewsItem[]
}

export interface ReportCreateRequest {
  query: string
}

export interface ReportStatusResponse {
  status: 'processing' | 'ready' | 'error'
  error?: string
}

export interface ReportsListResponse {
  items: Report[]
  total: number
  limit: number
  offset: number
}
```

#### 2.2 Добавить методы в ApiService
**Файл:**
- `frontend/src/services/api.ts`

**Методы:**
```typescript
// Создать отчёт
createReport(query: string): Promise<{ report_id: string; status: string; created_at: string }>

// Получить статус отчёта
getReportStatus(reportId: string): Promise<ReportStatusResponse>

// Получить данные отчёта
getReport(reportId: string): Promise<Report>

// Получить список отчётов
getReports(limit?: number, offset?: number): Promise<ReportsListResponse>
```

---

### Этап 3: Frontend - Рефакторинг UI Discover (1 день)

#### 3.1 Упростить Hero Section
**Файл:**
- `frontend/src/pages/DashboardPageTest.tsx` (строки 882-914)

**Изменения:**
- [ ] Убрать модальное окно (`setShowSearchModal`)
- [ ] Убрать `readOnly` с input поля
- [ ] Убрать кнопку "Search" (ввод по Enter)
- [ ] Добавить обработку `onKeyDown` для Enter
- [ ] Упростить placeholder: "Спросите что-нибудь..." (как на картинке)

**Новый код:**
```typescript
<input
  type="text"
  placeholder="Спросите что-нибудь..."
  className="input pl-12 pr-4 py-4 text-lg w-full shadow-sm"
  value={discoverSearchQuery}
  onChange={(e) => setDiscoverSearchQuery(e.target.value)}
  onKeyDown={(e) => {
    if (e.key === 'Enter' && discoverSearchQuery.trim()) {
      handleCreateReport(discoverSearchQuery.trim())
    }
  }}
/>
```

#### 3.2 Убрать информационные карточки
**Файл:**
- `frontend/src/pages/DashboardPageTest.tsx` (строки 917-939)

**Логика:**
- Показывать карточки только если `discoverSearchQuery.length === 0`
- При вводе текста (> 0 символов) - скрывать карточки
- При создании отчёта - сразу скрывать

**Код:**
```typescript
{discoverSearchQuery.length === 0 && reports.length === 0 && (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
    {/* Карточки */}
  </div>
)}
```

#### 3.3 Убрать/упростить Onboarding Helper
**Файл:**
- `frontend/src/pages/DashboardPageTest.tsx` (строки 941-955)

**Решение:**
- Удалить или заменить на простое сообщение (опционально)

---

### Этап 4: Frontend - State management для отчётов (1 день)

#### 4.1 Добавить state переменные
**Файл:**
- `frontend/src/pages/DashboardPageTest.tsx`

**Добавить:**
```typescript
// State для Discover
const [discoverSearchQuery, setDiscoverSearchQuery] = useState('')

// State для отчётов
const [reports, setReports] = useState<Report[]>([])
const [reportStatuses, setReportStatuses] = useState<Record<string, 'processing' | 'ready' | 'error'>>({})
const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set())
const [reportTabs, setReportTabs] = useState<Record<string, 'news' | 'sources' | 'pricing'>>({})
const [reportData, setReportData] = useState<Record<string, Report>>({})

// Polling intervals (для cleanup)
const [pollingIntervals, setPollingIntervals] = useState<Record<string, NodeJS.Timeout>>({})
```

#### 4.2 Функция создания отчёта
**Функция:**
```typescript
const handleCreateReport = async (query: string) => {
  if (!query.trim()) {
    toast.error('Please enter a company name or URL')
    return
  }

  try {
    const toastId = toast.loading('Creating report...', { id: `create-report-${Date.now()}` })
    
    const { report_id, status, created_at } = await ApiService.createReport(query.trim())
    
    // Добавить в список отчётов
    const newReport: Report = {
      id: report_id,
      query: query.trim(),
      status: 'processing',
      created_at,
    }
    
    setReports(prev => [newReport, ...prev]) // Новые отчёты вверху
    setReportStatuses(prev => ({ ...prev, [report_id]: 'processing' }))
    
    // Начать polling
    startPollingReportStatus(report_id)
    
    // Очистить поле ввода
    setDiscoverSearchQuery('')
    
    toast.success('Report creation started!', { id: toastId })
  } catch (error: any) {
    const errorMessage = error?.response?.data?.detail || 'Failed to create report'
    toast.error(errorMessage, { id: `create-report-${Date.now()}` })
    console.error('Failed to create report:', error)
  }
}
```

#### 4.3 Вспомогательные функции
```typescript
const toggleReportExpanded = (reportId: string) => {
  setExpandedReports(prev => {
    const next = new Set(prev)
    if (next.has(reportId)) {
      next.delete(reportId)
    } else {
      next.add(reportId)
    }
    return next
  })
}
```

---

### Этап 5: Frontend - Polling механизм (1 день)

#### 5.1 Реализовать polling для статуса
**Паттерн:** Использовать аналогичный подход из `CompetitorAnalysisPage.tsx` (строки 256-295)

**Функция:**
```typescript
const startPollingReportStatus = (reportId: string) => {
  // Очистить предыдущий интервал, если есть
  if (pollingIntervals[reportId]) {
    clearInterval(pollingIntervals[reportId])
  }

  const MAX_POLLING_TIME = 5 * 60 * 1000 // 5 минут
  const POLLING_INTERVAL = 2000 // 2 секунды
  const startTime = Date.now()

  const intervalId = setInterval(async () => {
    // Проверка таймаута
    if (Date.now() - startTime > MAX_POLLING_TIME) {
      clearInterval(intervalId)
      setReportStatuses(prev => ({ ...prev, [reportId]: 'error' }))
      toast.error('Report creation timeout', { id: `report-${reportId}` })
      return
    }

    try {
      const statusResponse = await ApiService.getReportStatus(reportId)
      const currentStatus = statusResponse.status
      
      setReportStatuses(prev => ({ ...prev, [reportId]: currentStatus }))
      
      if (currentStatus === 'ready') {
        clearInterval(intervalId)
        // Удалить из polling intervals
        setPollingIntervals(prev => {
          const next = { ...prev }
          delete next[reportId]
          return next
        })
        // Загрузить данные отчёта
        await loadReportData(reportId)
        toast.success('Report ready!', { id: `report-${reportId}` })
      } else if (currentStatus === 'error') {
        clearInterval(intervalId)
        setPollingIntervals(prev => {
          const next = { ...prev }
          delete next[reportId]
          return next
        })
        toast.error(`Report failed: ${statusResponse.error || 'Unknown error'}`, { 
          id: `report-${reportId}` 
        })
      }
    } catch (error) {
      console.error('Failed to check report status:', error)
      // Продолжать polling при ошибках сети
    }
  }, POLLING_INTERVAL)

  // Сохранить interval ID для cleanup
  setPollingIntervals(prev => ({ ...prev, [reportId]: intervalId }))
}
```

#### 5.2 Функция загрузки данных отчёта
```typescript
const loadReportData = async (reportId: string) => {
  try {
    const report = await ApiService.getReport(reportId)
    setReportData(prev => ({ ...prev, [reportId]: report }))
    
    // Обновить отчёт в списке
    setReports(prev => prev.map(r => r.id === reportId ? report : r))
  } catch (error) {
    console.error('Failed to load report data:', error)
    toast.error('Failed to load report data', { id: `report-${reportId}` })
  }
}
```

#### 5.3 Cleanup при размонтировании
```typescript
useEffect(() => {
  return () => {
    // Очистить все polling intervals
    Object.values(pollingIntervals).forEach(intervalId => {
      clearInterval(intervalId)
    })
  }
}, [pollingIntervals])
```

---

### Этап 6: Frontend - Компонент карточки отчёта (2 дня)

#### 6.1 Создать компонент ReportCard
**Файл:**
- `frontend/src/components/dashboard/ReportCard.tsx` (новый)

**Props:**
```typescript
interface ReportCardProps {
  report: Report
  isExpanded: boolean
  activeTab: 'news' | 'sources' | 'pricing'
  onExpand: () => void
  onTabChange: (tab: 'news' | 'sources' | 'pricing') => void
  reportData?: Report // Полные данные (только для status='ready')
}
```

**Структура компонента:**
1. **Заголовок** (всегда видимый):
   - Логотип компании или placeholder (Globe icon)
   - Название компании или query
   - Статус badge (processing/ready/error)
   - Дата создания
   - Кнопка expand/collapse

2. **Состояние `processing`:**
   - Спиннер
   - Текст: "Preparing report..."

3. **Состояние `error`:**
   - Сообщение об ошибке
   - Кнопка "Retry"

4. **Состояние `ready`** (развёрнутое):
   - Описание компании (выделенный блок)
   - Категории новостей с количеством
   - Табы: News, Sources, Pricing
   - Ссылки: Website, Social links

#### 6.2 Реализовать табы в аккордеоне
**Использовать паттерн из:** `DashboardPageTest.tsx` (строки 1224-1385)

**Tab: News** (аналог строк 1245-1282)
```typescript
{activeTab === 'news' && (
  <div className="space-y-3">
    {reportData?.news && reportData.news.length > 0 ? (
      reportData.news.map((news) => (
        <div key={news.id} className="border-l-2 border-primary-200 pl-3 py-1">
          <a
            href={news.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-gray-900 hover:text-primary-600 font-medium block"
          >
            {news.title}
          </a>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-gray-500">
              {formatDate(news.published_at || news.created_at)}
            </span>
            {news.category && (
              <>
                <span className="text-xs text-gray-400">•</span>
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                  {categoryLabels[news.category] || news.category}
                </span>
              </>
            )}
          </div>
        </div>
      ))
    ) : (
      <p className="text-sm text-gray-500 py-4">Новости не найдены</p>
    )}
  </div>
)}
```

**Tab: Sources** (аналог строк 1284-1320)
```typescript
{activeTab === 'sources' && (
  <div>
    {reportData?.sources && reportData.sources.length > 0 ? (
      <div className="space-y-2">
        {reportData.sources.map((source, idx) => (
          <div key={idx} className="flex items-start justify-between gap-2 p-2 bg-gray-50 rounded text-sm">
            <div className="flex-1 min-w-0">
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:text-primary-700 break-all inline-flex items-center gap-1"
              >
                {source.url}
                <ExternalLink className="h-3 w-3" />
              </a>
              <span className="text-xs text-gray-500 ml-2 capitalize">
                ({source.type})
              </span>
            </div>
            <span className="text-xs text-gray-500 whitespace-nowrap">
              {source.count} новостей
            </span>
          </div>
        ))}
      </div>
    ) : (
      <p className="text-xs text-gray-500 py-4">Источники не найдены</p>
    )}
  </div>
)}
```

**Tab: Pricing** (аналог строк 1322-1384)
```typescript
{activeTab === 'pricing' && (
  <div className="space-y-4">
    {reportData?.pricing?.description && 
     (reportData.pricing.description.toLowerCase().includes('pricing') || 
      reportData.pricing.description.toLowerCase().includes('price') ||
      reportData.pricing.description.toLowerCase().includes('$')) && (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="text-sm font-semibold text-gray-900 mb-2">Информация о ценообразовании:</h4>
        <p className="text-sm text-gray-700 leading-relaxed">
          {reportData.pricing.description}
        </p>
      </div>
    )}

    {reportData?.pricing?.news && reportData.pricing.news.length > 0 ? (
      <div>
        <h4 className="text-sm font-semibold text-gray-900 mb-3">Последние изменения цен:</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {reportData.pricing.news.map((news) => (
            <div key={news.id} className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
              <a
                href={news.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-gray-900 hover:text-primary-600 font-semibold block mb-2"
              >
                {news.title}
              </a>
              {news.summary && (
                <p className="text-xs text-gray-600 mb-2 line-clamp-2">{news.summary}</p>
              )}
              <div className="text-xs text-gray-500">
                {formatDate(news.published_at || news.created_at)}
              </div>
            </div>
          ))}
        </div>
      </div>
    ) : (
      !reportData?.pricing?.description && (
        <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
          <p className="text-sm text-gray-500">
            Информация о ценообразовании пока недоступна
          </p>
        </div>
      )
    )}
  </div>
)}
```

#### 6.3 Интегрировать ReportCard в Discover
**Файл:**
- `frontend/src/pages/DashboardPageTest.tsx`

**Код:**
```typescript
{activeTab === 'discover' && (
  <div className="space-y-6">
    {/* Hero Section with Search Bar */}
    <div className="card p-8 border-2">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-3xl font-bold text-gray-900 mb-3">
          Чем я могу помочь?
        </h2>
        
        {/* Search Bar */}
        <div className="relative mb-4">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Спросите что-нибудь..."
            className="input pl-12 pr-4 py-4 text-lg w-full shadow-sm"
            value={discoverSearchQuery}
            onChange={(e) => setDiscoverSearchQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && discoverSearchQuery.trim()) {
                handleCreateReport(discoverSearchQuery.trim())
              }
            }}
          />
        </div>
      </div>
    </div>

    {/* Information Cards - показывать только если нет запроса и отчётов */}
    {discoverSearchQuery.length === 0 && reports.length === 0 && (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Карточки */}
      </div>
    )}

    {/* Reports List */}
    {reports.length > 0 && (
      <div className="flex flex-col gap-4">
        {reports.map((report) => {
          const isExpanded = expandedReports.has(report.id)
          const activeTab = reportTabs[report.id] || 'news'
          const fullReportData = reportData[report.id] || report

          return (
            <ReportCard
              key={report.id}
              report={report}
              isExpanded={isExpanded}
              activeTab={activeTab}
              reportData={fullReportData.status === 'ready' ? fullReportData : undefined}
              onExpand={() => toggleReportExpanded(report.id)}
              onTabChange={(tab) => setReportTabs(prev => ({ ...prev, [report.id]: tab }))}
            />
          )
        })}
      </div>
    )}
  </div>
)}
```

---

### Этап 7: Frontend - Toast уведомления (0.5 дня)

#### 7.1 Добавить toast для всех событий
**Использовать:** `react-hot-toast` (уже подключен)

**События:**
1. При создании отчёта:
   ```typescript
   toast.loading('Creating report...', { id: `create-report-${timestamp}` })
   ```

2. При успешном старте:
   ```typescript
   toast.success('Report creation started!', { id: toastId })
   ```

3. При готовности отчёта:
   ```typescript
   toast.success('Report ready!', { id: `report-${reportId}` })
   ```

4. При ошибке:
   ```typescript
   toast.error(`Report failed: ${errorMessage}`, { id: `report-${reportId}` })
   ```

5. При таймауте:
   ```typescript
   toast.error('Report creation timeout', { id: `report-${reportId}` })
   ```

---

### Этап 8: Тестирование и полировка (1-2 дня)

#### 8.1 Unit тесты
- [ ] Тесты для функций создания/загрузки отчётов
- [ ] Тесты для polling логики
- [ ] Тесты для обработки ошибок

#### 8.2 E2E тесты
- [ ] Создание отчёта через UI
- [ ] Polling статуса до готовности
- [ ] Отображение готового отчёта
- [ ] Переключение табов
- [ ] Expand/collapse аккордеона

#### 8.3 Edge cases
- [ ] Что если пользователь закрыл вкладку во время создания?
  - Решение: polling автоматически остановится
- [ ] Что если отчёт упал с ошибкой?
  - Решение: показать сообщение об ошибке и кнопку retry
- [ ] Что если несколько отчётов создаются одновременно?
  - Решение: каждый отчёт в отдельном polling интервале
- [ ] Что если сервер недоступен?
  - Решение: показать ошибку, не ломать UI

#### 8.4 Оптимизация
- [ ] Debounce для input поля (500ms) - опционально
- [ ] Кэширование отчётов (React Query) - опционально
- [ ] Skeleton loader для loading состояния
- [ ] Анимации появления отчётов

---

### Этап 9: Финальная полировка (1 день)

#### 9.1 UI/UX улучшения
- [ ] Skeleton loader для loading состояния отчёта
- [ ] Плавные анимации expand/collapse
- [ ] Подтверждение перед созданием дубликата отчёта (опционально)
- [ ] Кнопка "Clear" для очистки поля ввода

#### 9.2 Обновить README
**Файл:**
- `README.md`

**Добавить:**
- Описание нового функционала Discover
- Информацию о файлах и их назначении:
  - `backend/app/models/report.py` - модель отчёта
  - `backend/app/tasks/reports.py` - Celery задачи для генерации отчётов
  - `backend/app/api/v1/endpoints/reports.py` - API endpoints для отчётов
  - `frontend/src/components/dashboard/ReportCard.tsx` - компонент карточки отчёта

---

## 📊 Timeline

| Этап | Время | Приоритет | Статус |
|------|-------|-----------|--------|
| Этап 1: Backend API | 2-3 дня | 🔴 Критично | ⏳ Pending |
| Этап 2: Frontend типы/API | 0.5 дня | 🔴 Критично | ⏳ Pending |
| Этап 3: Рефакторинг UI | 1 день | 🟠 Высокий | ⏳ Pending |
| Этап 4: State management | 1 день | 🟠 Высокий | ⏳ Pending |
| Этап 5: Polling | 1 день | 🟠 Высокий | ⏳ Pending |
| Этап 6: Компонент отчёта | 2 дня | 🔴 Критично | ⏳ Pending |
| Этап 7: Toast | 0.5 дня | 🟡 Средний | ⏳ Pending |
| Этап 8: Тестирование | 1-2 дня | 🟡 Средний | ⏳ Pending |
| Этап 9: Полировка | 1 день | 🟢 Низкий | ⏳ Pending |
| **Итого** | **9-12 дней** | | |

---

## ❓ Решения и допущения

### 1. Хранение отчётов
**Решение:** Отчёты сохраняются в БД для истории
- Пользователь может видеть историю своих отчётов
- Отчёты можно пересматривать позже
- **Лимит:** Последние 20 отчётов по умолчанию, остальные по запросу

### 2. Автоматическое добавление в "My competitors"
**Решение:** Нет, не добавлять автоматически
- Пользователь может добавить компанию вручную после просмотра отчёта
- Отчёты и подписки - разные сущности

### 3. Polling интервал и таймаут
**Решение:**
- Интервал: 2 секунды
- Таймаут: 5 минут
- Если отчёт не готов за 5 минут - показать ошибку

### 4. Обработка ошибок
**Решение:**
- Все ошибки логируются в консоль
- Пользователю показываются понятные сообщения через toast
- Статус отчёта обновляется на `error` с сообщением

---

## 🔗 Связанные файлы

### Backend
- `backend/app/models/report.py` (новый)
- `backend/app/domains/reports/repositories/report_repository.py` (новый)
- `backend/app/tasks/reports.py` (новый)
- `backend/app/api/v1/endpoints/reports.py` (новый)
- `backend/app/api/v1/router.py` (обновить)
- `backend/app/celery_app.py` (обновить, добавить tasks.reports)

### Frontend
- `frontend/src/types/index.ts` (обновить)
- `frontend/src/services/api.ts` (обновить)
- `frontend/src/pages/DashboardPageTest.tsx` (обновить)
- `frontend/src/components/dashboard/ReportCard.tsx` (новый)

### Миграции
- `backend/alembic/versions/XXXX_create_reports_table.py` (новый)

---

## 📝 Примечания

1. Использовать существующие паттерны из проекта:
   - Polling из `CompetitorAnalysisPage.tsx`
   - Аккордеон из "My competitors" таба
   - Toast уведомления из существующих компонентов

2. Приоритет на простоту и надёжность:
   - Не усложнять архитектуру
   - Использовать проверенные подходы
   - Обрабатывать все edge cases

3. Производительность:
   - Polling должен быть лёгким (только проверка статуса)
   - Загрузка данных только при `status='ready'`
   - Cleanup intervals при размонтировании

---

## ✅ Критерии готовности

- [ ] Backend API работает и протестирован
- [ ] Celery задачи выполняются корректно
- [ ] Frontend создаёт отчёты и отслеживает статус
- [ ] Отчёты отображаются в виде аккордеонов
- [ ] Табы News/Sources/Pricing работают
- [ ] Toast уведомления показываются корректно
- [ ] Edge cases обработаны
- [ ] README обновлён
- [ ] Код протестирован

---

**Последнее обновление:** 2025-01-XX

