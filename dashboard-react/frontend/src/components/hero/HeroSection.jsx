import React from 'react'
import { useFilter } from '../../context/FilterContext'

export default function HeroSection() {
  const { filters, provinsiList } = useFilter()
  const provName = filters.provinsi !== 'all'
    ? provinsiList.find(p => p.kode === filters.provinsi)?.nama || filters.provinsi
    : 'Nasional'

  return (
    <div className="bg-white rounded-xl shadow-card p-6 flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold text-text-primary flex items-center gap-2">
          Selamat Datang 👋
          {filters.komoditas !== 'all' && (
            <span className="text-sm font-normal text-text-muted">— {filters.komoditas}</span>
          )}
        </h1>
        <p className="text-text-muted text-sm mt-1">
          Dashboard Analitik Harga Pangan {provName}
        </p>
        <p className="text-xs text-text-muted mt-0.5">
          Memantau harga 17 komoditas di 6 provinsi secara realtime.
          {filters.startDate && filters.endDate && (
            <span> Periode: {new Date(filters.startDate).toLocaleDateString('id-ID', {day:'numeric',month:'short',year:'numeric'})} – {new Date(filters.endDate).toLocaleDateString('id-ID', {day:'numeric',month:'short',year:'numeric'})}</span>
          )}
        </p>
      </div>
      <img src="/src/assets/hero-agriculture.svg" alt="Ilustrasi pertanian"
        className="w-48 h-24 object-contain opacity-80" />
    </div>
  )
}
