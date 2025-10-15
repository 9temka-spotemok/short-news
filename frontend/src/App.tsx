import { useAuthStore } from '@/store/authStore'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { Navigate, Route, Routes } from 'react-router-dom'

import DashboardLayout from '@/components/DashboardLayout'
import Layout from '@/components/Layout'
import NewsPageWrapper from '@/components/NewsPageWrapper'
import CompetitorAnalysisPage from '@/pages/CompetitorAnalysisPage'
import DashboardPage from '@/pages/DashboardPage'
import DigestSettingsPage from '@/pages/DigestSettingsPage'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import NewsAnalyticsPage from '@/pages/NewsAnalyticsPage'
import NewsDetailPage from '@/pages/NewsDetailPage'
import NotificationsPage from '@/pages/NotificationsPage'
import ProfilePage from '@/pages/ProfilePage'
import RegisterPage from '@/pages/RegisterPage'
import SettingsPage from '@/pages/SettingsPage'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="news" element={<NewsPageWrapper />} />
            <Route path="news/:id" element={<NewsDetailPage />} />
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
            <Route 
              path="news-analytics" 
              element={isAuthenticated ? <NewsAnalyticsPage /> : <Navigate to="/login" />} 
            />
          </Route>

          {/* 404 route */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
        
        {/* Toast notifications */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#10B981',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#EF4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </div>
    </QueryClientProvider>
  )
}

export default App
