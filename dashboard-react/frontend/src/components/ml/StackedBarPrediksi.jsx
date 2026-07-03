import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts'
import { apiPrediksiPerHari } from '../../api'

const COLORS = { STABIL: '#22C55E', NAIK: '#EF4444', TURUN: '#3B82F6' }

export default function StackedBarPrediksi() {
  const [series, setSeries] = useState([])

  useEffect(() => {
    apiPrediksiPerHari().then(s => setSeries(s)).catch(() => {})
  }, [])

  if (series.length === 0) return null

  const sorted = [...series].sort((a, b) => a.name.localeCompare(b.name))

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: p => p.map(s => `${s.marker} ${s.seriesName}: <b>${s.value}</b>`).join('<br/>'),
    },
    legend: { bottom: 0, textStyle: { fontSize: 10 } },
    grid: { left: 50, right: 20, top: 10, bottom: 40 },
    xAxis: {
      type: 'time',
      axisLabel: { fontSize: 9, color: '#9CA3AF' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 9, color: '#9CA3AF' },
      splitLine: { lineStyle: { color: '#F3F4F6' } },
    },
    series: sorted.map(s => ({
      name: s.name,
      type: 'bar',
      stack: 'total',
      barWidth: '60%',
      data: s.data,
      itemStyle: { color: COLORS[s.name] || '#9CA3AF', borderRadius: 0 },
    })),
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">📅 Prediksi per Hari (Stacked Bar)</h3>
      <ReactEChartsCore option={option} style={{ height: 250 }} />
    </div>
  )
}
