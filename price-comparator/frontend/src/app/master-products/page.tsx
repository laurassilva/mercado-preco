'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { Layers, Search, RefreshCw, X, ClipboardList, Upload, Barcode } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import { formatBRL } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { MasterProductSummary, MasterProductOffers, MasterProductStats, Category } from '@/types'

export default function MasterProductsPage() {
  const [products, setProducts] = useState<MasterProductSummary[]>([])
  const [stats, setStats] = useState<MasterProductStats | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(false)
  const [reprocessing, setReprocessing] = useState(false)
  const [selected, setSelected] = useState<MasterProductOffers | null>(null)

  const fetchStats = useCallback(() => {
    api.get<MasterProductStats>('/master-products/stats').then(({ data }) => setStats(data)).catch(() => {})
  }, [])

  useEffect(() => {
    fetchStats()
    api.get<Category[]>('/categories/').then(({ data }) => setCategories(data)).catch(() => {})
  }, [fetchStats])

  const fetchProducts = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { limit: '100' }
      if (query.trim().length >= 2) params.q = query
      if (category) params.category = category
      const { data } = await api.get<MasterProductSummary[]>('/master-products/', { params })
      setProducts(data)
    } catch { setProducts([]) }
    finally { setLoading(false) }
  }, [query, category])

  useEffect(() => { fetchProducts() }, [fetchProducts])

  const handleReprocess = async () => {
    setReprocessing(true)
    try {
      const { data } = await api.post('/master-products/reprocess-unmatched')
      toast.success(data.message)
      fetchProducts()
      fetchStats()
    } catch { toast.error('Erro ao reprocessar') }
    finally { setReprocessing(false) }
  }

  const openOffers = async (id: string) => {
    try {
      const { data } = await api.get<MasterProductOffers>(`/master-products/${id}/offers`)
      setSelected(data)
    } catch { toast.error('Erro ao carregar ofertas') }
  }

  return (
    <AuthGuard title="Catálogo Mestre de Produtos">
      <div className="space-y-4">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
              <p className="text-xs text-blue-600 font-medium">Produtos Mestre</p>
              <p className="font-bold text-blue-800 text-xl">{stats.total_master_products.toLocaleString()}</p>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-xl p-3">
              <p className="text-xs text-green-600 font-medium">Vinculados</p>
              <p className="font-bold text-green-800 text-xl">{stats.matched_count.toLocaleString()}</p>
            </div>
            <div className="bg-purple-50 border border-purple-200 rounded-xl p-3">
              <p className="text-xs text-purple-600 font-medium">Comparáveis (2+ mercados)</p>
              <p className="font-bold text-purple-800 text-xl">{stats.multi_market_products.toLocaleString()}</p>
            </div>
            <Link href="/master-products/reviews" className="bg-amber-50 border border-amber-200 rounded-xl p-3 hover:bg-amber-100 transition-colors">
              <p className="text-xs text-amber-600 font-medium">Pendentes de Revisão</p>
              <p className="font-bold text-amber-800 text-xl">{stats.pending_review_count.toLocaleString()}</p>
            </Link>
            <div className="bg-gray-50 border border-gray-200 rounded-xl p-3">
              <p className="text-xs text-gray-600 font-medium">Sem Vínculo</p>
              <p className="font-bold text-gray-800 text-xl">{stats.unmatched_count.toLocaleString()}</p>
            </div>
          </div>
        )}

        {/* Search + filters */}
        <div className="card">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input type="text" value={query} onChange={e => setQuery(e.target.value)}
                placeholder="Buscar por nome, marca ou GTIN..." className="input pl-10 py-2" />
            </div>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input py-2 text-sm w-auto">
              <option value="">Todas categorias</option>
              {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
            <Link href="/master-products/import" className="btn-secondary px-4 whitespace-nowrap flex items-center">
              <Upload className="w-4 h-4 inline mr-1" /> Importar GTIN
            </Link>
            <button onClick={handleReprocess} disabled={reprocessing} className="btn-secondary px-4 whitespace-nowrap">
              <RefreshCw className={cn("w-4 h-4 inline mr-1", reprocessing && "animate-spin")} />
              {reprocessing ? 'Reprocessando...' : 'Reprocessar Não Vinculados'}
            </button>
          </div>
        </div>

        {/* Products table */}
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>GTIN</th>
                <th>Marca</th>
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
              ) : products.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">
                  <Layers className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  Nenhum produto mestre encontrado.
                </td></tr>
              ) : products.map(p => (
                <tr key={p.id} className="cursor-pointer hover:bg-blue-50/50 transition-colors" onClick={() => openOffers(p.id)}>
                  <td className="font-medium text-brand-700">{p.canonical_name}</td>
                  <td className="text-gray-500 text-xs font-mono">
                    {p.gtin ? (
                      <span className="inline-flex items-center gap-1"><Barcode className="w-3.5 h-3.5" />{p.gtin}</span>
                    ) : (
                      <span className="text-amber-600">sem GTIN</span>
                    )}
                  </td>
                  <td className="text-gray-500 text-sm">{p.brand || '-'}</td>
                  <td className="text-gray-500 text-xs">{p.category || '-'}</td>
                  <td>
                    <span className={cn(
                      'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                      p.market_count >= 3 ? 'bg-green-100 text-green-700' :
                      p.market_count >= 2 ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                    )}>
                      {p.market_count}
                    </span>
                  </td>
                  <td className="font-bold text-green-700">{p.min_price != null ? formatBRL(p.min_price) : '-'}</td>
                  <td className="text-red-600">{p.max_price != null ? formatBRL(p.max_price) : '-'}</td>
                  <td className="text-gray-700">{p.avg_price != null ? formatBRL(p.avg_price) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Offers modal — estilo Booking.com */}
        {selected && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setSelected(null)}>
            <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
              <div className="flex items-start justify-between p-5 border-b">
                <div>
                  <h3 className="font-bold text-gray-900">{selected.canonical_name}</h3>
                  <p className="text-sm text-gray-500">
                    {selected.gtin ? `GTIN ${selected.gtin} · ` : ''}{selected.offers.length} mercado(s)
                  </p>
                </div>
                <button onClick={() => setSelected(null)} className="p-1.5 hover:bg-gray-100 rounded-lg">
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              <div className="p-5 space-y-2">
                {selected.offers.map((o) => (
                  <div key={o.market_product_id} className={cn(
                    'flex items-center justify-between p-3 rounded-lg border',
                    o.is_cheapest ? 'bg-green-50 border-green-200' : 'border-gray-100'
                  )}>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-800 text-sm">{o.market_name}</p>
                      <p className="text-xs text-gray-500 truncate">{o.product_name}</p>
                    </div>
                    <div className="text-right ml-3">
                      <p className={cn('font-bold', o.is_cheapest ? 'text-green-700' : 'text-gray-800')}>
                        {o.price != null ? formatBRL(o.price) : '-'}
                      </p>
                      {o.is_cheapest && <span className="text-xs text-green-600">Mais barato</span>}
                      {!o.is_cheapest && o.difference != null && (
                        <span className="text-xs text-red-500">+{formatBRL(o.difference)} ({o.difference_pct}%)</span>
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
