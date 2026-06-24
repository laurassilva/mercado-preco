'use client'
import { useEffect, useState, useCallback } from 'react'
import {
  Plus, Pencil, Ban, CheckCircle, KeyRound, X, Search,
  Shield, User, ChevronLeft, ChevronRight, Copy, Check,
  Users as UsersIcon,
} from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { User as UserType } from '@/types'
import { formatDateShort } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

type StatusFilter = 'all' | 'active' | 'inactive' | 'blocked' | 'pending'
type RoleFilter = 'all' | 'admin' | 'gestor' | 'user'

const STATUS_BADGE: Record<string, string> = {
  active: 'badge-green',
  inactive: 'badge-gray',
  blocked: 'badge-red',
  pending: 'badge-yellow',
}
const STATUS_LABEL: Record<string, string> = {
  active: 'Ativo',
  inactive: 'Inativo',
  blocked: 'Bloqueado',
  pending: 'Pendente',
}
const ROLE_BADGE: Record<string, string> = {
  admin: 'badge-blue',
  gestor: 'bg-purple-100 text-purple-800 text-xs font-medium px-2.5 py-0.5 rounded-full',
  user: 'badge-gray',
}
const ROLE_LABEL: Record<string, string> = {
  admin: 'Admin',
  gestor: 'Gestor',
  user: 'Usuário',
}

const PER_PAGE = 10

interface UsersResponse {
  items?: UserType[]
  total?: number
}

export default function UsersPage() {
  const { isAdmin, user: currentUser } = useAuth()
  const [users, setUsers] = useState<UserType[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')

  // Modals
  const [showCreate, setShowCreate] = useState(false)
  const [editUser, setEditUser] = useState<UserType | null>(null)
  const [resetUser, setResetUser] = useState<UserType | null>(null)
  const [blockUser, setBlockUser] = useState<UserType | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string | number> = { page, per_page: PER_PAGE }
    if (search) params.q = search
    if (statusFilter !== 'all') params.status = statusFilter
    if (roleFilter !== 'all') params.role = roleFilter

    api.get('/users/', { params })
      .then(({ data }) => {
        // Handle both array and paginated response formats
        if (Array.isArray(data)) {
          setUsers(data)
          setTotal(data.length)
        } else {
          setUsers((data as UsersResponse).items || [])
          setTotal((data as UsersResponse).total || 0)
        }
      })
      .catch(() => toast.error('Erro ao carregar usuários'))
      .finally(() => setLoading(false))
  }, [page, search, statusFilter, roleFilter])

  useEffect(() => { load() }, [load])
  useEffect(() => { setPage(1) }, [search, statusFilter, roleFilter])

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  const getUserStatus = (u: UserType): string => {
    if (u.status) return u.status
    return u.is_active ? 'active' : 'inactive'
  }

  if (!isAdmin) return (
    <AuthGuard title="Usuários">
      <div className="flex items-center justify-center h-48 text-gray-400">Acesso restrito a administradores</div>
    </AuthGuard>
  )

  return (
    <AuthGuard title="Gerenciar Usuários">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <p className="page-title">Usuários</p>
            <p className="page-subtitle">{total} usuário(s)</p>
          </div>
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            <Plus className="w-4 h-4" /> <span className="hidden sm:inline">Novo Usuário</span>
          </button>
        </div>

        {/* Filters */}
        <div className="card">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                className="input pl-10"
                placeholder="Buscar por nome ou email..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <select className="input w-full sm:w-40" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}>
              <option value="all">Todos Status</option>
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
              <option value="blocked">Bloqueado</option>
              <option value="pending">Pendente</option>
            </select>
            <select className="input w-full sm:w-40" value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as RoleFilter)}>
              <option value="all">Todos Perfis</option>
              <option value="admin">Admin</option>
              <option value="gestor">Gestor</option>
              <option value="user">Usuário</option>
            </select>
          </div>
        </div>

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
          </div>
        ) : users.length === 0 ? (
          <div className="card text-center py-12">
            <UsersIcon className="w-10 h-10 mx-auto mb-2 text-gray-300" />
            <p className="text-gray-500">Nenhum usuário encontrado</p>
          </div>
        ) : (
          <>
            {/* Mobile: cards */}
            <div className="md:hidden space-y-2">
              {users.map((u) => {
                const status = getUserStatus(u)
                return (
                  <div key={u.id} className="card space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-gray-900 truncate">
                          {u.name}
                          {u.id === currentUser?.id && <span className="ml-1 text-xs text-brand-600">(você)</span>}
                        </p>
                        <p className="text-xs text-gray-500 truncate">{u.email}</p>
                        {u.company && <p className="text-xs text-gray-400 truncate">{u.company}</p>}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className={ROLE_BADGE[u.role] || 'badge-gray'}>
                          {ROLE_LABEL[u.role] || u.role}
                        </span>
                        <span className={STATUS_BADGE[status] || 'badge-gray'}>
                          {STATUS_LABEL[status] || status}
                        </span>
                      </div>
                    </div>
                    {u.last_login_at && (
                      <p className="text-xs text-gray-400">Último acesso: {formatDateShort(u.last_login_at)}</p>
                    )}
                    {u.id !== currentUser?.id && (
                      <div className="flex items-center gap-2 pt-1 border-t border-gray-100">
                        <button onClick={() => setEditUser(u)} className="btn-ghost text-xs flex items-center gap-1 py-1">
                          <Pencil className="w-3 h-3" /> Editar
                        </button>
                        <button
                          onClick={() => setBlockUser(u)}
                          className="btn-ghost text-xs flex items-center gap-1 py-1"
                        >
                          {status === 'blocked' ? <CheckCircle className="w-3 h-3" /> : <Ban className="w-3 h-3" />}
                          {status === 'blocked' ? 'Desbloquear' : 'Bloquear'}
                        </button>
                        <button onClick={() => setResetUser(u)} className="btn-ghost text-xs flex items-center gap-1 py-1">
                          <KeyRound className="w-3 h-3" /> Resetar
                        </button>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Desktop: table */}
            <div className="hidden md:block table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nome</th>
                    <th>Email</th>
                    <th>Empresa</th>
                    <th>Perfil</th>
                    <th>Status</th>
                    <th>Último Acesso</th>
                    <th>Ações</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const status = getUserStatus(u)
                    return (
                      <tr key={u.id}>
                        <td className="font-medium whitespace-nowrap">
                          {u.name}
                          {u.id === currentUser?.id && <span className="text-xs text-brand-600 ml-1">(você)</span>}
                          {u.position && <p className="text-xs text-gray-400 font-normal">{u.position}</p>}
                        </td>
                        <td className="text-gray-500">{u.email}</td>
                        <td className="text-gray-500 text-sm">{u.company || '-'}</td>
                        <td>
                          <span className={ROLE_BADGE[u.role] || 'badge-gray'}>
                            {u.role === 'admin' && <Shield className="w-3 h-3 inline mr-1" />}
                            {u.role === 'user' && <User className="w-3 h-3 inline mr-1" />}
                            {ROLE_LABEL[u.role] || u.role}
                          </span>
                        </td>
                        <td>
                          <span className={STATUS_BADGE[status] || 'badge-gray'}>
                            {STATUS_LABEL[status] || status}
                          </span>
                        </td>
                        <td className="text-gray-500 text-xs whitespace-nowrap">
                          {u.last_login_at ? formatDateShort(u.last_login_at) : '-'}
                        </td>
                        <td>
                          {u.id !== currentUser?.id && (
                            <div className="flex items-center gap-1">
                              <button
                                onClick={() => setEditUser(u)}
                                className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors"
                                title="Editar"
                              >
                                <Pencil className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => setBlockUser(u)}
                                className={`p-1.5 rounded hover:bg-gray-100 transition-colors ${status === 'blocked' ? 'text-green-500 hover:text-green-700' : 'text-red-500 hover:text-red-700'}`}
                                title={status === 'blocked' ? 'Desbloquear' : 'Bloquear'}
                              >
                                {status === 'blocked' ? <CheckCircle className="w-4 h-4" /> : <Ban className="w-4 h-4" />}
                              </button>
                              <button
                                onClick={() => setResetUser(u)}
                                className="p-1.5 rounded hover:bg-gray-100 text-amber-500 hover:text-amber-700 transition-colors"
                                title="Resetar Senha"
                              >
                                <KeyRound className="w-4 h-4" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between py-2">
                <p className="text-sm text-gray-600">
                  Página {page} de {totalPages} ({total} total)
                </p>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    let pageNum: number
                    if (totalPages <= 5) {
                      pageNum = i + 1
                    } else if (page <= 3) {
                      pageNum = i + 1
                    } else if (page >= totalPages - 2) {
                      pageNum = totalPages - 4 + i
                    } else {
                      pageNum = page - 2 + i
                    }
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        className={`min-w-[32px] h-8 rounded text-sm font-medium transition-colors ${
                          page === pageNum ? 'bg-brand-600 text-white' : 'hover:bg-gray-100 text-gray-700'
                        }`}
                      >
                        {pageNum}
                      </button>
                    )
                  })}
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Create Modal */}
        {showCreate && (
          <CreateUserModal onClose={() => setShowCreate(false)} onSuccess={() => { setShowCreate(false); load() }} />
        )}

        {/* Edit Modal */}
        {editUser && (
          <EditUserModal user={editUser} onClose={() => setEditUser(null)} onSuccess={() => { setEditUser(null); load() }} />
        )}

        {/* Reset Password Modal */}
        {resetUser && (
          <ResetPasswordModal user={resetUser} onClose={() => setResetUser(null)} />
        )}

        {/* Block Confirmation */}
        {blockUser && (
          <BlockConfirmModal
            user={blockUser}
            isBlocked={getUserStatus(blockUser) === 'blocked'}
            onClose={() => setBlockUser(null)}
            onSuccess={() => { setBlockUser(null); load() }}
          />
        )}
      </div>
    </AuthGuard>
  )
}

// ==================== CREATE USER MODAL ====================
function CreateUserModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({
    name: '', email: '', password: '', phone: '', company: '', position: '', role: 'user',
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload: Record<string, string> = { name: form.name, email: form.email, password: form.password, role: form.role }
      if (form.phone) payload.phone = form.phone
      if (form.company) payload.company = form.company
      if (form.position) payload.position = form.position
      await api.post('/users/', payload)
      toast.success('Usuário criado!')
      onSuccess()
    } catch {
      toast.error('Erro ao criar usuário')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Novo Usuário</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="label">Nome *</label>
            <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Email *</label>
            <input className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <label className="label">Senha *</label>
            <input className="input" type="password" required minLength={6} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
          </div>
          <div>
            <label className="label">Telefone</label>
            <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="(00) 00000-0000" />
          </div>
          <div>
            <label className="label">Empresa</label>
            <input className="input" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          </div>
          <div>
            <label className="label">Cargo</label>
            <input className="input" value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
          </div>
          <div>
            <label className="label">Perfil</label>
            <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="user">Usuário</option>
              <option value="gestor">Gestor</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? 'Salvando...' : 'Criar Usuário'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ==================== EDIT USER MODAL ====================
function EditUserModal({ user, onClose, onSuccess }: { user: UserType; onClose: () => void; onSuccess: () => void }) {
  const [form, setForm] = useState({
    name: user.name,
    email: user.email,
    phone: user.phone || '',
    company: user.company || '',
    position: user.position || '',
    role: user.role,
    status: user.status || (user.is_active ? 'active' : 'inactive'),
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await api.patch(`/users/${user.id}`, {
        name: form.name,
        email: form.email,
        phone: form.phone || null,
        company: form.company || null,
        position: form.position || null,
        role: form.role,
        status: form.status,
      })
      toast.success('Usuário atualizado!')
      onSuccess()
    } catch {
      toast.error('Erro ao atualizar usuário')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Editar Usuário</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1"><X className="w-5 h-5" /></button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="label">Nome</label>
            <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <label className="label">Telefone</label>
            <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div>
            <label className="label">Empresa</label>
            <input className="input" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          </div>
          <div>
            <label className="label">Cargo</label>
            <input className="input" value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
          </div>
          <div>
            <label className="label">Perfil</label>
            <select className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserType['role'] })}>
              <option value="user">Usuário</option>
              <option value="gestor">Gestor</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          <div>
            <label className="label">Status</label>
            <select className="input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as 'active' | 'inactive' | 'blocked' | 'pending' })}>
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
              <option value="blocked">Bloqueado</option>
              <option value="pending">Pendente</option>
            </select>
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? 'Salvando...' : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ==================== RESET PASSWORD MODAL ====================
function ResetPasswordModal({ user, onClose }: { user: UserType; onClose: () => void }) {
  const [loading, setLoading] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const handleReset = async () => {
    setLoading(true)
    try {
      const { data } = await api.post(`/users/${user.id}/reset-password`)
      setToken(data.token)
      toast.success('Token de redefinição gerado!')
    } catch {
      toast.error('Erro ao resetar senha')
    } finally {
      setLoading(false)
    }
  }

  const copyToken = () => {
    if (token) {
      navigator.clipboard.writeText(token)
      setCopied(true)
      toast.success('Token copiado!')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Resetar Senha</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1"><X className="w-5 h-5" /></button>
        </div>

        <p className="text-sm text-gray-600 mb-4">
          Resetar senha do usuário <strong>{user.name}</strong> ({user.email})
        </p>

        {!token ? (
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
            <button onClick={handleReset} disabled={loading} className="btn-primary flex-1">
              <KeyRound className="w-4 h-4" /> {loading ? 'Gerando...' : 'Gerar Token'}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
              <p className="text-sm font-medium text-green-800 mb-2">Token gerado com sucesso!</p>
              <p className="text-xs text-green-600 mb-3">Envie este token ao usuário para redefinir a senha.</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 bg-white rounded text-xs font-mono text-gray-800 break-all border">
                  {token}
                </code>
                <button onClick={copyToken} className="btn-ghost p-2">
                  {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button onClick={onClose} className="btn-secondary w-full">Fechar</button>
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== BLOCK CONFIRMATION MODAL ====================
function BlockConfirmModal({ user, isBlocked, onClose, onSuccess }: {
  user: UserType; isBlocked: boolean; onClose: () => void; onSuccess: () => void
}) {
  const [loading, setLoading] = useState(false)

  const handleAction = async () => {
    setLoading(true)
    try {
      if (isBlocked) {
        await api.post(`/users/${user.id}/unblock`)
        toast.success('Usuário desbloqueado!')
      } else {
        await api.post(`/users/${user.id}/block`)
        toast.success('Usuário bloqueado!')
      }
      onSuccess()
    } catch {
      toast.error(isBlocked ? 'Erro ao desbloquear' : 'Erro ao bloquear')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
      <div className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">{isBlocked ? 'Desbloquear' : 'Bloquear'} Usuário</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1"><X className="w-5 h-5" /></button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          {isBlocked
            ? <>Deseja desbloquear o acesso de <strong>{user.name}</strong>?</>
            : <>Deseja bloquear o acesso de <strong>{user.name}</strong>? O usuário não conseguirá fazer login.</>
          }
        </p>
        <div className="flex gap-3">
          <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
          <button onClick={handleAction} disabled={loading} className={`flex-1 ${isBlocked ? 'btn-primary' : 'btn-danger'}`}>
            {loading ? 'Processando...' : isBlocked ? 'Desbloquear' : 'Bloquear'}
          </button>
        </div>
      </div>
    </div>
  )
}
