'use client'
import { useEffect, useState } from 'react'
import { RefreshCw, Search, Clock } from 'lucide-react'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { SearchHistory } from '@/types'
import { formatDate } from '@/lib/utils'
import { useRouter } from 'next/navigation'

export default function HistoryPage() {
  const router = useRouter()
  const [history, setHistory] = useState<SearchHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  const load = () => {
    setLoading(true)
    api.get<SearchHistory[]>('/history/?limit=200').then(({ data }) => setHistory(data)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const filtered = history.filter(
    (h) =>
      !filter ||
      h.query.toLowerCase().includes(filter.toLowerCase()) ||
      (h.user_name ?? '').toLowerCase().includes(filter.toLowerCase())
  )

  return (
    <AuthGuard title="Histórico de Pesquisas">
      <div className="space-y-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              className="input pl-9"
              placeholder="Filtrar pesquisas..."
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
          </div>
          <button onClick={load} className="btn-secondary flex-shrink-0">
            <RefreshCw className="w-4 h-4" /> Atualizar
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="card text-center py-12">
            <Clock className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Nenhuma pesquisa encontrada</p>
          </div>
        ) : (
          <>
            {/* Mobile: cards */}
            <div className="md:hidden space-y-2">
              {filtered.map((h) => (
                <div key={h.id} className="card flex items-center justify-between gap-3 py-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{h.query}</p>
                    <p className="text-xs text-gray-400">{h.user_name ?? 'Sistema'} · {formatDate(h.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="badge-blue">{h.results_count}</span>
                    <button
                      onClick={() => router.push(`/search?q=${encodeURIComponent(h.query)}`)}
                      className="text-brand-600 p-1.5 rounded hover:bg-brand-50"
                      title="Pesquisar novamente"
                    >
                      <Search className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop: tabela */}
            <div className="hidden md:block table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Produto Pesquisado</th>
                    <th>Usuário</th>
                    <th>Resultados</th>
                    <th>Data / Hora</th>
                    <th>Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((h) => (
                    <tr key={h.id}>
                      <td className="font-medium text-gray-800">{h.query}</td>
                      <td className="text-gray-600">{h.user_name ?? 'Sistema'}</td>
                      <td><span className="badge-blue">{h.results_count}</span></td>
                      <td className="text-gray-500 text-xs whitespace-nowrap">{formatDate(h.created_at)}</td>
                      <td>
                        <button
                          onClick={() => router.push(`/search?q=${encodeURIComponent(h.query)}`)}
                          className="text-brand-600 hover:underline text-xs flex items-center gap-1 whitespace-nowrap"
                        >
                          <Search className="w-3 h-3" /> Pesquisar novamente
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </AuthGuard>
  )
}
