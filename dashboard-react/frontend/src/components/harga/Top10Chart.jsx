import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts'
import { useFilter } from '../../context/FilterContext'
import { apiTop10 } from '../../api'

export default function Top10Chart() {
  const { queryString } = useFilter()
  const [data, setData] = useState([])

  useEffect(() => {
    apiTop10(queryString).then(d => setData(d.slice(0, 10))).catch(() => {})
  }, [queryString])

  if (data.length === 0) return null

  const names = data.map(d => d.komoditas).reverse()
  const values = data.map(d => d.value).reverse()

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: p => `${p[0].name}: <b>Rp${Number(p[0].value).toLocaleString('id-ID')}</b>`,
    },
    grid: { left: 140, right: 20, top: 10, bottom: 10, containLabel: true },
    xAxis: { type: 'value', axisLabel: { formatter: v => `Rp${(v/1000).toFixed(0)}k`, fontSize: 10 }, splitLine: { lineStyle: { color: '#F3F4F6' } } },
    yAxis: { type: 'category', data: names, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { fontSize: 10, fontWeight: 500 } },
    series: [{
      type: 'bar',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#DCFCE7' },
            { offset: 1, color: '#22C55E' },
          ]),
          borderRadius: [0, 6, 6, 0],
        },
      })),
      barWidth: 18,
      label: {
        show: true,
        position: 'right',
        formatter: p => `Rp${Number(p.value).toLocaleString('id-ID')}`,
        fontSize: 9,
        color: '#6B7280',
      },
    }],
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5">
      <h3 className="text-sm font-semibold text-text-primary mb-3">🏆 Top 10 Komoditas Termahal</h3>
      <ReactEChartsCore option={option} style={{ height: 280 }} />
    </div>
  )
}
