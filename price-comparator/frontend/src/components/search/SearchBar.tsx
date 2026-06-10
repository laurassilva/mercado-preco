'use client'
import { useState, type KeyboardEvent } from 'react'
import { Search, X } from 'lucide-react'

interface Props {
  onSearch: (query: string) => void
  loading: boolean
  initialValue?: string
}

const SUGGESTIONS = [
  'Coca-Cola 2L', 'Arroz 5kg', 'Feijão Carioca 1kg', 'Leite Integral',
  'Óleo de Soja', 'Açúcar 1kg', 'Macarrão 500g', 'Cerveja Brahma',
]

export default function SearchBar({ onSearch, loading, initialValue = '' }: Props) {
  const [value, setValue] = useState(initialValue)

  const handleSearch = () => {
    if (value.trim().length >= 2) onSearch(value.trim())
  }

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div className="space-y-3">
      <div className="relative flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ex: Coca-Cola 2L, Arroz 5kg, Leite Integral..."
            className="input pl-10 pr-10 py-3 text-base"
          />
          {value && (
            <button
              onClick={() => setValue('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || value.trim().length < 2}
          className="btn-primary px-6 py-3 text-base"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Buscando...
            </span>
          ) : (
            'Buscar'
          )}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-gray-500">Sugestões:</span>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => { setValue(s); onSearch(s) }}
            className="text-xs px-3 py-1 rounded-full bg-gray-100 hover:bg-brand-100 hover:text-brand-700 text-gray-600 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
