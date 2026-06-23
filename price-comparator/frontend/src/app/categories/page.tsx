'use client'
import { useEffect, useState } from 'react'
import { Tag, Plus, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { Category, CategoryStats } from '@/types'

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [stats, setStats] = useState<CategoryStats[]>([])
  const [newName, setNewName] = useState('')
  const [newKeywords, setNewKeywords] = useState('')
  const [loading, setLoading] = useState(true)
  const [reclassifying, setReclassifying] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [catRes, statsRes] = await Promise.all([
        api.get<Category[]>('/categories/'),
        api.get<CategoryStats[]>('/categories/stats'),
      ])
      setCategories(catRes.data)
      setStats(statsRes.data)
    } catch {} finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleAdd = async () => {
    if (!newName.trim() || !newKeywords.trim()) return
    try {
      await api.post('/categories/', {
        name: newName.trim(),
        keywords: newKeywords.split(',').map(k => k.trim()).filter(Boolean),
      })
      setNewName('')
      setNewKeywords('')
      toast.success('Categoria criada')
      fetchData()
    } catch { toast.error('Erro ao criar categoria') }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Remover esta categoria?')) return
    try {
      await api.delete(`/categories/${id}`)
      toast.success('Categoria removida')
      fetchData()
    } catch { toast.error('Erro ao remover') }
  }

  const handleReclassify = async () => {
    setReclassifying(true)
    try {
      const { data } = await api.post('/categories/reclassify')
      toast.success(data.message)
      fetchData()
    } catch { toast.error('Erro ao reclassificar') }
    finally { setReclassifying(false) }
  }

  const getStatFor = (name: string) => stats.find(s => s.category === name)

  return (
    <AuthGuard title="Categorias">
      <div className="space-y-4">
        {/* Add category form */}
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Nova Categoria</h2>
          <div className="flex flex-col sm:flex-row gap-3">
            <input className="input flex-1" placeholder="Nome (ex: Bebidas)" value={newName} onChange={e => setNewName(e.target.value)} />
            <input className="input flex-[2]" placeholder="Palavras-chave separadas por vírgula (ex: cerveja, refrigerante, suco)" value={newKeywords} onChange={e => setNewKeywords(e.target.value)} />
            <button onClick={handleAdd} className="btn-primary px-4 whitespace-nowrap">
              <Plus className="w-4 h-4 inline mr-1" />Adicionar
            </button>
          </div>
        </div>

        {/* Reclassify button */}
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">{categories.length} categoria(s) cadastrada(s)</p>
          <button onClick={handleReclassify} disabled={reclassifying} className="btn-secondary text-xs py-1.5 px-3">
            {reclassifying ? 'Reclassificando...' : 'Reclassificar todos os produtos'}
          </button>
        </div>

        {/* Categories table */}
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Categoria</th>
                <th>Palavras-chave</th>
                <th>Produtos</th>
                <th>Alertas Hoje</th>
                <th>Preço Médio</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-8 text-gray-400">Carregando...</td></tr>
              ) : categories.map(c => {
                const st = getStatFor(c.name)
                return (
                  <tr key={c.id}>
                    <td>
                      <span className="inline-flex items-center gap-1.5">
                        <Tag className="w-3.5 h-3.5 text-brand-600" />
                        <span className="font-medium text-gray-800">{c.name}</span>
                      </span>
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        {c.keywords.slice(0, 6).map(k => (
                          <span key={k} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{k}</span>
                        ))}
                        {c.keywords.length > 6 && (
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-400 text-xs rounded-full">+{c.keywords.length - 6}</span>
                        )}
                      </div>
                    </td>
                    <td className="text-gray-600">{st?.products_count ?? 0}</td>
                    <td className="text-gray-600">{st?.alerts_today ?? 0}</td>
                    <td className="text-gray-600">{st?.avg_price != null ? `R$ ${st.avg_price.toFixed(2)}` : '-'}</td>
                    <td>
                      <button onClick={() => handleDelete(c.id)} className="text-red-500 hover:text-red-700 p-1" title="Remover">
                        <Trash2 className="w-4 h-4" />
                      </button>
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
