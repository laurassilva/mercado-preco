'use client'
import { useState } from 'react'
import type { Market } from '@/types'
import { X } from 'lucide-react'

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
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    await onSave(form)
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
            <input className="input" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div>
            <label className="label">URL Principal *</label>
            <input className="input" type="url" required value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} />
          </div>
          <div>
            <label className="label">Logo URL</label>
            <input className="input" type="url" value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Tipo de Integração</label>
              <select className="input" value={form.integration_type} onChange={(e) => setForm({ ...form, integration_type: e.target.value })}>
                <option value="scraping">Web Scraping</option>
                <option value="api">API Oficial</option>
                <option value="xml">Feed XML</option>
                <option value="json">Feed JSON</option>
              </select>
            </div>
            <div>
              <label className="label">Conector</label>
              <select className="input" value={form.scraper_class} onChange={(e) => setForm({ ...form, scraper_class: e.target.value })}>
                <option value="mock">Mock (Demo)</option>
                <option value="playwright">Playwright</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="active" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="accent-brand-600" />
            <label htmlFor="active" className="text-sm font-medium text-gray-700">Mercado ativo</label>
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">Cancelar</button>
            <button type="submit" disabled={saving} className="btn-primary flex-1">
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
