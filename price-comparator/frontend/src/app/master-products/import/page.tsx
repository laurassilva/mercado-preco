'use client'
import { useEffect, useRef, useState } from 'react'
import { Upload, FileSpreadsheet, CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import api from '@/services/api'
import type { MasterProductImportBatch } from '@/types'

const POLL_MS = 2000

export default function MasterProductImportPage() {
  const [uploading, setUploading] = useState(false)
  const [batch, setBatch] = useState<MasterProductImportBatch | null>(null)
  const [history, setHistory] = useState<MasterProductImportBatch[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const fetchHistory = async () => {
    try {
      const { data } = await api.get<MasterProductImportBatch[]>('/master-products/imports')
      setHistory(data)
    } catch {}
  }

  useEffect(() => { fetchHistory() }, [])

  useEffect(() => {
    if (!batch || batch.status === 'completed' || batch.status === 'failed') return
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get<MasterProductImportBatch>(`/master-products/import/${batch.id}`)
        setBatch(data)
        if (data.status === 'completed' || data.status === 'failed') fetchHistory()
      } catch {}
    }, POLL_MS)
    return () => clearTimeout(timer)
  }, [batch])

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xlsm')) {
      toast.error('Envie um arquivo .xlsx')
      return
    }
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.post<MasterProductImportBatch>('/master-products/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setBatch(data)
      toast.success('Importação iniciada')
    } catch {
      toast.error('Erro ao enviar planilha')
    } finally {
      setUploading(false)
    }
  }

  return (
    <AuthGuard title="Importar Catálogo Mestre (GTIN)">
      <div className="space-y-4 max-w-3xl">
        <div className="card">
          <h3 className="font-bold text-gray-900 mb-1">Planilha de GTIN</h3>
          <p className="text-sm text-gray-500 mb-4">
            Envie um .xlsx com colunas como <code>gtin</code>/<code>ean</code>, <code>nome</code>,
            <code> marca</code>, <code>fabricante</code>, <code>categoria</code>, <code>subcategoria</code>,
            <code> peso/volume</code>, <code>unidade</code>. Produtos existentes (mesmo GTIN) são atualizados;
            novos GTINs são inseridos. Linhas inválidas são reportadas sem interromper a importação.
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xlsm"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="btn-primary flex items-center gap-2"
          >
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            {uploading ? 'Enviando...' : 'Selecionar planilha'}
          </button>
        </div>

        {batch && (
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <FileSpreadsheet className="w-5 h-5 text-brand-600" />
              <p className="font-medium text-gray-800">{batch.filename}</p>
              <StatusBadge status={batch.status} />
            </div>
            {batch.status === 'processing' || batch.status === 'pending' ? (
              <p className="text-sm text-gray-500">Processando planilha em segundo plano...</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                <div><p className="text-gray-500">Linhas</p><p className="font-bold">{batch.total_rows}</p></div>
                <div><p className="text-gray-500">Inseridos</p><p className="font-bold text-green-700">{batch.inserted_count}</p></div>
                <div><p className="text-gray-500">Atualizados</p><p className="font-bold text-blue-700">{batch.updated_count}</p></div>
                <div><p className="text-gray-500">Erros</p><p className="font-bold text-red-600">{batch.error_count}</p></div>
              </div>
            )}
            {!!batch.errors?.length && (
              <div className="mt-4 max-h-56 overflow-y-auto border rounded-lg">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50"><tr><th className="text-left p-2">Linha</th><th className="text-left p-2">Erro</th></tr></thead>
                  <tbody>
                    {batch.errors.map((e, i) => (
                      <tr key={i} className="border-t"><td className="p-2">{e.row}</td><td className="p-2 text-gray-600">{e.message}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        <div className="card">
          <h3 className="font-bold text-gray-900 mb-3">Histórico de importações</h3>
          <div className="table-container">
            <table className="data-table">
              <thead><tr><th>Arquivo</th><th>Status</th><th>Linhas</th><th>Inseridos</th><th>Atualizados</th><th>Erros</th><th>Data</th></tr></thead>
              <tbody>
                {history.length === 0 ? (
                  <tr><td colSpan={7} className="text-center py-6 text-gray-400">Nenhuma importação ainda</td></tr>
                ) : history.map(h => (
                  <tr key={h.id}>
                    <td>{h.filename}</td>
                    <td><StatusBadge status={h.status} /></td>
                    <td>{h.total_rows}</td>
                    <td className="text-green-700">{h.inserted_count}</td>
                    <td className="text-blue-700">{h.updated_count}</td>
                    <td className="text-red-600">{h.error_count}</td>
                    <td className="text-gray-500 text-xs">{new Date(h.created_at).toLocaleString('pt-BR')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AuthGuard>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string; icon: React.ReactNode }> = {
    pending: { label: 'Pendente', cls: 'bg-gray-100 text-gray-600', icon: <Loader2 className="w-3 h-3" /> },
    processing: { label: 'Processando', cls: 'bg-blue-100 text-blue-700', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    completed: { label: 'Concluído', cls: 'bg-green-100 text-green-700', icon: <CheckCircle2 className="w-3 h-3" /> },
    failed: { label: 'Falhou', cls: 'bg-red-100 text-red-700', icon: <XCircle className="w-3 h-3" /> },
  }
  const cfg = map[status] || map.pending
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.cls}`}>
      {cfg.icon}{cfg.label}
    </span>
  )
}
