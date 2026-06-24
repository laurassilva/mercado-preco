'use client'
import { useState, useEffect, useRef, type KeyboardEvent } from 'react'
import { Search, X, Loader2 } from 'lucide-react'
import api from '@/services/api'

interface Props {
  onSearch: (query: string) => void
  loading: boolean
  initialValue?: string
}

const POPULAR = [
  'Coca-Cola 2L', 'Arroz 5kg', 'Feijão Carioca 1kg', 'Leite Integral',
  'Óleo de Soja', 'Açúcar 1kg', 'Macarrão 500g', 'Cerveja Brahma',
]

export default function SearchBar({ onSearch, loading, initialValue = '' }: Props) {
  const [value, setValue] = useState(initialValue)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [selectedIdx, setSelectedIdx] = useState(-1)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const fetchSuggestions = async (q: string) => {
    if (q.length < 2) {
      setSuggestions([])
      return
    }
    setLoadingSuggestions(true)
    try {
      const { data } = await api.get('/products/autocomplete', { params: { q, limit: 8 } })
      setSuggestions(data.suggestions || [])
      setShowSuggestions(true)
      setSelectedIdx(-1)
    } catch {
      setSuggestions([])
    } finally {
      setLoadingSuggestions(false)
    }
  }

  const handleChange = (text: string) => {
    setValue(text)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => fetchSuggestions(text), 300)
  }

  const handleSearch = (q?: string) => {
    const searchQuery = q || value
    if (searchQuery.trim().length >= 2) {
      setShowSuggestions(false)
      onSearch(searchQuery.trim())
    }
  }

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      if (selectedIdx >= 0 && selectedIdx < suggestions.length) {
        setValue(suggestions[selectedIdx])
        handleSearch(suggestions[selectedIdx])
      } else {
        handleSearch()
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(prev => Math.min(prev + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(prev => Math.max(prev - 1, -1))
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  const selectSuggestion = (s: string) => {
    setValue(s)
    setShowSuggestions(false)
    handleSearch(s)
  }

  return (
    <div className="space-y-3">
      <div className="relative flex gap-2" ref={wrapperRef}>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            value={value}
            onChange={(e) => handleChange(e.target.value)}
            onKeyDown={handleKey}
            onFocus={() => { if (suggestions.length > 0) setShowSuggestions(true) }}
            placeholder="Ex: Coca-Cola 2L, Arroz 5kg, Leite Integral..."
            className="input pl-10 pr-10 py-3 text-base"
            autoComplete="off"
          />
          {value && !loading && (
            <button
              onClick={() => { setValue(''); setSuggestions([]); setShowSuggestions(false) }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          {loadingSuggestions && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 animate-spin" />
          )}

          {/* Autocomplete Dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => selectSuggestion(s)}
                  className={`w-full text-left px-4 py-2.5 text-sm flex items-center gap-2 transition-colors ${
                    i === selectedIdx ? 'bg-brand-50 text-brand-700' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Search className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                  <span className="truncate">{s}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={() => handleSearch()}
          disabled={loading || value.trim().length < 2}
          className="btn-primary px-6 py-3 text-base"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="animate-spin h-4 w-4" />
              Buscando...
            </span>
          ) : (
            'Buscar'
          )}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-gray-500">Populares:</span>
        {POPULAR.map((s) => (
          <button
            key={s}
            onClick={() => { setValue(s); handleSearch(s) }}
            className="text-xs px-3 py-1 rounded-full bg-gray-100 hover:bg-brand-100 hover:text-brand-700 text-gray-600 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
