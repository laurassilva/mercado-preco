'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/services/auth'
import Sidebar from './Sidebar'
import Header from './Header'

interface Props {
  children: React.ReactNode
  title: string
}

export default function AuthGuard({ children, title }: Props) {
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace('/auth/login')
    }
  }, [router])

  if (!isAuthenticated()) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600" />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content: sem margem no mobile, com margem no desktop */}
      <main className="flex-1 flex flex-col min-h-screen w-full lg:ml-[260px] min-w-0">
        <Header title={title} onMenuToggle={() => setSidebarOpen((o) => !o)} />
        <div className="flex-1 p-3 md:p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
