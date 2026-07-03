import React, { useState, useEffect } from 'react'
import ReactEChartsCore from 'echarts-for-react'
import * as echarts from 'echarts'
import { apiRisiko } from '../../api'

export default function GaugeRisiko() {
  const [alertCount, setAlertCount] = useState(0)

  useEffect(() => {
    apiRisiko().then(d => setAlertCount(d.alert_count)).catch(() => {})
  }, [])

  const level = alertCount === 0 ? 'Normal' : alertCount <= 2 ? 'Waspada' : 'Tinggi'
  const color = alertCount === 0 ? '#22C55E' : alertCount <= 2 ? '#F59E0B' : '#EF4444'

  const option = {
    series: [{
      type: 'gauge',
      startAngle: 180,
      endAngle: 0,
      min: 0,
      max: 10,
      center: ['50%', '60%'],
      radius: '90%',
      axisLine: {
        lineStyle: { width: 12, color: [
          [alertCount / 10, color],
          [1, '#F3F4F6'],
        ]},
      },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      detail: {
        offsetCenter: [0, 20],
        fontSize: 24,
        fontWeight: 700,
        color: '#111827',
        formatter: `${alertCount}\n{sub|${level}}`,
        rich: { sub: { fontSize: 12, color: '#6B7280', fontWeight: 400, padding: [4, 0, 0, 0] } },
      },
      data: [{ value: alertCount }],
    }],
  }

  return (
    <div className="bg-white rounded-xl shadow-card p-5 flex flex-col items-center">
      <h3 className="text-sm font-semibold text-text-primary mb-1 self-start">🚨 Gauge Risiko Alert</h3>
      <ReactEChartsCore option={option} style={{ height: 180, width: '100%' }} />
    </div>
  )
}
