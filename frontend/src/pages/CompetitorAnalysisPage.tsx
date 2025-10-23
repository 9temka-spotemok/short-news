import { ArrowLeft, ArrowRight, BarChart3, Building2, Download, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import BrandPreview from '../components/BrandPreview'
import CompanySelector from '../components/CompanySelector'
import CompetitorSuggestions from '../components/CompetitorSuggestions'
import { ExportMenu } from '../components/ExportMenu'
import ProgressSteps from '../components/ProgressSteps'
import ThemeAnalysis from '../components/ThemeAnalysis'
import { ApiService } from '../services/api'
import { Company } from '../types'

type AnalysisMode = 'company' | 'custom'
type Step = 'select' | 'suggest' | 'analyze'

export default function CompetitorAnalysisPage() {
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode | null>(null)
  const [step, setStep] = useState<Step>('select')
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [suggestedCompetitors, setSuggestedCompetitors] = useState<any[]>([])
  const [selectedCompetitors, setSelectedCompetitors] = useState<string[]>([])
  const [analysisData, setAnalysisData] = useState<any>(null)
  const [themesData, setThemesData] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Очищаем данные анализа при смене компании в режиме Company Analysis
  useEffect(() => {
    if (analysisMode === 'company' && selectedCompany) {
      setAnalysisData(null)
      setThemesData(null)
    }
  }, [selectedCompany, analysisMode])

  const handleExport = async (format: 'json' | 'pdf' | 'csv') => {
    if (!analysisData) return
    
    try {
      await ApiService.exportAnalysis(analysisData, format)
    } catch (err) {
      console.error('Export failed:', err)
      setError('Export failed. Please try again.')
    }
  }

  // Главное меню выбора режима анализа
  const renderModeSelection = () => (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Choose Analysis Type
        </h2>
        <p className="text-gray-600">
          Select the type of competitor analysis you want to perform
        </p>
      </div>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* Анализ компании */}
        <div 
          onClick={() => {
            setAnalysisMode('company')
            // Сбрасываем состояние при смене режима
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
          }}
          className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-blue-200"
        >
          <div className="flex items-center mb-4">
            <Building2 className="w-8 h-8 text-blue-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">
              Company Analysis
            </h3>
          </div>
          <p className="text-gray-600 mb-4">
            Quick analysis of a specific company with AI-suggested competitors. 
            Perfect for getting immediate insights about a company and its competitive landscape.
          </p>
          <ul className="text-sm text-gray-500 space-y-1">
            <li>• Select target company</li>
            <li>• AI-powered competitor suggestions</li>
            <li>• Instant analysis results</li>
            <li>• Export capabilities</li>
          </ul>
        </div>

        {/* Кастомный анализ */}
        <div 
          onClick={() => {
            setAnalysisMode('custom')
            // Сбрасываем состояние при смене режима
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            setStep('select')
            setSelectedCompetitors([])
            setSuggestedCompetitors([])
          }}
          className="bg-white rounded-lg shadow-md p-6 cursor-pointer hover:shadow-lg transition-shadow border-2 border-transparent hover:border-green-200"
        >
          <div className="flex items-center mb-4">
            <Users className="w-8 h-8 text-green-600 mr-3" />
            <h3 className="text-xl font-semibold text-gray-900">
              Custom Analysis
            </h3>
          </div>
          <p className="text-gray-600 mb-4">
            Advanced step-by-step analysis with full control over competitor selection. 
            Ideal for detailed research and comprehensive competitive intelligence.
          </p>
          <ul className="text-sm text-gray-500 space-y-1">
            <li>• Step-by-step process</li>
            <li>• Manual competitor selection</li>
            <li>• Detailed theme analysis</li>
            <li>• Advanced export options</li>
          </ul>
        </div>
      </div>
    </div>
  )

  // Режим анализа компании
  const renderCompanyAnalysis = () => (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Company Analysis
          </h2>
          <p className="text-gray-600 mt-1">
            Quick analysis with AI-suggested competitors
          </p>
        </div>
        <button
          onClick={() => {
            setAnalysisMode(null)
            // Сбрасываем все состояние при возврате в меню
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            setStep('select')
            setSelectedCompetitors([])
            setSuggestedCompetitors([])
          }}
          className="text-gray-600 hover:text-gray-800 flex items-center"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Menu
        </button>
      </div>

      {/* Выбор компании */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Select Company to Analyze
        </h3>
        <CompanySelector
          onSelect={setSelectedCompany}
          selectedCompany={selectedCompany}
        />
        
        {selectedCompany && (
          <div className="mt-6">
            <button
              onClick={runCompanyAnalysis}
              disabled={loading}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Analyzing...
                </>
              ) : (
                <>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Analyze Company
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Результаты анализа компании */}
      {analysisData && selectedCompany && (
        <div className="space-y-6">
          {/* Brand Preview */}
          <BrandPreview
            company={selectedCompany}
            stats={{
              total_news: analysisData.metrics.news_volume[selectedCompany.id] || 0,
              categories_breakdown: Object.entries(analysisData.metrics.category_distribution[selectedCompany.id] || {}).map(([category, count]) => ({
                category,
                count: count as number
              })),
              activity_score: analysisData.metrics.activity_score[selectedCompany.id] || 0,
              avg_priority: 0.5
            }}
          />
          
          {/* News Volume Comparison */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                News Volume Comparison
              </h3>
              <ExportMenu onExport={handleExport} />
            </div>
            <div className="space-y-3">
              {analysisData.companies.map((company: Company, index: number) => {
                const volume = analysisData.metrics.news_volume[company.id] || 0
                const maxVolume = Math.max(...Object.values(analysisData.metrics.news_volume).map(v => Number(v)))
                const percentage = maxVolume > 0 ? (volume / maxVolume) * 100 : 0
                const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500']
                
                return (
                  <div key={company.id}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">
                        {company.name}
                      </span>
                      <span className="text-sm text-gray-600">{volume} news</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full ${colors[index % colors.length]}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )

  // Режим кастомного анализа (существующий функционал)
  const renderCustomAnalysis = () => (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Custom Analysis
          </h2>
          <p className="text-gray-600 mt-1">
            Step-by-step competitor analysis with full control
          </p>
        </div>
        <button
          onClick={() => {
            setAnalysisMode(null)
            // Сбрасываем все состояние при возврате в меню
            setSelectedCompany(null)
            setAnalysisData(null)
            setThemesData(null)
            setError(null)
            setStep('select')
            setSelectedCompetitors([])
            setSuggestedCompetitors([])
          }}
          className="text-gray-600 hover:text-gray-800 flex items-center"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Menu
        </button>
      </div>

      {/* Progress Steps */}
      <ProgressSteps current={step} />
      
      {/* Content by step */}
      {step === 'select' && renderCompanySelection()}
      {step === 'suggest' && renderCompetitorSuggestion()}
      {step === 'analyze' && renderAnalysis()}
    </div>
  )

  // Функция для быстрого анализа компании
  const runCompanyAnalysis = async () => {
    if (!selectedCompany) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Получаем предложения конкурентов
      const suggestionsResponse = await ApiService.suggestCompetitors(selectedCompany.id, {
        limit: 5,
        days: 30
      })
      
      // Берем первых 3 конкурентов для анализа
      const competitorIds = suggestionsResponse.suggestions.slice(0, 3).map(s => s.company.id)
      const allCompanyIds = [selectedCompany.id, ...competitorIds]
      
      // Выполняем анализ
      const dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      const dateTo = new Date().toISOString()
      
      const response = await ApiService.compareCompanies({
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })
      
      setAnalysisData(response)
      
    } catch (err: any) {
      console.error('Error running company analysis:', err)
      setError(err.response?.data?.detail || 'Failed to run analysis')
    } finally {
      setLoading(false)
    }
  }
  
  // Шаг 1: Выбор основной компании
  const renderCompanySelection = () => (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Select Your Company
        </h2>
        <p className="text-gray-600 mb-6">
          Choose the company you want to analyze and find competitors for.
        </p>
        
        <CompanySelector
          onSelect={setSelectedCompany}
          selectedCompany={selectedCompany}
        />
        
        <div className="mt-6 flex justify-end">
          <button
            onClick={() => {
              if (selectedCompany) {
                loadCompetitorSuggestions()
                setStep('suggest')
              }
            }}
            disabled={!selectedCompany}
            className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            Continue
            <ArrowRight className="w-5 h-5 ml-2" />
          </button>
        </div>
      </div>
    </div>
  )
  
  // Шаг 2: Подбор конкурентов
  const renderCompetitorSuggestion = () => (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Choose Competitors
            </h2>
            <p className="text-gray-600 mt-1">
              AI has suggested competitors based on similarity analysis
            </p>
          </div>
          <button
            onClick={() => setStep('select')}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </button>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg border border-red-200 text-sm">
            {error}
          </div>
        )}
        
        <CompetitorSuggestions
          suggestions={suggestedCompetitors}
          selectedCompetitors={selectedCompetitors}
          onToggleCompetitor={toggleCompetitor}
          onAddManual={() => {
            // TODO: Implement manual competitor addition
            console.log('Add manual competitor')
          }}
        />
        
        <div className="mt-6 flex justify-between">
          <button
            onClick={() => setStep('select')}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </button>
          <button
            onClick={() => {
              if (selectedCompetitors.length > 0) {
                runAnalysis()
                setStep('analyze')
              }
            }}
            disabled={selectedCompetitors.length === 0}
            className="bg-primary-600 text-white px-6 py-3 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
          >
            Analyze
            <ArrowRight className="w-5 h-5 ml-2" />
          </button>
        </div>
      </div>
    </div>
  )
  
  // Шаг 3: Анализ
  const renderAnalysis = () => (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">
            Analysis Results
          </h2>
          <p className="text-gray-600 mt-1">
            Comprehensive analysis of {selectedCompany?.name} and its competitors
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={() => setStep('suggest')}
            className="text-gray-600 hover:text-gray-800 flex items-center"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back
          </button>
          <button
            onClick={exportResults}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
        </div>
      </div>
      
      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Analyzing competitors...</p>
        </div>
      )}
      
      {analysisData && (
        <div className="space-y-6">
          {/* Brand Preview */}
          <BrandPreview
            company={selectedCompany!}
            stats={{
              total_news: analysisData.metrics.news_volume[selectedCompany!.id] || 0,
              categories_breakdown: Object.entries(analysisData.metrics.category_distribution[selectedCompany!.id] || {}).map(([category, count]) => ({
                category,
                count: count as number
              })),
              activity_score: analysisData.metrics.activity_score[selectedCompany!.id] || 0,
              avg_priority: 0.5 // Placeholder - не вычисляется в текущей версии
            }}
          />
          
          {/* News Volume Comparison */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                News Volume Comparison
              </h3>
              <ExportMenu onExport={handleExport} />
            </div>
            <div className="space-y-3">
              {analysisData.companies.map((company: Company, index: number) => {
                const volume = analysisData.metrics.news_volume[company.id] || 0
                const maxVolume = Math.max(...Object.values(analysisData.metrics.news_volume).map(v => Number(v)))
                const percentage = maxVolume > 0 ? (volume / maxVolume) * 100 : 0
                const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-pink-500']
                
                return (
                  <div key={company.id}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-700">
                        {company.name}
                      </span>
                      <span className="text-sm text-gray-600">{volume} news</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full ${colors[index % colors.length]}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
          
          {/* Theme Analysis */}
          {themesData && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Theme Analysis
              </h3>
              <ThemeAnalysis
                themesData={themesData}
                companies={analysisData.companies}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
  
  const loadCompetitorSuggestions = async () => {
    if (!selectedCompany) return
    
    setLoading(true)
    setError(null)
    
    try {
      const response = await ApiService.suggestCompetitors(selectedCompany.id, {
        limit: 5,
        days: 30
      })
      setSuggestedCompetitors(response.suggestions)
    } catch (err: any) {
      console.error('Error loading suggestions:', err)
      setError(err.response?.data?.detail || 'Failed to load competitor suggestions')
    } finally {
      setLoading(false)
    }
  }
  
  const toggleCompetitor = (companyId: string) => {
    setSelectedCompetitors(prev => 
      prev.includes(companyId)
        ? prev.filter(id => id !== companyId)
        : [...prev, companyId]
    )
  }
  
  const runAnalysis = async () => {
    if (!selectedCompany || selectedCompetitors.length === 0) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Валидация данных
      if (!selectedCompany || !selectedCompany.id) {
        throw new Error('Selected company is invalid')
      }
      
      if (!Array.isArray(selectedCompetitors)) {
        throw new Error('Selected competitors is not an array')
      }
      
      // Проверяем что все ID являются строками
      const allCompanyIds = [selectedCompany.id, ...selectedCompetitors].map(id => String(id))
      
      // Исправить формат дат - добавить время
      const dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()
      const dateTo = new Date().toISOString()
      
      console.log('Sending request with:', {
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })
      
      console.log('Selected company:', selectedCompany)
      console.log('Selected competitors:', selectedCompetitors)
      console.log('All company IDs:', allCompanyIds)
      console.log('Request object:', {
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })
      
      const response = await ApiService.compareCompanies({
        company_ids: allCompanyIds,
        date_from: dateFrom,
        date_to: dateTo
      })
      
      setAnalysisData(response)
      
      // Get themes data
      const themesResponse = await ApiService.analyzeThemes(allCompanyIds, {
        date_from: dateFrom,
        date_to: dateTo
      })
      
      setThemesData(themesResponse)
      
    } catch (err: any) {
      console.error('Error running analysis:', err)
      console.error('Error details:', err.response?.data)
      setError(err.response?.data?.detail || 'Failed to run analysis')
    } finally {
      setLoading(false)
    }
  }
  
  const exportResults = () => {
    if (!analysisData) return
    
    const exportData = {
      company: selectedCompany,
      competitors: analysisData.companies.filter((c: Company) => c.id !== selectedCompany?.id),
      analysis: analysisData,
      themes: themesData,
      generated_at: new Date().toISOString()
    }
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `competitor-analysis-${selectedCompany?.name}-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
  
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-8 px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <BarChart3 className="w-8 h-8 mr-3" />
            Competitor Analysis
          </h1>
          <p className="text-gray-600 mt-2">
            Professional competitor analysis with AI-powered insights
          </p>
        </div>
        
        {/* Content by mode */}
        {!analysisMode && renderModeSelection()}
        {analysisMode === 'company' && renderCompanyAnalysis()}
        {analysisMode === 'custom' && renderCustomAnalysis()}
      </div>
    </div>
  )
}