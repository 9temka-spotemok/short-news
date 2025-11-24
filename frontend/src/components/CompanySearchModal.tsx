import { ApiService } from '@/services/api'
import type { Company, CompanyScanRequest, CompanyScanResult, CreateCompanyRequest } from '@/types'
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Edit2,
  ExternalLink,
  Loader2,
  MinusCircle,
  Plus,
  Search,
  UserPlus,
  X
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'

interface CompanySearchModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
  initialQuery?: string
}

type SearchStep = 'input' | 'scanning' | 'preview' | 'confirming' | 'competitors'

interface SuggestedCompetitor {
  company: Company
  similarity_score: number
  common_categories: string[]
  reason: string
}

const DEFAULT_COMPANY_STATE = {
  name: '',
  website: '',
  description: '',
  logo_url: '',
  category: ''
}

export default function CompanySearchModal({ 
  isOpen, 
  onClose, 
  onSuccess,
  initialQuery = '' 
}: CompanySearchModalProps) {
  const [step, setStep] = useState<SearchStep>('input')
  const [websiteUrl, setWebsiteUrl] = useState(initialQuery)
  const [newsPageUrl, setNewsPageUrl] = useState('')
  const [showManualUrl, setShowManualUrl] = useState(false)
  const [scanResult, setScanResult] = useState<CompanyScanResult | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  
  // Редактируемые поля компании
  const [editableCompany, setEditableCompany] = useState(DEFAULT_COMPANY_STATE)
  const [isEditingCompany, setIsEditingCompany] = useState(false)
  
  // Выбранные новости для добавления
  const [selectedNewsIndices, setSelectedNewsIndices] = useState<Set<number>>(new Set())
  const [addAllNews, setAddAllNews] = useState(true)
  
  // После создания компании - предложения конкурентов
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [suggestedCompetitors, setSuggestedCompetitors] = useState<SuggestedCompetitor[]>([])
  const [removedCompetitorIds, setRemovedCompetitorIds] = useState<Set<string>>(new Set())
  const [selectedCompetitorIds, setSelectedCompetitorIds] = useState<Set<string>>(new Set())
  const [isLoadingCompetitors, setIsLoadingCompetitors] = useState(false)

  const trimmedInitialQuery = initialQuery.trim()

  const availableCompetitors = useMemo(
    () => suggestedCompetitors.filter((item) => !removedCompetitorIds.has(item.company.id)),
    [suggestedCompetitors, removedCompetitorIds]
  )

  useEffect(() => {
    if (isOpen) {
      setWebsiteUrl(trimmedInitialQuery)
    }
  }, [isOpen, trimmedInitialQuery])

  // Валидация URL
  const validateUrlFormat = (url: string): boolean => {
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  // Поиск компании по имени (если введен не URL)
  const resolveWebsiteUrl = async (input: string): Promise<string | null> => {
    const trimmed = input.trim()
    
    // Если это уже валидный URL, возвращаем его
    if (validateUrlFormat(trimmed)) {
      return trimmed
    }
    
    // Иначе ищем компанию по имени
    try {
      const response = await ApiService.getCompanies(trimmed, 5, 0)
      if (response.items && response.items.length > 0) {
        // Возвращаем URL первой найденной компании
        return response.items[0].website || null
      }
    } catch (error) {
      console.error('Failed to search company by name:', error)
    }
    
    return null
  }

  const handleScan = async () => {
    if (!websiteUrl.trim()) {
      toast.error('Enter company URL or name first')
      return
    }

    setIsScanning(true)
    setErrorMessage(null)
    setStep('scanning')

    try {
      const resolvedUrl = await resolveWebsiteUrl(websiteUrl)
      if (!resolvedUrl) {
        throw new Error('Company not found. Provide a valid website URL.')
      }

      const request: CompanyScanRequest = {
        website_url: resolvedUrl,
        ...(showManualUrl && newsPageUrl.trim()
          ? { news_page_url: newsPageUrl.trim() }
          : {})
      }

      const result = await ApiService.scanCompany(request)
      setScanResult(result)
      setEditableCompany({
        name: result.company_preview.name || '',
        website: result.company_preview.website || resolvedUrl,
        description: result.company_preview.description || '',
        logo_url: result.company_preview.logo_url || '',
        category: result.company_preview.category || ''
      })

      setAddAllNews(true)
      setSelectedNewsIndices(new Set(result.all_news_items.map((_, idx) => idx)))
      setStep('preview')
    } catch (error: any) {
      let message = 'Failed to scan company'
      if (error?.response?.data?.detail) {
        message = error.response.data.detail
      } else if (error?.message) {
        message = error.message
      }
      setErrorMessage(message)
      toast.error(message)
      setStep('input')
    } finally {
      setIsScanning(false)
    }
  }

  const toggleNewsItem = (index: number) => {
    setAddAllNews(false)
    setSelectedNewsIndices((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  const toggleAllNews = () => {
    if (addAllNews) {
      setAddAllNews(false)
      setSelectedNewsIndices(new Set())
    } else {
      setAddAllNews(true)
      setSelectedNewsIndices(new Set(scanResult?.all_news_items.map((_, idx) => idx) ?? []))
    }
  }

  const handleCreateCompany = async () => {
    if (!scanResult) return

    if (!editableCompany.name.trim()) {
      toast.error('Company name is required')
      return
    }

    if (!validateUrlFormat(editableCompany.website.trim())) {
      toast.error('Enter a valid website URL')
      return
    }

    setIsCreating(true)
    setStep('confirming')

    try {
      let newsItemsToAdd = scanResult.all_news_items
      if (!addAllNews && selectedNewsIndices.size > 0) {
        newsItemsToAdd = Array.from(selectedNewsIndices)
          .sort((a, b) => a - b)
          .map(idx => scanResult.all_news_items[idx])
      } else if (!addAllNews) {
        newsItemsToAdd = []
      }

      const request: CreateCompanyRequest = {
        company: {
          name: editableCompany.name.trim(),
          website: editableCompany.website.trim(),
          description: editableCompany.description.trim() || undefined,
          logo_url: editableCompany.logo_url.trim() || undefined,
          category: editableCompany.category.trim() || undefined
        },
        news_items: newsItemsToAdd.map(item => ({
          title: item.title,
          content: item.content,
          summary: item.summary,
          source_url: item.source_url,
          source_type: item.source_type,
          category: item.category,
          published_at: item.published_at
        }))
      }

      const response = await ApiService.createCompany(request)
      
      toast.success(
        response.action === 'created' 
          ? `Company "${response.company.name}" added successfully!`
          : `Company "${response.company.name}" updated successfully!`
      )
      
      // Сохраняем ID созданной компании для предложений конкурентов
      setCompanyId(response.company.id)
      
      // Загружаем предложения конкурентов
      await loadSuggestedCompetitors(response.company.id)
      
      // Переходим к шагу выбора конкурентов
      setStep('competitors')
    } catch (error: any) {
      let message = 'Failed to create company'
      if (error?.response?.data?.detail) {
        message = error.response.data.detail
      } else if (error?.message) {
        message = error.message
      }
      setErrorMessage(message)
      toast.error(message)
      setStep('preview')
    } finally {
      setIsCreating(false)
    }
  }

  const loadSuggestedCompetitors = async (id: string) => {
    setIsLoadingCompetitors(true)
    try {
      const result = await ApiService.suggestCompetitors(id, { limit: 10, days: 30 })
      setSuggestedCompetitors(result.suggestions || [])
      // Автоматически выбираем всех предложенных конкурентов
      setSelectedCompetitorIds(new Set(result.suggestions?.map(s => s.company.id) || []))
    } catch (error) {
      console.error('Failed to load competitor suggestions:', error)
      toast.error('Failed to load competitor suggestions')
    } finally {
      setIsLoadingCompetitors(false)
    }
  }

  const toggleCompetitorSelection = (competitorId: string) => {
    setSelectedCompetitorIds((prev) => {
      const next = new Set(prev)
      if (next.has(competitorId)) {
        next.delete(competitorId)
      } else {
        next.add(competitorId)
      }
      return next
    })
  }

  const removeCompetitor = (competitorId: string) => {
    setRemovedCompetitorIds((prev) => new Set(prev).add(competitorId))
  }

  const handleConfirmSelection = async () => {
    if (!companyId) return

    try {
      // Подписываемся на выбранных конкурентов
      const competitorIds = Array.from(selectedCompetitorIds)
      for (const competitorId of competitorIds) {
        try {
          await ApiService.subscribeToCompany(competitorId)
        } catch (error) {
          console.error(`Failed to subscribe to competitor ${competitorId}:`, error)
        }
      }

      toast.success(`Successfully added ${competitorIds.length} competitor${competitorIds.length !== 1 ? 's' : ''} to tracking`)
      
      onSuccess?.()
      handleClose()
    } catch (error) {
      console.error('Failed to confirm competitor selection:', error)
      toast.error('Failed to save competitor selections')
    }
  }

  const handleClose = () => {
    setStep('input')
    setWebsiteUrl('')
    setNewsPageUrl('')
    setShowManualUrl(false)
    setScanResult(null)
    setErrorMessage(null)
    setIsScanning(false)
    setIsCreating(false)
    setEditableCompany(DEFAULT_COMPANY_STATE)
    setIsEditingCompany(false)
    setSelectedNewsIndices(new Set())
    setAddAllNews(true)
    setCompanyId(null)
    setSuggestedCompetitors([])
    setRemovedCompetitorIds(new Set())
    setSelectedCompetitorIds(new Set())
    setIsLoadingCompetitors(false)
    onClose()
  }

  if (!isOpen) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b sticky top-0 bg-white z-10">
          <div>
            <p className="text-xs uppercase tracking-wide text-primary-500 font-semibold">
              Competitor Discovery
            </p>
            <h2 className="text-2xl font-bold text-gray-900">Find company insights</h2>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label="Close"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {step === 'input' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company URL or Name *
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-5 w-5" />
                  <input
                    type="text"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="https://example.com or Acme AI"
                    className="input pl-10 w-full"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleScan()
                      }
                    }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  We scan the website, detect blog/news sources and prepare recent updates.
                </p>
              </div>

              {showManualUrl && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    News/Blog Page URL (optional)
                  </label>
                  <input
                    type="url"
                    value={newsPageUrl}
                    onChange={(e) => setNewsPageUrl(e.target.value)}
                    placeholder="https://example.com/blog"
                    className="input w-full"
                  />
                </div>
              )}

              {errorMessage && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex gap-3">
                  <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                  <p className="text-sm text-yellow-800">{errorMessage}</p>
                </div>
              )}

              <div className="flex flex-col sm:flex-row justify-between items-center gap-3 pt-4">
                <button
                  type="button"
                  className="text-sm text-gray-500 hover:text-gray-700"
                  onClick={() => setShowManualUrl((prev) => !prev)}
                >
                  {showManualUrl ? <span className="underline">Hide manual news URL</span> : <span className="underline">Add manual news URL</span>}
                </button>
                <div className="flex gap-3 w-full sm:w-auto">
                  <button onClick={handleClose} className="btn btn-outline flex-1 sm:flex-none">
                    Cancel
                  </button>
                  <button
                    onClick={handleScan}
                    className="btn btn-primary flex-1 sm:flex-none"
                    disabled={isScanning || !websiteUrl.trim()}
                  >
                    {isScanning ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Scanning...
                      </>
                    ) : (
                      <>
                        <Search className="h-4 w-4 mr-2" />
                        Find Company
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {step === 'scanning' && (
            <div className="text-center py-12">
              <Loader2 className="h-12 w-12 text-primary-600 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Scanning website and collecting news...</p>
            </div>
          )}

          {step === 'preview' && scanResult && (
            <div className="space-y-6">
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-gray-500 font-semibold">
                      Company profile
                    </p>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {editableCompany.name || 'Untitled company'}
                    </h3>
                  </div>
                  <button
                    className="text-sm text-primary-600 hover:text-primary-700 inline-flex items-center gap-2 transition-colors"
                    onClick={() => setIsEditingCompany((prev) => !prev)}
                  >
                    <Edit2 className="h-4 w-4" />
                    {isEditingCompany ? 'Stop editing' : 'Edit'}
                  </button>
                </div>

                {isEditingCompany ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Name *</label>
                      <input
                        type="text"
                        value={editableCompany.name}
                        onChange={(e) =>
                          setEditableCompany((prev) => ({ ...prev, name: e.target.value }))
                        }
                        className="input w-full"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Website *</label>
                      <input
                        type="url"
                        value={editableCompany.website}
                        onChange={(e) =>
                          setEditableCompany((prev) => ({ ...prev, website: e.target.value }))
                        }
                        className="input w-full"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">Description</label>
                      <textarea
                        value={editableCompany.description}
                        onChange={(e) =>
                          setEditableCompany((prev) => ({ ...prev, description: e.target.value }))
                        }
                        className="input w-full"
                        rows={3}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Website</p>
                      <a
                        href={editableCompany.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline inline-flex items-center gap-1"
                      >
                        {editableCompany.website || 'N/A'}
                        {editableCompany.website && <ExternalLink className="h-3 w-3" />}
                      </a>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Category</p>
                      <p className="text-sm text-gray-700">{editableCompany.category || '—'}</p>
                    </div>
                    {editableCompany.description && (
                      <div className="md:col-span-2">
                        <p className="text-xs text-gray-500 uppercase tracking-wide">Overview</p>
                        <p className="text-sm text-gray-700">{editableCompany.description}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Total articles</p>
                  <p className="text-3xl font-bold text-primary-600">
                    {scanResult.news_preview.total_found}
                  </p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Categories</p>
                  <p className="text-3xl font-bold text-primary-600">
                    {Object.keys(scanResult.news_preview.categories).length}
                  </p>
                </div>
                <div className="rounded-lg border p-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Source types</p>
                  <p className="text-3xl font-bold text-primary-600">
                    {Object.keys(scanResult.news_preview.source_types).length}
                  </p>
                </div>
              </div>

              {Object.keys(scanResult.news_preview.categories).length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-800 mb-2">Categories</p>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(scanResult.news_preview.categories).map(([category, count]) => (
                      <span
                        key={category}
                        className="px-3 py-1 rounded-full bg-gray-100 text-gray-700 text-sm"
                      >
                        {category.replace(/_/g, ' ')} ({count})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {scanResult.all_news_items.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-gray-800">
                      News ({scanResult.all_news_items.length} found)
                    </p>
                    <label className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={addAllNews}
                        onChange={toggleAllNews}
                        className="rounded"
                      />
                      Add all
                    </label>
                  </div>
                  <div className="max-h-60 overflow-y-auto border rounded-lg divide-y">
                    {scanResult.all_news_items.map((item, index) => {
                      const isSelected = addAllNews || selectedNewsIndices.has(index)
                      return (
                        <div
                          key={item.source_url}
                          className={`p-3 hover:bg-gray-50 cursor-pointer transition-colors ${
                            isSelected ? 'bg-primary-50/70' : ''
                          }`}
                          onClick={() => toggleNewsItem(index)}
                        >
                          <div className="flex items-start gap-3">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleNewsItem(index)}
                              className="mt-1 rounded"
                              onClick={(e) => e.stopPropagation()}
                            />
                            <div>
                              <a
                                href={item.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm font-medium text-gray-900 hover:text-primary-600 inline-flex items-center gap-1"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {item.title}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                              <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                                <span className="capitalize">{item.category}</span>
                                <span>•</span>
                                <span>{item.source_type}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              <div className="flex flex-col sm:flex-row justify-end gap-3">
                <button
                  onClick={() => {
                    setStep('input')
                    setErrorMessage(null)
                  }}
                  className="btn btn-outline"
                  disabled={isCreating}
                >
                  Back
                </button>
                <button
                  onClick={handleCreateCompany}
                  className="btn btn-primary"
                  disabled={isCreating}
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Add to platform
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {step === 'confirming' && (
            <div className="text-center py-12">
              <Loader2 className="h-12 w-12 text-primary-600 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">Adding company to platform...</p>
            </div>
          )}

          {step === 'competitors' && companyId && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-gray-800">
                    Suggested competitors
                  </p>
                  <p className="text-xs text-gray-500">
                    Select companies to track together or remove unnecessary ones.
                  </p>
                </div>
                {isLoadingCompetitors && (
                  <Loader2 className="h-4 w-4 animate-spin text-primary-600" />
                )}
              </div>

              {availableCompetitors.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto border rounded-lg p-3">
                  {availableCompetitors.map((suggestion) => {
                    const isSelected = selectedCompetitorIds.has(suggestion.company.id)
                    return (
                      <div
                        key={suggestion.company.id}
                        className={`border rounded-lg p-3 hover:border-primary-400 transition-colors ${
                          isSelected ? 'border-primary-400 bg-primary-50/40' : 'border-gray-200'
                        }`}
                      >
                        <div className="flex flex-col gap-2">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="flex items-center gap-2 text-gray-900 font-medium">
                                <Building2 className="h-4 w-4 text-gray-400" />
                                {suggestion.company.name}
                              </div>
                              {suggestion.company.website && (
                                <a
                                  href={suggestion.company.website}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs text-primary-600 hover:underline inline-flex items-center gap-1"
                                >
                                  {suggestion.company.website}
                                  <ExternalLink className="h-3 w-3" />
                                </a>
                              )}
                              <p className="text-xs text-gray-500 mt-1">
                                {suggestion.reason}
                              </p>
                            </div>
                            <button
                              className="text-gray-400 hover:text-red-500"
                              onClick={() => removeCompetitor(suggestion.company.id)}
                              title="Remove suggestion"
                            >
                              <MinusCircle className="h-4 w-4" />
                            </button>
                          </div>
                          <div className="flex flex-wrap gap-1">
                            {suggestion.common_categories.map((category) => (
                              <span
                                key={category}
                                className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600"
                              >
                                {category.replace(/_/g, ' ')}
                              </span>
                            ))}
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="text-xs text-gray-500">
                              Similarity: {Math.round(suggestion.similarity_score * 100)}%
                            </div>
                            <button
                              className={`btn btn-sm ${
                                isSelected ? 'btn-secondary' : 'btn-outline'
                              } flex items-center gap-2`}
                              onClick={() => toggleCompetitorSelection(suggestion.company.id)}
                            >
                              {isSelected ? (
                                <>
                                  <CheckCircle2 className="h-4 w-4" />
                                  Added
                                </>
                              ) : (
                                <>
                                  <UserPlus className="h-4 w-4" />
                                  Track
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="border rounded-lg p-4 text-center text-sm text-gray-500">
                  {isLoadingCompetitors
                    ? 'Loading competitor suggestions...'
                    : 'No competitor suggestions yet. Add them later from the dashboard.'}
                </div>
              )}

              <div className="flex flex-col sm:flex-row justify-end gap-3">
                <button onClick={handleClose} className="btn btn-outline">
                  Skip
                </button>
                <button onClick={handleConfirmSelection} className="btn btn-primary">
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  Confirm selection
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}



