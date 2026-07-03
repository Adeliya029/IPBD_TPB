import React, { useState, useEffect } from 'react'
import { useFilter } from '../../context/FilterContext'
import { apiKorelasi } from '../../api'
import { Thermometer, CloudRain, Droplets } from 'lucide-react'

const items = [
  { key: 'suhu_harga', label: 'Suhu vs Harga', icon: Thermometer, desc: v => Math.abs(v) < 0.1 ? 'Tidak ada korelasi' : v > 0 ? 'Positif lemah' : 'Negatif lemah' },
  { key: 'hujan_harga', label: 'Hujan vs Harga', icon: CloudRain, desc: v => Math.abs(v) < 0.1 ? 'Tidak ada korelasi' : v > 0 ? 'Positif lemah' : 'Negatif lemah' },
  { key: 'lembab_harga', label: 'Kelembapan vs Harga', icon: Droplets, desc: v => Math.abs(v) < 0.1 ? 'Tidak ada korelasi' : v > 0 ? 'Positif lemah' : 'Negatif lemah' },
]

export default function KorelasiCards() {
  const { queryString } = useFilter()
  const [data, setData] = useState(null)

  useEffect(() => {
    apiKorelasi(queryString).then(d => setData(d)).catch(() => {})
  }, [queryString])

  if (!data) return null

  return (
    <div className="grid grid-cols-3 gap-4">
      {items.map(item => {
        const Icon = item.icon
        const val = data[item.key]
        const absVal = Math.abs(val)
        const color = absVal < 0.1 ? 'text-gray-500 bg-gray-50' :
                      val > 0 ? 'text-orange-600 bg-orange-50' :
                      'text-emerald-600 bg-emerald-50'
        return (
          <div key={item.key} className="bg-white rounded-xl shadow-card p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-8 h-8 rounded-lg ${color} flex items-center justify-center`}>
                <Icon size={16} />
              </div>
              <p className="text-xs font-medium text-text-primary">{item.label}</p>
            </div>
            <p className={`text-lg font-bold ${color.split(' ')[0]}`}>{val.toFixed(4)}</p>
            <p className="text-[10px] text-text-muted mt-0.5">{item.desc(val)}</p>
          </div>
        )
      })}
    </div>
  )
}
