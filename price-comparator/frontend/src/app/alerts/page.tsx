'use client'
import { useEffect, useState, useCallback } from 'react'
import { Bell, TrendingDown, TrendingUp, ArrowUpDown, Filter } from 'lucide-react'
import AuthGuard from '@/components/layout/AuthGuard'
import StatsCard from '@/components/dashboard/StatsCard'
import api from '@/services/api'
import { formatBRL, formatDate } from '@/lib/utils'
import { cn } from '@/lib/utils'
import type { PriceAlert, AlertsSummary, Market, Category } from '@/types'

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<PriceAlert[]>([])
  const [summary, setSummary] = useState<AlertsSummary | null>(null)
  const [markets, setMarkets] = useState<Market[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [marketId, setMarketId] = useState('')
  const [alertType, setAlertType] = useState('')
  const [category, setCategory] = useState('')
  const [period, setPeriod] = useState('7d')

  useEffect(() => {
    api.get<Market[]>('/markets/').then(({ data }) => setMarkets(data)).catch(() => {})
    api.get<Category[]>('/categories/').then(({ data }) => setCategories(data)).catch(() => {})
    api.get<AlertsSummary>('/alerts/summary').then(({ data }) => setSummary(data)).catch(() => {})
  }, [])

  const fetchAlerts = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { period, limit: '100' }
      if (marketId) params.market_id = marketId
      if (alertType) params.alert_type = alertType
      if (category) params.category = category
      const { data } = await api.get<PriceAlert[]>('/alerts/', { params })
      setAlerts(data)
    } catch { setAlerts([]) }
    finally { setLoading(false) }
  }, [marketId, alertType, category, period])

  useEffect(() => { fetchAlerts() }, [fetchAlerts])

  return (
    <AuthGuard title="Alertas de Preços">
      <div className="space-y-4">
        {/* Summary cards */}
        {summary && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <StatsCard title="Total Hoje" value={String(summary.total_today)} icon={Bell} color="blue" />
            <StatsCard title="Aumentos" value={String(summary.increases_today)} icon={TrendingUp} color="red" />
            <StatsCard title="Reduções" value={String(summary.decreases_today)} icon={TrendingDown} color="green" />
            <div className="bg-red-50 border border-red-200 rounded-xl p-3">
              <p className="text-xs text-red-600 font-medium">Maior Aumento</p>
              {summary.biggest_increase ? (
                <>
                  <p className="font-bold text-red-800 text-sm truncate">{summary.biggest_increase.product_name}</p>
                  <p className="text-xs text-red-500">+{summary.biggest_increase.price_diff_pct.toFixed(1)}% · {summary.biggest_increase.market_name}</p>
                </>
              ) : <p className="text-sm text-gray-400">Nenhum</p>}
            </div>
            <div className="bg-green-50 border border-green-200 rounded-xl p-3">
              <p className="text-xs text-green-600 font-medium">Maior Queda</p>
              {summary.biggest_decrease ? (
                <>
                  <p className="font-bold text-green-800 text-sm truncate">{summary.biggest_decrease.product_name}</p>
                  <p className="text-xs text-green-500">{summary.biggest_decrease.price_diff_pct.toFixed(1)}% · {summary.biggest_decrease.market_name}</p>
                </>
              ) : <p className="text-sm text-gray-400">Nenhum</p>}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="card">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-sm text-gray-600"><Filter className="w-4 h-4" /> Filtros:</div>
            <select value={period} onChange={e => setPeriod(e.target.value)} className="input py-1.5 text-sm w-auto">
              <option value="1d">Hoje</option>
              <option value="7d">7 dias</option>
              <option value="15d">15 dias</option>
              <option value="30d">30 dias</option>
              <option value="60d">60 dias</option>
              <option value="90d">90 dias</option>
            </select>
            <select value={alertType} onChange={e => setAlertType(e.target.value)} className="input py-1.5 text-sm w-auto">
              <option value="">Todos os tipos</option>
              <option value="decrease">Reduções</option>
              <option value="increase">Aumentos</option>
            </select>
            <select value={marketId} onChange={e => setMarketId(e.target.value)} className="input py-1.5 text-sm w-auto">
              <option value="">Todos os mercados</option>
              {markets.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <select value={category} onChange={e => setCategory(e.target.value)} className="input py-1.5 text-sm w-auto">
              <option value="">Todas categorias</option>
              {categories.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
            </select>
          </div>
        </div>

        {/* Results info */}
        <p className="text-sm text-gray-500">{alerts.length} alerta(s) encontrado(s)</p>

        {/* Mobile cards */}
        <div className="md:hidden space-y-3">
          {loading ? (
            <div className="text-center py-12 text-gray-400">Carregando...</div>
          ) : alerts.length === 0 ? (
            <div className="card text-center py-12">
              <Bell className="w-10 h-10 mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500">Nenhum alerta encontrado</p>
            </div>
          ) : alerts.map((a) => (
            <div key={a.id} className={cn('rounded-xl border p-4', a.alert_type === 'decrease' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200')}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-gray-900 text-sm">{a.product_name}</p>
                  <p className="text-xs text-gray-500">{a.market_name} {a.category && `· ${a.category}`}</p>
                </div>
                <span className={cn('text-sm font-bold', a.alert_type === 'decrease' ? 'text-green-700' : 'text-red-700')}>
                  {a.alert_type === 'decrease' ? '↓' : '↑'} {a.price_diff_pct.toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center gap-3 mt-2 text-xs text-gray-600">
                <span>De: {formatBRL(a.old_price)}</span>
                <span>→</span>
                <span className="font-medium">Para: {formatBRL(a.new_price)}</span>
                <span className="ml-auto">{formatDate(a.detected_at)}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Desktop table */}
        <div className="hidden md:block table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Produto</th>
                <th>Mercado</th>
                <th>Categoria</th>
                <th>Preço Anterior</th>
                <th>Novo Preço</th>
                <th>Diferença</th>
                <th>%</th>
                <th>Data</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">Carregando...</td></tr>
              ) : alerts.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-8 text-gray-400">Nenhum alerta encontrado</td></tr>
              ) : alerts.map((a) => (
                <tr key={a.id} className={a.alert_type === 'decrease' ? 'bg-green-50/50' : ''}>
                  <td className="font-medium text-gray-800">{a.product_name}</td>
                  <td className="text-gray-600 text-sm">{a.market_name}</td>
                  <td className="text-gray-500 text-xs">{a.category || '-'}</td>
                  <td className="text-gray-500">{formatBRL(a.old_price)}</td>
                  <td className="font-medium">{formatBRL(a.new_price)}</td>
                  <td>
                    <span className={cn('font-medium', a.alert_type === 'decrease' ? 'text-green-600' : 'text-red-600')}>
                      {a.alert_type === 'decrease' ? '' : '+'}{formatBRL(a.price_diff)}
                    </span>
                  </td>
                  <td>
                    <span className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                      a.alert_type === 'decrease' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    )}>
                      {a.alert_type === 'decrease' ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
                      {a.price_diff_pct.toFixed(1)}%
                    </span>
                  </td>
                  <td className="text-gray-500 text-xs whitespace-nowrap">{formatDate(a.detected_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AuthGuard>
  )
}
