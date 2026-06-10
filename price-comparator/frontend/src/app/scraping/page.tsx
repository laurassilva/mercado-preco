'use client'
import { useEffect, useState } from 'react'
import { Play, RefreshCw, CheckCircle, XCircle, Clock, Loader, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { ScrapingJob, Market } from '@/types'
import { formatDate } from '@/lib/utils'

const statusConfig: Record<string, { label: string; icon: typeof CheckCircle; className: string }> = {
  pending:   { label: 'Pendente',    icon: Clock,       className: 'badge-yellow' },
  running:   { label: 'Executando',  icon: Loader,      className: 'badge-blue' },
  completed: { label: 'Concluído',   icon: CheckCircle, className: 'badge-green' },
  failed:    { label: 'Falhou',      icon: XCircle,     className: 'badge-red' },
}

export default function ScrapingPage() {
  const [jobs, setJobs]       = useState<ScrapingJob[]>([])
  const [markets, setMarkets] = useState<Market[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery]     = useState('')
  const [triggering, setTriggering] = useState(false)
  const [crawling, setCrawling]     = useState(false)

  const loadJobs = () => {
    setLoading(true)
    api.get<ScrapingJob[]>('/scraping/jobs?limit=100')
      .then(({ data }) => setJobs(data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadJobs()
    api.get<Market[]>('/markets/').then(({ data }) => setMarkets(data)).catch(() => {})
    const t = setInterval(loadJobs, 6000)
    return () => clearInterval(t)
  }, [])

  const handleTrigger = async () => {
    if (!query.trim()) { toast.error('Digite um produto'); return }
    setTriggering(true)
    try {
      await api.post('/scraping/trigger', { query })
      toast.success('Coleta por busca iniciada!')
      setQuery('')
      setTimeout(loadJobs, 1500)
    } catch { toast.error('Erro ao iniciar coleta') }
    finally { setTriggering(false) }
  }

  const handleCrawlAll = async () => {
    if (!confirm('Isso vai varrer TODOS os produtos de todos os mercados. Pode levar vários minutos. Confirmar?')) return
    setCrawling(true)
    try {
      const { data } = await api.post('/scraping/crawl-all')
      toast.success(data.message)
      setTimeout(loadJobs, 2000)
    } catch { toast.error('Erro ao iniciar varredura') }
    finally { setCrawling(false) }
  }

  const runningCount = jobs.filter(j => j.status === 'running').length
  const completedCount = jobs.filter(j => j.status === 'completed').length

  return (
    <AuthGuard title="Coleta de Dados">
      <div className="space-y-6">

        {/* Varredura completa */}
        <div className="card border-l-4 border-brand-600">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-bold text-gray-800 text-base flex items-center gap-2">
                <Zap className="w-5 h-5 text-brand-600" /> Varredura Completa
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Coleta TODOS os produtos de <strong>{markets.length} mercado(s)</strong> varrendo
                todas as categorias — sem precisar digitar um produto específico.
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Brasão: ~17 categorias com paginação &nbsp;|&nbsp; Super Alfa: ~13 categorias com scroll automático
              </p>
            </div>
            <button
              onClick={handleCrawlAll}
              disabled={crawling}
              className="btn-primary flex-shrink-0 whitespace-nowrap"
            >
              <Zap className="w-4 h-4" />
              {crawling ? 'Iniciando...' : 'Varrer Tudo Agora'}
            </button>
          </div>
        </div>

        {/* Busca por produto específico */}
        <div className="card">
          <h2 className="font-semibold text-gray-800 mb-3">Coleta por Produto Específico</h2>
          <div className="flex gap-3">
            <input
              className="input flex-1"
              placeholder="Ex: Coca-Cola 2L, Arroz 5kg..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleTrigger()}
            />
            <button onClick={handleTrigger} disabled={triggering} className="btn-secondary">
              <Play className="w-4 h-4" /> {triggering ? 'Iniciando...' : 'Coletar'}
            </button>
          </div>
        </div>

        {/* Contadores */}
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <p className="text-2xl font-bold text-blue-600">{jobs.length}</p>
            <p className="text-xs text-gray-500">Total de jobs</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-yellow-600">{runningCount}</p>
            <p className="text-xs text-gray-500">Em execução</p>
          </div>
          <div className="card text-center">
            <p className="text-2xl font-bold text-green-600">{completedCount}</p>
            <p className="text-xs text-gray-500">Concluídos</p>
          </div>
        </div>

        {/* Tabela de jobs */}
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-gray-700">Histórico de Coletas</p>
          <button onClick={loadJobs} className="btn-secondary text-xs py-1.5">
            <RefreshCw className="w-3 h-3" /> Atualizar
          </button>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Produto / Tipo</th>
                <th>Mercado</th>
                <th>Status</th>
                <th>Resultados</th>
                <th>Início</th>
                <th>Conclusão</th>
                <th>Erro</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center py-10">
                  <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-brand-600" />
                </td></tr>
              ) : jobs.length === 0 ? (
                <tr><td colSpan={7} className="text-center text-gray-400 py-10">
                  Nenhuma coleta registrada. Clique em "Varrer Tudo Agora" para começar.
                </td></tr>
              ) : jobs.map((j) => {
                const cfg = statusConfig[j.status] ?? statusConfig.pending
                const Icon = cfg.icon
                const marketName = markets.find((m) => m.id === j.market_id)?.name ?? 'Todos'
                const isFullCrawl = j.query === '[varredura completa]'
                return (
                  <tr key={j.id}>
                    <td>
                      <span className={`font-medium ${isFullCrawl ? 'text-brand-700' : 'text-gray-800'}`}>
                        {isFullCrawl ? '⚡ Varredura completa' : (j.query ?? '-')}
                      </span>
                    </td>
                    <td className="text-gray-600 text-xs">{marketName}</td>
                    <td>
                      <span className={cfg.className}>
                        <Icon className="w-3 h-3 inline mr-1" />{cfg.label}
                      </span>
                    </td>
                    <td className="font-semibold text-gray-700">{j.results_count}</td>
                    <td className="text-xs text-gray-500">{formatDate(j.started_at)}</td>
                    <td className="text-xs text-gray-500">{formatDate(j.completed_at)}</td>
                    <td className="text-xs text-red-500 max-w-[200px] truncate" title={j.error_message ?? ''}>
                      {j.error_message ?? '-'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </AuthGuard>
  )
}
