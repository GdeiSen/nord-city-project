"use client"

import { useEffect, useRef } from "react"
import type { FilterItem, ServerPaginationParams } from "@/types/filters"

export interface UseServerParamsSyncOptions {
  serverPagination: boolean
  onServerParamsChange?: (params: ServerPaginationParams) => void
  /** Called when search or filters change (reset page to 0) */
  onSearchOrFiltersChange?: () => void
  debouncedSearch: string
  advancedSorts: { columnId: string; direction: string }[]
  serverFilters: FilterItem[] | undefined
  searchColumns: string[] | undefined
  pageIndex: number
  pageSize: number
}

/**
 * Syncs internal table state (search, filters, sorts, pagination) to parent via onServerParamsChange.
 * Always syncs so pagination clicks work on first interaction after load.
 */
export function useServerParamsSync({
  serverPagination,
  onServerParamsChange,
  onSearchOrFiltersChange,
  debouncedSearch,
  advancedSorts,
  serverFilters,
  searchColumns,
  pageIndex,
  pageSize,
}: UseServerParamsSyncOptions): void {
  const prevSearchRef = useRef(debouncedSearch)
  const prevFiltersRef = useRef("")
  const mountedRef = useRef(false)

  useEffect(() => {
    if (!serverPagination || !onServerParamsChange) return

    const searchChanged = prevSearchRef.current !== debouncedSearch
    prevSearchRef.current = debouncedSearch

    const filtersStr = JSON.stringify(serverFilters ?? [])
    const filtersChanged = prevFiltersRef.current !== filtersStr
    prevFiltersRef.current = filtersStr

    if (mountedRef.current && (searchChanged || filtersChanged)) {
      onSearchOrFiltersChange?.()
    }
    mountedRef.current = true

    const sortStr = advancedSorts
      .filter((s) => s.columnId)
      .map((s) => `${s.columnId}:${s.direction}`)
      .join(",")

    onServerParamsChange({
      pageIndex: searchChanged || filtersChanged ? 0 : pageIndex,
      pageSize,
      search: debouncedSearch,
      sort: sortStr,
      searchColumns: searchColumns ?? undefined,
      filters: serverFilters,
    })
  }, [
    serverPagination,
    onServerParamsChange,
    debouncedSearch,
    advancedSorts,
    serverFilters,
    searchColumns,
    pageIndex,
    pageSize,
  ])
}
