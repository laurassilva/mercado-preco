'use client'
import { useState, useCallback } from 'react'
import api from '@/services/api'
import type { SearchResponse } from '@/types'

export function useSearch() {
  const [results, setResults] = useState<SearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = useCallback(async (query: string, marketIds?: string[], live = false) => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = { q: query, live: String(live) }
      if (marketIds && marketIds.length > 0) params.market_ids = marketIds.join(',')
      const { data } = await api.get<SearchResponse>('/products/search', { params })
      setResults(data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg || 'Erro ao buscar produtos')
    } finally {
      setLoading(false)
    }
  }, [])

  const clear = useCallback(() => {
    setResults(null)
    setError(null)
  }, [])

  return { results, loading, error, search, clear }
}
