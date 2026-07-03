import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const FilterContext = createContext()

export function FilterProvider({ children }) {
  const [filters, setFilters] = useState({
    startDate: '2026-01-01',
    endDate: '2026-05-31',
    provinsi: 'all',
    komoditas: 'all',
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [activeSection, setActiveSection] = useState('dashboard')
  const [dateRange, setDateRange] = useState({ min: '2026-01-01', max: '2026-05-31' })
  const [provinsiList, setProvinsiList] = useState([])
  const [komoditasList, setKomoditasList] = useState([])

  useEffect(() => {
    fetch('/api/filter-options')
      .then(r => r.json())
      .then(data => {
        setProvinsiList(data.provinsi || [])
        setKomoditasList(data.komoditas || [])
        if (data.date_range) {
          setDateRange(data.date_range)
          setFilters(prev => ({
            ...prev,
            startDate: data.date_range.min || prev.startDate,
            endDate: data.date_range.max || prev.endDate,
          }))
        }
      })
      .catch(() => {})
  }, [])

  const updateFilter = useCallback((key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }, [])

  const params = new URLSearchParams()
  if (filters.startDate) params.set('start', filters.startDate)
  if (filters.endDate) params.set('end', filters.endDate)
  if (filters.provinsi && filters.provinsi !== 'all') params.set('provinsi', filters.provinsi)
  if (filters.komoditas && filters.komoditas !== 'all') params.set('komoditas', filters.komoditas)
  const queryString = params.toString()

  return (
    <FilterContext.Provider value={{
      filters, updateFilter, searchQuery, setSearchQuery,
      activeSection, setActiveSection,
      dateRange, provinsiList, komoditasList, queryString,
    }}>
      {children}
    </FilterContext.Provider>
  )
}

export const useFilter = () => useContext(FilterContext)
