# Frontend ↔ Backend Endpoint Usage

> Актуально на 12 ноября 2025 года. Описаны только ручки, к которым обращается фронтендовый код (в том числе E2E/тесты). Базовый URL определяется переменной `VITE_API_URL`; далее указан относительный путь внутри `/api`.

## Аутентификация (`/v1/auth`)

| Method | Path | Frontend Usage | Примечания |
| --- | --- | --- | --- |
| `POST` | `/v1/auth/login` | `ApiService.login`, Playwright авторизация (`authenticate`) | Возвращает JWT `access_token`. Ошибки 401 обрабатываются в interceptor. |
| `POST` | `/v1/auth/refresh` | `ApiService.refreshToken` (`authStore.refreshTokens`) | Обновляет access-token по refresh-токену. |

## Компании и поиск (`/v1/companies`)

| Method | Path | Frontend Usage | Примечания |
| --- | --- | --- | --- |
| `GET` | `/v1/companies` | `ApiService.getCompanies`, `ApiService.searchCompanies`, автодополнение в Competitor Analysis и настройках | Query-параметры `search`, `limit`, `offset`. Результат кэшируется локально (не через React Query). |
| `GET` | `/v1/companies/{company_id}` | `ApiService.getCompany` | Карточки компаний, пресеты. |

## Новости (`/v1/news`)

| Method | Path | Frontend Usage | Примечания |
| --- | --- | --- | --- |
| `GET` | `/v1/news` | `ApiService.getNews`, дашборды | Фильтры `company_id`, `company_ids`, `category`, `source_type`, `search`. |
| `GET` | `/v1/news/stats` | `ApiService.getNewsStats`, `DashboardPage` | Используется для сводных графиков. |
| `GET` | `/v1/news/stats/by-companies` | `DashboardPage` | Расширенная аналитика; пока без отдельного клиента в `ApiService`. |

## Конкуренты (`/v1/competitors`)

| Method | Path | Frontend Usage | React Query / Инвалидация | Примечания |
| --- | --- | --- | --- | --- |
| `GET` | `/v1/competitors/changes/{company_id}` | `useChangeEventsQuery` | `competitorAnalysisKeys.changeEvents(companyId, limit, status)` | Возвращает `{ events, total }`. |
| `POST` | `/v1/competitors/changes/{event_id}/recompute` | `useRecomputeChangeEventMutation`, кнопка «Recompute» в change log | Локальный `setQueryData` по `changeEvents` | Триггер пересчёта отдельного события; результат подставляется в кэш. |
| `GET` | `/v1/competitors/suggest/{company_id}` | `useAnalysisFlow` (шаг выбора конкурентов) | — | Возвращает AI-рекомендации. |
| `GET` | `/v1/competitors/activity/{company_id}` | `ApiService.getCompanyActivity` (виджеты активности) | — | Девелоперский адаптер до миграции на v2. |
| `POST` | `/v1/competitors/themes` | `ApiService.analyzeThemes` (внутренние отчёты) | — | Формирует тематику по набору компаний. |
| `POST` | `/v1/competitors/compare` | `ApiService.compareCompanies` (legacy UI) | — | Используется в переходных сценариях и внутренних отчётах. |

## Аналитика v2 (`/v2/analytics`)

| Method | Path | Frontend Usage | React Query / Инвалидация | Примечания |
| --- | --- | --- | --- | --- |
| `GET` | `/v2/analytics/companies/{company_id}/impact/latest` | `useCompanyAnalyticsInsights` | `companyAnalyticsInsightsQueryKey(companyId)` | Возвращает последний snapshot; 404 трактуется как отсутствие данных. |
| `GET` | `/v2/analytics/companies/{company_id}/snapshots` | `useCompanyAnalyticsInsights` | `companyAnalyticsInsightsQueryKey(companyId)` | История метрик (серии). |
| `POST` | `/v2/analytics/companies/{company_id}/recompute` | Кнопка «Recompute» (Playwright сценарий) | Ручной `refetch` (`useCompanyAnalyticsInsights`, `useChangeEventsQuery`) | Возвращает `task_id` для Celery. |
| `POST` | `/v2/analytics/companies/{company_id}/graph/sync` | Кнопка «Sync Knowledge Graph» | `useKnowledgeGraph` (ручной `refetch`) | Старт синхронизации knowledge graph. |
| `GET` | `/v2/analytics/graph` | `useKnowledgeGraph`, `useCompanyAnalyticsInsights` | `competitorAnalysisKeys.knowledgeGraph({ companyId, relationship, limit })` | Параметры: `company_id`, `relationship`, `limit`. |
| `GET` | `/v2/analytics/change-log` | `useChangeLog` | `competitorAnalysisKeys.changeLog({ companyId, subjectKey, period, filterState, limit })` | Поддерживает `cursor`, `filters`. |
| `POST` | `/v2/analytics/comparisons` | `useAnalyticsComparisonMutation`, `usePrefetchAnalytics` | `competitorAnalysisKeys.comparison(payload)` | Кэш заполняется `setQueryData`. |
| `POST` | `/v2/analytics/export` | `useExportAnalyticsMutation`, `useAnalyticsExportHandler` | — (mutation без кэша) | Возвращает payload для дальнейшего экспорта. |
| `GET` | `/v2/analytics/reports/presets` | `useReportPresetsQuery` | `competitorAnalysisKeys.reportPresets()` | Срок жизни кэша 2 минуты. |
| `POST` | `/v2/analytics/reports/presets` | `useReportPresetActions.createPreset` | Инвалидируется `refetchReportPresets` → `reportPresets` | Требует список компаний и фильтры. |

## Пользовательские настройки / уведомления

| Method | Path | Frontend Usage | Примечания |
| --- | --- | --- | --- |
| `GET` | `/v1/users/preferences` | `SettingsPage.loadData` | Возвращает подписки, категории, ключевые слова, частоту уведомлений. |
| `PUT` | `/v1/users/preferences` | `SettingsPage.handleSavePreferences`, `handleSaveNotifications` | В Playwright моки для контроля тостов. |
| `PUT` | `/v1/users/preferences/digest` | `SettingsPage.handleSaveNotifications` | Управление дайджестами (включение, периодичность, формат). |

## Служебные / прочие

| Method | Path | Frontend Usage | Примечания |
| --- | --- | --- | --- |
| `GET` | `/v1/health` | `ApiService.healthCheck` (диагностика) | Используется в сервисных скриптах/отладке. |
| `POST` | `/v1/users/companies/{company_id}/subscribe` | `ApiService.subscribeToCompany` (UI подписок) | Актуально для раздела предпочтений. |
| `DELETE` | `/v1/users/companies/{company_id}/unsubscribe` | `ApiService.unsubscribeFromCompany` | — |

---

### Покрытие тестами
- **Vitest**: хуки `useChangeLog`, `useKnowledgeGraph`, `useReportPresetActions`, `useAnalyticsExportHandler`, `usePrefetchAnalytics`, `useAnalysisFlow`, `useComparisonManager` и др.  
- **Playwright (`@refactor-phase2`)**: основные сценарии (recompute → export, фильтры, пресеты, экспорт 200/500, notifications toggle).  
- **Unit/Component**: компоненты `CompanyAnalysisFlow`, `AnalyticsTabs`, `PresetManager` и пр. используют те же ручки через абстракции.

### Замечания и TODO
1. **Триггеры уведомлений** пока не вынесены в React Query — при расширении стоит добавить кэш (`userPreferences.notifications`) и invalidate после `PUT`.  
2. **`/v1/competitors/activity`** остаётся переходной ручкой; после полной миграции на v2 следует заменить на `/analytics` эквивалент.  
3. Для пресетов требуется backend endpoint, принимающий батч ID (`/companies/batch`) — сейчас используем обходной путь с `getCompanies('', 200, 0)`.  
4. Дополнительно синхронизировать документацию по новостным статистикам (`/news/stats/by-companies`) с backend.












