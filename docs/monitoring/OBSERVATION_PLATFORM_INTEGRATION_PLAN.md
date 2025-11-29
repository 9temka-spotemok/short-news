# План интеграции процессов наблюдения на платформу

## 📋 Обзор

Документ описывает, как данные наблюдения за конкурентами (соцсети, структура сайтов, маркетинговые изменения, SEO сигналы) будут интегрироваться в существующую платформу и отображаться пользователям.

---

## 🎯 Цели интеграции

1. **Отображение данных наблюдения** на существующих страницах
2. **Новые компоненты** для визуализации данных
3. **API endpoints** для получения данных наблюдения
4. **Уведомления** о важных изменениях
5. **Единый интерфейс** для управления мониторингом

---

## 📍 Места интеграции на платформе

### 1. Dashboard (Главная страница)

**Файл:** `frontend/src/pages/DashboardPage.tsx`

#### 1.1. Новая секция "Monitoring Status"

**Расположение:** После секции StatsCards, перед списком новостей

**Компонент:** `MonitoringStatusCard.tsx` (новый)

**Что отображает:**
- Статус мониторинга для каждой отслеживаемой компании
- Количество найденных источников (соцсети, страницы сайта)
- Последнее обновление данных
- Индикатор активности (зелёный/жёлтый/красный)

**Данные:**
```typescript
interface MonitoringStatus {
  company_id: string
  company_name: string
  logo_url?: string
  social_media_count: number
  website_sources_count: number
  last_updated: string
  status: 'active' | 'pending' | 'error'
  changes_detected_today: number
}
```

**API endpoint:** `GET /api/v1/companies/monitoring/status?company_ids[]=...`

#### 1.2. Расширение ReportCard

**Файл:** `frontend/src/components/dashboard/ReportCard.tsx`

**Новый таб:** "Monitoring" (после таба "Competitors")

**Что отображает:**
- Найденные соцсети (иконки + ссылки)
- Структура сайта (основные страницы)
- Последние изменения (маркетинг, структура, SEO)
- SEO сигналы (meta tags, structured data)

**Данные:**
```typescript
interface MonitoringData {
  social_media: {
    facebook?: string
    instagram?: string
    twitter?: string
    linkedin?: string
    youtube?: string
    tiktok?: string
  }
  website_structure: {
    main_pages: Array<{ url: string; title: string; last_checked: string }>
    navigation_changes: number
  }
  recent_changes: Array<{
    type: 'marketing' | 'structure' | 'seo'
    description: string
    detected_at: string
  }>
  seo_signals: {
    meta_tags: Record<string, string>
    structured_data_types: string[]
    sitemap_url?: string
  }
}
```

**API endpoint:** `GET /api/v1/reports/{report_id}/monitoring`

---

### 2. CompetitorAnalysisPage (Страница анализа конкурентов)

**Файл:** `frontend/src/pages/CompetitorAnalysisPage.tsx`

#### 2.1. Расширение CurrentSignalsBoard

**Файл:** `frontend/src/features/competitor-analysis/components/CurrentSignalsBoard.tsx`

**Новая секция:** "Monitoring Sources"

**Что отображает:**
- Карточка с найденными соцсетями (иконки платформ)
- Ссылки на основные страницы сайта (pricing, blog, careers)
- Индикатор последнего обновления

**Компонент:** `MonitoringSourcesCard.tsx` (новый)

#### 2.2. Расширение ChangeEventsSection

**Файл:** `frontend/src/features/competitor-analysis/components/ChangeEventsSection.tsx`

**Дополнение:** Добавить фильтры по типу изменений

**Новые типы событий:**
- `website_structure` - изменения структуры сайта
- `marketing_banner` - изменения баннеров
- `marketing_landing` - изменения лендингов
- `marketing_product` - новые продукты
- `marketing_jobs` - новые вакансии
- `seo_meta` - изменения meta tags
- `seo_structure` - изменения structured data

**Фильтры:**
```typescript
type ChangeEventType = 
  | 'pricing' 
  | 'features' 
  | 'website_structure'
  | 'marketing_banner'
  | 'marketing_landing'
  | 'marketing_product'
  | 'marketing_jobs'
  | 'seo_meta'
  | 'seo_structure'
```

#### 2.3. Новая секция "Monitoring Matrix"

**Расположение:** После ChangeEventsSection

**Компонент:** `MonitoringMatrixSection.tsx` (новый)

**Что отображает:**
- Таблица/матрица всех источников мониторинга
- Статус каждого источника (активен/неактивен)
- Последняя проверка
- Количество изменений за период

**Структура:**
```
┌─────────────────────────────────────────────────┐
│ Monitoring Matrix                                 │
├─────────────────────────────────────────────────┤
│ Social Media                                      │
│  ✓ Facebook    https://fb.com/company  (2h ago) │
│  ✓ Twitter     https://x.com/company   (1h ago) │
│  ✗ Instagram   Not found                        │
│                                                  │
│ Website Pages                                    │
│  ✓ Pricing     https://company.com/pricing      │
│  ✓ Blog        https://company.com/blog         │
│  ✓ Careers     https://company.com/careers      │
│                                                  │
│ SEO Signals                                      │
│  ✓ Meta tags   Updated 3h ago                   │
│  ✓ Sitemap     Found                            │
└─────────────────────────────────────────────────┘
```

**API endpoint:** `GET /api/v1/companies/{company_id}/monitoring/matrix`

---

### 3. Новая страница "Monitoring Dashboard"

**Файл:** `frontend/src/pages/MonitoringDashboardPage.tsx` (новый)

**Роут:** `/monitoring`

**Назначение:** Централизованное управление мониторингом всех отслеживаемых компаний

**Структура страницы:**

#### 3.1. Заголовок
- Название страницы "Competitor Monitoring"
- Кнопка "Refresh All" для обновления всех данных
- Фильтры по компаниям

#### 3.2. Список компаний с мониторингом

**Компонент:** `CompanyMonitoringCard.tsx` (новый)

**Для каждой компании отображает:**
- Логотип и название
- Статус мониторинга (активен/ошибка)
- Быстрая статистика:
  - Найдено соцсетей: X/6
  - Отслеживается страниц: X
  - Изменений за неделю: X
- Кнопка "View Details" → переход на CompetitorAnalysisPage

#### 3.3. Сводная таблица изменений

**Компонент:** `MonitoringChangesTable.tsx` (новый)

**Таблица с колонками:**
- Компания
- Тип изменения
- Описание
- Дата обнаружения
- Источник
- Действия (View, Dismiss)

**API endpoint:** `GET /api/v1/monitoring/changes?company_ids[]=...&limit=50`

---

### 4. Настройки мониторинга

**Файл:** `frontend/src/pages/SettingsPage.tsx`

**Новая секция:** "Monitoring Settings"

**Что настраивается:**
- Частота проверки изменений (ежедневно, каждые 6 часов, еженедельно)
- Типы изменений для уведомлений (чекбоксы)
- Email/Telegram уведомления о критических изменениях
- Автоматическое обновление данных

**API endpoint:** `GET/PUT /api/v1/user/preferences/monitoring`

---

## 🔌 API Endpoints для интеграции

### Новые endpoints

#### 1. Получение статуса мониторинга
```
GET /api/v1/companies/monitoring/status
Query params:
  - company_ids[]: string[] (UUID компаний)
Response: {
  companies: MonitoringStatus[]
}
```

#### 2. Получение матрицы мониторинга
```
GET /api/v1/companies/{company_id}/monitoring/matrix
Response: {
  company_id: string
  social_media: SocialMediaSources
  website_structure: WebsiteStructure
  seo_signals: SEOSignals
  last_updated: string
}
```

#### 3. Получение данных мониторинга для отчёта
```
GET /api/v1/reports/{report_id}/monitoring
Response: MonitoringData
```

#### 4. Получение изменений мониторинга
```
GET /api/v1/monitoring/changes
Query params:
  - company_ids[]: string[]
  - change_types[]: string[] (pricing, structure, marketing, seo)
  - limit: number
  - offset: number
Response: {
  items: MonitoringChangeEvent[]
  total: number
}
```

#### 5. Настройки мониторинга пользователя
```
GET /api/v1/user/preferences/monitoring
PUT /api/v1/user/preferences/monitoring
Body: {
  check_frequency: 'daily' | '6h' | 'weekly'
  notify_on_changes: boolean
  change_types: string[]
  auto_refresh: boolean
}
```

### Расширение существующих endpoints

#### 1. GET /api/v1/companies/{company_id}
**Добавить поля:**
```json
{
  "id": "...",
  "name": "...",
  "social_media": {
    "facebook": "...",
    "instagram": "...",
    "twitter": "...",
    "linkedin": "...",
    "youtube": "...",
    "tiktok": "..."
  },
  "monitoring_enabled": true,
  "monitoring_last_updated": "2025-01-15T10:00:00Z"
}
```

#### 2. GET /api/v1/competitors/changes/{company_id}
**Расширить типы событий:**
- Добавить новые `source_type` для маркетинга, структуры, SEO
- Добавить фильтрацию по новым типам

---

## 🎨 Новые компоненты

### 1. MonitoringStatusCard
**Файл:** `frontend/src/components/monitoring/MonitoringStatusCard.tsx`

**Назначение:** Карточка статуса мониторинга компании

**Props:**
```typescript
interface MonitoringStatusCardProps {
  company: Company
  status: MonitoringStatus
  onViewDetails?: () => void
}
```

### 2. MonitoringSourcesCard
**Файл:** `frontend/src/components/monitoring/MonitoringSourcesCard.tsx`

**Назначение:** Отображение найденных источников (соцсети, страницы)

**Props:**
```typescript
interface MonitoringSourcesCardProps {
  companyId: string
  socialMedia: SocialMediaSources
  websitePages: WebsitePage[]
}
```

### 3. MonitoringMatrixSection
**Файл:** `frontend/src/components/monitoring/MonitoringMatrixSection.tsx`

**Назначение:** Полная матрица мониторинга компании

**Props:**
```typescript
interface MonitoringMatrixSectionProps {
  companyId: string
  matrix: MonitoringMatrix
  onRefresh?: () => void
}
```

### 4. MonitoringChangesTable
**Файл:** `frontend/src/components/monitoring/MonitoringChangesTable.tsx`

**Назначение:** Таблица изменений мониторинга

**Props:**
```typescript
interface MonitoringChangesTableProps {
  changes: MonitoringChangeEvent[]
  loading?: boolean
  onLoadMore?: () => void
  hasMore?: boolean
}
```

### 5. CompanyMonitoringCard
**Файл:** `frontend/src/components/monitoring/CompanyMonitoringCard.tsx`

**Назначение:** Карточка компании на странице Monitoring Dashboard

**Props:**
```typescript
interface CompanyMonitoringCardProps {
  company: Company
  monitoringStats: MonitoringStats
  onViewDetails: () => void
  onRefresh: () => void
}
```

### 6. SocialMediaIcons
**Файл:** `frontend/src/components/monitoring/SocialMediaIcons.tsx`

**Назначение:** Иконки соцсетей с ссылками

**Props:**
```typescript
interface SocialMediaIconsProps {
  socialMedia: SocialMediaSources
  size?: 'sm' | 'md' | 'lg'
}
```

---

## 📊 Типы данных (TypeScript)

### Новые типы в `frontend/src/types/index.ts`

```typescript
// Соцсети
export interface SocialMediaSources {
  facebook?: string
  instagram?: string
  twitter?: string
  linkedin?: string
  youtube?: string
  tiktok?: string
}

// Структура сайта
export interface WebsitePage {
  url: string
  title: string
  type: 'main' | 'pricing' | 'blog' | 'careers' | 'about'
  last_checked: string
  changes_detected: number
}

export interface WebsiteStructure {
  main_pages: WebsitePage[]
  navigation_changes: number
  last_snapshot: string
}

// SEO сигналы
export interface SEOSignals {
  meta_tags: Record<string, string>
  structured_data_types: string[]
  sitemap_url?: string
  robots_txt_url?: string
  last_checked: string
}

// Матрица мониторинга
export interface MonitoringMatrix {
  company_id: string
  social_media: SocialMediaSources
  website_structure: WebsiteStructure
  seo_signals: SEOSignals
  last_updated: string
}

// Статус мониторинга
export interface MonitoringStatus {
  company_id: string
  company_name: string
  logo_url?: string
  social_media_count: number
  website_sources_count: number
  last_updated: string
  status: 'active' | 'pending' | 'error'
  changes_detected_today: number
}

// События изменений мониторинга
export interface MonitoringChangeEvent {
  id: string
  company_id: string
  change_type: 'website_structure' | 'marketing_banner' | 'marketing_landing' | 'marketing_product' | 'marketing_jobs' | 'seo_meta' | 'seo_structure'
  description: string
  detected_at: string
  source_url?: string
  details?: Record<string, any>
}

// Статистика мониторинга
export interface MonitoringStats {
  social_media_count: number
  website_pages_count: number
  changes_last_week: number
  changes_last_month: number
  last_updated: string
  status: 'active' | 'pending' | 'error'
}
```

---

## 🔄 Интеграция с существующими компонентами

### 1. ReportCard

**Изменения:**
- Добавить таб "Monitoring" после "Competitors"
- Загружать данные мониторинга при открытии таба
- Отображать соцсети, структуру сайта, последние изменения

**Код:**
```typescript
// В ReportCard.tsx
const [monitoringData, setMonitoringData] = useState<MonitoringData | null>(null)

const loadMonitoringData = async () => {
  if (!report.id) return
  const data = await ApiService.getReportMonitoring(report.id)
  setMonitoringData(data)
}

// В табах
{activeTab === 'monitoring' && (
  <MonitoringTab 
    data={monitoringData} 
    loading={loadingMonitoring}
    onRefresh={loadMonitoringData}
  />
)}
```

### 2. ChangeEventsSection

**Изменения:**
- Расширить фильтры для новых типов изменений
- Добавить иконки для типов изменений
- Группировать по типу изменения

**Код:**
```typescript
// Фильтры
const changeTypeFilters = [
  'pricing',
  'features',
  'website_structure',
  'marketing_banner',
  'marketing_landing',
  'marketing_product',
  'marketing_jobs',
  'seo_meta',
  'seo_structure'
]
```

### 3. CurrentSignalsBoard

**Изменения:**
- Добавить секцию "Monitoring Sources"
- Показывать найденные соцсети
- Показывать основные страницы сайта

**Код:**
```typescript
// В CurrentSignalsBoard.tsx
<MonitoringSourcesCard
  companyId={selectedCompany?.id}
  socialMedia={monitoringMatrix?.social_media}
  websitePages={monitoringMatrix?.website_structure.main_pages}
/>
```

---

## 🔔 Уведомления

### Интеграция с системой уведомлений

**Файл:** `backend/app/domains/notifications/services/notification_service.py`

**Новые типы уведомлений:**
- `monitoring_structure_change` - изменение структуры сайта
- `monitoring_marketing_change` - маркетинговые изменения
- `monitoring_seo_change` - изменения SEO
- `monitoring_new_social` - найдена новая соцсеть

**Настройки пользователя:**
- Включить/выключить уведомления о мониторинге
- Выбрать типы изменений для уведомлений
- Настроить частоту уведомлений

---

## 📱 Мобильная версия

Все новые компоненты должны быть адаптивными:
- Карточки мониторинга → вертикальный layout на мобильных
- Таблицы → скроллируемые списки
- Матрица мониторинга → аккордеон с секциями

---

## 🚀 Поэтапная реализация

### Этап 1: Backend API (1-2 дня)
- [ ] Создать новые API endpoints
- [ ] Расширить существующие endpoints
- [ ] Добавить типы данных в схемы

### Этап 2: Базовые компоненты (2-3 дня)
- [ ] MonitoringStatusCard
- [ ] MonitoringSourcesCard
- [ ] SocialMediaIcons
- [ ] Базовые типы TypeScript

### Этап 3: Интеграция в Dashboard (1-2 дня)
- [ ] Добавить секцию Monitoring Status
- [ ] Расширить ReportCard табом Monitoring
- [ ] Интеграция с API

### Этап 4: Интеграция в CompetitorAnalysisPage (2-3 дня)
- [ ] Расширить CurrentSignalsBoard
- [ ] Расширить ChangeEventsSection
- [ ] Добавить MonitoringMatrixSection

### Этап 5: Новая страница Monitoring Dashboard (2-3 дня)
- [ ] Создать MonitoringDashboardPage
- [ ] CompanyMonitoringCard
- [ ] MonitoringChangesTable
- [ ] Роутинг

### Этап 6: Настройки и уведомления (1-2 дня)
- [ ] Секция Monitoring Settings
- [ ] Интеграция с системой уведомлений
- [ ] Тестирование

**Итого: 9-15 дней**

---

## ✅ Критерии готовности

1. ✅ Все API endpoints реализованы и протестированы
2. ✅ Все компоненты созданы и интегрированы
3. ✅ Данные отображаются на всех страницах
4. ✅ Уведомления работают корректно
5. ✅ Мобильная версия адаптивна
6. ✅ Документация обновлена

---

## 📝 Примечания

- Все данные мониторинга должны кэшироваться на фронтенде (React Query)
- Обновление данных должно быть инкрементальным (не перезагружать всё)
- Ошибки должны обрабатываться gracefully (показывать fallback UI)
- Производительность: ленивая загрузка данных мониторинга (только при открытии таба/секции)







