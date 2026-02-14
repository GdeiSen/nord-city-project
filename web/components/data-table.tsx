"use client"

import * as React from "react"
import {
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
  IconChevronUp,
  IconCircleCheckFilled,
  IconDotsVertical,
  IconLayoutColumns,
  IconPlus,
  IconTrendingUp,
  IconFilter,
  IconSortAscending,
  IconSortDescending,
  IconX,
  IconGripVertical,
  IconTrash,
  IconEdit,
  IconCopy,
  IconEyeOff,
  IconSearch,
  IconSearchOff,
} from "@tabler/icons-react"
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
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"
import { toast } from "sonner"
import { z } from "zod"

import { useIsMobile } from "@/hooks/use-mobile"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
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
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Spinner } from "@/components/ui/spinner"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
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
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { format } from "date-fns"
import { ru } from "date-fns/locale"
import { DataPicker, DataPickerField } from "@/components/data-picker"

function FilterDataPicker({
  data,
  fields,
  displayValue,
  placeholder,
  open,
  onOpenChange,
  onSelect,
}: {
  data: any[]
  fields: DataPickerField[]
  displayValue: string
  placeholder: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (item: { id: number }) => void
}) {
  return (
    <div className="min-w-[140px] flex-1" onClick={(e) => e.stopPropagation()}>
      <DataPicker
        title={placeholder}
        description="Выберите значение из списка"
        data={data}
        fields={fields}
        displayValue={displayValue}
        placeholder={placeholder}
        onSelect={onSelect}
        open={open}
        onOpenChange={onOpenChange}
      />
    </div>
  )
}

/**
 * Filter operator types for different data types
 */
export type FilterOperator = 
  | 'contains'      // For strings: substring match
  | 'equals'        // For strings/numbers: exact match
  | 'notEquals'     // For strings/numbers: not equal
  | 'greaterThan'   // For numbers: >
  | 'lessThan'      // For numbers: <
  | 'greaterOrEqual'// For numbers: >=
  | 'lessOrEqual'   // For numbers: <=
  | 'dateRange'     // For dates: from..to
  | 'isEmpty'       // For any: is empty/null
  | 'isNotEmpty'    // For any: is not empty/null

/**
 * Filter configuration for a column
 */
export interface ColumnFilter {
  columnId: string
  operator: FilterOperator
  value: string
  /** For date columns: start of range (ISO string) */
  dateFrom?: string
  /** For date columns: end of range (ISO string) */
  dateTo?: string
}

/**
 * Sort configuration for a column
 */
export interface ColumnSort {
  columnId: string
  direction: 'asc' | 'desc'
}

/**
 * Zod schema for data table row validation
 * 
 * Defines the structure and validation rules for table data items.
 * This schema ensures type safety and data integrity across the
 * table component and provides runtime validation for incoming data.
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


/**
 * Advanced data table component with sorting and filtering capabilities
 * 
 * This comprehensive table component provides advanced features for
 * data manipulation and presentation using TanStack Table for data
 * management, providing a powerful interface for business data management.
 * 
 * Key features:
 * - Multi-column sorting and filtering capabilities
 * - Row selection with bulk operations support
 * - Column visibility customization and reordering
 * - Responsive pagination with configurable page sizes
 * - Keyboard accessibility and screen reader support
 * - Mobile-responsive design with touch gesture support
 * 
 * The component implements a sophisticated state management system to handle
 * complex user interactions while maintaining performance for large datasets.
 * It uses React.memo optimization patterns and efficient re-rendering strategies.
 */
/** Filter item for server-side filtering */
export interface ServerFilterItem {
  columnId: string
  operator: FilterOperator
  value?: string
  dateFrom?: string
  dateTo?: string
}

export interface ServerPaginationParams {
  pageIndex: number
  pageSize: number
  search: string
  sort: string
  searchColumns?: string[]
  filters?: ServerFilterItem[]
}

/** Column meta for server-side search/filter. Add to ColumnDef when column maps to DB columns. */
export interface DataTableColumnMeta {
  searchDbColumns?: string[]
  /** DB column for filtering when frontend column id differs (e.g. user -> user_id) */
  filterDbColumn?: string
  /** Use DataPicker for equals operator instead of text input ('users' | 'objects') */
  filterPicker?: 'users' | 'objects'
  /** Fixed options for Select (status, role, etc.). Equals only, no "contains" */
  filterSelect?: { value: string; label: string }[]
  /** Column type for filter UI (from TableColumnConfig). Falls back to heuristic if omitted. */
  type?: 'string' | 'number' | 'date'
}

/** Context menu actions for table rows. All optional — menu only shown when at least one action is provided. */
export interface DataTableContextMenuActions<TData> {
  onEdit?: (row: Row<TData>) => void
  onDelete?: (row: Row<TData>) => void
  /** Returns text to copy to clipboard. If omitted, Copy action is hidden. */
  getCopyText?: (row: Row<TData>) => string
  deleteTitle?: string
  deleteDescription?: string
}

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
}: {
  data: TData[]
  columns: ColumnDef<TData>[]
  loading?: boolean
  loadingMessage?: string
  view?: 'table' | 'cards'
  renderCard?: (row: Row<TData>) => React.ReactNode
  cardsClassName?: string
  /** Optional callback when a table row is clicked. Pass the row data. Ignored for card view. */
  onRowClick?: (row: Row<TData>) => void
  /** Context menu on right-click: Edit, Delete (with AlertDialog), Copy. */
  contextMenuActions?: DataTableContextMenuActions<TData>
  /** Enable server-side pagination. Data is the current page only. */
  serverPagination?: boolean
  /** Total row count for server pagination. */
  totalRowCount?: number
  /** Current server params (controlled). */
  serverParams?: Partial<ServerPaginationParams>
  /** Callback when pagination/sort/search changes. */
  onServerParamsChange?: (params: ServerPaginationParams) => void
  /** Data for filter pickers: users and/or objects for DataPicker in filters */
  filterPickerData?: { users?: { id: number; first_name?: string; last_name?: string; username?: string; email?: string }[]; objects?: { id: number; name: string }[] }
}) {
  const pageSizeFromParams = serverParams?.pageSize ?? 10
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({})
  /** Columns inactive for search have muted header and are excluded from global search */
  const [columnSearchActive, setColumnSearchActive] = React.useState<Record<string, boolean>>({})
  const [columnOrder, setColumnOrder] = React.useState<string[]>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState({
    pageIndex: serverParams?.pageIndex ?? 0,
    pageSize: pageSizeFromParams,
  })
  const [isSortFilterOpen, setIsSortFilterOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<'sort' | 'filter'>('sort')
  const [globalQuery, setGlobalQuery] = React.useState(serverParams?.search ?? "")
  const [debouncedSearch, setDebouncedSearch] = React.useState(serverParams?.search ?? "")
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)
  const [pendingDeleteRow, setPendingDeleteRow] = React.useState<Row<TData> | null>(null)
  const isMobile = useIsMobile()

  const hasContextMenu = Boolean(
    contextMenuActions?.onEdit || contextMenuActions?.onDelete || contextMenuActions?.getCopyText
  )

  // Debounce search input (300ms) for server-side requests
  React.useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(globalQuery), 300)
    return () => clearTimeout(t)
  }, [globalQuery])

  // Sync from serverParams when in server mode
  React.useEffect(() => {
    if (serverPagination && serverParams) {
      setPagination({
        pageIndex: serverParams.pageIndex ?? 0,
        pageSize: serverParams.pageSize ?? 10,
      })
      const s = serverParams.search ?? ""
      setGlobalQuery(s)
      setDebouncedSearch(s)
      if (serverParams.sort) {
        const parts = serverParams.sort.split(",").filter(Boolean)
        const sorts = parts.map((p) => {
          const [col, dir] = p.includes(":") ? p.split(":") : [p, "asc"]
          return { columnId: col.trim(), direction: (dir?.trim() || "asc") as "asc" | "desc" }
        })
        setAdvancedSorts(sorts)
      }
    }
  }, [serverPagination, serverParams?.pageIndex, serverParams?.pageSize, serverParams?.search, serverParams?.sort])
  
  // Advanced filter state
  const [advancedFilters, setAdvancedFilters] = React.useState<ColumnFilter[]>([])
  const [openFilterPickerIndex, setOpenFilterPickerIndex] = React.useState<number | null>(null)
  
  // Advanced sort state (ordered list)
  const [advancedSorts, setAdvancedSorts] = React.useState<ColumnSort[]>([])

  // Helper functions
  const clearAllFilters = () => {
    setColumnFilters([])
    setSorting([])
    setAdvancedFilters([])
    setAdvancedSorts([])
    setOpenFilterPickerIndex(null)
    setPagination({ pageIndex: 0, pageSize: pagination.pageSize })
    setGlobalQuery("")
  }

  const addSort = (columnId: string) => {
    setAdvancedSorts(prev => [...prev, { columnId, direction: 'asc' }])
  }

  const removeSort = (columnId: string) => {
    setAdvancedSorts(prev => prev.filter(s => s.columnId !== columnId))
  }

  const updateSortDirection = (columnId: string, direction: 'asc' | 'desc') => {
    setAdvancedSorts(prev => 
      prev.map(s => s.columnId === columnId ? { ...s, direction } : s)
    )
  }

  const moveSortUp = (index: number) => {
    if (index === 0) return
    setAdvancedSorts(prev => {
      const newSorts = [...prev]
      ;[newSorts[index - 1], newSorts[index]] = [newSorts[index], newSorts[index - 1]]
      return newSorts
    })
  }

  const moveSortDown = (index: number) => {
    if (index === advancedSorts.length - 1) return
    setAdvancedSorts(prev => {
      const newSorts = [...prev]
      ;[newSorts[index], newSorts[index + 1]] = [newSorts[index + 1], newSorts[index]]
      return newSorts
    })
  }

  const addFilter = () => {
    const firstAvailable = availableColumns.find(col => col.canFilter)
    if (firstAvailable) {
      const colType = getColumnType(firstAvailable.id)
      const ops = getAvailableOperators(firstAvailable.id)
      const op = colType === 'date' ? 'dateRange' : (firstAvailable.filterPicker || firstAvailable.filterSelect?.length) ? 'equals' : colType === 'number' ? 'equals' : 'contains'
      const actualOp = ops.includes(op) ? op : ops[0]
      setAdvancedFilters(prev => [...prev, {
        columnId: firstAvailable.id,
        operator: actualOp,
        value: '',
        ...(colType === 'date' ? { dateFrom: '', dateTo: '' } : {})
      }])
    }
  }

  const removeFilter = (index: number) => {
    setAdvancedFilters(prev => prev.filter((_, i) => i !== index))
  }

  const updateFilter = (index: number, updates: Partial<ColumnFilter>) => {
    setAdvancedFilters(prev =>
      prev.map((f, i) => {
        if (i !== index) return f
        const next = { ...f, ...updates }
        if ('columnId' in updates && updates.columnId) {
          const ops = getAvailableOperators(updates.columnId)
          if (!ops.includes(next.operator)) {
            next.operator = ops[0]
            if (next.operator === 'dateRange') {
              next.value = ''
              next.dateFrom = ''
              next.dateTo = ''
            } else {
              next.dateFrom = undefined
              next.dateTo = undefined
            }
          }
        }
        return next
      })
    )
  }

  // Custom filter function that handles our advanced operators
  const customFilterFn = React.useCallback((row: any, columnId: string, filterValue: any) => {
    if (!filterValue || typeof filterValue !== 'object') return true

    const { operator, value, dateFrom, dateTo } = filterValue as {
      operator: FilterOperator
      value?: string
      dateFrom?: string
      dateTo?: string
    }
    const cellValue = row.getValue(columnId)

    // Handle empty/not empty operators
    if (operator === 'isEmpty') {
      return cellValue === null || cellValue === undefined || cellValue === ''
    }
    if (operator === 'isNotEmpty') {
      return cellValue !== null && cellValue !== undefined && cellValue !== ''
    }

    // Date range filter
    if (operator === 'dateRange') {
      const from = dateFrom ? new Date(dateFrom) : null
      const to = dateTo ? new Date(dateTo) : null
      if (!from && !to) return true
      const cellDate = cellValue ? new Date(String(cellValue)) : null
      if (!cellDate || isNaN(cellDate.getTime())) return false
      const cellTime = cellDate.getTime()
      if (from && cellTime < from.getTime()) return false
      if (to) {
        const toEnd = new Date(to)
        toEnd.setHours(23, 59, 59, 999)
        if (cellTime > toEnd.getTime()) return false
      }
      return true
    }

    // If no value provided for other operators, don't filter
    if (!value) return true

    // Convert to string for comparison
    const cellStr = String(cellValue || '').toLowerCase()
    const valueStr = String(value).toLowerCase()

    // String operations
    if (operator === 'contains') {
      return cellStr.includes(valueStr)
    }
    if (operator === 'equals') {
      return cellStr === valueStr
    }
    if (operator === 'notEquals') {
      return cellStr !== valueStr
    }

    // Number operations
    const cellNum = parseFloat(String(cellValue))
    const valueNum = parseFloat(value)

    if (isNaN(cellNum) || isNaN(valueNum)) return true

    if (operator === 'greaterThan') return cellNum > valueNum
    if (operator === 'lessThan') return cellNum < valueNum
    if (operator === 'greaterOrEqual') return cellNum >= valueNum
    if (operator === 'lessOrEqual') return cellNum <= valueNum

    return true
  }, [])

  const isFirstServerParamsSync = React.useRef(true)
  const prevSearchRef = React.useRef(debouncedSearch)
  const prevFiltersRef = React.useRef<string>("")

  // Apply advanced filters and sorts to table
  React.useEffect(() => {
    // Apply sorts
    const sortingState: SortingState = advancedSorts.map(s => ({
      id: s.columnId,
      desc: s.direction === 'desc'
    }))
    setSorting(sortingState)
  }, [advancedSorts])

  // Apply custom filtering manually
  React.useEffect(() => {
    const filterState: ColumnFiltersState = advancedFilters
      .filter(f =>
        f.operator === 'isEmpty' || f.operator === 'isNotEmpty' ||
        (f.operator === 'dateRange' ? (f.dateFrom || f.dateTo) : f.value)
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

  // Get operator label
  const getOperatorLabel = (operator: FilterOperator): string => {
    const labels: Record<FilterOperator, string> = {
      contains: 'Содержит',
      equals: 'Равно',
      notEquals: 'Не равно',
      greaterThan: 'Больше',
      lessThan: 'Меньше',
      greaterOrEqual: 'Больше или равно',
      lessOrEqual: 'Меньше или равно',
      dateRange: 'Период',
      isEmpty: 'Пусто',
      isNotEmpty: 'Не пусто'
    }
    return labels[operator]
  }

  // Get column type: from meta first, then heuristic fallback
  const getColumnType = (columnId: string): 'string' | 'number' | 'date' => {
    const col = table.getColumn(columnId)
    const meta = (col?.columnDef as { meta?: DataTableColumnMeta })?.meta
    if (meta?.type) return meta.type
    const lower = columnId.toLowerCase()
    if (['id', 'count', 'amount', 'price', 'total', 'quantity', 'age'].some(kw => lower.includes(kw))) return 'number'
    if (['_at', 'date', 'time', 'created', 'updated', 'дата', 'время'].some(kw => lower.includes(kw))) return 'date'
    return 'string'
  }

  // Get available operators for column type
  const getAvailableOperators = (columnId: string): FilterOperator[] => {
    const col = table.getColumn(columnId)
    const meta = (col?.columnDef as { meta?: DataTableColumnMeta })?.meta
    if (meta?.filterPicker || meta?.filterSelect?.length) {
      return ['equals', 'isEmpty', 'isNotEmpty']
    }
    const type = getColumnType(columnId)
    if (type === 'number') {
      return ['equals', 'notEquals', 'greaterThan', 'lessThan', 'greaterOrEqual', 'lessOrEqual', 'isEmpty', 'isNotEmpty']
    }
    if (type === 'date') {
      return ['dateRange', 'isEmpty', 'isNotEmpty']
    }
    return ['contains', 'equals', 'notEquals', 'isEmpty', 'isNotEmpty']
  }

  // Render sort/filter content (shared between Drawer and Popover)
  const renderSortFilterContent = () => (
    <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as 'sort' | 'filter')}>
      <div className="flex items-center justify-between mb-3">
        <TabsList className="grid w-[200px] grid-cols-2">
          <TabsTrigger value="sort">Сортировка</TabsTrigger>
          <TabsTrigger value="filter">Фильтры</TabsTrigger>
        </TabsList>
        <Button
          variant="ghost"
          size="sm"
          onClick={clearAllFilters}
          className="h-8 px-2"
        >
          <IconX className="h-4 w-4 mr-1" />
          Очистить
        </Button>
      </div>

      <TabsContent value="sort" className="mt-0">
        <ScrollArea>
          <div className="space-y-4">
            {/* Active sorts */}
            {advancedSorts.length > 0 && (
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Активные сортировки</Label>
                {advancedSorts.map((sort, index) => (
                  <div key={sort.columnId} className="flex items-center gap-2 p-2 border rounded-md bg-muted/30">
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={() => moveSortUp(index)}
                        disabled={index === 0}
                        aria-label="Move up"
                      >
                        <IconChevronUp className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={() => moveSortDown(index)}
                        disabled={index === advancedSorts.length - 1}
                        aria-label="Move down"
                      >
                        <IconChevronDown className="h-4 w-4" />
                      </Button>
                    </div>
                    <span className="text-sm font-medium flex-1 capitalize">{sort.columnId}</span>
                    <Select
                      value={sort.direction}
                      onValueChange={(v) => updateSortDirection(sort.columnId, v as 'asc' | 'desc')}
                    >
                      <SelectTrigger className="h-8">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="asc">
                          <div className="flex items-center">
                            <IconSortAscending className="h-4 w-4" />
                          </div>
                        </SelectItem>
                        <SelectItem value="desc">
                          <div className="flex items-center">
                            <IconSortDescending className="h-4 w-4" />
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSort(sort.columnId)}
                      className="h-8 w-8 p-0"
                    >
                      <IconTrash className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* Available columns to add */}
            {availableSortColumns.length > 0 && (
              <div className={cn("space-y-2", isMobile && "pb-[50dvh]") }>
                <Label className="text-xs text-muted-foreground">Доступные столбцы</Label>
                {availableSortColumns.map((col) => (
                  <div key={col.id} className="flex items-center justify-between p-2 border rounded-md hover:bg-muted/50 transition-colors">
                    <span className="text-sm capitalize">{col.label}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => addSort(col.id)}
                      className="h-8 px-2"
                    >
                      <IconPlus className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {advancedSorts.length === 0 && availableSortColumns.length === 0 && (
              <div className="text-center text-sm text-muted-foreground py-8">
                Нет доступных столбцов для сортировки
              </div>
            )}
          </div>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="filter" className="mt-0">
        <div className="space-y-3">
          {advancedFilters.map((filter, index) => {
            const colType = getColumnType(filter.columnId)
            const isDateFilter = filter.operator === 'dateRange'
            const needsValue = filter.operator !== 'isEmpty' && filter.operator !== 'isNotEmpty' && !isDateFilter

            return (
              <div key={index} className="p-3 border rounded-md bg-muted/30 space-y-2">
                {/* Horizontal row: column | operator | value/calendar | delete */}
                <div className="flex flex-wrap items-center gap-2">
                  <Select
                    value={filter.columnId}
                    onValueChange={(v) => updateFilter(index, { columnId: v })}
                  >
                    <SelectTrigger className="h-8 min-w-[100px] flex-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {availableColumns.filter(col => col.canFilter).map((col) => (
                        <SelectItem key={col.id} value={col.id} className="capitalize">
                          {col.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={filter.operator}
                    onValueChange={(v) => updateFilter(index, { operator: v as FilterOperator })}
                  >
                    <SelectTrigger className="h-8 min-w-[110px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {getAvailableOperators(filter.columnId).map((op) => (
                        <SelectItem key={op} value={op}>
                          {getOperatorLabel(op)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {needsValue && (() => {
                    const col = availableColumns.find(c => c.id === filter.columnId)
                    const picker = col?.filterPicker
                    const pickerData = picker === 'users' ? filterPickerData?.users : picker === 'objects' ? filterPickerData?.objects : undefined
                    if (picker && pickerData && filter.operator === 'equals') {
                      const fields: DataPickerField[] = picker === 'users'
                        ? [
                            { key: 'first_name', label: 'Имя', searchable: true },
                            { key: 'last_name', label: 'Фамилия', searchable: true },
                            { key: 'username', label: 'Username', searchable: true },
                            { key: 'id', label: 'ID', render: (v) => <span className="text-right">#{v}</span> },
                          ]
                        : [
                            { key: 'name', label: 'Название', searchable: true },
                            { key: 'id', label: 'ID', render: (v) => <span className="text-right">#{v}</span> },
                          ]
                      const selected = picker === 'users'
                        ? pickerData.find((u: { id: number }) => String(u.id) === filter.value)
                        : pickerData.find((o: { id: number }) => String(o.id) === filter.value)
                      const displayValue = selected
                        ? (picker === 'users'
                          ? `${(selected as { last_name?: string; first_name?: string }).last_name ?? ''} ${(selected as { first_name?: string }).first_name ?? ''} @${(selected as { username?: string }).username ?? ''}`.trim() || `#${(selected as { id: number }).id}`
                          : (selected as { name: string }).name || `#${(selected as { id: number }).id}`)
                        : ''
                      return (
                        <FilterDataPicker
                          key={`picker-${index}`}
                          data={pickerData}
                          fields={fields}
                          displayValue={displayValue}
                          placeholder={picker === 'users' ? 'Выберите пользователя' : 'Выберите объект'}
                          open={openFilterPickerIndex === index}
                          onOpenChange={(open) => setOpenFilterPickerIndex(open ? index : null)}
                          onSelect={(item: { id: number }) => {
                            updateFilter(index, { value: String(item.id) })
                            setOpenFilterPickerIndex(null)
                          }}
                        />
                      )
                    }
                    if (col?.filterSelect?.length && filter.operator === 'equals') {
                      return (
                        <Select
                          value={filter.value || '_none'}
                          onValueChange={(v) => updateFilter(index, { value: v === '_none' ? '' : v })}
                        >
                          <SelectTrigger className="h-8 min-w-[140px] flex-1">
                            <SelectValue placeholder="Выберите..." />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="_none">
                              <span className="text-muted-foreground">Не выбрано</span>
                            </SelectItem>
                            {col.filterSelect.map((opt) => (
                              <SelectItem key={opt.value} value={opt.value}>
                                {opt.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )
                    }
                    return colType === 'number' ? (
                      <Input
                        placeholder="Значение..."
                        value={filter.value}
                        onChange={(e) => updateFilter(index, { value: e.target.value })}
                        className="h-8 w-24 shrink-0"
                        type="number"
                      />
                    ) : (
                      <Input
                        placeholder="Текст..."
                        value={filter.value}
                        onChange={(e) => updateFilter(index, { value: e.target.value })}
                        className="h-8 min-w-[120px] flex-1"
                        type="text"
                      />
                    )
                  })()}
                  {isDateFilter && (
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button variant="outline" className="h-8 min-w-[140px] justify-start text-left font-normal">
                          {filter.dateFrom || filter.dateTo
                            ? `${filter.dateFrom ? format(new Date(filter.dateFrom), "dd.MM.yyyy", { locale: ru }) : "…"} — ${filter.dateTo ? format(new Date(filter.dateTo), "dd.MM.yyyy", { locale: ru }) : "…"}`
                            : "Выберите период"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="range"
                          locale={ru}
                          selected={{
                            from: filter.dateFrom ? new Date(filter.dateFrom) : undefined,
                            to: filter.dateTo ? new Date(filter.dateTo) : undefined,
                          }}
                          onSelect={(range) =>
                            updateFilter(index, {
                              dateFrom: range?.from?.toISOString().slice(0, 10) ?? "",
                              dateTo: range?.to ? new Date(range.to).toISOString().slice(0, 10) : "",
                            })
                          }
                          numberOfMonths={2}
                          className="rounded-md border"
                        />
                      </PopoverContent>
                    </Popover>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFilter(index)}
                    className="h-8 w-8 p-0 shrink-0"
                    aria-label="Удалить фильтр"
                  >
                    <IconTrash className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )
          })}

          <Button
            variant="outline"
            size="sm"
            onClick={addFilter}
            className="w-full"
            disabled={availableColumns.filter(col => col.canFilter).length === 0}
          >
            <IconPlus className="h-4 w-4 mr-2" />
            Добавить фильтр
          </Button>

          {advancedFilters.length === 0 && (
            <div className="text-center text-sm text-muted-foreground py-8">
              Нажмите «Добавить фильтр» для начала
            </div>
          )}
        </div>
      </TabsContent>
    </Tabs>
  )

  // Wrap columns to add custom filter function
  const wrappedColumns = React.useMemo(
    () =>
      columns.map((col) => ({
        ...col,
        filterFn: customFilterFn as any,
      })) as ColumnDef<TData>[],
    [columns, customFilterFn]
  )

  // Global search across visible, search-active columns only
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

  const pageCount = serverPagination && totalRowCount > 0
    ? Math.ceil(totalRowCount / pagination.pageSize) || 1
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

  // Get available columns for sorting/filtering (after table initialization)
  const availableColumns = React.useMemo(() => {
    return table.getAllColumns()
      .filter(col => col.id !== 'select' && col.id !== 'actions')
      .map(col => {
        const meta = (col.columnDef as { meta?: DataTableColumnMeta })?.meta
        const header = col.columnDef.header
        const label = typeof header === 'string' ? header : col.id
        return {
          id: col.id,
          label,
          canSort: col.getCanSort(),
          canFilter: col.getCanFilter(),
          filterPicker: meta?.filterPicker,
          filterSelect: meta?.filterSelect,
        }
      })
  }, [table])

  // Get columns not yet in sort list
  const availableSortColumns = React.useMemo(() => {
    const usedIds = new Set(advancedSorts.map(s => s.columnId))
    return availableColumns.filter(col => !usedIds.has(col.id) && col.canSort)
  }, [availableColumns, advancedSorts])

  // Build searchColumns for server: visible, search-active columns only
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

  // Build server filters from advancedFilters (map columnId to filterDbColumn when needed)
  const serverFilters = React.useMemo((): ServerFilterItem[] | undefined => {
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

  // Notify parent when server params change (after searchColumns is available)
  React.useEffect(() => {
    if (!serverPagination || !onServerParamsChange) return
    if (isFirstServerParamsSync.current) {
      isFirstServerParamsSync.current = false
      prevSearchRef.current = debouncedSearch
      return
    }
    const searchChanged = prevSearchRef.current !== debouncedSearch
    prevSearchRef.current = debouncedSearch
    const filtersStr = JSON.stringify(serverFilters ?? [])
    const filtersChanged = prevFiltersRef.current !== filtersStr
    prevFiltersRef.current = filtersStr
    if (searchChanged || filtersChanged) setPagination((p) => ({ ...p, pageIndex: 0 }))
    const sortStr = advancedSorts.map((s) => `${s.columnId}:${s.direction}`).join(",")
    onServerParamsChange({
      pageIndex: (searchChanged || filtersChanged) ? 0 : pagination.pageIndex,
      pageSize: pagination.pageSize,
      search: debouncedSearch,
      sort: sortStr,
      searchColumns: searchColumns ?? undefined,
      filters: serverFilters,
    })
  }, [serverPagination, onServerParamsChange, pagination.pageIndex, pagination.pageSize, debouncedSearch, advancedSorts, searchColumns, serverFilters])

  return (
    <div className="w-full min-w-0 flex flex-col gap-4">
      {/* Top toolbar: global search + sort/filter button */}
      <div className="flex w-full items-center gap-2">
        <Input
          placeholder="Поиск по таблице..."
          value={globalQuery}
          onChange={(e) => setGlobalQuery(e.target.value)}
          className="h-9"
        />
        {isMobile ? (
          <Drawer open={isSortFilterOpen} onOpenChange={setIsSortFilterOpen}>
            <DrawerTrigger asChild>
              <Button variant="outline" size="sm" className="h-9">
                <IconFilter className="h-4 w-4 mr-2" />
                Сортировка и фильтры
                {(advancedSorts.length > 0 || advancedFilters.length > 0) && (
                  <Badge variant="secondary" className="ml-2 h-5 w-5 rounded-full p-0 flex items-center justify-center">
                    {advancedSorts.length + advancedFilters.length}
                  </Badge>
                )}
              </Button>
            </DrawerTrigger>
            <DrawerContent className="p-0 flex flex-col max-h-[90dvh]">
              <DrawerHeader className="shrink-0">
                <DrawerTitle>Сортировка и фильтры</DrawerTitle>
                <DrawerDescription>
                  Настройте сортировку и фильтры для таблицы
                </DrawerDescription>
              </DrawerHeader>
              <ScrollArea className="flex-1 min-h-0 px-4">
                <div className="pb-4">
                  {renderSortFilterContent()}
                </div>
              </ScrollArea>
              <DrawerFooter className="shrink-0">
                <DrawerClose asChild>
                  <Button variant="outline">Закрыть</Button>
                </DrawerClose>
              </DrawerFooter>
            </DrawerContent>
          </Drawer>
        ) : (
          <Sheet open={isSortFilterOpen} onOpenChange={setIsSortFilterOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="sm" className="h-9">
                <IconFilter className="h-4 w-4 mr-2" />
                Сортировка и фильтры
                {(advancedSorts.length > 0 || advancedFilters.length > 0) && (
                  <Badge variant="secondary" className="ml-2 h-5 w-5 rounded-full p-0 flex items-center justify-center">
                    {advancedSorts.length + advancedFilters.length}
                  </Badge>
                )}
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="flex flex-col w-full sm:max-w-md p-0">
              <SheetHeader className="p-4 pb-2 shrink-0">
                <SheetTitle>Сортировка и фильтры</SheetTitle>
                <SheetDescription>
                  Настройте сортировку и фильтры для таблицы
                </SheetDescription>
              </SheetHeader>
              <ScrollArea className="flex-1 px-4 min-h-0">
                <div className="pb-4">
                  {renderSortFilterContent()}
                </div>
              </ScrollArea>
            </SheetContent>
          </Sheet>
        )}
      </div>
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
                  {headerGroup.headers.map((header, idx) => {
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
                  const rowEl = (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() && "selected"}
                      className={onRowClick ? "cursor-pointer hover:bg-muted/50 transition-colors" : undefined}
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
                              onClick={() => {
                                setPendingDeleteRow(row as Row<TData>)
                                setDeleteDialogOpen(true)
                              }}
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
            <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
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
                      if (pendingDeleteRow) {
                        contextMenuActions.onDelete?.(pendingDeleteRow)
                        setPendingDeleteRow(null)
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
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex-1 text-sm text-muted-foreground">
          {serverPagination
            ? `${table.getFilteredSelectedRowModel().rows.length} of ${totalRowCount} row(s) selected.`
            : `${table.getFilteredSelectedRowModel().rows.length} of ${table.getFilteredRowModel().rows.length} row(s) selected.`}
        </div>
        <div className="flex items-center justify-end space-x-4 h-9">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-9">
                <IconLayoutColumns className="h-4 w-4 mr-2" />
                Columns
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {table.getAllColumns().filter((column) => column.getCanHide()).map((column) => (
                <DropdownMenuCheckboxItem
                  key={column.id}
                  className="capitalize"
                  checked={column.getIsVisible()}
                  onCheckedChange={(value) => column.toggleVisibility(!!value)}
                >
                  {column.id}
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
    </div>
  )
}

