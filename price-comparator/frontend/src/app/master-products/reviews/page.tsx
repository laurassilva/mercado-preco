'use client'
import { useEffect, useState } from 'react'
import { ClipboardCheck, Check, X, PlusCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { ProductMatchReviewItem } from '@/types'

export default function ReviewQueuePage() {
  const [items, setItems] = useState<ProductMatchReviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<string | null>(null)

  const fetchItems = async () => {
    setLoading(true)
    try {
      const { data } = await api.get<ProductMatchReviewItem[]>('/master-products/reviews', { params: { status: 'pending', limit: 100 } })
      setItems(data)
    } catch { setItems([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchItems() }, [])

  const act = async (id: string, action: 'approve' | 'reject' | 'create-new') => {
    setBusyId(id)
    try {
      await api.post(`/master-products/reviews/${id}/${action}`)
      toast.success(action === 'approve' ? 'Vínculo aprovado' : action === 'reject' ? 'Revisão rejeitada' : 'Produto mestre criado')
      setItems(prev => prev.filter(i => i.id !== id))
    } catch {
      toast.error('Erro ao processar revisão')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <AuthGuard title="Fila de Revisão — Catálogo Mestre">
      <div className="space-y-4">
        <p className="text-sm text-gray-500">
          Produtos capturados com similaridade entre 70% e 90% em relação a um Produto Mestre existente.
          Aprove para vincular, rejeite para manter sem vínculo, ou crie um Produto Mestre novo a partir dele.
        </p>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Produto Capturado</th>
                <th>Mercado</th>
                <th>Candidato (Produto Mestre)</th>
                <th>Confiança</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={5} className="text-center py-8 text-gray-400">Carregando...</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={5} className="text-center py-8 text-gray-400">
                  <ClipboardCheck className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  Nenhuma revisão pendente.
                </td></tr>
              ) : items.map(item => (
                <tr key={item.id}>
                  <td className="font-medium text-gray-800">{item.market_product_name}</td>
                  <td className="text-gray-500 text-sm">{item.market_name}</td>
                  <td className="text-gray-700 text-sm">{item.candidate_canonical_name || '-'}</td>
                  <td>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
                      {item.similarity_score != null ? `${item.similarity_score}%` : '-'}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => act(item.id, 'approve')}
                        disabled={busyId === item.id}
                        title="Aprovar vínculo"
                        className="p-1.5 rounded-lg bg-green-50 hover:bg-green-100 text-green-700 disabled:opacity-50"
                      ><Check className="w-4 h-4" /></button>
                      <button
                        onClick={() => act(item.id, 'reject')}
                        disabled={busyId === item.id}
                        title="Rejeitar"
                        className="p-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-red-700 disabled:opacity-50"
                      ><X className="w-4 h-4" /></button>
                      <button
                        onClick={() => act(item.id, 'create-new')}
                        disabled={busyId === item.id}
                        title="Criar novo Produto Mestre"
                        className="p-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 disabled:opacity-50"
                      ><PlusCircle className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AuthGuard>
  )
}
