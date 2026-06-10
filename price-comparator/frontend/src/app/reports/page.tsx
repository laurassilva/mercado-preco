'use client'
import { useState } from 'react'
import { FileText, FileSpreadsheet, Download } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'

const COMMON_PRODUCTS = [
  'Coca-Cola 2L', 'Arroz 5kg', 'Feijão Carioca 1kg', 'Leite Integral',
  'Óleo de Soja', 'Açúcar 1kg', 'Macarrão 500g', 'Café 500g',
]

export default function ReportsPage() {
  const [query, setQuery] = useState('')
  const [generating, setGenerating] = useState<string | null>(null)

  const handleExport = async (format: 'pdf' | 'excel' | 'csv', q?: string) => {
    const term = q || query
    if (!term.trim()) { toast.error('Digite um produto'); return }
    setGenerating(format)
    try {
      const ext = format === 'excel' ? 'xlsx' : format
      const resp = await api.get(`/reports/${format}?q=${encodeURIComponent(term)}`, { responseType: 'blob' })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a'); a.href = url
      a.download = `comparacao_${term.replace(/ /g, '_')}.${ext}`; a.click()
      URL.revokeObjectURL(url)
      toast.success('Relatório gerado!')
    } catch {
      toast.error('Erro ao gerar relatório')
    } finally {
      setGenerating(null)
    }
  }

  return (
    <AuthGuard title="Relatórios">
      <div className="max-w-2xl space-y-6">
        <div className="card">
          <h2 className="text-base font-semibold text-gray-800 mb-4">Gerar Relatório de Comparação</h2>
          <div className="space-y-4">
            <div>
              <label className="label">Produto a comparar</label>
              <input
                className="input"
                placeholder="Ex: Coca-Cola 2L"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="text-xs text-gray-500 self-center">Produtos populares:</span>
              {COMMON_PRODUCTS.map((p) => (
                <button key={p} onClick={() => setQuery(p)}
                  className="text-xs px-3 py-1 rounded-full bg-gray-100 hover:bg-brand-100 hover:text-brand-700 text-gray-600 transition-colors">
                  {p}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <button onClick={() => handleExport('pdf')} disabled={!!generating}
                className="flex flex-col items-center gap-3 p-5 border-2 border-dashed border-red-200 rounded-xl hover:border-red-400 hover:bg-red-50 transition-all disabled:opacity-50">
                <FileText className="w-8 h-8 text-red-600" />
                <div className="text-center">
                  <p className="font-semibold text-sm">PDF</p>
                  <p className="text-xs text-gray-500">Relatório formatado</p>
                </div>
                {generating === 'pdf' && <span className="text-xs text-red-600">Gerando...</span>}
              </button>

              <button onClick={() => handleExport('excel')} disabled={!!generating}
                className="flex flex-col items-center gap-3 p-5 border-2 border-dashed border-green-200 rounded-xl hover:border-green-400 hover:bg-green-50 transition-all disabled:opacity-50">
                <FileSpreadsheet className="w-8 h-8 text-green-600" />
                <div className="text-center">
                  <p className="font-semibold text-sm">Excel</p>
                  <p className="text-xs text-gray-500">Planilha .xlsx</p>
                </div>
                {generating === 'excel' && <span className="text-xs text-green-600">Gerando...</span>}
              </button>

              <button onClick={() => handleExport('csv')} disabled={!!generating}
                className="flex flex-col items-center gap-3 p-5 border-2 border-dashed border-blue-200 rounded-xl hover:border-blue-400 hover:bg-blue-50 transition-all disabled:opacity-50">
                <Download className="w-8 h-8 text-blue-600" />
                <div className="text-center">
                  <p className="font-semibold text-sm">CSV</p>
                  <p className="text-xs text-gray-500">Dados tabulares</p>
                </div>
                {generating === 'csv' && <span className="text-xs text-blue-600">Gerando...</span>}
              </button>
            </div>
          </div>
        </div>

        <div className="card bg-blue-50 border border-blue-200">
          <h3 className="font-semibold text-blue-800 mb-2">Relatórios Rápidos</h3>
          <p className="text-sm text-blue-600 mb-4">Gere relatórios de produtos populares em um clique</p>
          <div className="grid grid-cols-2 gap-2">
            {COMMON_PRODUCTS.slice(0, 6).map((p) => (
              <button key={p} onClick={() => handleExport('pdf', p)} disabled={!!generating}
                className="text-left px-3 py-2 bg-white rounded-lg text-sm hover:bg-blue-100 transition-colors border border-blue-200 disabled:opacity-50">
                📄 {p}
              </button>
            ))}
          </div>
        </div>
      </div>
    </AuthGuard>
  )
}
