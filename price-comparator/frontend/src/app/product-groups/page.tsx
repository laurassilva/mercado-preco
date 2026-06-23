'use client'
import { useEffect, useState, useCallback } from 'react'
import { Layers, Search, RefreshCw, BarChart3, X } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import { formatBRL } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { ProductGroupSummary, ProductGroupPrices, GroupingStats, Category } from '@/types'

export default function ProductGroupsPage() {
  const [groups, setGroups] = useState<ProductGroupSummary[]>([])
  const [stats, setStats] = useState<GroupingStats | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [regrouping, setRegrouping] = useState(false)
  const [selectedGroup, setSelectedGroup] = useState<ProductGroupPrices | null>(null)

  useEffect(() => {
    api.get('/product-groups/stats').then(({ data }) => setStats(data)).catch(() => {})
    api.get<Category[]>('/categories/').then(({ data }) => setCategories(data)).catch(() => {})
  }, [])

  const fetchGroups = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { limit: '100' }
      if (query.trim().length >= 2) params.q = query
      if (category) params.category = category
      const { data } = await api.get<ProductGroupSummary[]>('/product-groups/', { params })
      setGroups(data)
    } catch { setGroups([]) }
    finally { setLoading(false) }
  }, [query, category])

  useEffect(() => { fetchGroups() }, [fetchGroups])

  const handleRegroup = async () => {
    setRegrouping(true)
    try {
      const { data } = await api.post('/product-groups/regroup')
      toast.success(data.message)
      fetchGroups()
      api.get('/product-groups/stats').then(({ data }) => setStats(data)).catch(() => {})
    } catch { toast.error('Erro ao reagrupar') }
    finally { setRegrouping(false) }
  }

  const openGroupPrices = async (groupId: string) => {
    try {
      const { data } = await api.get<ProductGroupPrices>(`/product-groups/${groupId}/prices`)
      setSelectedGroup(data)
    } catch { toast.error('Erro ao carregar preços') }
  }

  return (
    <AuthGuard title="Produtos Mestre">
      <div className="space-y-4">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
              <p className="text-xs text-blue-600 font-medium">Grupos Criados</p>
              <p className="font-bold text-blue-800 text-xl">{stats.total_groups.toLocaleString()}</p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-xl p-3">
              <p className="text-xs text-green-600 font-medium">Produtos Agrupados</p>
              <p className="font-bold text-green-800 text-xl">{stats.total_grouped.toLocaleString()}</p>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-xl p-3">
              <p className="text-xs text-purple-600 font-medium">Comparáveis (2+ mercados)</p>
              <p className="font-bold text-purple-800 text-xl">{stats.multi_market_groups.toLocaleString()}</p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <p className="text-xs text-amber-600 font-medium">Sem Grupo</p>
              <p className="font-bold text-amber-800 text-xl">{stats.total_ungrouped.toLocaleString()}</p>
            </div>
          </div>
        )}

        {/* Search + filters */}
        <div className="card">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input type="text" value={query} onChange={e => setQuery(e.target.value)}
                placeholder="Buscar produto mestre..." className="input pl-10 py-2" />
            </div>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input py-2 text-sm w-auto">
              <option value="">Todas categorias</option>
              {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
            <button onClick={handleRegroup} disabled={regrouping} className="btn-secondary px-4 whitespace-nowrap">
              <RefreshCw className={cn("w-4 h-4 inline mr-1", regrouping && "animate-spin")} />
              {regrouping ? 'Reagrupando...' : 'Reagrupar Tudo'}
            </button>
          </div>
        </div>

        {/* Groups table */}
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Marca</th>
                <th>Qtd</th>
                <th>Categoria</th>
                <th>Mercados</th>
                <th>Menor</th>
                <th>Maior</th>
                <th>Média</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">Carregando...</td></tr>
              ) : groups.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">
                  <Layers className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  Nenhum grupo encontrado. Clique em "Reagrupar Tudo" para criar.
                </td></tr>
              ) : groups.map(g => (
                <tr key={g.id} className="cursor-pointer hover:bg-blue-50/50 transition-colors" onClick={() => openGroupPrices(g.id)}>
                  <td className="font-medium text-brand-700">{g.canonical_name}</td>
                  <td className="text-gray-500 text-sm">{g.brand || '-'}</td>
                  <td className="text-gray-500 text-sm">{g.quantity || '-'}</td>
                  <td className="text-gray-500 text-xs">{g.category || '-'}</td>
                  <td>
                    <span className={cn(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      g.market_count >= 3 ? 'bg-green-100 text-green-700' :
                      g.market_count >= 2 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                    )}>
                      {g.market_count}
                    </span>
                  </td>
                  <td className="font-bold text-green-700">{g.min_price != null ? formatBRL(g.min_price) : '-'}</td>
                  <td className="text-red-600">{g.max_price != null ? formatBRL(g.max_price) : '-'}</td>
                  <td className="text-gray-700">{g.avg_price != null ? formatBRL(g.avg_price) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Group prices modal */}
        {selectedGroup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setSelectedGroup(null)}>
            <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between p-5 border-b">
                <div>
                  <h3 className="font-bold text-gray-900">Comparação de Preços</h3>
                  <p className="text-sm text-gray-500">{selectedGroup.products.length} mercado(s)</p>
                </div>
                <button onClick={() => setSelectedGroup(null)} className="p-1.5 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              <div className="p-5 space-y-2">
                {selectedGroup.products.map((p, i) => (
                  <div key={p.id} className={cn(
                    'flex items-center justify-between p-3 rounded-lg border',
                    i === 0 ? 'bg-green-50 border-green-200' : 'border-gray-100'
                  )}>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 text-sm">{p.market_name}</p>
                      <p className="text-xs text-gray-500 truncate">{p.product_name}</p>
                    </div>
                    <div className="text-right ml-3">
                      <p className={cn('font-bold', i === 0 ? 'text-green-700' : 'text-gray-800')}>
                        {p.price != null ? formatBRL(p.price) : '-'}
                      </p>
                      {i === 0 && <span className="text-xs text-green-600">Mais barato</span>}
                      {i > 0 && p.price != null && selectedGroup.products[0].price != null && (
                        <span className="text-xs text-red-500">
                          +{formatBRL(p.price - selectedGroup.products[0].price)}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  )
}
