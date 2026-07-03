import React from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiKPI } from '../../api'
import { Wallet, Package, Bell, ShieldCheck } from 'lucide-react'

const cards = [
  { key: 'avg_harga', label: 'Rata-rata Harga Nasional', icon: Wallet, color: 'text-emerald-600 bg-emerald-50', format: v => `Rp${Number(v).toLocaleString('id-ID')}` },
  { key: 'komoditas_count', label: 'Komoditas Dipantau', icon: Package, color: 'text-blue-600 bg-blue-50', format: v => `${v}` },
  { key: 'alerts', label: 'Alert Aktif', icon: Bell, color: 'text-red-600 bg-red-50', format: v => `${v}` },
  { key: 'prediksi_stabil', label: 'Prediksi Stabil', icon: ShieldCheck, color: 'text-primary-dark bg-primary-light', format: v => `${v}` },
]

export default function KpiCards() {
  const { queryString } = useFilter()
  const [data, setData] = React.useState(null)

  React.useEffect(() => {
    apiKPI(queryString).then(setData).catch(() => {})
  }, [queryString])

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map(card => {
        const Icon = card.icon
        const value = data ? card.format(data[card.key]) : '...'
        return (
          <div key={card.key} className="bg-white rounded-xl shadow-card p-5 flex items-center gap-4">
            <div className={`w-12 h-12 rounded-xl ${card.color} flex items-center justify-center shrink-0`}>
              <Icon size={22} />
            </div>
            <div>
              <p className="text-xs text-text-muted">{card.label}</p>
              <p className="text-xl font-bold text-text-primary mt-0.5">{value}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
