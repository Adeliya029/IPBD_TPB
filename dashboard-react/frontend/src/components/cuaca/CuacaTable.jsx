import React, { useState, useEffect } from 'react'
import { apiCuacaRealtime } from '../../api'

export default function CuacaTable() {
  const [data, setData] = useState([])

  useEffect(() => {
    apiCuacaRealtime().then(d => setData(Array.isArray(d) ? d.slice(0, 15) : [])).catch(() => {})
  }, [])

  if (data.length === 0) return null

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">🌤️ Cuaca Realtime Terkini</h3>
      <div className="overflow-x-auto max-h-[280px] overflow-y-auto scrollbar-thin">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b border-border">
              <th className="text-left py-2 px-2 font-medium text-text-muted">Kota</th>
              <th className="text-left py-2 px-2 font-medium text-text-muted">Prov</th>
              <th className="text-right py-2 px-2 font-medium text-text-muted">Suhu</th>
              <th className="text-right py-2 px-2 font-medium text-text-muted">Hujan</th>
              <th className="text-right py-2 px-2 font-medium text-text-muted">Lembab</th>
              <th className="text-right py-2 px-2 font-medium text-text-muted">Angin</th>
              <th className="text-left py-2 px-2 font-medium text-text-muted">Cluster</th>
            </tr>
          </thead>
          <tbody>
            {data.map((r, i) => (
              <tr key={i} className="border-b border-border/50 hover:bg-gray-50/50">
                <td className="py-1.5 px-2 text-text-primary font-medium">{r.kab_kota}</td>
                <td className="py-1.5 px-2 text-text-muted">{r.provinsi}</td>
                <td className={`py-1.5 px-2 text-right font-medium ${
                  r.suhu_mean > 33 ? 'text-red-500' : r.suhu_mean > 28 ? 'text-orange-500' : 'text-blue-500'
                }`}>{r.suhu_mean}°</td>
                <td className="py-1.5 px-2 text-right text-text-muted">{r.hujan_mm}mm</td>
                <td className="py-1.5 px-2 text-right text-text-muted">{r.lembab}%</td>
                <td className="py-1.5 px-2 text-right text-text-muted">{r.angin} km/h</td>
                <td className="py-1.5 px-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                    r.cluster_nama?.includes('Normal') ? 'bg-emerald-50 text-emerald-600' :
                    r.cluster_nama?.includes('Kering') ? 'bg-orange-50 text-orange-600' :
                    'bg-blue-50 text-blue-600'
                  }`}>{r.cluster_nama || '–'}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
