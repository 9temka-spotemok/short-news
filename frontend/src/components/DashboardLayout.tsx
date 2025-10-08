import { Outlet } from 'react-router-dom'
import Header from './Header'

export default function DashboardLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}

