"use client"

import { useState, useEffect, useCallback } from "react"
import { toast } from "sonner"
import type { ServerPaginationParams, FilterItem } from "@/types/filters"
import { useLoading } from "@/hooks/ui/use-loading"

interface PaginatedResponse<T> {
  items: T[]
  total: number
}

interface ApiWithGetPaginated<T> {
  getPaginated(params: {
    page?: number
    pageSize?: number
    search?: string
    sort?: string
    searchColumns?: string[]
    filters?: FilterItem[]
  }): Promise<PaginatedResponse<T>>
}

interface UseServerPaginatedDataOptions<T> {
  /** API with getPaginated method */
  api: ApiWithGetPaginated<T>
  /** Initial server params */
  initialParams?: Partial<ServerPaginationParams>
  /** Custom error message for toast on fetch failure */
  errorMessage?: string
}

export function useServerPaginatedData<T>({
  api,
  initialParams,
  errorMessage = "Не удалось загрузить данные",
}: UseServerPaginatedDataOptions<T>) {
  const { loading, withLoading } = useLoading(true)
  const [data, setData] = useState<T[]>([])
  const [total, setTotal] = useState(0)
  const [serverParams, setServerParams] = useState<ServerPaginationParams>({
    pageIndex: 0,
    pageSize: 10,
    search: "",
    sort: "",
    ...initialParams,
  })

  const refetch = useCallback(async () => {
    await withLoading(async () => {
      const res = await api.getPaginated({
        page: serverParams.pageIndex + 1,
        pageSize: serverParams.pageSize,
        search: serverParams.search || undefined,
        sort: serverParams.sort || undefined,
        searchColumns: serverParams.searchColumns?.length ? serverParams.searchColumns : undefined,
        filters: serverParams.filters?.length ? serverParams.filters : undefined,
      })
      setData(res.items)
      setTotal(res.total)
    })
  }, [
    api,
    serverParams.pageIndex,
    serverParams.pageSize,
    serverParams.search,
    serverParams.sort,
    serverParams.searchColumns,
    serverParams.filters,
    withLoading,
  ])

  useEffect(() => {
    refetch().catch((err: unknown) => {
      toast.error(errorMessage, {
        description: err instanceof Error ? err.message : "Unknown error",
      })
      console.error(err)
    })
  }, [refetch, errorMessage])

  return { data, total, loading, serverParams, setServerParams, refetch }
}
