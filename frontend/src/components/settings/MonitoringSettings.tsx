import { ApiService } from '@/services/api'
import type { MonitoringPreferences } from '@/types'
import { useEffect, useState } from 'react'
import { toast } from 'react-hot-toast'

const CHANGE_TYPE_LABELS: Record<string, string> = {
  website_structure: 'Website structure',
  marketing_banner: 'Marketing banners',
  marketing_landing: 'Marketing landing pages',
  marketing_product: 'Product pages',
  marketing_jobs: 'Job postings',
  seo_meta: 'SEO meta tags',
  seo_structure: 'SEO structure',
  pricing: 'Pricing',
}

export default function MonitoringSettings() {
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  const [enabled, setEnabled] = useState<boolean>(true)
  const [checkFrequency, setCheckFrequency] = useState<MonitoringPreferences['check_frequency']>({
    website_structure: 24,
    marketing_changes: 24,
    seo_signals: 24,
    press_releases: 24,
  })
  const [notificationEnabled, setNotificationEnabled] = useState<boolean>(true)
  const [notificationTypes, setNotificationTypes] = useState<string[]>([])

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true)
        const prefs = await ApiService.getMonitoringPreferences()
        setEnabled(prefs.enabled)
        setCheckFrequency(prefs.check_frequency)
        setNotificationEnabled(prefs.notification_enabled)
        setNotificationTypes(prefs.notification_types)
      } catch (error: any) {
        console.error('Failed to load monitoring preferences', error)
        toast.error(error?.response?.data?.detail || 'Failed to load monitoring preferences')
      } finally {
        setIsLoading(false)
      }
    }

    load()
  }, [])

  const toggleChangeType = (type: string) => {
    setNotificationTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    )
  }

  const handleSave = async () => {
    try {
      setIsSaving(true)
      const payload: MonitoringPreferences = {
        enabled,
        check_frequency: checkFrequency,
        notification_enabled: notificationEnabled,
        notification_types: notificationTypes,
      }
      await ApiService.updateMonitoringPreferences(payload)
      toast.success('Monitoring settings saved')
    } catch (error: any) {
      console.error('Failed to save monitoring preferences', error)
      toast.error(error?.response?.data?.detail || 'Failed to save monitoring preferences')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="card p-6">
        <p className="text-sm text-gray-500">Loading monitoring settings...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="card p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Monitoring</h3>
            <p className="text-sm text-gray-500">
              Control how often we check competitors and which changes trigger alerts.
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600" />
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Check frequency</h4>
            <p className="text-xs text-gray-500 mb-3">
              Approximate interval between monitoring runs (in hours).
            </p>
            <div className="space-y-3">
              {[
                { key: 'website_structure', label: 'Website structure' },
                { key: 'marketing_changes', label: 'Marketing & pricing' },
                { key: 'seo_signals', label: 'SEO signals' },
                { key: 'press_releases', label: 'Press releases & news' },
              ].map((item) => (
                <div key={item.key} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={1}
                      max={24 * 7}
                      value={checkFrequency[item.key as keyof MonitoringPreferences['check_frequency']] || 24}
                      onChange={(e) =>
                        setCheckFrequency({
                          ...checkFrequency,
                          [item.key]: Number(e.target.value) || 1,
                        })
                      }
                      className="w-20 input py-1 px-2 text-sm"
                    />
                    <span className="text-xs text-gray-500">hours</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-3">Change alerts</h4>
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm text-gray-700">Enable change notifications</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificationEnabled}
                  onChange={(e) => setNotificationEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600" />
              </label>
            </div>

            <p className="text-xs text-gray-500 mb-2">Types of changes to notify about:</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
              {Object.entries(CHANGE_TYPE_LABELS).map(([key, label]) => (
                <label key={key} className="flex items-center space-x-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={notificationTypes.includes(key)}
                    onChange={() => toggleChangeType(key)}
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    disabled={!notificationEnabled}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-2 border-t border-gray-100 flex justify-end">
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="btn btn-primary btn-md"
          >
            {isSaving ? 'Saving...' : 'Save monitoring settings'}
          </button>
        </div>
      </div>
    </div>
  )
}


