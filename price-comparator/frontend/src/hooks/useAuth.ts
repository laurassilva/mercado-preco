'use client'
import { useState, useEffect } from 'react'
import { getStoredUser, isAuthenticated } from '@/services/auth'
import type { User } from '@/types'

export function useAuth() {
  const [user, setUser] = useState<Partial<User> | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isAuthenticated()) {
      setUser(getStoredUser())
    }
    setLoading(false)
  }, [])

  const isAdmin = user?.role === 'admin'
  const isGestor = user?.role === 'gestor'

  return { user, loading, isAdmin, isGestor }
}
