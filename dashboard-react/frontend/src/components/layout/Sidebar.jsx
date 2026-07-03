import React from 'react'
import { useFilter } from '../../context/FilterContext'
import {
  LayoutDashboard, TrendingUp, Globe, Cloud, Cpu,
} from 'lucide-react'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'harga', label: 'Analitik Harga', icon: TrendingUp },
  { id: 'wilayah', label: 'Wilayah', icon: Globe },
  { id: 'cuaca', label: 'Cuaca', icon: Cloud },
  { id: 'ml', label: 'Machine Learning', icon: Cpu },
]

export default function Sidebar() {
  const { activeSection, setActiveSection } = useFilter()

  return (
    <aside className="w-60 h-screen bg-white border-r border-border flex flex-col shrink-0">
      <div className="px-5 py-6 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-white font-bold text-sm">IP</span>
          </div>
          <div>
            <h1 className="font-semibold text-sm text-text-primary">IPBD</h1>
            <p className="text-xs text-text-muted">Harga Pangan</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(item => {
          const Icon = item.icon
          const active = activeSection === item.id
          return (
            <button
              key={item.id}
              onClick={() => setActiveSection(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                active
                  ? 'bg-primary-light text-primary-dark'
                  : 'text-text-muted hover:bg-gray-50 hover:text-text-primary'
              }`}
            >
              <Icon size={18} strokeWidth={active ? 2.5 : 1.5} />
              {item.label}
            </button>
          )
        })}
      </nav>
      <div className="px-5 py-4 border-t border-border">
        <p className="text-xs text-text-muted">© 2026 IPBD</p>
      </div>
    </aside>
  )
}
