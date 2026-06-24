'use client'
import { useState } from 'react'
import { Eye, EyeOff, Lock, Save } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import { changePassword } from '@/services/auth'

export default function SettingsPage() {
  const [form, setForm] = useState({ current: '', newPass: '', confirm: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.newPass !== form.confirm) {
      toast.error('As senhas não coincidem')
      return
    }
    if (form.newPass.length < 6) {
      toast.error('A senha deve ter pelo menos 6 caracteres')
      return
    }
    setLoading(true)
    try {
      await changePassword(form.current, form.newPass)
      toast.success('Senha alterada com sucesso!')
      setForm({ current: '', newPass: '', confirm: '' })
    } catch {
      toast.error('Senha atual incorreta')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthGuard title="Configurações">
      <div className="max-w-lg">
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-4 flex items-center gap-2">
            <Lock className="w-4 h-4" /> Alterar Senha
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Senha Atual</label>
              <input type={showPass ? 'text' : 'password'} className="input" required value={form.current} onChange={(e) => setForm({ ...form, current: e.target.value })} />
            </div>
            <div>
              <label className="label">Nova Senha</label>
              <input type={showPass ? 'text' : 'password'} className="input" required minLength={6} value={form.newPass} onChange={(e) => setForm({ ...form, newPass: e.target.value })} />
            </div>
            <div>
              <label className="label">Confirmar Nova Senha</label>
              <input type={showPass ? 'text' : 'password'} className="input" required minLength={6} value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
              <input type="checkbox" checked={showPass} onChange={() => setShowPass(v => !v)} className="rounded" />
              Mostrar senhas
            </label>
            <button type="submit" disabled={loading} className="btn-primary py-2.5 justify-center flex items-center gap-2">
              <Save className="w-4 h-4" /> {loading ? 'Salvando...' : 'Salvar Nova Senha'}
            </button>
          </form>
        </div>
      </div>
    </AuthGuard>
  )
}
