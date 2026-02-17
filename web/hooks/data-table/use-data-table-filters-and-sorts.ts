"use client"

import { useState, useCallback, useEffect } from "react"
import { getOperators, getDefaultOperator } from "@/components/data-table/filter"
import type { ColumnFilter, ColumnSort } from "@/components/data-table/types"
import type { ServerPaginationParams } from "@/types/filters"

export interface AvailableFilterColumn {
  id: string
  label: string
  canFilter: boolean
  filterConfig: import("@/components/data-table/filter").FilterColumnConfig
}

export interface UseDataTableFiltersAndSortsOptions {
  serverPagination?: boolean
  serverParams?: Partial<ServerPaginationParams>
  onClearAll?: () => void
}

export interface UseDataTableFiltersAndSortsReturn {
  advancedFilters: ColumnFilter[]
  setAdvancedFilters: React.Dispatch<React.SetStateAction<ColumnFilter[]>>
  advancedSorts: ColumnSort[]
  setAdvancedSorts: React.Dispatch<React.SetStateAction<ColumnSort[]>>
  openFilterPickerIndex: number | null
  setOpenFilterPickerIndex: (index: number | null) => void
  addSort: () => void
  removeSort: (index: number) => void
  updateSort: (index: number, updates: Partial<Pick<ColumnSort, "columnId" | "direction">>) => void
  moveSortUp: (index: number) => void
  moveSortDown: (index: number) => void
  addFilter: (availableColumns: AvailableFilterColumn[]) => void
  removeFilter: (index: number) => void
  updateFilter: (
    index: number,
    updates: Partial<ColumnFilter>,
    availableColumns: AvailableFilterColumn[]
  ) => void
  clearAllFilters: () => void
}

export function useDataTableFiltersAndSorts(
  options: UseDataTableFiltersAndSortsOptions = {}
): UseDataTableFiltersAndSortsReturn {
  const { serverPagination = false, serverParams, onClearAll } = options

  const [advancedFilters, setAdvancedFilters] = useState<ColumnFilter[]>([])
  const [advancedSorts, setAdvancedSorts] = useState<ColumnSort[]>([])
  const [openFilterPickerIndex, setOpenFilterPickerIndex] = useState<number | null>(null)

  useEffect(() => {
    if (serverPagination && serverParams?.sort) {
      const parts = serverParams.sort.split(",").filter(Boolean)
      const sorts = parts.map((p) => {
        const [col, dir] = p.includes(":") ? p.split(":") : [p, "asc"]
        return {
          columnId: col.trim(),
          direction: (dir?.trim() || "asc") as "asc" | "desc",
        }
      })
      setAdvancedSorts(sorts)
    }
  }, [serverPagination, serverParams?.sort])

  const addSort = useCallback(() => {
    setAdvancedSorts((prev) => [...prev, { columnId: "", direction: "asc" as const }])
  }, [])

  const removeSort = useCallback((index: number) => {
    setAdvancedSorts((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const updateSort = useCallback(
    (index: number, updates: Partial<Pick<ColumnSort, "columnId" | "direction">>) => {
      setAdvancedSorts((prev) =>
        prev.map((s, i) => (i === index ? { ...s, ...updates } : s))
      )
    },
    []
  )

  const moveSortUp = useCallback((index: number) => {
    if (index === 0) return
    setAdvancedSorts((prev) => {
      const newSorts = [...prev]
      ;[newSorts[index - 1], newSorts[index]] = [newSorts[index], newSorts[index - 1]]
      return newSorts
    })
  }, [])

  const moveSortDown = useCallback((index: number) => {
    setAdvancedSorts((prev) => {
      if (index >= prev.length - 1) return prev
      const newSorts = [...prev]
      ;[newSorts[index], newSorts[index + 1]] = [newSorts[index + 1], newSorts[index]]
      return newSorts
    })
  }, [])

  const addFilter = useCallback((availableColumns: AvailableFilterColumn[]) => {
    const firstAvailable = availableColumns.find((col) => col.canFilter)
    if (firstAvailable) {
      const ops = getOperators(firstAvailable.filterConfig)
      const op = getDefaultOperator(firstAvailable.filterConfig)
      const actualOp = ops.includes(op) ? op : ops[0]
      setAdvancedFilters((prev) => [
        ...prev,
        {
          columnId: firstAvailable.id,
          operator: actualOp,
          value: "",
        },
      ])
    }
  }, [])

  const removeFilter = useCallback((index: number) => {
    setAdvancedFilters((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const updateFilter = useCallback(
    (
      index: number,
      updates: Partial<ColumnFilter>,
      availableColumns: AvailableFilterColumn[]
    ) => {
      setAdvancedFilters((prev) =>
        prev.map((f, i) => {
          if (i !== index) return f
          const next = { ...f, ...updates }
          if ("columnId" in updates && updates.columnId) {
            const col = availableColumns.find((c) => c.id === updates.columnId)
            const ops = col ? getOperators(col.filterConfig) : []
            if (ops.length && !ops.includes(next.operator)) {
              next.operator = ops[0]
              next.value = ""
              next.dateFrom = undefined
              next.dateTo = undefined
            }
          }
          return next
        })
      )
    },
    []
  )

  const clearAllFilters = useCallback(() => {
    setAdvancedFilters([])
    setAdvancedSorts([])
    setOpenFilterPickerIndex(null)
    onClearAll?.()
  }, [onClearAll])

  return {
    advancedFilters,
    setAdvancedFilters,
    advancedSorts,
    setAdvancedSorts,
    openFilterPickerIndex,
    setOpenFilterPickerIndex,
    addSort,
    removeSort,
    updateSort,
    moveSortUp,
    moveSortDown,
    addFilter,
    removeFilter,
    updateFilter,
    clearAllFilters,
  }
}
