import { Bell, Filter, Shield, User, X, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { ApiService } from '@/services/api'
import toast from 'react-hot-toast'
import type { Company, NewsCategoryInfo } from '@/types'
import { useNavigate } from 'react-router-dom'

export default function SettingsPage() {
  const { user, isAuthenticated, updateUser } = useAuthStore()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('profile')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  // Profile state
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')

  // Preferences state
  const [subscribedCompanies, setSubscribedCompanies] = useState<string[]>([])
  const [interestedCategories, setInterestedCategories] = useState<string[]>([])
  const [keywords, setKeywords] = useState<string[]>([])
  const [notificationFrequency, setNotificationFrequency] = useState<'realtime' | 'daily' | 'weekly' | 'never'>('daily')

  // Data for dropdowns
  const [allCompanies, setAllCompanies] = useState<Company[]>([])
  const [allCategories, setAllCategories] = useState<NewsCategoryInfo[]>([])
  const [newKeyword, setNewKeyword] = useState('')
  const [companySearchQuery, setCompanySearchQuery] = useState('')

  // Security state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'preferences', label: 'Preferences', icon: Filter },
    { id: 'security', label: 'Security', icon: Shield },
  ]

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }

    loadData()
  }, [isAuthenticated, navigate])

  const loadData = async () => {
    try {
      setIsLoading(true)

      // Load user data
      if (user) {
        setFullName(user.full_name || '')
        setEmail(user.email)
      }

      // Load preferences
      const preferences = await ApiService.getUserPreferences()
      setSubscribedCompanies(preferences.subscribed_companies || [])
      setInterestedCategories(preferences.interested_categories || [])
      setKeywords(preferences.keywords || [])
      setNotificationFrequency((preferences.notification_frequency as any) || 'daily')

      // Load companies
      const companiesResponse = await ApiService.getCompanies('', 200, 0)
      setAllCompanies(companiesResponse.items)

      // Load categories
      const categoriesResponse = await ApiService.getNewsCategories()
      setAllCategories(categoriesResponse.categories)
    } catch (error: any) {
      console.error('Error loading settings:', error)
      toast.error('Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      setIsSaving(true)
      await ApiService.updateUser({ full_name: fullName })
      toast.success('Profile updated successfully')
      // Reload user data
      const updatedUser = await ApiService.getCurrentUser()
      updateUser(updatedUser)
    } catch (error: any) {
      console.error('Error saving profile:', error)
      toast.error(error.response?.data?.detail || 'Failed to update profile')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSavePreferences = async () => {
    try {
      setIsSaving(true)
      await ApiService.updateUserPreferences({
        subscribed_companies: subscribedCompanies,
        interested_categories: interestedCategories,
        keywords: keywords,
        notification_frequency: notificationFrequency,
      })
      toast.success('Preferences saved successfully')
    } catch (error: any) {
      console.error('Error saving preferences:', error)
      toast.error(error.response?.data?.detail || 'Failed to save preferences')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveNotifications = async () => {
    try {
      setIsSaving(true)
      await ApiService.updateUserPreferences({
        notification_frequency: notificationFrequency,
      })
      toast.success('Notification settings saved successfully')
    } catch (error: any) {
      console.error('Error saving notification settings:', error)
      toast.error(error.response?.data?.detail || 'Failed to save notification settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleAddKeyword = () => {
    if (newKeyword.trim() && !keywords.includes(newKeyword.trim())) {
      setKeywords([...keywords, newKeyword.trim()])
      setNewKeyword('')
    }
  }

  const handleRemoveKeyword = (keyword: string) => {
    setKeywords(keywords.filter(k => k !== keyword))
  }

  const toggleCompany = (companyId: string) => {
    if (subscribedCompanies.includes(companyId)) {
      setSubscribedCompanies(subscribedCompanies.filter(id => id !== companyId))
    } else {
      setSubscribedCompanies([...subscribedCompanies, companyId])
    }
  }

  const toggleCategory = (category: string) => {
    if (interestedCategories.includes(category)) {
      setInterestedCategories(interestedCategories.filter(c => c !== category))
    } else {
      setInterestedCategories([...interestedCategories, category])
    }
  }

  const filteredCompanies = allCompanies.filter((company) =>
    company.name.toLowerCase().includes(companySearchQuery.toLowerCase())
  )

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }

    try {
      setIsSaving(true)
      // TODO: Implement password change API endpoint
      toast.error('Password change functionality is not yet implemented')
      // await ApiService.changePassword({ current_password: currentPassword, new_password: newPassword })
    } catch (error: any) {
      console.error('Error changing password:', error)
      toast.error(error.response?.data?.detail || 'Failed to change password')
    } finally {
      setIsSaving(false)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    }
  }

  const getCategoryLabel = (categoryValue: string): string => {
    const category = allCategories.find(c => c.value === categoryValue)
    return category ? category.description : categoryValue.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  if (!isAuthenticated || !user) {
    return null
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-500">Loading settings...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Settings
          </h1>
          <p className="text-gray-600">
            Manage your profile and preferences
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1">
            <nav className="space-y-1">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md ${
                      activeTab === tab.id
                        ? 'bg-primary-100 text-primary-700'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="mr-3 h-5 w-5" />
                    {tab.label}
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="lg:col-span-3">
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Profile Information
                  </h3>
                  <form onSubmit={handleSaveProfile} className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Full Name
                        </label>
                        <input
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          className="input"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Email
                        </label>
                        <input
                          type="email"
                          value={email}
                          disabled
                          className="input bg-gray-50"
                        />
                        <p className="text-xs text-gray-500 mt-1">
                          Email cannot be changed
                        </p>
                      </div>
                    </div>
                    <button 
                      type="submit"
                      disabled={isSaving}
                      className="btn btn-primary btn-md"
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </button>
                  </form>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Avatar
                  </h3>
                  <div className="flex items-center space-x-4">
                    <div className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center">
                      <span className="text-white font-bold text-lg">
                        {fullName.charAt(0).toUpperCase() || user.email.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <button className="btn btn-outline btn-sm" disabled>
                        Change Avatar
                      </button>
                      <p className="text-sm text-gray-500 mt-1">
                        Avatar upload coming soon
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Notification Frequency
                  </h3>
                  <div className="space-y-3">
                    {[
                      { value: 'realtime', label: 'Real-time' },
                      { value: 'daily', label: 'Daily' },
                      { value: 'weekly', label: 'Weekly' },
                      { value: 'never', label: 'Never' },
                    ].map((option) => (
                      <label key={option.value} className="flex items-center">
                        <input
                          type="radio"
                          name="frequency"
                          value={option.value}
                          checked={notificationFrequency === option.value}
                          onChange={(e) => setNotificationFrequency(e.target.value as any)}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300"
                        />
                        <span className="ml-2 text-sm text-gray-700">
                          {option.label}
                        </span>
                      </label>
                    ))}
                  </div>
                  <button
                    onClick={handleSaveNotifications}
                    disabled={isSaving}
                    className="btn btn-primary btn-md mt-4"
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Notification Types
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          Email Notifications
                        </h4>
                        <p className="text-sm text-gray-500">
                          Receive notifications via email
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        defaultChecked
                        disabled
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          Daily Digests
                        </h4>
                        <p className="text-sm text-gray-500">
                          Receive daily news digests
                        </p>
                      </div>
                      <input
                        type="checkbox"
                        defaultChecked
                        disabled
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <p className="text-xs text-gray-500 ml-2">
                        Configure in <a href="/digest-settings" className="text-primary-600 hover:underline">Digest Settings</a>
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Tracked Companies
                  </h3>
                  
                  {/* Поисковая строка */}
                  <div className="mb-4">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                      <input
                        type="text"
                        placeholder="Search companies..."
                        value={companySearchQuery}
                        onChange={(e) => setCompanySearchQuery(e.target.value)}
                        className="input pl-10 w-full"
                      />
                      {companySearchQuery && (
                        <button
                          onClick={() => setCompanySearchQuery('')}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          type="button"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {allCompanies.length === 0 ? (
                      <p className="text-sm text-gray-500">Loading companies...</p>
                    ) : filteredCompanies.length === 0 ? (
                      <p className="text-sm text-gray-500">
                        {companySearchQuery ? `No companies found for "${companySearchQuery}"` : 'No companies available'}
                      </p>
                    ) : (
                      filteredCompanies.map((company) => (
                        <label key={company.id} className="flex items-center">
                          <input
                            type="checkbox"
                            checked={subscribedCompanies.includes(company.id)}
                            onChange={() => toggleCompany(company.id)}
                            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <span className="ml-2 text-sm text-gray-700">
                            {company.name}
                          </span>
                        </label>
                      ))
                    )}
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Interested Categories
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-64 overflow-y-auto">
                    {allCategories.length === 0 ? (
                      <p className="text-sm text-gray-500">Loading categories...</p>
                    ) : (
                      allCategories.map((category) => (
                        <label key={category.value} className="flex items-center">
                          <input
                            type="checkbox"
                            checked={interestedCategories.includes(category.value)}
                            onChange={() => toggleCategory(category.value)}
                            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <span className="ml-2 text-sm text-gray-700">
                            {getCategoryLabel(category.value)}
                          </span>
                        </label>
                      ))
                    )}
                  </div>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Keywords
                  </h3>
                  <div className="flex gap-2 mb-3">
                    <input
                      type="text"
                      placeholder="Add keyword"
                      value={newKeyword}
                      onChange={(e) => setNewKeyword(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          handleAddKeyword()
                        }
                      }}
                      className="input flex-1"
                    />
                    <button
                      type="button"
                      onClick={handleAddKeyword}
                      className="btn btn-outline btn-sm"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {keywords.length === 0 ? (
                      <p className="text-sm text-gray-500">No keywords added yet</p>
                    ) : (
                      keywords.map((keyword) => (
                        <span
                          key={keyword}
                          className="badge badge-gray flex items-center"
                        >
                          {keyword}
                          <button
                            onClick={() => handleRemoveKeyword(keyword)}
                            className="ml-1 text-gray-400 hover:text-gray-600"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      ))
                    )}
                  </div>
                </div>

                <button
                  onClick={handleSavePreferences}
                  disabled={isSaving}
                  className="btn btn-primary btn-md"
                >
                  {isSaving ? 'Saving...' : 'Save Preferences'}
                </button>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Change Password
                  </h3>
                  <form onSubmit={handleChangePassword} className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Current Password
                      </label>
                      <input
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        className="input"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        New Password
                      </label>
                      <input
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="input"
                        required
                        minLength={8}
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Confirm Password
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="input"
                        required
                        minLength={8}
                      />
                    </div>
                    <button
                      type="submit"
                      disabled={isSaving}
                      className="btn btn-primary btn-md"
                    >
                      {isSaving ? 'Changing...' : 'Change Password'}
                    </button>
                  </form>
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Two-Factor Authentication
                  </h3>
                  <p className="text-gray-600 mb-4">
                    Add an extra layer of security to your account
                  </p>
                  <button className="btn btn-outline btn-md" disabled>
                    Enable 2FA
                  </button>
                  <p className="text-xs text-gray-500 mt-2">
                    Coming soon
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


