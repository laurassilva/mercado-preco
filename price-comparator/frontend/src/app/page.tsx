'use client'
import { useEffect, useState } from 'react'
import { Package, ShoppingCart, Search, Clock, TrendingDown, TrendingUp, Bell, Tag } from 'lucide-react'
import AuthGuard from '@/components/layout/AuthGuard'
import StatsCard from '@/components/dashboard/StatsCard'
import PriceChart from '@/components/dashboard/PriceChart'
import api from '@/services/api'
import type { DashboardData } from '@/types'
import { formatDate, formatBRL } from '@/lib/utils'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [alertsSummary, setAlertsSummary] = useState<any>(null)
  const [categoryStats, setCategoryStats] = useState<any[]>([])

  useEffect(() => {
    api.get<DashboardData>('/dashboard/')
      .then(({ data }) => setData(data))
      .finally(() => setLoading(false))
    api.get('/alerts/summary').then(({ data }) => setAlertsSummary(data)).catch(() => {})
    api.get('/categories/stats').then(({ data }) => setCategoryStats(data)).catch(() => {})
  }, [])

  return (
    <AuthGuard title="Dashboard">
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <StatsCard
              title="Produtos Monitorados"
              value={data?.stats.total_products_monitored ?? 0}
              icon={Package}
              color="blue"
              subtitle="em todos os mercados"
            />
            <StatsCard
              title="Mercados Ativos"
              value={data?.stats.total_markets ?? 0}
              icon={ShoppingCart}
              color="green"
            />
            <StatsCard
              title="Pesquisas Hoje"
              value={data?.stats.total_searches_today ?? 0}
              icon={Search}
              color="purple"
            />
            <StatsCard
              title="Última Atualização"
              value={data?.stats.last_update ? formatDate(data.stats.last_update) : 'N/A'}
              icon={Clock}
              color="yellow"
            />
          </div>

          {/* Best/Worst market */}
          {(data?.stats.cheapest_market || data?.stats.most_expensive_market) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {data?.stats.cheapest_market && (
                <div className="card flex items-center gap-4 border-l-4 border-green-500">
                  <TrendingDown className="w-8 h-8 text-green-600 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-gray-500">Mercado com Menor Preço Médio</p>
                    <p className="text-xl font-bold text-green-700">{data.stats.cheapest_market}</p>
                  </div>
                </div>
              )}
              {data?.stats.most_expensive_market && (
                <div className="card flex items-center gap-4 border-l-4 border-red-400">
                  <TrendingUp className="w-8 h-8 text-red-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm text-gray-500">Mercado com Maior Preço Médio</p>
                    <p className="text-xl font-bold text-red-600">{data.stats.most_expensive_market}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Chart */}
            <div className="card xl:col-span-2">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Preço Médio por Mercado</h2>
              <PriceChart data={data?.market_summary ?? []} />
            </div>

            {/* Recent searches */}
            <div className="card">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Pesquisas Recentes</h2>
              {data?.recent_searches.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-6">Nenhuma pesquisa realizada</p>
              ) : (
                <div className="space-y-3">
                  {data?.recent_searches.map((s, i) => (
                    <div key={i} className="flex items-start justify-between gap-2 py-2 border-b border-gray-50 last:border-0">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{s.query}</p>
                        <p className="text-xs text-gray-400">{s.user_name} · {formatDate(s.created_at)}</p>
                      </div>
                      <span className="badge-blue flex-shrink-0">{s.results_count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Market summary table */}
          {(data?.market_summary?.length ?? 0) > 0 && (
            <div className="card">
              <h2 className="text-base font-semibold text-gray-800 mb-4">Resumo por Mercado</h2>
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Mercado</th>
                      <th>Preço Médio</th>
                      <th>Produtos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.market_summary.map((m, i) => (
                      <tr key={i}>
                        <td className="text-gray-400 text-xs">{i + 1}</td>
                        <td className="font-medium">{m.market_name}</td>
                        <td className={i === 0 ? 'text-green-700 font-bold' : 'text-gray-800'}>{formatBRL(m.avg_price)}</td>
                        <td className="text-gray-500">{m.products_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Alerts Summary */}
          {alertsSummary && alertsSummary.total_today > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Bell className="w-4 h-4" /> Alertas de Preço Hoje
              </h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-700">{alertsSummary.total_today}</p>
                  <p className="text-xs text-blue-500">Total</p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-2xl font-bold text-red-700">{alertsSummary.increases_today}</p>
                  <p className="text-xs text-red-500">Aumentos</p>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-2xl font-bold text-green-700">{alertsSummary.decreases_today}</p>
                  <p className="text-xs text-green-500">Reduções</p>
                </div>
              </div>
            </div>
          )}

          {/* Category Stats */}
          {categoryStats.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4" /> Produtos por Categoria
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {categoryStats.map((cs: any) => (
                  <div key={cs.category} className="p-3 border border-gray-100 rounded-lg">
                    <p className="font-medium text-gray-800 text-sm">{cs.category}</p>
                    <p className="text-xs text-gray-500">{cs.products_count} produtos</p>
                    {cs.alerts_today > 0 && <p className="text-xs text-amber-600">{cs.alerts_today} alertas hoje</p>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </AuthGuard>
  )
}
