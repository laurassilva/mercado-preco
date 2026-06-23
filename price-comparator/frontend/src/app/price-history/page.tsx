'use client'
import { useState, useCallback, useEffect } from 'react'
import { Search, TrendingDown, TrendingUp, Award, BarChart3, Download } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import { formatBRL, formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { PriceHistorySearchResponse, Market, Category } from '@/types'

const PERIODS = ['7d', '15d', '30d', '60d', '90d'] as const
const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2', '#e11d48', '#4f46e5']

export default function PriceHistoryPage() {
  const [query, setQuery] = useState('')
  const [period, setPeriod] = useState('30d')
  const [marketId, setMarketId] = useState('')
  const [category, setCategory] = useState('')
  const [data, setData] = useState<PriceHistorySearchResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [markets, setMarkets] = useState<Market[]>([])
  const [categories, setCategories] = useState<Category[]>([])

  useEffect(() => {
    api.get<Market[]>('/markets/').then(({ data }) => setMarkets(data)).catch(() => {})
    api.get<Category[]>('/categories/').then(({ data }) => setCategories(data)).catch(() => {})
  }, [])

  const handleSearch = useCallback(async () => {
    if (!query.trim() || query.trim().length < 2) return
    setLoading(true)
    try {
      const params: Record<string, string> = { q: query, period }
      if (marketId) params.market_id = marketId
      if (category) params.category = category
      const { data } = await api.get<PriceHistorySearchResponse>('/price-history/search', { params })
      setData(data)
    } catch { setData(null) }
    finally { setLoading(false) }
  }, [query, period, marketId, category])

  const handleExport = async (format: 'pdf' | 'excel') => {
    if (!query.trim()) return
    try {
      const params: Record<string, string> = { q: query, period }
      if (marketId) params.market_id = marketId
      if (category) params.category = category
      const ext = format === 'excel' ? 'xlsx' : 'pdf'
      const resp = await api.get(`/price-history/export/${format}`, { params, responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `historico_${query.replace(/ /g, '_')}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  // Build chart data: each data point is a date with prices from each market
  const chartData = (() => {
    if (!data?.products.length) return []
    const dateMap = new Map<string, Record<string, number>>()
    for (const product of data.products) {
      for (const entry of product.history) {
        const dateKey = new Date(entry.checked_at).toLocaleDateString('pt-BR')
        if (!dateMap.has(dateKey)) dateMap.set(dateKey, {})
        dateMap.get(dateKey)![product.market_name] = entry.price
      }
    }
    return Array.from(dateMap.entries())
      .sort((a, b) => {
        const [da, ma, ya] = a[0].split('/').map(Number)
        const [db, mb, yb] = b[0].split('/').map(Number)
        return (ya * 10000 + ma * 100 + da) - (yb * 10000 + mb * 100 + db)
      })
      .map(([date, prices]) => ({ date, ...prices }))
  })()

  const marketNames = data ? [...new Set(data.products.map(p => p.market_name))] : []

  return (
    <AuthGuard title="Histórico de Preços">
      <div className="space-y-4">
        {/* Search bar */}
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Consultar Histórico</h2>
          <div className="flex gap-2 mb-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
              <input
                type="text" value={query} onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="Ex: Coca-Cola 2L, Arroz 5kg..."
                className="input pl-10 py-3"
              />
            </div>
            <button onClick={handleSearch} disabled={loading || query.trim().length < 2} className="btn-primary px-6">
              {loading ? 'Buscando...' : 'Buscar'}
            </button>
          </div>

          {/* Period + filters */}
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-gray-500">Período:</span>
            {PERIODS.map(p => (
              <button key={p} onClick={() => { setPeriod(p); if (data) setTimeout(handleSearch, 0) }}
                className={cn('px-3 py-1 rounded-full text-sm font-medium transition-colors',
                  period === p ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                )}>
                {p.replace('d', ' dias')}
              </button>
            ))}
            <select value={marketId} onChange={e => setMarketId(e.target.value)} className="input py-1.5 text-sm w-auto ml-auto">
              <option value="">Todos mercados</option>
              {markets.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input py-1.5 text-sm w-auto">
              <option value="">Todas categorias</option>
              {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          </div>
        </div>

        {data && (
          <>
            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="bg-green-50 border border-green-200 rounded-xl p-3">
                <div className="flex items-center gap-1.5 text-green-700 text-xs font-medium mb-1">
                  <TrendingDown className="w-3 h-3" /> Menor Preço
                </div>
                <p className="font-bold text-green-800">{data.stats.min_price != null ? formatBRL(data.stats.min_price) : '-'}</p>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-xl p-3">
                <div className="flex items-center gap-1.5 text-red-700 text-xs font-medium mb-1">
                  <TrendingUp className="w-3 h-3" /> Maior Preço
                </div>
                <p className="font-bold text-red-800">{data.stats.max_price != null ? formatBRL(data.stats.max_price) : '-'}</p>
              </div>
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
                <div className="flex items-center gap-1.5 text-blue-700 text-xs font-medium mb-1">
                  <Award className="w-3 h-3" /> Preço Médio
                </div>
                <p className="font-bold text-blue-800">{data.stats.avg_price != null ? formatBRL(data.stats.avg_price) : '-'}</p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-xl p-3">
                <div className="flex items-center gap-1.5 text-purple-700 text-xs font-medium mb-1">
                  <BarChart3 className="w-3 h-3" /> Variações
                </div>
                <p className="font-bold text-purple-800">{data.stats.total_changes}</p>
                <p className="text-xs text-purple-500">{data.products.length} produto(s)</p>
              </div>
            </div>

            {/* Export + info */}
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Período: <span className="font-medium">{data.period_days} dias</span> · {data.products.length} produto(s)
              </p>
              <div className="flex gap-2">
                <button onClick={() => handleExport('pdf')} className="btn-secondary text-xs py-1.5 px-3">
                  <Download className="w-3 h-3 inline mr-1" />PDF
                </button>
                <button onClick={() => handleExport('excel')} className="btn-secondary text-xs py-1.5 px-3">
                  <Download className="w-3 h-3 inline mr-1" />Excel
                </button>
              </div>
            </div>

            {/* Chart */}
            {chartData.length > 1 && (
              <div className="card">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Evolução de Preços</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `R$${v}`} />
                    <Tooltip formatter={(value: number) => formatBRL(value)} />
                    <Legend />
                    {marketNames.map((name, i) => (
                      <Line key={name} type="monotone" dataKey={name} stroke={COLORS[i % COLORS.length]}
                        strokeWidth={2} dot={{ r: 3 }} connectNulls />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Timeline table */}
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Mercado</th>
                    <th>Produto</th>
                    <th>Categoria</th>
                    <th>Data</th>
                    <th>Preço</th>
                  </tr>
                </thead>
                <tbody>
                  {data.products.flatMap(p =>
                    p.history.map((h, i) => (
                      <tr key={`${p.product_id}-${i}`}>
                        <td className="text-gray-600 text-sm">{p.market_name}</td>
                        <td className="font-medium text-gray-800">{p.product_name}</td>
                        <td className="text-gray-500 text-xs">{p.category || '-'}</td>
                        <td className="text-gray-500 text-xs whitespace-nowrap">{formatDate(h.checked_at)}</td>
                        <td className="font-medium">{formatBRL(h.price)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {!data && !loading && (
          <div className="card text-center py-12">
            <BarChart3 className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p className="text-lg font-semibold text-gray-700">Consulte o histórico de preços</p>
            <p className="text-sm text-gray-400 mt-1">Pesquise um produto para ver a evolução dos preços ao longo do tempo</p>
          </div>
        )}
      </div>
    </AuthGuard>
  )
}
