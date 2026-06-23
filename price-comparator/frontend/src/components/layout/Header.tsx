'use client'
import { Menu, Sun, Moon } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'

interface Props {
  title: string
  onMenuToggle: () => void
}

export default function Header({ title, onMenuToggle }: Props) {
  const [dark, setDark] = useState(false)
  const { user } = useAuth()

  useEffect(() => {
    if (dark) document.documentElement.classList.add('dark')
    else document.documentElement.classList.remove('dark')
  }, [dark])

  const firstName = user?.name?.split(' ')[0] || ''

  return (
    <header className="h-14 md:h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 md:px-6 sticky top-0 z-20 shadow-sm">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
          aria-label="Abrir menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-base md:text-lg font-semibold text-gray-900 truncate">{title}</h1>
      </div>
      <div className="flex items-center gap-3">
        {firstName && (
          <span className="text-sm text-gray-600 hidden sm:block">
            Olá, <span className="font-semibold text-gray-800">{firstName}</span>
          </span>
        )}
        <button
          onClick={() => setDark((d) => !d)}
          className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
          title="Alternar tema"
        >
          {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  )
}
