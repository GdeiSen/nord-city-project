"use client"

import * as React from "react"
import {
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
  IconLayoutColumns,
  IconDotsVertical,
  IconPlus,
  IconTrash,
  IconEdit,
  IconCopy,
  IconEyeOff,
  IconSearch,
  IconSearchOff,
  IconX,
  IconDownload,
} from "@tabler/icons-react"
import type { Column } from "@tanstack/react-table"
import {
  ColumnDef,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  Row,
  SortingState,
  useReactTable,
  VisibilityState,
} from "@tanstack/react-table"
import { toast } from "sonner"
import { z } from "zod"

import { useIsMobile } from "@/hooks/ui/use-mobile"
import { useDebounce } from "@/hooks/ui/use-debounce"
import { useDeleteDialog } from "@/hooks/ui/use-delete-dialog"
import { useDataTableFiltersAndSorts } from "@/hooks/data-table/use-data-table-filters-and-sorts"
import { useServerParamsSync } from "@/hooks/data-table/use-server-params-sync"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Spinner } from "@/components/ui/spinner"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { DataTableToolbar } from "./toolbar"
import { DataTableSortPanel } from "./sort"
import { DataTableFilterPanel } from "./filter"
import {
  getFilterConfigFromMeta,
  needsValue,
  createClientFilterFn,
} from "./filter"
import type { FilterItem, ServerPaginationParams } from "@/types/filters"
import type { GetExportParams } from "@/lib/api"
import type { ColumnFilter, ColumnSort, DataTableColumnMeta, DataTableContextMenuActions } from "./types"

/** Returns human-readable column label for column selector (header string or meta.headerLabel or id) */
function getColumnLabel(column: Column<unknown, unknown>): string {
  const header = column.columnDef.header
  if (typeof header === "string") return header
  const meta = (column.columnDef as { meta?: DataTableColumnMeta })?.meta
  if (meta?.headerLabel) return meta.headerLabel
  return column.id
}

/**
 * Zod schema for data table row validation
 */
export const schema = z.object({
  id: z.number(),
  header: z.string(),
  type: z.string(),
  status: z.string(),
  target: z.string(),
  limit: z.string(),
  reviewer: z.string(),
})

/** Unified select column for row selection. Use in all tables for consistent checkbox layout. */
export function createSelectColumn<TData>(): ColumnDef<TData> {
  return {
    id: "select",
    size: 40,
    minSize: 40,
    maxSize: 40,
    header: ({ table }) => (
      <div className="flex h-full w-10 shrink-0 items-center justify-center px-2">
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div className="flex h-full w-10 shrink-0 items-center justify-center px-2">
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableSorting: false,
    enableHiding: false,
  }
}

/**
 * Advanced data table component with sorting and filtering capabilities
 */
export function DataTable<TData>({
  data,
  columns,
  loading = false,
  loadingMessage = "Загрузка данных...",
  view = 'table',
  renderCard,
  cardsClassName,
  onRowClick,
  contextMenuActions,
  serverPagination = false,
  totalRowCount = 0,
  serverParams,
  onServerParamsChange,
  filterPickerData,
  exportConfig,
  getRowClassName,
}: {
  data: TData[]
  columns: ColumnDef<TData>[]
  loading?: boolean
  loadingMessage?: string
  view?: 'table' | 'cards'
  renderCard?: (row: Row<TData>) => React.ReactNode
  cardsClassName?: string
  onRowClick?: (row: Row<TData>) => void
  contextMenuActions?: DataTableContextMenuActions<TData>
  serverPagination?: boolean
  totalRowCount?: number
  serverParams?: Partial<ServerPaginationParams>
  onServerParamsChange?: (params: ServerPaginationParams) => void
  filterPickerData?: import("@/hooks/data/use-filter-picker-data").FilterPickerData
  exportConfig?: {
    getExport: (params: GetExportParams) => Promise<Blob>
    maxLimit?: number
    filename?: string
  }
  getRowClassName?: (row: Row<TData>) => string | undefined
}) {
  const pageSizeFromParams = serverParams?.pageSize ?? 10
  const isCardsView = view === "cards"
  const effectivePageSize =
    isCardsView && !serverPagination ? 10000 : pageSizeFromParams
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({})
  const [columnSearchActive, setColumnSearchActive] = React.useState<Record<string, boolean>>({})
  const [columnOrder, setColumnOrder] = React.useState<string[]>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState({
    pageIndex: serverParams?.pageIndex ?? 0,
    pageSize: effectivePageSize,
  })
  const [isSortFilterOpen, setIsSortFilterOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<'sort' | 'filter'>('sort')
  const [exportModalOpen, setExportModalOpen] = React.useState(false)
  const [exporting, setExporting] = React.useState(false)
  const [globalQuery, setGlobalQuery] = React.useState(serverParams?.search ?? "")
  const debouncedSearch = useDebounce(globalQuery, 300)
  const isMobile = useIsMobile()

  const deleteDialog = useDeleteDialog<Row<TData>>()

  const onClearAllFilters = React.useCallback(() => {
    setColumnFilters([])
    setSorting([])
    setPagination((p) => ({ pageIndex: 0, pageSize: p.pageSize }))
    setGlobalQuery("")
  }, [])

  const {
    advancedFilters,
    advancedSorts,
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
  } = useDataTableFiltersAndSorts({
    serverPagination,
    serverParams,
    onClearAll: onClearAllFilters,
  })

  const hasContextMenu = Boolean(
    contextMenuActions?.onEdit || contextMenuActions?.onDelete || contextMenuActions?.getCopyText
  )

  React.useEffect(() => {
    if (serverPagination && serverParams) {
      setPagination({
        pageIndex: serverParams.pageIndex ?? 0,
        pageSize: serverParams.pageSize ?? 10,
      })
      setGlobalQuery(serverParams.search ?? "")
    }
  }, [serverPagination, serverParams?.pageIndex, serverParams?.pageSize, serverParams?.search])

  React.useEffect(() => {
    const sortingState: SortingState = advancedSorts
      .filter(s => s.columnId)
      .map(s => ({ id: s.columnId, desc: s.direction === 'desc' }))
    setSorting(sortingState)
  }, [advancedSorts])

  React.useEffect(() => {
    const filterState: ColumnFiltersState = advancedFilters
      .filter(f =>
        f.operator === 'isEmpty' || f.operator === 'isNotEmpty' ||
        (needsValue(f.operator) && (f.value || f.dateFrom || f.dateTo))
      )
      .map(f => ({
        id: f.columnId,
        value: {
          operator: f.operator,
          value: f.value,
          dateFrom: f.dateFrom,
          dateTo: f.dateTo,
        }
      }))
    setColumnFilters(filterState)
  }, [advancedFilters])

  const renderSortFilterContent = () => (
    <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'sort' | 'filter')}>
      <div className="mb-3 flex items-center justify-between">
        <TabsList className="grid w-[200px] grid-cols-2">
          <TabsTrigger value="sort">Сортировка</TabsTrigger>
          <TabsTrigger value="filter">Фильтры</TabsTrigger>
        </TabsList>
        {(advancedFilters.length > 0 || advancedSorts.length > 0) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clearAllFilters}
            className="h-8 px-2"
          >
            <IconX className="h-4 w-4 mr-1" />
            Очистить
          </Button>
        )}
      </div>

      <TabsContent value="sort" className="mt-0">
        <DataTableSortPanel
          advancedSorts={advancedSorts}
          addSort={addSort}
          removeSort={removeSort}
          updateSort={updateSort}
          moveSortUp={moveSortUp}
          moveSortDown={moveSortDown}
          getSortColumnOptions={getSortColumnOptions}
          allSortColumnsUsed={allSortColumnsUsed}
          sortableColumns={availableColumns.filter((c) => c.canSort)}
          isMobile={isMobile}
        />
      </TabsContent>

      <TabsContent value="filter" className="mt-0">
        <DataTableFilterPanel
          advancedFilters={advancedFilters}
          addFilter={() => addFilter(availableColumns)}
          removeFilter={removeFilter}
          updateFilter={(index, updates) => updateFilter(index, updates, availableColumns)}
          availableColumns={availableColumns}
          filterPickerData={filterPickerData}
          openFilterPickerIndex={openFilterPickerIndex}
          onOpenFilterPickerIndexChange={setOpenFilterPickerIndex}
        />
      </TabsContent>
    </Tabs>
  )

  const customFilterFn = React.useMemo(() => createClientFilterFn(), [])

  const wrappedColumns = React.useMemo(
    () =>
      columns.map((col) => ({
        ...col,
        filterFn: customFilterFn as any,
      })) as ColumnDef<TData>[],
    [columns, customFilterFn]
  )

  const globalSearchFn = React.useCallback((row: any, _columnId: string, filterValue: string) => {
    const q = String(filterValue ?? '').toLowerCase().trim()
    if (!q) return true
    for (const cell of row.getVisibleCells()) {
      if (columnSearchActive[cell.column.id] === false) continue
      const value = row.getValue(cell.column.id)
      if (String(value ?? '').toLowerCase().includes(q)) return true
    }
    return false
  }, [columnSearchActive])

  const pageCount = serverPagination
    ? (totalRowCount === 0 ? 1 : Math.ceil(totalRowCount / pagination.pageSize) || 1)
    : undefined

  const table = useReactTable({
    data,
    columns: wrappedColumns as ColumnDef<unknown, unknown>[],
    state: {
      sorting,
      columnVisibility,
      columnOrder: columnOrder.length > 0 ? columnOrder : undefined,
      rowSelection,
      columnFilters,
      pagination,
      globalFilter: globalQuery,
    },
    onColumnOrderChange: setColumnOrder,
    getRowId: (row) => (row as any).id.toString(),
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    onGlobalFilterChange: setGlobalQuery,
    getCoreRowModel: getCoreRowModel(),
    ...(serverPagination
      ? {
          manualPagination: true,
          manualSorting: true,
          manualFiltering: true,
          pageCount: pageCount ?? -1,
          getFilteredRowModel: undefined,
          getSortedRowModel: undefined,
          getPaginationRowModel: undefined,
          getFacetedRowModel: undefined,
          getFacetedUniqueValues: undefined,
          globalFilterFn: undefined,
        }
      : {
          getFilteredRowModel: getFilteredRowModel(),
          getPaginationRowModel: getPaginationRowModel(),
          getSortedRowModel: getSortedRowModel(),
          getFacetedRowModel: getFacetedRowModel(),
          getFacetedUniqueValues: getFacetedUniqueValues(),
          globalFilterFn: globalSearchFn as any,
        }),
    meta: {
      globalQuery,
    },
  })

  const availableColumns = React.useMemo(() => {
    return table.getAllColumns()
      .filter(col => col.id !== 'select' && col.id !== 'actions')
      .map(col => {
        const meta = (col.columnDef as { meta?: DataTableColumnMeta })?.meta
        const header = col.columnDef.header
        const label = typeof header === 'string' ? header : col.id
        const filterConfig = getFilterConfigFromMeta({ ...meta, id: col.id })
        return {
          id: col.id,
          label,
          canSort: col.getCanSort(),
          canFilter: col.getCanFilter(),
          filterConfig,
        }
      })
  }, [table])

  const getSortColumnOptions = React.useCallback(
    (excludeIndex: number) => {
      const usedByOthers = new Set(
        advancedSorts
          .filter((_, i) => i !== excludeIndex)
          .map(s => s.columnId)
          .filter(Boolean)
      )
      return availableColumns.filter(
        col => col.canSort && (col.id === advancedSorts[excludeIndex]?.columnId || !usedByOthers.has(col.id))
      )
    },
    [availableColumns, advancedSorts]
  )

  const allSortColumnsUsed = React.useMemo(() => {
    const sortable = availableColumns.filter(col => col.canSort)
    if (sortable.length === 0) return true
    const usedIds = new Set(advancedSorts.map(s => s.columnId).filter(Boolean))
    return sortable.every(col => usedIds.has(col.id))
  }, [availableColumns, advancedSorts])

  const searchColumns = React.useMemo(() => {
    if (!serverPagination) return undefined
    try {
      const visible = table.getVisibleLeafColumns()
      const result: string[] = []
      const seen = new Set<string>()
      for (const col of visible) {
        if (col.id === "select" || col.id === "actions") continue
        if (columnSearchActive[col.id] === false) continue
        const meta = (col.columnDef as { meta?: DataTableColumnMeta })?.meta
        const dbCols = meta?.searchDbColumns
        const toAdd = Array.isArray(dbCols)
          ? dbCols
          : [col.id]
        for (const c of toAdd) {
          if (c && !seen.has(c)) {
            seen.add(c)
            result.push(c)
          }
        }
      }
      return result
    } catch {
      return undefined
    }
  }, [serverPagination, table, columnVisibility, columnOrder, columnSearchActive])

  const serverFilters = React.useMemo((): FilterItem[] | undefined => {
    const active = advancedFilters.filter(f =>
      f.operator === 'isEmpty' || f.operator === 'isNotEmpty' ||
      (f.operator === 'dateRange' ? (f.dateFrom || f.dateTo) : !!f.value)
    )
    if (active.length === 0) return undefined
    return active.map(f => {
      const colDef = table.getColumn(f.columnId)?.columnDef
      const meta = (colDef as { meta?: DataTableColumnMeta })?.meta
      const dbCol = meta?.filterDbColumn ?? f.columnId
      return {
        columnId: dbCol,
        operator: f.operator,
        value: f.value,
        dateFrom: f.dateFrom,
        dateTo: f.dateTo,
      }
    })
  }, [advancedFilters, table])

  const resetPageIndex = React.useCallback(
    () => setPagination((p) => ({ ...p, pageIndex: 0 })),
    []
  )

  const handleExport = React.useCallback(async () => {
    if (!exportConfig?.getExport || !serverPagination) return
    setExporting(true)
    try {
      const visibleCols = table.getVisibleLeafColumns()
        .filter((c) => c.id !== "select" && c.id !== "actions")
        .map((c) => c.id)
      if (visibleCols.length === 0) {
        toast.error("Нет видимых столбцов для экспорта")
        return
      }
      const sortStr = advancedSorts
        .filter((s) => s.columnId)
        .map((s) => `${s.columnId}:${s.direction}`)
        .join(",")
      const blob = await exportConfig.getExport({
        page: 1,
        pageSize: exportConfig.maxLimit ?? 10_000,
        search: debouncedSearch || undefined,
        sort: sortStr || undefined,
        searchColumns: searchColumns ?? undefined,
        filters: serverFilters,
        columns: visibleCols,
        limit: exportConfig.maxLimit ?? 10_000,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = exportConfig.filename ?? "export.csv"
      a.click()
      URL.revokeObjectURL(url)
      setExportModalOpen(false)
      toast.success("Экспорт завершён")
    } catch (e: any) {
      toast.error("Ошибка экспорта", { description: e?.message })
    } finally {
      setExporting(false)
    }
  }, [
    exportConfig,
    serverPagination,
    table,
    advancedSorts,
    debouncedSearch,
    searchColumns,
    serverFilters,
  ])

  useServerParamsSync({
    serverPagination,
    onServerParamsChange,
    onSearchOrFiltersChange: resetPageIndex,
    debouncedSearch,
    advancedSorts,
    serverFilters,
    searchColumns,
    pageIndex: pagination.pageIndex,
    pageSize: pagination.pageSize,
  })

  return (
    <div className="w-full min-w-0 flex flex-col gap-4">
      {!isCardsView && (
        <DataTableToolbar
          globalQuery={globalQuery}
          onGlobalQueryChange={setGlobalQuery}
          isSortFilterOpen={isSortFilterOpen}
          onSortFilterOpenChange={setIsSortFilterOpen}
          activeSortsCount={advancedSorts.length}
          activeFiltersCount={advancedFilters.length}
          sortFilterContent={renderSortFilterContent()}
          isMobile={isMobile}
        />
      )}
      {view === 'cards' ? (
        <div className={cn("grid gap-6 md:grid-cols-2 xl:grid-cols-3", cardsClassName)}>
          {loading ? (
            <div className="col-span-full">
              <Empty className="w-full">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <Spinner className="size-6" />
                  </EmptyMedia>
                  <EmptyTitle>{loadingMessage}</EmptyTitle>
                  <EmptyDescription>
                    Пожалуйста, подождите. Идет загрузка данных.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            </div>
          ) : table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <React.Fragment key={row.id}>
                {renderCard ? renderCard(row as Row<TData>) : null}
              </React.Fragment>
            ))
          ) : (
            <div className="col-span-full">
              <Empty className="w-full">
                <EmptyHeader>
                  <EmptyTitle>Нет данных</EmptyTitle>
                  <EmptyDescription>
                    Данные отсутствуют или не соответствуют текущим фильтрам.
                  </EmptyDescription>
                </EmptyHeader>
                <EmptyContent>
                  <Button variant="outline" size="sm" onClick={clearAllFilters}>
                    Сбросить фильтры
                  </Button>
                </EmptyContent>
              </Empty>
            </div>
          )}
        </div>
      ) : (
        <div className="min-w-0 overflow-x-auto rounded-md border">
          <Table className="min-w-full rounded-md">
            <TableHeader className="bg-muted sticky top-0 z-10 rounded-md">
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    const canReorder =
                      header.id !== "select" && header.id !== "actions"
                    const visibleCols = table.getVisibleLeafColumns()
                    const colIdx = visibleCols.findIndex((c) => c.id === header.id)
                    const canMoveLeft = canReorder && colIdx > 0
                    const canMoveRight =
                      canReorder && colIdx >= 0 && colIdx < visibleCols.length - 1

                    const moveColumn = (dir: "left" | "right") => {
                      const currentOrder =
                        table.getState().columnOrder?.length > 0
                          ? [...table.getState().columnOrder]
                          : table.getAllLeafColumns().map((c) => c.id)
                      const i = currentOrder.indexOf(header.id)
                      if (i < 0) return
                      const j = dir === "left" ? i - 1 : i + 1
                      if (j < 0 || j >= currentOrder.length) return
                      const next = [...currentOrder]
                      ;[next[i], next[j]] = [next[j], next[i]]
                      setColumnOrder(next)
                    }

                    const isSearchActive = columnSearchActive[header.id] !== false
                    const toggleSearchActive = () => {
                      setColumnSearchActive((prev) => ({
                        ...prev,
                        [header.id]: !isSearchActive,
                      }))
                    }
                    const canHide = header.column.getCanHide()
                    const hasColumnContextMenu = canReorder && (canHide || true)

                    const tableHeadEl = (
                      <TableHead
                        key={header.id}
                        colSpan={header.colSpan}
                        className={cn(
                          canReorder ? "group relative" : "",
                          !isSearchActive && "text-muted-foreground"
                        )}
                      >
                        {header.isPlaceholder ? null : (
                          <>
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {canReorder && (
                              <>
                                <div
                                  className="absolute inset-y-0 right-0 w-32 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-r from-transparent via-muted/70 to-muted"
                                  aria-hidden
                                />
                                <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity absolute right-1 top-1/2 -translate-y-1/2 pointer-events-auto z-10">
                                  <Button
                                  type="button"
                                  variant="outline"
                                  size="icon"
                                  className="h-6 w-6 rounded-sm bg-muted/45 border border-border/35 text-muted-foreground hover:bg-muted/60 dark:bg-muted/55 dark:border-border/45 dark:hover:bg-muted/75 shadow-none"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    moveColumn("left")
                                  }}
                                  disabled={!canMoveLeft}
                                  aria-label="Переместить столбец влево"
                                >
                                  <IconChevronLeft className="h-3.5 w-3.5" />
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="icon"
                                  className="h-6 w-6 rounded-sm bg-muted/45 border border-border/35 text-muted-foreground hover:bg-muted/60 dark:bg-muted/55 dark:border-border/45 dark:hover:bg-muted/75 shadow-none"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    moveColumn("right")
                                  }}
                                  disabled={!canMoveRight}
                                  aria-label="Переместить столбец вправо"
                                >
                                  <IconChevronRight className="h-3.5 w-3.5" />
                                </Button>
                              </div>
                              </>
                            )}
                          </>
                        )}
                      </TableHead>
                    )

                    if (hasColumnContextMenu) {
                      return (
                        <ContextMenu key={header.id}>
                          <ContextMenuTrigger asChild>
                            {tableHeadEl}
                          </ContextMenuTrigger>
                          <ContextMenuContent className="w-56">
                            {canHide && (
                              <ContextMenuItem
                                onClick={() => header.column.toggleVisibility(false)}
                              >
                                <IconEyeOff className="h-4 w-4" />
                                Скрыть
                              </ContextMenuItem>
                            )}
                            <ContextMenuItem onClick={toggleSearchActive}>
                              {isSearchActive ? (
                                <>
                                  <IconSearchOff className="h-4 w-4" />
                                  Деактивировать для поиска
                                </>
                              ) : (
                                <>
                                  <IconSearch className="h-4 w-4" />
                                  Активировать для поиска
                                </>
                              )}
                            </ContextMenuItem>
                          </ContextMenuContent>
                        </ContextMenu>
                      )
                    }
                    return tableHeadEl
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    <Empty className="w-full">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <Spinner className="size-6" />
                        </EmptyMedia>
                        <EmptyTitle>{loadingMessage}</EmptyTitle>
                        <EmptyDescription>
                          Пожалуйста, подождите. Идет загрузка данных таблицы.
                        </EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  </TableCell>
                </TableRow>
              ) : table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row) => {
                  const baseClass = onRowClick ? "cursor-pointer hover:bg-muted/50 transition-colors" : undefined
                  const rowClass = getRowClassName?.(row as Row<TData>)
                  const rowEl = (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() && "selected"}
                      className={[baseClass, rowClass].filter(Boolean).join(" ") || undefined}
                      onClick={onRowClick ? (e) => {
                        const target = e.target as HTMLElement
                        if (target.closest("button") || target.closest("[role=checkbox]") || target.closest("a")) return
                        onRowClick(row as Row<TData>)
                      } : undefined}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </TableCell>
                      ))}
                    </TableRow>
                  )
                  if (hasContextMenu) {
                    return (
                      <ContextMenu key={row.id}>
                        <ContextMenuTrigger asChild>{rowEl}</ContextMenuTrigger>
                        <ContextMenuContent className="w-48">
                          {contextMenuActions?.onEdit && (
                            <ContextMenuItem onClick={() => contextMenuActions.onEdit?.(row as Row<TData>)}>
                              <IconEdit className="h-4 w-4" />
                              Изменить
                            </ContextMenuItem>
                          )}
                          {contextMenuActions?.getCopyText && (
                            <ContextMenuItem
                              onClick={() => {
                                const text = contextMenuActions.getCopyText?.(row as Row<TData>)
                                if (text) {
                                  navigator.clipboard.writeText(text)
                                  toast.success("Скопировано в буфер обмена")
                                }
                              }}
                            >
                              <IconCopy className="h-4 w-4" />
                              Скопировать
                            </ContextMenuItem>
                          )}
                          {contextMenuActions?.onDelete && (
                            <ContextMenuItem
                              variant="destructive"
                              onClick={() => deleteDialog.requestDelete(row as Row<TData>)}
                            >
                              <IconTrash className="h-4 w-4" />
                              Удалить
                            </ContextMenuItem>
                          )}
                        </ContextMenuContent>
                      </ContextMenu>
                    )
                  }
                  return rowEl
                })
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    <Empty className="w-full">
                      <EmptyHeader>
                        <EmptyTitle>Нет данных</EmptyTitle>
                        <EmptyDescription>
                          Данные отсутствуют или не соответствуют текущим фильтрам.
                        </EmptyDescription>
                      </EmptyHeader>
                      <EmptyContent>
                        <Button variant="outline" size="sm" onClick={clearAllFilters}>
                          Сбросить фильтры
                        </Button>
                      </EmptyContent>
                    </Empty>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          {hasContextMenu && contextMenuActions?.onDelete && (
            <AlertDialog open={deleteDialog.open} onOpenChange={deleteDialog.setOpen}>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>
                    {contextMenuActions.deleteTitle ?? "Удалить?"}
                  </AlertDialogTitle>
                  <AlertDialogDescription>
                    {contextMenuActions.deleteDescription ?? "Это действие нельзя отменить."}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Отмена</AlertDialogCancel>
                  <AlertDialogAction
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    onClick={() => {
                      if (deleteDialog.pendingRow) {
                        contextMenuActions.onDelete?.(deleteDialog.pendingRow)
                        deleteDialog.confirmDelete()
                      }
                    }}
                  >
                    Удалить
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      )}
      {!isCardsView && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex-1 text-sm text-muted-foreground">
            {serverPagination
              ? `${table.getFilteredSelectedRowModel().rows.length} of ${totalRowCount} row(s) selected.`
              : `${table.getFilteredSelectedRowModel().rows.length} of ${table.getFilteredRowModel().rows.length} row(s) selected.`}
          </div>
          <div className="flex items-center justify-end space-x-4 h-9">
            {exportConfig && serverPagination && (
              <Dialog open={exportModalOpen} onOpenChange={setExportModalOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="h-9">
                    <IconDownload className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle>Экспорт данных</DialogTitle>
                    <DialogDescription>
                      Будет экспортировано до {(exportConfig.maxLimit ?? 10_000).toLocaleString("ru")} записей
                      с текущими фильтрами, сортировкой и видимыми столбцами.
                    </DialogDescription>
                  </DialogHeader>
                  <DialogFooter>
                    <Button onClick={handleExport} disabled={exporting}>
                      {exporting ? "Экспорт..." : "Экспорт"}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-9">
                  <IconLayoutColumns className="h-4 w-4 mr-2" />
                  Столбцы
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                {table.getAllColumns().filter((column) => column.getCanHide()).map((column) => (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    checked={column.getIsVisible()}
                    onCheckedChange={(value) => column.toggleVisibility(!!value)}
                  >
                    {getColumnLabel(column)}
                  </DropdownMenuCheckboxItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div className="flex items-center space-x-2">
            <Select
              value={`${table.getState().pagination.pageSize}`}
              onValueChange={(value) => table.setPageSize(Number(value))}
            >
              <SelectTrigger className="w-[70px]">
                <SelectValue placeholder={table.getState().pagination.pageSize} />
              </SelectTrigger>
              <SelectContent>
                {[10, 20, 30, 40, 50].map((size) => (
                  <SelectItem key={size} value={`${size}`}>{size}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="text-sm text-muted-foreground">
              Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.setPageIndex(0)}
              disabled={!table.getCanPreviousPage()}
            >
              <IconChevronsLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              <IconChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              <IconChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.setPageIndex(table.getPageCount() - 1)}
              disabled={!table.getCanNextPage()}
            >
              <IconChevronsRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
