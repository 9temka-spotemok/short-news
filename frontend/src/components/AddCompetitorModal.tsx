import { ApiService } from '@/services/api'
import type { CompanyScanRequest, CompanyScanResult, CreateCompanyRequest } from '@/types'
import { AlertCircle, CheckCircle2, Edit2, ExternalLink, Loader2, Plus, Search, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

interface AddCompetitorModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

type ScanStep = 'input' | 'scanning' | 'preview' | 'confirming' | 'manual'

export default function AddCompetitorModal({ isOpen, onClose, onSuccess }: AddCompetitorModalProps) {
  const [step, setStep] = useState<ScanStep>('input')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [newsPageUrl, setNewsPageUrl] = useState('')
  const [showManualUrl, setShowManualUrl] = useState(false)
  const [scanResult, setScanResult] = useState<CompanyScanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  
  // Редактируемые поля компании
  const [editableCompany, setEditableCompany] = useState<{
    name: string
    website: string
    description: string
    logo_url: string
    category: string
  } | null>(null)
  const [isEditingCompany, setIsEditingCompany] = useState(false)
  
  // Выбранные новости для добавления
  const [selectedNewsIndices, setSelectedNewsIndices] = useState<Set<number>>(new Set())
  const [addAllNews, setAddAllNews] = useState(true)
  
  // Ручной режим
  const [manualCompanyData, setManualCompanyData] = useState({
    name: '',
    website: '',
    description: '',
    logo_url: '',
    category: ''
  })

  // Валидация URL
  const validateUrl = (url: string): boolean => {
    try {
      const urlObj = new URL(url)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  const handleScan = async () => {
    if (!websiteUrl.trim()) {
      toast.error('Please enter a website URL')
      return
    }

    if (!validateUrl(websiteUrl.trim())) {
      toast.error('Please enter a valid URL (must start with http:// or https://)')
      return
    }

    setIsScanning(true)
    setError(null)
    setStep('scanning')

    try {
      const request: CompanyScanRequest = {
        website_url: websiteUrl.trim(),
        ...(showManualUrl && newsPageUrl.trim() ? { news_page_url: newsPageUrl.trim() } : {})
      }

      const result = await ApiService.scanCompany(request)
      setScanResult(result)
      
      // Инициализируем редактируемые поля
      setEditableCompany({
        name: result.company_preview.name || '',
        website: result.company_preview.website || websiteUrl.trim(),
        description: result.company_preview.description || '',
        logo_url: result.company_preview.logo_url || '',
        category: result.company_preview.category || ''
      })
      
      // Выбираем все новости по умолчанию
      setAddAllNews(true)
      setSelectedNewsIndices(new Set(result.all_news_items.map((_, idx) => idx)))

      if (result.news_preview.total_found === 0) {
        // Если новости не найдены, переходим в preview с возможностью добавить без новостей
        setStep('preview')
      } else {
        setStep('preview')
      }
    } catch (err: any) {
      // Улучшенная обработка ошибок
      let errorMessage = 'Failed to scan company'
      
      // Проверка на таймаут - ПЕРВЫМ ДЕЛОМ
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = 'Scanning took too long (more than 90 seconds). The website might be large or slow. Please try manual mode instead.'
        setError(errorMessage)
        setShowManualUrl(true)
        setStep('input')
        setIsScanning(false)
        toast.error(errorMessage)
        return
      }
      
      if (err.response) {
        // Ошибка от сервера
        const errorData = err.response.data
        if (typeof errorData === 'string') {
          errorMessage = errorData
        } else if (errorData?.detail) {
          errorMessage = errorData.detail
        } else if (errorData?.message) {
          errorMessage = errorData.message
        } else if (err.response.status === 404) {
          errorMessage = 'Company website not found. Please check the URL or try manual mode.'
        } else if (err.response.status === 500) {
          errorMessage = 'Server error occurred. Please try again later.'
        } else {
          errorMessage = `Server error (${err.response.status}). Please try again.`
        }
      } else if (err.request) {
        // Запрос отправлен, но ответа нет (сетевая ошибка или таймаут)
        if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
          errorMessage = 'Scanning took too long. Please try manual mode instead.'
        } else {
          errorMessage = 'Network error. Please check your connection and try again.'
        }
      } else if (err.message) {
        // Другая ошибка
        errorMessage = err.message
      }
      
      setError(errorMessage)
      console.error('Scan company error:', err)
      
      // Если ошибка связана с тем, что страница не найдена или таймаут, предлагаем ручной режим
      const lowerMessage = errorMessage.toLowerCase()
      if (lowerMessage.includes('not found') || 
          lowerMessage.includes('404') || 
          lowerMessage.includes('network error') ||
          lowerMessage.includes('timeout') ||
          lowerMessage.includes('too long')) {
        setShowManualUrl(true)
        setStep('input')
      } else {
        setStep('input')
      }
    } finally {
      setIsScanning(false)
    }
  }
  
  const handleManualAdd = () => {
    if (!manualCompanyData.name.trim() || !manualCompanyData.website.trim()) {
      toast.error('Please enter company name and website')
      return
    }

    if (!validateUrl(manualCompanyData.website.trim())) {
      toast.error('Please enter a valid URL (must start with http:// or https://)')
      return
    }

    // Создаем компанию без новостей
    handleCreateManual()
  }
  
  const handleCreateManual = async () => {
    setIsCreating(true)
    setStep('confirming')

    try {
      const request: CreateCompanyRequest = {
        company: {
          name: manualCompanyData.name.trim(),
          website: manualCompanyData.website.trim(),
          description: manualCompanyData.description.trim() || undefined,
          logo_url: manualCompanyData.logo_url.trim() || undefined,
          category: manualCompanyData.category.trim() || undefined
        },
        news_items: []
      }

      const response = await ApiService.createCompany(request)
      
      toast.success(
        response.action === 'created' 
          ? `Company "${response.company.name}" added successfully!`
          : `Company "${response.company.name}" updated successfully!`
      )
      
      onSuccess()
      handleClose()
    } catch (err: any) {
      // Улучшенная обработка ошибок
      let errorMessage = 'Failed to create company'
      
      if (err.response) {
        const errorData = err.response.data
        if (typeof errorData === 'string') {
          errorMessage = errorData
        } else if (errorData?.detail) {
          errorMessage = errorData.detail
        } else if (errorData?.message) {
          errorMessage = errorData.message
        } else if (err.response.status === 400) {
          errorMessage = 'Invalid data. Please check the company information.'
        } else if (err.response.status === 500) {
          errorMessage = 'Server error occurred. Please try again later.'
        } else {
          errorMessage = `Server error (${err.response.status}). Please try again.`
        }
      } else if (err.request) {
        errorMessage = 'Network error. Please check your connection and try again.'
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
      toast.error(errorMessage)
      console.error('Create company (manual) error:', err)
      setStep('manual')
    } finally {
      setIsCreating(false)
    }
  }

  const handleCreate = async () => {
    if (!scanResult || !editableCompany) return

    // Валидация обязательных полей
    if (!editableCompany.name.trim()) {
      toast.error('Company name is required')
      return
    }

    if (!validateUrl(editableCompany.website.trim())) {
      toast.error('Please enter a valid website URL')
      return
    }

    setIsCreating(true)
    setStep('confirming')

    try {
      // Определяем, какие новости добавлять
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
      
      onSuccess()
      handleClose()
    } catch (err: any) {
      // Улучшенная обработка ошибок
      let errorMessage = 'Failed to create company'
      
      if (err.response) {
        const errorData = err.response.data
        if (typeof errorData === 'string') {
          errorMessage = errorData
        } else if (errorData?.detail) {
          errorMessage = errorData.detail
        } else if (errorData?.message) {
          errorMessage = errorData.message
        } else if (err.response.status === 400) {
          errorMessage = 'Invalid data. Please check the company information.'
        } else if (err.response.status === 500) {
          errorMessage = 'Server error occurred. Please try again later.'
        } else {
          errorMessage = `Server error (${err.response.status}). Please try again.`
        }
      } else if (err.request) {
        errorMessage = 'Network error. Please check your connection and try again.'
      } else if (err.message) {
        errorMessage = err.message
      }
      
      setError(errorMessage)
      toast.error(errorMessage)
      console.error('Create company error:', err)
      setStep('preview')
    } finally {
      setIsCreating(false)
    }
  }
  
  // Обработка выбора новостей
  const toggleNewsItem = (index: number) => {
    const newSelected = new Set(selectedNewsIndices)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedNewsIndices(newSelected)
    setAddAllNews(false)
  }
  
  const toggleAllNews = () => {
    if (addAllNews) {
      setSelectedNewsIndices(new Set())
      setAddAllNews(false)
    } else {
      setSelectedNewsIndices(new Set(scanResult?.all_news_items.map((_, idx) => idx) || []))
      setAddAllNews(true)
    }
  }

  const handleClose = () => {
    setStep('input')
    setWebsiteUrl('')
    setNewsPageUrl('')
    setShowManualUrl(false)
    setScanResult(null)
    setError(null)
    setIsScanning(false)
    setIsCreating(false)
    setEditableCompany(null)
    setIsEditingCompany(false)
    setSelectedNewsIndices(new Set())
    setAddAllNews(true)
    setManualCompanyData({
      name: '',
      website: '',
      description: '',
      logo_url: '',
      category: ''
    })
    onClose()
  }
  
  // Синхронизация редактируемых полей при изменении scanResult
  useEffect(() => {
    if (scanResult && !editableCompany) {
      setEditableCompany({
        name: scanResult.company_preview.name || '',
        website: scanResult.company_preview.website || websiteUrl.trim(),
        description: scanResult.company_preview.description || '',
        logo_url: scanResult.company_preview.logo_url || '',
        category: scanResult.company_preview.category || ''
      })
    }
  }, [scanResult, editableCompany, websiteUrl])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-2xl font-bold text-gray-900">Add Competitor</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={isScanning || isCreating}
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Step 1: Input */}
          {step === 'input' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company Website URL *
                </label>
                <input
                  type="url"
                  value={websiteUrl}
                  onChange={(e) => setWebsiteUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="input w-full"
                  disabled={isScanning}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !isScanning && websiteUrl.trim()) {
                      handleScan()
                    }
                  }}
                />
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
                    placeholder="https://example.com/blog or https://example.com/news"
                    className="input w-full"
                    disabled={isScanning}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    If the system cannot find the news page automatically, provide it here.
                    Example: https://www.accuranker.com/blog/
                  </p>
                </div>
              )}

              {error && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mr-2 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-yellow-800">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-between items-center pt-4">
                <button
                  onClick={() => setStep('manual')}
                  className="btn btn-outline btn-sm text-sm"
                  disabled={isScanning}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Manually
                </button>
                <div className="flex gap-3">
                  <button
                    onClick={handleClose}
                    className="btn btn-outline btn-md"
                    disabled={isScanning}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleScan}
                    className="btn btn-primary btn-md"
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
                        Scan
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Scanning */}
          {step === 'scanning' && (
            <div className="text-center py-12">
              <Loader2 className="h-12 w-12 animate-spin text-primary-600 mx-auto mb-4" />
              <p className="text-gray-600">Scanning company website...</p>
              <p className="text-sm text-gray-500 mt-2">This may take a few seconds</p>
            </div>
          )}

          {/* Step 3: Preview */}
          {step === 'preview' && scanResult && editableCompany && (
            <div className="space-y-6">
              {/* Company Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900">Company Information</h3>
                  <button
                    onClick={() => setIsEditingCompany(!isEditingCompany)}
                    className="text-primary-600 hover:text-primary-700 text-sm flex items-center gap-1"
                  >
                    <Edit2 className="h-4 w-4" />
                    {isEditingCompany ? 'Cancel Edit' : 'Edit'}
                  </button>
                </div>
                
                {isEditingCompany ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Company Name *
                      </label>
                      <input
                        type="text"
                        value={editableCompany.name}
                        onChange={(e) => setEditableCompany({ ...editableCompany, name: e.target.value })}
                        className="input w-full"
                        placeholder="Company name"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Website URL *
                      </label>
                      <input
                        type="url"
                        value={editableCompany.website}
                        onChange={(e) => setEditableCompany({ ...editableCompany, website: e.target.value })}
                        className="input w-full"
                        placeholder="https://example.com"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Description
                      </label>
                      <textarea
                        value={editableCompany.description}
                        onChange={(e) => setEditableCompany({ ...editableCompany, description: e.target.value })}
                        className="input w-full"
                        rows={3}
                        placeholder="Company description"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Logo URL
                        </label>
                        <input
                          type="url"
                          value={editableCompany.logo_url}
                          onChange={(e) => setEditableCompany({ ...editableCompany, logo_url: e.target.value })}
                          className="input w-full"
                          placeholder="https://example.com/logo.png"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Category
                        </label>
                        <input
                          type="text"
                          value={editableCompany.category}
                          onChange={(e) => setEditableCompany({ ...editableCompany, category: e.target.value })}
                          className="input w-full"
                          placeholder="e.g., llm_provider, toolkit"
                        />
                      </div>
                    </div>
                    <button
                      onClick={() => setIsEditingCompany(false)}
                      className="btn btn-primary btn-sm"
                    >
                      Save Changes
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Name</p>
                      <p className="font-medium">{editableCompany.name || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Website</p>
                      <a
                        href={editableCompany.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline inline-flex items-center gap-1"
                      >
                        {editableCompany.website}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    {editableCompany.description && (
                      <div className="col-span-2">
                        <p className="text-sm text-gray-600">Description</p>
                        <p className="text-sm">{editableCompany.description}</p>
                      </div>
                    )}
                    {editableCompany.category && (
                      <div>
                        <p className="text-sm text-gray-600">Category</p>
                        <p className="text-sm">{editableCompany.category}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* News Statistics */}
              <div>
                <h3 className="font-semibold text-gray-900 mb-3">News Statistics</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Total Found</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {scanResult.news_preview.total_found}
                    </p>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Categories</p>
                    <p className="text-2xl font-bold text-green-600">
                      {Object.keys(scanResult.news_preview.categories).length}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600">Source Types</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {Object.keys(scanResult.news_preview.source_types).length}
                    </p>
                  </div>
                </div>
              </div>

              {/* Categories Breakdown */}
              {Object.keys(scanResult.news_preview.categories).length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-3">Categories</h3>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(scanResult.news_preview.categories).map(([cat, count]) => (
                      <span
                        key={cat}
                        className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm"
                      >
                        {cat.replace(/_/g, ' ')} ({count})
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* News Selection */}
              {scanResult.news_preview.total_found > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900">
                      News Items ({scanResult.all_news_items.length} found)
                    </h3>
                    <div className="flex items-center gap-2">
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="checkbox"
                          checked={addAllNews}
                          onChange={toggleAllNews}
                          className="rounded"
                        />
                        <span>Add all news</span>
                      </label>
                    </div>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
                    <p className="text-sm text-blue-800">
                      {addAllNews 
                        ? `All ${scanResult.all_news_items.length} news items will be added.`
                        : `${selectedNewsIndices.size} of ${scanResult.all_news_items.length} news items selected.`
                      }
                    </p>
                  </div>
                  <div className="space-y-2 max-h-60 overflow-y-auto border rounded-lg p-3">
                    {scanResult.all_news_items.map((item, idx) => {
                      const isSelected = addAllNews || selectedNewsIndices.has(idx)
                      return (
                        <div
                          key={idx}
                          className={`border-l-2 pl-3 py-2 hover:bg-gray-50 cursor-pointer ${
                            isSelected ? 'border-primary-500 bg-primary-50' : 'border-gray-200'
                          }`}
                          onClick={() => toggleNewsItem(idx)}
                        >
                          <div className="flex items-start gap-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleNewsItem(idx)}
                              className="mt-1 rounded"
                              onClick={(e) => e.stopPropagation()}
                            />
                            <div className="flex-1">
                              <a
                                href={item.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-gray-900 hover:text-primary-600 inline-flex items-center gap-1"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {item.title}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                              <div className="flex items-center gap-2 mt-1">
                                <span className="text-xs text-gray-500">{item.category}</span>
                                <span className="text-xs text-gray-400">•</span>
                                <span className="text-xs text-gray-500">{item.source_type}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
              
              {scanResult.news_preview.total_found === 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-yellow-600 mr-2 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-yellow-800">
                        No news articles found. You can still add the company without news items.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  onClick={() => {
                    setStep('input')
                    setError(null)
                  }}
                  className="btn btn-outline btn-md"
                  disabled={isCreating}
                >
                  Back
                </button>
                <button
                  onClick={handleCreate}
                  className="btn btn-primary btn-md"
                  disabled={isCreating}
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                      Add Company
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Manual Add */}
          {step === 'manual' && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-blue-800">
                  Add a company manually without scanning. You can add news items later.
                </p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Company Name *
                </label>
                <input
                  type="text"
                  value={manualCompanyData.name}
                  onChange={(e) => setManualCompanyData({ ...manualCompanyData, name: e.target.value })}
                  className="input w-full"
                  placeholder="Company name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Website URL *
                </label>
                <input
                  type="url"
                  value={manualCompanyData.website}
                  onChange={(e) => setManualCompanyData({ ...manualCompanyData, website: e.target.value })}
                  className="input w-full"
                  placeholder="https://example.com"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                </label>
                <textarea
                  value={manualCompanyData.description}
                  onChange={(e) => setManualCompanyData({ ...manualCompanyData, description: e.target.value })}
                  className="input w-full"
                  rows={3}
                  placeholder="Company description (optional)"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Logo URL
                  </label>
                  <input
                    type="url"
                    value={manualCompanyData.logo_url}
                    onChange={(e) => setManualCompanyData({ ...manualCompanyData, logo_url: e.target.value })}
                    className="input w-full"
                    placeholder="https://example.com/logo.png"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Category
                  </label>
                  <input
                    type="text"
                    value={manualCompanyData.category}
                    onChange={(e) => setManualCompanyData({ ...manualCompanyData, category: e.target.value })}
                    className="input w-full"
                    placeholder="e.g., llm_provider, toolkit"
                  />
                </div>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-red-600 mr-2 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-sm text-red-800">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4">
                <button
                  onClick={() => {
                    setStep('input')
                    setError(null)
                  }}
                  className="btn btn-outline btn-md"
                  disabled={isCreating}
                >
                  Back
                </button>
                <button
                  onClick={handleManualAdd}
                  className="btn btn-primary btn-md"
                  disabled={isCreating || !manualCompanyData.name.trim() || !manualCompanyData.website.trim()}
                >
                  {isCreating ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Adding...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4 mr-2" />
                      Add Company
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Step 5: Confirming */}
          {step === 'confirming' && (
            <div className="text-center py-12">
              <Loader2 className="h-12 w-12 animate-spin text-primary-600 mx-auto mb-4" />
              <p className="text-gray-600">Adding company to platform...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

