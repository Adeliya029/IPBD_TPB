import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import { apiPrediksi, apiCluster } from '../../api'

const PREDIKSI_COLORS = { STABIL: '#22C55E', NAIK: '#EF4444', TURUN: '#3B82F6' }
const CLUSTER_COLORS = ['#22C55E', '#F59E0B', '#3B82F6', '#8B5CF6']

function PieChartCard({ title, fetchFn, colors }) {
  const [data, setData] = useState([])

  useEffect(() => {
    fetchFn().then(d => setData(d)).catch(() => {})
  }, [])

  if (data.length === 0) return null

  const option = {
    tooltip: { trigger: 'item', formatter: p => `${p.name}: <b>${p.value}</b> (${p.percent}%)` },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, position: 'outside', formatter: p => `${p.percent}%`, fontSize: 10, fontWeight: 600 },
      emphasis: { label: { show: true, fontSize: 12 } },
      data: data.map(d => ({ name: d.label || d.name, value: d.value, itemStyle: { color: colors[d.label] || colors[0] } })),
    }],
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-1">{title}</h3>
      <ReactEChartsCore option={option} style={{ height: 200 }} />
    </div>
  )
}

export function PiePrediksi() {
  return <PieChartCard title="🤖 Distribusi Prediksi ML" fetchFn={apiPrediksi} colors={PREDIKSI_COLORS} />
}

export function PieCluster() {
  return <PieChartCard title="🔵 Distribusi Cluster (K-Means)" fetchFn={apiCluster} colors={CLUSTER_COLORS} />
}
