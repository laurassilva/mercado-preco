'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Search, ShoppingCart, History,
  FileText, Users, Activity, LogOut, ShoppingBag, X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { logout } from '@/services/auth'
import { useAuth } from '@/hooks/useAuth'

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/search', label: 'Pesquisar Preços', icon: Search },
  { href: '/markets', label: 'Mercados', icon: ShoppingCart },
  { href: '/history', label: 'Histórico', icon: History },
  { href: '/reports', label: 'Relatórios', icon: FileText },
]

const adminItems = [
  { href: '/users', label: 'Usuários', icon: Users },
  { href: '/scraping', label: 'Coleta', icon: Activity },
]

interface Props {
  isOpen: boolean
  onClose: () => void
}

export default function Sidebar({ isOpen, onClose }: Props) {
  const pathname = usePathname()
  const { user, isAdmin } = useAuth()

  return (
    <>
      {/* Overlay para mobile */}
      {isOpen && (
        <div
          className="sidebar-overlay"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 h-screen w-[260px] bg-brand-800 text-white flex flex-col z-30',
          'transition-transform duration-300 ease-in-out',
          // Mobile: oculto por padrão, desliza com isOpen
          isOpen ? 'translate-x-0' : '-translate-x-full',
          // Desktop: sempre visível
          'lg:translate-x-0'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-brand-700">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-white/20 flex items-center justify-center flex-shrink-0">
              <ShoppingBag className="w-5 h-5 text-white" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-sm leading-none">Price Comparator</p>
              <p className="text-xs text-blue-200 mt-0.5">Comparação de Preços</p>
            </div>
          </div>
          {/* Botão fechar no mobile */}
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded hover:bg-white/10 text-blue-200"
            aria-label="Fechar menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-4 px-3">
          <p className="text-xs text-blue-300 uppercase tracking-wider px-3 mb-2">Menu</p>
          {navItems.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium mb-1 transition-colors',
                pathname === href
                  ? 'bg-white/20 text-white'
                  : 'text-blue-100 hover:bg-white/10 hover:text-white'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </Link>
          ))}

          {isAdmin && (
            <>
              <p className="text-xs text-blue-300 uppercase tracking-wider px-3 mt-4 mb-2">Admin</p>
              {adminItems.map(({ href, label, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  onClick={onClose}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium mb-1 transition-colors',
                    pathname === href
                      ? 'bg-white/20 text-white'
                      : 'text-blue-100 hover:bg-white/10 hover:text-white'
                  )}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {label}
                </Link>
              ))}
            </>
          )}
        </nav>

        {/* User section */}
        <div className="border-t border-brand-700 p-4">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold flex-shrink-0">
              {user?.name?.charAt(0)?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name}</p>
              <p className="text-xs text-blue-200 truncate">
                {user?.role === 'admin' ? 'Administrador' : 'Usuário'}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-blue-100 hover:bg-white/10 hover:text-white transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </aside>
    </>
  )
}
