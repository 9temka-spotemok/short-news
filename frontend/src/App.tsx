import { useAuthStore } from '@/store/authStore'
import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from '@/components/Layout'
import DashboardPage from '@/pages/DashboardPage'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import NewsPage from '@/pages/NewsPage'
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

      {/* Protected routes */}
      <Route 
        path="/dashboard" 
        element={isAuthenticated ? <DashboardPage /> : <Navigate to="/login" />} 
      />
      <Route 
        path="/settings" 
        element={isAuthenticated ? <SettingsPage /> : <Navigate to="/login" />} 
      />

      {/* 404 route */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

export default App
