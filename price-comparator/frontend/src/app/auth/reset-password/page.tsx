'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ShoppingBag, ArrowLeft, Eye, EyeOff, KeyRound } from 'lucide-react'
import toast from 'react-hot-toast'
import { resetPassword } from '@/services/auth'

export default function ResetPasswordPage() {
  const router = useRouter()
  const [form, setForm] = useState({ token: '', password: '', confirm: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (form.password !== form.confirm) {
      toast.error('As senhas não coincidem')
      return
    }
    if (form.password.length < 6) {
      toast.error('A senha deve ter pelo menos 6 caracteres')
      return
    }
    setLoading(true)
    try {
      await resetPassword(form.token, form.password)
      toast.success('Senha redefinida com sucesso!')
      router.push('/auth/login')
    } catch {
      toast.error('Token inválido ou expirado')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-800 to-brand-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-brand-700 flex items-center justify-center">
            <KeyRound className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Redefinir Senha</h1>
            <p className="text-sm text-gray-500">Informe o token e a nova senha</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Token de Recuperação</label>
            <input
              type="text"
              className="input font-mono text-sm"
              required
              value={form.token}
              onChange={(e) => setForm({ ...form, token: e.target.value })}
              placeholder="Cole o token aqui"
            />
          </div>
          <div>
            <label className="label">Nova Senha</label>
            <div className="relative">
              <input
                type={showPass ? 'text' : 'password'}
                className="input pr-10"
                required
                minLength={6}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400" onClick={() => setShowPass(v => !v)}>
                {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="label">Confirmar Nova Senha</label>
            <input
              type={showPass ? 'text' : 'password'}
              className="input"
              required
              minLength={6}
              value={form.confirm}
              onChange={(e) => setForm({ ...form, confirm: e.target.value })}
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center mt-2">
            {loading ? 'Redefinindo...' : 'Redefinir Senha'}
          </button>
        </form>

        <button onClick={() => router.push('/auth/login')} className="mt-4 flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 mx-auto">
          <ArrowLeft className="w-3.5 h-3.5" /> Voltar ao login
        </button>
      </div>
    </div>
  )
}
