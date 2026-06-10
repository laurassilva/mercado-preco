'use client'
import { useState } from 'react'
import { Filter } from 'lucide-react'
import type { Market } from '@/types'

interface Props {
  markets: Market[]
  selected: string[]
  onChange: (ids: string[]) => void
}

export default function MarketFilter({ markets, selected, onChange }: Props) {
  const [open, setOpen] = useState(false)

  const toggle = (id: string) => {
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id])
  }

  const selectAll = () => onChange(markets.map((m) => m.id))
  const clearAll = () => onChange([])

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="btn-secondary flex items-center gap-2"
      >
        <Filter className="w-4 h-4" />
        Filtrar Mercados
        {selected.length > 0 && selected.length < markets.length && (
          <span className="badge-blue">{selected.length}</span>
        )}
        {selected.length === 0 && <span className="badge-yellow">Todos</span>}
      </button>

      {open && (
        <div className="absolute top-full mt-2 left-0 bg-white border border-gray-200 rounded-xl shadow-lg p-4 z-10 min-w-[220px]">
          <div className="flex justify-between mb-3">
            <button onClick={selectAll} className="text-xs text-brand-600 hover:underline">Todos</button>
            <button onClick={clearAll} className="text-xs text-gray-500 hover:underline">Nenhum</button>
          </div>
          {markets.map((m) => (
            <label key={m.id} className="flex items-center gap-2 py-1.5 cursor-pointer hover:text-brand-700">
              <input
                type="checkbox"
                checked={selected.length === 0 || selected.includes(m.id)}
                onChange={() => toggle(m.id)}
                className="accent-brand-600"
              />
              <span className="text-sm">{m.name}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
