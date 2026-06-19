'use client'
import { useEffect, useState } from 'react'
import { Plus, Edit2, Trash2, CheckCircle, XCircle, ExternalLink } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import MarketForm from '@/components/markets/MarketForm'
import api from '@/services/api'
import { useAuth } from '@/hooks/useAuth'
import type { Market } from '@/types'

const integrationLabel: Record<string, string> = {
  scraping: 'Web Scraping', api: 'API Oficial', xml: 'Feed XML', json: 'Feed JSON',
}

export default function MarketsPage() {
  const { isAdmin } = useAuth()
  const [markets, setMarkets] = useState<Market[]>([])
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Market | undefined>()

  const load = () => {
    setLoading(true)
    api.get<Market[]>('/markets/').then(({ data }) => setMarkets(data)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleSave = async (data: Partial<Market>) => {
    try {
      if (editing) {
        await api.patch(`/markets/${editing.id}`, data)
        toast.success('Mercado atualizado!')
      } else {
        await api.post('/markets/', data)
        toast.success('Mercado cadastrado! Coleta iniciada automaticamente.', { duration: 5000 })
      }
      setFormOpen(false)
      setEditing(undefined)
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      const msg = Array.isArray(detail)
        ? detail.map((d: any) => d.msg).join(', ')
        : (typeof detail === 'string' ? detail : 'Erro ao salvar mercado')
      toast.error(msg)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Deseja excluir este mercado?')) return
    try {
      await api.delete(`/markets/${id}`)
      toast.success('Mercado excluído')
      load()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      toast.error(typeof detail === 'string' ? detail : 'Erro ao excluir mercado')
    }
  }

  return (
    <AuthGuard title="Mercados">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="page-title">Mercados</p>
            <p className="page-subtitle">{markets.length} mercado(s) cadastrado(s)</p>
          </div>
          {isAdmin && (
            <button onClick={() => { setEditing(undefined); setFormOpen(true) }} className="btn-primary">
              <Plus className="w-4 h-4" /> <span className="hidden sm:inline">Novo Mercado</span>
            </button>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
          </div>
        ) : (
          <>
            {/* Mobile: cards */}
            <div className="md:hidden space-y-3">
              {markets.map((m) => (
                <div key={m.id} className="card space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-gray-900">{m.name}</p>
                      <a href={m.url} target="_blank" rel="noreferrer"
                        className="text-brand-600 text-xs flex items-center gap-1 mt-0.5 hover:underline truncate">
                        {m.url} <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      </a>
                    </div>
                    <span className={`text-xs font-medium flex items-center gap-1 flex-shrink-0 ${m.is_active ? 'text-green-700' : 'text-red-600'}`}>
                      {m.is_active ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                      {m.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <span className="badge-blue">{integrationLabel[m.integration_type] ?? m.integration_type}</span>
                      <code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{m.scraper_class}</code>
                    </div>
                    {isAdmin && (
                      <div className="flex gap-2">
                        <button onClick={() => { setEditing(m); setFormOpen(true) }} className="btn-ghost p-1.5" title="Editar">
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(m.id)} className="text-red-500 hover:text-red-700 p-1.5 rounded-lg hover:bg-red-50" title="Excluir">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Desktop: tabela */}
            <div className="hidden md:block table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>URL</th>
                    <th>Tipo</th>
                    <th>Conector</th>
                    <th>Status</th>
                    {isAdmin && <th>Ações</th>}
                  </tr>
                </thead>
                <tbody>
                  {markets.map((m) => (
                    <tr key={m.id}>
                      <td className="font-medium text-gray-800 whitespace-nowrap">{m.name}</td>
                      <td>
                        <a href={m.url} target="_blank" rel="noreferrer"
                          className="text-brand-600 hover:underline text-xs flex items-center gap-1">
                          <span className="truncate max-w-[200px] block">{m.url}</span>
                          <ExternalLink className="w-3 h-3 flex-shrink-0" />
                        </a>
                      </td>
                      <td><span className="badge-blue">{integrationLabel[m.integration_type] ?? m.integration_type}</span></td>
                      <td><code className="text-xs bg-gray-100 px-2 py-0.5 rounded">{m.scraper_class}</code></td>
                      <td>
                        {m.is_active
                          ? <span className="flex items-center gap-1 text-green-700 text-xs font-medium"><CheckCircle className="w-3 h-3" /> Ativo</span>
                          : <span className="flex items-center gap-1 text-red-600 text-xs font-medium"><XCircle className="w-3 h-3" /> Inativo</span>}
                      </td>
                      {isAdmin && (
                        <td>
                          <div className="flex gap-2">
                            <button onClick={() => { setEditing(m); setFormOpen(true) }} className="btn-ghost p-1.5" title="Editar">
                              <Edit2 className="w-4 h-4" />
                            </button>
                            <button onClick={() => handleDelete(m.id)} className="text-red-500 hover:text-red-700 p-1.5 rounded-lg hover:bg-red-50" title="Excluir">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {formOpen && (
        <MarketForm market={editing} onSave={handleSave} onClose={() => { setFormOpen(false); setEditing(undefined) }} />
      )}
    </AuthGuard>
  )
}
