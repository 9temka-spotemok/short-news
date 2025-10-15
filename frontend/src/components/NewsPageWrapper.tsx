import AuthNewsPage from '@/pages/AuthNewsPage'
import GuestNewsPage from '@/pages/GuestNewsPage'
import { useAuthStore } from '@/store/authStore'

export default function NewsPageWrapper() {
  const { isAuthenticated } = useAuthStore()

  // Return appropriate page based on authentication status
  return isAuthenticated ? <AuthNewsPage /> : <GuestNewsPage />
}
