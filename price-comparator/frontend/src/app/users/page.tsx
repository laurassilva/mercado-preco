'use client'
import { useEffect, useState } from 'react'
import { Plus, Trash2, Shield, User, X } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { User as UserType } from '@/types'
import { formatDateShort } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

export default function UsersPage() {
  const { isAdmin, user: currentUser } = useAuth()
  const [users, setUsers] = useState<UserType[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'user' })
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    api.get<UserType[]>('/users/').then(({ data }) => setUsers(data)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.post('/users/', form)
      toast.success('Usuário criado!')
      setShowForm(false)
      setForm({ name: '', email: '', password: '', role: 'user' })
      load()
    } catch { toast.error('Erro ao criar usuário') }
    finally { setSaving(false) }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Deseja excluir este usuário?')) return
    try { await api.delete(`/users/${id}`); toast.success('Usuário excluído'); load() }
    catch { toast.error('Erro ao excluir') }
  }

  if (!isAdmin) return (
    <AuthGuard title="Usuários">
      <div className="flex items-center justify-center h-48 text-gray-400">Acesso restrito a administradores</div>
    </AuthGuard>
  )

  return (
    <AuthGuard title="Gerenciar Usuários">
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="page-title">Usuários</p>
            <p className="page-subtitle">{users.length} usuário(s)</p>
          </div>
          <button onClick={() => setShowForm(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> <span className="hidden sm:inline">Novo Usuário</span>
          </button>
        </div>

        {/* Modal de criação */}
        {showForm && (
          <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
            <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold">Novo Usuário</h2>
                <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600 p-1">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleCreate} className="space-y-3">
                <div>
                  <label className="label">Nome</label>
                  <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div>
                  <label className="label">Senha</label>
                  <input className="input" type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
                <div>
                  <label className="label">Perfil</label>
                  <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                    <option value="user">Usuário</option>
                    <option value="admin">Administrador</option>
                  </select>
                </div>
                <div className="flex gap-3 pt-2">
                  <button type="button" onClick={() => setShowForm(false)} className="btn-secondary flex-1">Cancelar</button>
                  <button type="submit" disabled={saving} className="btn-primary flex-1">
                    {saving ? 'Salvando...' : 'Criar Usuário'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Mobile: cards */}
        <div className="md:hidden space-y-2">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
            </div>
          ) : users.map((u) => (
            <div key={u.id} className="card flex items-center justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {u.name}
                  {u.id === currentUser?.id && <span className="ml-1 text-xs text-brand-600">(você)</span>}
                </p>
                <p className="text-xs text-gray-500 truncate">{u.email}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <span className={u.role === 'admin' ? 'badge-blue' : 'badge-gray'}>
                  {u.role === 'admin' ? <Shield className="w-3 h-3 inline mr-0.5" /> : <User className="w-3 h-3 inline mr-0.5" />}
                  {u.role === 'admin' ? 'Admin' : 'Usuário'}
                </span>
                {u.id !== currentUser?.id && (
                  <button onClick={() => handleDelete(u.id)} className="text-red-500 hover:text-red-700 p-1.5 rounded hover:bg-red-50">
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Desktop: tabela */}
        <div className="hidden md:block table-container">
          <table className="data-table">
            <thead>
              <tr><th>Nome</th><th>Email</th><th>Perfil</th><th>Status</th><th>Criado em</th><th>Ações</th></tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={6} className="text-center py-10">
                  <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-brand-600" />
                </td></tr>
              ) : users.map((u) => (
                <tr key={u.id}>
                  <td className="font-medium whitespace-nowrap">
                    {u.name} {u.id === currentUser?.id && <span className="text-xs text-brand-600">(você)</span>}
                  </td>
                  <td className="text-gray-500">{u.email}</td>
                  <td>
                    <span className={u.role === 'admin' ? 'badge-blue' : 'badge-gray'}>
                      {u.role === 'admin'
                        ? <><Shield className="w-3 h-3 inline mr-1" />Admin</>
                        : <><User className="w-3 h-3 inline mr-1" />Usuário</>}
                    </span>
                  </td>
                  <td><span className={u.is_active ? 'badge-green' : 'badge-red'}>{u.is_active ? 'Ativo' : 'Inativo'}</span></td>
                  <td className="text-gray-500 text-xs whitespace-nowrap">{formatDateShort(u.created_at)}</td>
                  <td>
                    {u.id !== currentUser?.id && (
                      <button onClick={() => handleDelete(u.id)} className="text-red-500 hover:text-red-700 p-1.5 rounded hover:bg-red-50 transition-colors">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
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
