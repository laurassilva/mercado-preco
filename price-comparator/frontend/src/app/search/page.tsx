'use client'
import { useEffect, useState } from 'react'
import { Database, Globe } from 'lucide-react'
import toast from 'react-hot-toast'
import AuthGuard from '@/components/layout/AuthGuard'
import SearchBar from '@/components/search/SearchBar'
import ResultsTable from '@/components/search/ResultsTable'
import MarketFilter from '@/components/search/MarketFilter'
import { useSearch } from '@/hooks/useSearch'
import api from '@/services/api'
import type { Market } from '@/types'

export default function SearchPage() {
  const { results, loading, error, search } = useSearch()
  const [markets, setMarkets] = useState<Market[]>([])
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([])
  const [lastQuery, setLastQuery] = useState('')
  const [liveMode, setLiveMode] = useState(false)
  const [sortBy, setSortBy] = useState<'relevance' | 'price'>('relevance')

  useEffect(() => {
    api.get<Market[]>('/markets/').then(({ data }) => setMarkets(data)).catch(() => {})
  }, [])

  const handleSearch = (query: string) => {
    setLastQuery(query)
    const ids = selectedMarkets.length > 0 && selectedMarkets.length < markets.length
      ? selectedMarkets : undefined
    search(query, ids, liveMode)
  }

  const handleExport = async (format: 'pdf' | 'excel' | 'csv') => {
    if (!lastQuery) return
    try {
      const ext = format === 'excel' ? 'xlsx' : format
      const resp = await api.get(`/reports/${format}?q=${encodeURIComponent(lastQuery)}`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `comparacao_${lastQuery.replace(/ /g, '_')}.${ext}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Erro ao gerar relatório')
    }
  }

  const sortedResults = results ? {
    ...results,
    results: [...results.results].sort((a, b) =>
      sortBy === 'price'
        ? a.price - b.price
        : (b.confidence_score || 0) - (a.confidence_score || 0)
    )
  } : null

  return (
    <AuthGuard title="Pesquisar Preços">
      <div className="space-y-4">
        <div className="card">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h2 className="text-base font-semibold text-gray-800">Buscar Produto</h2>

            <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 self-start sm:self-auto">
              <button
                onClick={() => setLiveMode(false)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  !liveMode ? 'bg-white text-brand-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Database className="w-3.5 h-3.5" />
                Banco de dados
              </button>
              <button
                onClick={() => setLiveMode(true)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  liveMode ? 'bg-white text-brand-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                Ao vivo
              </button>
            </div>
          </div>

          <div className="space-y-3">
            <SearchBar onSearch={handleSearch} loading={loading} />
            {markets.length > 0 && (
              <MarketFilter markets={markets} selected={selectedMarkets} onChange={setSelectedMarkets} />
            )}
          </div>

          {!liveMode && (
            <p className="mt-3 text-xs text-gray-400 flex items-center gap-1.5">
              <Database className="w-3 h-3" />
              Buscando no banco local. Use &quot;Coleta &gt; Varrer Tudo&quot; para atualizar os dados.
            </p>
          )}
          {liveMode && (
            <p className="mt-3 text-xs text-amber-600 flex items-center gap-1.5">
              <Globe className="w-3 h-3" />
              Buscando ao vivo nos sites dos mercados — pode ser mais lento.
            </p>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">{error}</div>
        )}

        {results && (
          <div className="space-y-3">
            {results.corrected_query && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-center gap-2 text-sm">
                <span className="text-amber-600">Mostrando resultados para:</span>
                <button
                  onClick={() => handleSearch(results.corrected_query!)}
                  className="font-semibold text-brand-700 hover:underline"
                >
                  {results.corrected_query}
                </button>
              </div>
            )}

            <div className="flex items-center gap-2 text-xs">
              <span className="text-gray-500">Ordenar:</span>
              <button
                onClick={() => setSortBy('relevance')}
                className={`px-3 py-1 rounded-full transition-colors ${sortBy === 'relevance' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                Relevância
              </button>
              <button
                onClick={() => setSortBy('price')}
                className={`px-3 py-1 rounded-full transition-colors ${sortBy === 'price' ? 'bg-brand-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >
                Menor Preço
              </button>
            </div>

            <ResultsTable
              data={sortedResults!}
              onExportPDF={() => handleExport('pdf')}
              onExportExcel={() => handleExport('excel')}
              onExportCSV={() => handleExport('csv')}
            />
          </div>
        )}

        {!loading && !results && !error && (
          <div className="card text-center py-12 md:py-16">
            <p className="text-4xl mb-3">🔍</p>
            <p className="text-lg font-semibold text-gray-700">Pesquise um produto acima</p>
            <p className="text-sm text-gray-400 mt-1">Resultados ordenados do menor para o maior preço</p>
            <div className="mt-4 flex flex-col sm:flex-row items-center justify-center gap-2 text-xs text-gray-400">
              <span className="flex items-center gap-1"><Database className="w-3 h-3" /> Banco: busca nos dados já coletados</span>
              <span className="hidden sm:inline">·</span>
              <span className="flex items-center gap-1"><Globe className="w-3 h-3" /> Ao vivo: consulta os sites em tempo real</span>
            </div>
          </div>
        )}
      </div>
    </AuthGuard>
  )
}
