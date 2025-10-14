import { Calendar, Clock, MessageSquare, Save, Settings as SettingsIcon } from 'lucide-react'
import { useEffect, useState } from 'react'
import api from '../services/api'
import { CustomSchedule, DigestSettings } from '../types'

export default function DigestSettingsPage() {
  const [settings, setSettings] = useState<DigestSettings>({
    digest_enabled: false,
    digest_frequency: 'daily',
    digest_custom_schedule: null,
    digest_format: 'short',
    digest_include_summaries: true,
    telegram_chat_id: null,
    telegram_enabled: false,
    timezone: 'UTC',
    week_start_day: 0
  })
  
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      setIsLoading(true)
      const response = await api.get('/users/preferences/digest')
      setSettings(response.data)
    } catch (error) {
      console.error('Error fetching digest settings:', error)
      setMessage({ type: 'error', text: 'Failed to load digest settings' })
    } finally {
      setIsLoading(false)
    }
  }

  const saveSettings = async () => {
    try {
      setIsSaving(true)
      setMessage(null)
      
      await api.put('/users/preferences/digest', settings)
      
      setMessage({ type: 'success', text: 'Digest settings saved successfully!' })
      
      // Clear message after 3 seconds
      setTimeout(() => setMessage(null), 3000)
    } catch (error: any) {
      console.error('Error saving digest settings:', error)
      setMessage({ 
        type: 'error',
        text: error.response?.data?.detail || 'Failed to save digest settings' 
      })
    } finally {
      setIsSaving(false)
    }
  }

  const updateCustomSchedule = (field: keyof CustomSchedule, value: any) => {
    setSettings(prev => ({
      ...prev,
      digest_custom_schedule: {
        ...(prev.digest_custom_schedule || { time: '09:00', days: [1, 2, 3, 4, 5], timezone: 'UTC' }),
        [field]: value
      }
    }))
  }

  const toggleDay = (day: number) => {
    const currentDays = settings.digest_custom_schedule?.days || []
    const newDays = currentDays.includes(day)
      ? currentDays.filter(d => d !== day)
      : [...currentDays, day].sort()
    
    updateCustomSchedule('days', newDays)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-600">Loading settings...</div>
      </div>
    )
  }

  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center">
            <SettingsIcon className="w-8 h-8 mr-3" />
            Digest Settings
          </h1>
          <p className="text-gray-600 mt-2">
            Configure your personalized news digest delivery
          </p>
        </div>

        {message && (
          <div
            className={`mb-6 p-4 rounded-lg ${
              message.type === 'success' 
                ? 'bg-green-50 text-green-800 border border-green-200' 
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {message.text}
          </div>
        )}

        <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
          {/* Enable/Disable Digest */}
          <div className="flex items-center justify-between pb-6 border-b">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Enable Digests</h3>
              <p className="text-sm text-gray-600 mt-1">
                Receive personalized news digests
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.digest_enabled}
                onChange={(e) => setSettings({ ...settings, digest_enabled: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </div>

          {/* Frequency */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Calendar className="w-5 h-5 mr-2" />
              Frequency
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {(['daily', 'weekly', 'custom'] as const).map((freq) => (
                <button
                  key={freq}
                  onClick={() => setSettings({ ...settings, digest_frequency: freq })}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    settings.digest_frequency === freq
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <span className="capitalize font-medium">{freq}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Schedule */}
          {settings.digest_frequency === 'custom' && (
            <div className="space-y-4 p-4 bg-gray-50 rounded-lg">
              <h4 className="font-medium text-gray-900">Custom Schedule</h4>
              
              {/* Time */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  <Clock className="w-4 h-4 inline mr-1" />
                  Time
                </label>
                <input
                  type="time"
                  value={settings.digest_custom_schedule?.time || '09:00'}
                  onChange={(e) => updateCustomSchedule('time', e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Days */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Days of Week
                </label>
                <div className="flex flex-wrap gap-2">
                  {dayNames.map((day, index) => (
                    <button
                      key={index}
                      onClick={() => toggleDay(index)}
                      className={`px-3 py-2 rounded-lg border transition-all ${
                        settings.digest_custom_schedule?.days?.includes(index)
                          ? 'bg-blue-500 text-white border-blue-500'
                          : 'bg-white border-gray-300 hover:border-blue-300'
                      }`}
                    >
                      {day.slice(0, 3)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Format */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-gray-900">Format</h3>
            <div className="grid grid-cols-2 gap-3">
              {(['short', 'detailed'] as const).map((format) => (
                <button
                  key={format}
                  onClick={() => setSettings({ ...settings, digest_format: format })}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    settings.digest_format === format
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium capitalize">{format}</div>
                  <div className="text-xs mt-1 text-gray-600">
                    {format === 'short' ? 'Headlines only' : 'Full summaries'}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Include Summaries */}
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-gray-900">Include Summaries</h3>
              <p className="text-xs text-gray-600 mt-1">
                Add article summaries to digest
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.digest_include_summaries}
              onChange={(e) => setSettings({ ...settings, digest_include_summaries: e.target.checked })}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
            />
          </div>

          {/* Timezone and Week Settings */}
          <div className="pt-6 border-t space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <Clock className="w-5 h-5 mr-2" />
              Timezone & Week Settings
            </h3>
            
            {/* Timezone */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Timezone
              </label>
              <select
                value={settings.timezone || 'UTC'}
                onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="UTC">UTC</option>
                <option value="America/New_York">America/New York (EST/EDT)</option>
                <option value="America/Chicago">America/Chicago (CST/CDT)</option>
                <option value="America/Los_Angeles">America/Los Angeles (PST/PDT)</option>
                <option value="Europe/London">Europe/London (GMT/BST)</option>
                <option value="Europe/Paris">Europe/Paris (CET/CEST)</option>
                <option value="Europe/Berlin">Europe/Berlin (CET/CEST)</option>
                <option value="Europe/Moscow">Europe/Moscow (MSK)</option>
                <option value="Asia/Dubai">Asia/Dubai (GST)</option>
                <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                <option value="Asia/Shanghai">Asia/Shanghai (CST)</option>
                <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
                <option value="Asia/Singapore">Asia/Singapore (SGT)</option>
                <option value="Australia/Sydney">Australia/Sydney (AEDT/AEST)</option>
                <option value="Pacific/Auckland">Pacific/Auckland (NZDT/NZST)</option>
              </select>
              <p className="text-xs text-gray-600 mt-1">
                Digest dates will be calculated based on your timezone
              </p>
            </div>

            {/* Week Start Day */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Week Starts On
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setSettings({ ...settings, week_start_day: 0 })}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    (settings.week_start_day === 0 || settings.week_start_day === undefined)
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium">Sunday</div>
                  <div className="text-xs mt-1 opacity-75">US/GitHub style</div>
                </button>
                <button
                  onClick={() => setSettings({ ...settings, week_start_day: 1 })}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    settings.week_start_day === 1
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium">Monday</div>
                  <div className="text-xs mt-1 opacity-75">ISO 8601</div>
                </button>
              </div>
              <p className="text-xs text-gray-600 mt-2">
                <strong>Sunday:</strong> Week runs Sun-Sat (like GitHub, US calendars)<br />
                <strong>Monday:</strong> Week runs Mon-Sun (ISO 8601, EU standard)
              </p>
            </div>
          </div>

          {/* Telegram Integration */}
          <div className="pt-6 border-t space-y-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center">
              <MessageSquare className="w-5 h-5 mr-2" />
              Telegram Integration
            </h3>
            
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-gray-900">Send to Telegram</h4>
                <p className="text-xs text-gray-600 mt-1">
                  Receive digests in Telegram
                </p>
              </div>
              <input
                type="checkbox"
                checked={settings.telegram_enabled}
                onChange={(e) => setSettings({ ...settings, telegram_enabled: e.target.checked })}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Telegram Chat ID
              </label>
              <input
                type="text"
                value={settings.telegram_chat_id || ''}
                onChange={(e) => setSettings({ ...settings, telegram_chat_id: e.target.value })}
                placeholder="Get from @ai_insight_hub_bot /start"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Send <code className="bg-gray-100 px-1 py-0.5 rounded">/start</code> to the bot to get your Chat ID
              </p>
            </div>
          </div>

          {/* Save Button */}
          <div className="pt-6 border-t">
            <button
              onClick={saveSettings}
              disabled={isSaving}
              className="w-full bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              <Save className="w-5 h-5 mr-2" />
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

