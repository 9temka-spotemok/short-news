import { ApiService } from '@/services/api'
import type { CompanyScanRequest, CompanyScanResult, CreateCompanyRequest } from '@/types'
import { AlertCircle, CheckCircle2, ExternalLink, Loader2, Search, X } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'

interface AddCompetitorModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

type ScanStep = 'input' | 'scanning' | 'preview' | 'confirming'

export default function AddCompetitorModal({ isOpen, onClose, onSuccess }: AddCompetitorModalProps) {
  const [step, setStep] = useState<ScanStep>('input')
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [newsPageUrl, setNewsPageUrl] = useState('')
  const [showManualUrl, setShowManualUrl] = useState(false)
  const [scanResult, setScanResult] = useState<CompanyScanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  const handleScan = async () => {
    if (!websiteUrl.trim()) {
      toast.error('Please enter a website URL')
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

      if (result.news_preview.total_found === 0) {
        // Если новости не найдены, показываем поле для ручного ввода
        setShowManualUrl(true)
        setError('No news articles found. Please provide the URL of the news/blog page.')
        setStep('input')
      } else {
        setStep('preview')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to scan company'
      setError(errorMessage)
      
      // Если ошибка связана с тем, что страница не найдена, показываем поле для ручного ввода
      if (errorMessage.toLowerCase().includes('not found') || errorMessage.toLowerCase().includes('404')) {
        setShowManualUrl(true)
        setStep('input')
      } else {
        setStep('input')
      }
    } finally {
      setIsScanning(false)
    }
  }

  const handleCreate = async () => {
    if (!scanResult) return

    setIsCreating(true)
    setStep('confirming')

    try {
      const request: CreateCompanyRequest = {
        company: {
          name: scanResult.company_preview.name,
          website: scanResult.company_preview.website,
          description: scanResult.company_preview.description,
          logo_url: scanResult.company_preview.logo_url,
          category: scanResult.company_preview.category
        },
        news_items: scanResult.all_news_items.map(item => ({
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
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create company'
      setError(errorMessage)
      toast.error(errorMessage)
      setStep('preview')
    } finally {
      setIsCreating(false)
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
    onClose()
  }

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

              <div className="flex justify-end gap-3 pt-4">
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
          {step === 'preview' && scanResult && (
            <div className="space-y-6">
              {/* Company Info */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Company Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-600">Name</p>
                    <p className="font-medium">{scanResult.company_preview.name}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Website</p>
                    <a
                      href={scanResult.company_preview.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline inline-flex items-center gap-1"
                    >
                      {scanResult.company_preview.website}
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                  {scanResult.company_preview.description && (
                    <div className="col-span-2">
                      <p className="text-sm text-gray-600">Description</p>
                      <p className="text-sm">{scanResult.company_preview.description}</p>
                    </div>
                  )}
                  {scanResult.company_preview.category && (
                    <div>
                      <p className="text-sm text-gray-600">Category</p>
                      <p className="text-sm">{scanResult.company_preview.category}</p>
                    </div>
                  )}
                </div>
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

              {/* Sample News Items */}
              {scanResult.news_preview.sample_items.length > 0 && (
                <div>
                  <h3 className="font-semibold text-gray-900 mb-3">
                    Sample News Items ({scanResult.news_preview.sample_items.length} of {scanResult.news_preview.total_found})
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {scanResult.news_preview.sample_items.map((item, idx) => (
                      <div
                        key={idx}
                        className="border-l-2 border-primary-200 pl-3 py-2 hover:bg-gray-50"
                      >
                        <a
                          href={item.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-gray-900 hover:text-primary-600 inline-flex items-center gap-1"
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
                    ))}
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

          {/* Step 4: Confirming */}
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

