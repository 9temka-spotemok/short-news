import { useAuthStore } from '@/store/authStore'
import { Navigate, Route, Routes } from 'react-router-dom'

import DashboardLayout from '@/components/DashboardLayout'
import Layout from '@/components/Layout'
import CompetitorAnalysisPage from '@/pages/CompetitorAnalysisPage'
import DashboardPage from '@/pages/DashboardPage'
import DigestSettingsPage from '@/pages/DigestSettingsPage'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import NewsPage from '@/pages/NewsPage'
import NotificationsPage from '@/pages/NotificationsPage'
import ProfilePage from '@/pages/ProfilePage'
import RegisterPage from '@/pages/RegisterPage'
import SettingsPage from '@/pages/SettingsPage'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="news" element={<NewsPage />} />
        <Route 
          path="login" 
          element={isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />} 
        />
        <Route 
          path="register" 
          element={isAuthenticated ? <Navigate to="/dashboard" /> : <RegisterPage />} 
        />
      </Route>

      {/* Protected routes - с DashboardLayout (без Footer) */}
      <Route element={<DashboardLayout />}>
        <Route 
          path="dashboard" 
          element={isAuthenticated ? <DashboardPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="profile" 
          element={isAuthenticated ? <ProfilePage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="settings" 
          element={isAuthenticated ? <SettingsPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="digest-settings" 
          element={isAuthenticated ? <DigestSettingsPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="notifications" 
          element={isAuthenticated ? <NotificationsPage /> : <Navigate to="/login" />} 
        />
        <Route 
          path="competitor-analysis" 
          element={isAuthenticated ? <CompetitorAnalysisPage /> : <Navigate to="/login" />} 
        />
      </Route>

      {/* 404 route */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
