'use client'
import { useState, useEffect } from 'react'
import type { Market } from '@/types'
import { X, Info } from 'lucide-react'
import api from '@/services/api'

interface Connector {
  key: string
  label: string
  description: string
}

interface Props {
  market?: Market
  onSave: (data: Partial<Market>) => Promise<void>
  onClose: () => void
}

export default function MarketForm({ market, onSave, onClose }: Props) {
  const [form, setForm] = useState({
    name: market?.name ?? '',
    url: market?.url ?? '',
    logo_url: market?.logo_url ?? '',
    integration_type: market?.integration_type ?? 'scraping',
    scraper_class: market?.scraper_class ?? 'mock',
    is_active: market?.is_active ?? true,
  })
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get<Connector[]>('/markets/connectors')
      .then(({ data }) => setConnectors(data))
      .catch(() => setConnectors([
        { key: 'brasao',    label: 'Brasão Supermercados', description: 'Scraper real do brasao.com.br' },
        { key: 'superalfa', label: 'Super Alfa',            description: 'Scraper real do superalfanumclick.com.br' },
        { key: 'mock',      label: 'Demonstração (Mock)',   description: 'Dados fictícios para testes' },
      ]))
  }, [])

  const selectedConnector = connectors.find(c => c.key === form.scraper_class)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const payload = {
      ...form,
      logo_url: form.logo_url.trim() || null,
    }
    await onSave(payload)
    setSaving(false)
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold">{market ? 'Editar Mercado' : 'Novo Mercado'}</h2>
          <button onClick={onClose} className="btn-ghost p-1"><X className="w-5 h-5" /></button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label">Nome do Mercado *</label>
            <input
              className="input"
              required
              placeholder="Ex: Atacadão Centro"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>

          <div>
            <label className="label">URL do Site *</label>
            <input
              className="input"
              required
              placeholder="https://www.exemplo.com.br"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
            />
          </div>

          <div>
            <label className="label">Logo URL <span className="text-gray-400 font-normal">(opcional)</span></label>
            <input
              className="input"
              placeholder="https://..."
              value={form.logo_url}
              onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
            />
          </div>

          <div>
            <label className="label">Conector de Coleta *</label>
            <select
              className="input"
              value={form.scraper_class}
              onChange={(e) => setForm({ ...form, scraper_class: e.target.value })}
            >
              {connectors.map(c => (
                <option key={c.key} value={c.key}>{c.label}</option>
              ))}
            </select>
            {selectedConnector && (
              <div className="flex items-start gap-1.5 mt-1.5 text-xs text-gray-500">
                <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-blue-400" />
                <span>{selectedConnector.description}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="active"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="accent-brand-600"
            />
            <label htmlFor="active" className="text-sm font-medium text-gray-700">Mercado ativo</label>
          </div>

          {!market && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-700">
              <strong>Após salvar</strong>, a coleta de produtos será iniciada automaticamente para este mercado.
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? 'Salvando...' : (market ? 'Salvar alterações' : 'Cadastrar e coletar')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
