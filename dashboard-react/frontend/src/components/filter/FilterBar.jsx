import React, { useState, useRef, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { Search, Download, FileText, X } from 'lucide-react'

export default function FilterBar() {
  const { filters, updateFilter, searchQuery, setSearchQuery, provinsiList, komoditasList, dateRange } = useFilter()
  const [showSearch, setShowSearch] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const searchRef = useRef(null)
  const exportRef = useRef(null)

  const filteredKomoditas = komoditasList.filter(k =>
    k.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleExport = async (format) => {
    if (format === 'csv') {
      const qs = new URLSearchParams()
      if (filters.startDate) qs.set('start', filters.startDate)
      if (filters.endDate) qs.set('end', filters.endDate)
      if (filters.provinsi !== 'all') qs.set('provinsi', filters.provinsi)
      if (filters.komoditas !== 'all') qs.set('komoditas', filters.komoditas)
      window.open(`/api/export/csv?${qs.toString()}`, '_blank')
    }
    setShowExport(false)
  }

  const handleExportPDF = async () => {
    const html2canvas = (await import('html2canvas')).default
    const jsPDF = (await import('jspdf')).default
    const el = document.getElementById('main-content')
    if (!el) return
    const canvas = await html2canvas(el, { scale: 2, useCORS: true, backgroundColor: '#F5F7FB' })
    const imgData = canvas.toDataURL('image/png')
    const pdf = new jsPDF('l', 'mm', 'a3')
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = (canvas.height * pageWidth) / canvas.width
    pdf.addImage(imgData, 'PNG', 0, 0, pageWidth, pageHeight)
    pdf.save('dashboard-harga-pangan.pdf')
    setShowExport(false)
  }

  useEffect(() => {
    const handler = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) setShowSearch(false)
      if (exportRef.current && !exportRef.current.contains(e.target)) setShowExport(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Date Range */}
      <div className="flex items-center gap-2 bg-white border border-border rounded-xl px-3 py-2 text-sm">
        <span className="text-text-muted text-xs">📅</span>
        <input type="date" value={filters.startDate}
          onChange={e => updateFilter('startDate', e.target.value)}
          min={dateRange.min} max={dateRange.max}
          className="text-xs text-text-primary bg-transparent outline-none w-[110px]" />
        <span className="text-text-muted">–</span>
        <input type="date" value={filters.endDate}
          onChange={e => updateFilter('endDate', e.target.value)}
          min={dateRange.min} max={dateRange.max}
          className="text-xs text-text-primary bg-transparent outline-none w-[110px]" />
      </div>

      {/* Provinsi Dropdown */}
      <select value={filters.provinsi}
        onChange={e => updateFilter('provinsi', e.target.value)}
        className="bg-white border border-border rounded-xl px-3 py-2 text-xs text-text-primary outline-none cursor-pointer">
        <option value="all">🌎 Semua Provinsi</option>
        {provinsiList.map(p => (
          <option key={p.kode} value={p.kode}>{p.nama}</option>
        ))}
      </select>

      {/* Search */}
      <div className="relative" ref={searchRef}>
        <button onClick={() => setShowSearch(!showSearch)}
          className="flex items-center gap-1.5 bg-white border border-border rounded-xl px-3 py-2 text-xs text-text-muted hover:text-text-primary transition-colors">
          <Search size={14} /> Cari Komoditas
        </button>
        {showSearch && (
          <div className="absolute top-full mt-1 left-0 w-64 bg-white border border-border rounded-xl shadow-lg z-50 p-2">
            <div className="flex items-center gap-2 px-2 py-1 border-b border-border mb-1">
              <Search size={14} className="text-text-muted" />
              <input autoFocus
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Cari komoditas..."
                className="flex-1 text-xs outline-none py-1" />
              {searchQuery && (
                <button onClick={() => { setSearchQuery(''); setShowSearch(false) }}>
                  <X size={14} className="text-text-muted" />
                </button>
              )}
            </div>
            <div className="max-h-40 overflow-y-auto">
              {filteredKomoditas.slice(0, 10).map(k => (
                <button key={k}
                  onClick={() => {
                    updateFilter('komoditas', k)
                    setSearchQuery(k)
                    setShowSearch(false)
                  }}
                  className={`w-full text-left px-2 py-1.5 text-xs rounded-lg transition-colors ${
                    filters.komoditas === k ? 'bg-primary-light text-primary-dark font-medium' : 'hover:bg-gray-50'
                  }`}>
                  {k}
                </button>
              ))}
              {filteredKomoditas.length === 0 && (
                <p className="text-xs text-text-muted text-center py-2">Tidak ditemukan</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Komoditas Tag */}
      {filters.komoditas !== 'all' && (
        <span className="flex items-center gap-1 bg-primary-light text-primary-dark text-xs font-medium px-2.5 py-1.5 rounded-full">
          {filters.komoditas}
          <button onClick={() => { updateFilter('komoditas', 'all'); setSearchQuery('') }}>
            <X size={12} />
          </button>
        </span>
      )}

      {/* Export */}
      <div className="relative ml-auto" ref={exportRef}>
        <button onClick={() => setShowExport(!showExport)}
          className="flex items-center gap-1.5 bg-white border border-border rounded-xl px-3 py-2 text-xs text-text-muted hover:text-text-primary transition-colors">
          <Download size={14} /> Export
        </button>
        {showExport && (
          <div className="absolute top-full mt-1 right-0 w-36 bg-white border border-border rounded-xl shadow-lg z-50 p-1">
            <button onClick={() => handleExport('pdf')}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-text-primary hover:bg-gray-50 rounded-lg">
              <FileText size={14} /> Export PDF
            </button>
            <button onClick={() => handleExport('csv')}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-text-primary hover:bg-gray-50 rounded-lg">
              <Download size={14} /> Export CSV
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
