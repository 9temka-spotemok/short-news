import MonitoringSourcesCard from '@/components/monitoring/MonitoringSourcesCard'
import MonitoringStatusCard from '@/components/monitoring/MonitoringStatusCard'
import { ApiService } from '@/services/api'
import { useQuery } from '@tanstack/react-query'
import { Activity, RefreshCw, Search } from 'lucide-react'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

export default function MonitoringDashboardPage() {
  const navigate = useNavigate()
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Get user preferences to get subscribed companies
  const { data: userPreferences } = useQuery({
    queryKey: ['user-preferences'],
    queryFn: ApiService.getUserPreferences,
    staleTime: 1000 * 60 * 5,
  })

  const subscribedCompanies = userPreferences?.subscribed_companies || []

  // Get monitoring status for all subscribed companies
  const { data: monitoringStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['monitoring-status', subscribedCompanies],
    queryFn: () => ApiService.getMonitoringStatus(subscribedCompanies),
    enabled: subscribedCompanies.length > 0,
    staleTime: 1000 * 60 * 5,
  })

  // Get monitoring stats
  const { data: monitoringStats } = useQuery({
    queryKey: ['monitoring-stats'],
    queryFn: ApiService.getMonitoringStats,
    staleTime: 1000 * 60 * 5,
  })

  // Get monitoring matrix for selected company
  const { data: monitoringMatrix, isLoading: matrixLoading } = useQuery({
    queryKey: ['monitoring-matrix', selectedCompanyId],
    queryFn: () => ApiService.getMonitoringMatrix(selectedCompanyId!),
    enabled: !!selectedCompanyId,
    staleTime: 1000 * 60 * 5,
  })

  const handleRefreshAll = async () => {
    try {
      await refetchStatus()
      toast.success('Monitoring status refreshed')
    } catch (error) {
      toast.error('Failed to refresh monitoring status')
    }
  }

  const filteredStatuses = monitoringStatus?.statuses?.filter((status) => {
    if (!searchQuery) return true
    return status.company_name.toLowerCase().includes(searchQuery.toLowerCase())
  }) || []

  if (subscribedCompanies.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <Activity className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Companies Tracked</h2>
          <p className="text-gray-600 mb-4">
            Add companies to start monitoring their changes and updates.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn btn-primary"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <Activity className="w-8 h-8 text-primary-600" />
              Monitoring Dashboard
            </h1>
            <p className="text-gray-600 mt-2">
              Track changes in competitor websites, social media, and marketing
            </p>
          </div>
          <button
            onClick={handleRefreshAll}
            disabled={statusLoading}
            className="btn btn-outline flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${statusLoading ? 'animate-spin' : ''}`} />
            Refresh All
          </button>
        </div>

        {/* Stats Cards */}
        {monitoringStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-sm text-gray-600 mb-1">Total Companies</div>
              <div className="text-2xl font-bold text-gray-900">
                {monitoringStats.total_companies}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-sm text-gray-600 mb-1">Active Monitoring</div>
              <div className="text-2xl font-bold text-green-600">
                {monitoringStats.active_monitoring}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-sm text-gray-600 mb-1">Changes Detected</div>
              <div className="text-2xl font-bold text-blue-600">
                {monitoringStats.total_changes_detected}
              </div>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="text-sm text-gray-600 mb-1">Last 24h</div>
              <div className="text-2xl font-bold text-orange-600">
                {monitoringStats.last_24h_changes}
              </div>
            </div>
          </div>
        )}

        {/* Search and Filter */}
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search companies..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Company Status Cards */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Company Status</h2>
            <span className="text-sm text-gray-500">
              {filteredStatuses.length} {filteredStatuses.length === 1 ? 'company' : 'companies'}
            </span>
          </div>

          {statusLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-3"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : filteredStatuses.length > 0 ? (
            <div className="space-y-4">
              {filteredStatuses.map((status) => (
                <div
                  key={status.company_id}
                  className={selectedCompanyId === status.company_id ? 'ring-2 ring-primary-500 rounded-lg' : ''}
                >
                  <MonitoringStatusCard
                    status={status}
                    onViewDetails={() => {
                      setSelectedCompanyId(
                        selectedCompanyId === status.company_id ? null : status.company_id
                      )
                    }}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
              <p className="text-gray-500">No companies found matching your search</p>
            </div>
          )}
        </div>

        {/* Right Column - Monitoring Matrix Details */}
        <div className="lg:col-span-1">
          {selectedCompanyId ? (
            <>
              {matrixLoading ? (
                <div className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                  <div className="h-32 bg-gray-200 rounded"></div>
                </div>
              ) : monitoringMatrix ? (
                <div className="sticky top-4">
                  <MonitoringSourcesCard matrix={monitoringMatrix as any} />
                </div>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 p-4">
                  <p className="text-sm text-gray-500">
                    No monitoring data available for this company
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 p-6 text-center">
              <Activity className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="text-sm text-gray-600 mb-2">Select a company</p>
              <p className="text-xs text-gray-500">
                Click on a company card to view detailed monitoring information
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
