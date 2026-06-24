'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { ShoppingBag, ArrowLeft, Mail, Copy, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import { forgotPassword } from '@/services/auth'

export default function ForgotPasswordPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<{ token: string; expires_at: string } | null>(null)
  const [copied, setCopied] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await forgotPassword(email)
      setResult(data)
      toast.success('Token de recuperação gerado!')
    } catch {
      toast.error('Email não encontrado')
    } finally {
      setLoading(false)
    }
  }

  const copyToken = () => {
    if (result) {
      navigator.clipboard.writeText(result.token)
      setCopied(true)
      toast.success('Token copiado!')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-800 to-brand-900 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-xl bg-brand-700 flex items-center justify-center">
            <ShoppingBag className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Recuperar Senha</h1>
            <p className="text-sm text-gray-500">Price Comparator</p>
          </div>
        </div>

        {!result ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email cadastrado</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="email"
                  className="input pl-10"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="seu@email.com"
                />
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5 justify-center">
              {loading ? 'Gerando...' : 'Gerar Token de Recuperação'}
            </button>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
              <p className="text-sm font-medium text-green-800 mb-2">Token gerado com sucesso!</p>
              <p className="text-xs text-green-600 mb-3">Copie o token abaixo e use na página de redefinição de senha.</p>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 bg-white rounded text-xs font-mono text-gray-800 break-all border">
                  {result.token}
                </code>
                <button onClick={copyToken} className="btn-ghost p-2">
                  {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              onClick={() => router.push('/auth/reset-password')}
              className="btn-primary w-full py-2.5 justify-center"
            >
              Ir para Redefinir Senha
            </button>
          </div>
        )}

        <button
          onClick={() => router.push('/auth/login')}
          className="mt-4 flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 mx-auto"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Voltar ao login
        </button>
      </div>
    </div>
  )
}
