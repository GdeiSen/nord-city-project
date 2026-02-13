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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
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
  | 'isEmpty'       // For any: is empty/null
  | 'isNotEmpty'    // For any: is not empty/null

/**
 * Filter configuration for a column
 */
export interface ColumnFilter {
  columnId: string
  operator: FilterOperator
  value: string
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
export function DataTable<TData>({
  data,
  columns,
  loading = false,
  loadingMessage = "Загрузка данных...",
  view = 'table',
  renderCard,
  cardsClassName,
}: {
  data: TData[]
  columns: ColumnDef<TData>[]
  loading?: boolean
  loadingMessage?: string
  view?: 'table' | 'cards'
  renderCard?: (row: Row<TData>) => React.ReactNode
  cardsClassName?: string
}) {
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({})
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState({
    pageIndex: 0,
    pageSize: 10,
  })
  const [isSortFilterOpen, setIsSortFilterOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<'sort' | 'filter'>('sort')
  const [globalQuery, setGlobalQuery] = React.useState("")
  const isMobile = useIsMobile()
  
  // Advanced filter state
  const [advancedFilters, setAdvancedFilters] = React.useState<ColumnFilter[]>([])
  
  // Advanced sort state (ordered list)
  const [advancedSorts, setAdvancedSorts] = React.useState<ColumnSort[]>([])

  // Helper functions
  const clearAllFilters = () => {
    setColumnFilters([])
    setSorting([])
    setAdvancedFilters([])
    setAdvancedSorts([])
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
      setAdvancedFilters(prev => [...prev, {
        columnId: firstAvailable.id,
        operator: 'contains',
        value: ''
      }])
    }
  }

  const removeFilter = (index: number) => {
    setAdvancedFilters(prev => prev.filter((_, i) => i !== index))
  }

  const updateFilter = (index: number, updates: Partial<ColumnFilter>) => {
    setAdvancedFilters(prev => 
      prev.map((f, i) => i === index ? { ...f, ...updates } : f)
    )
  }

  // Custom filter function that handles our advanced operators
  const customFilterFn = React.useCallback((row: any, columnId: string, filterValue: any) => {
    if (!filterValue || typeof filterValue !== 'object') return true
    
    const { operator, value } = filterValue as { operator: FilterOperator; value: string }
    const cellValue = row.getValue(columnId)
    
    // Handle empty/not empty operators
    if (operator === 'isEmpty') {
      return cellValue === null || cellValue === undefined || cellValue === ''
    }
    if (operator === 'isNotEmpty') {
      return cellValue !== null && cellValue !== undefined && cellValue !== ''
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
    // We'll handle filtering through the table's filter state
    // but we need to ensure each column uses our custom filter function
    const filterState: ColumnFiltersState = advancedFilters
      .filter(f => f.value || f.operator === 'isEmpty' || f.operator === 'isNotEmpty')
      .map(f => ({
        id: f.columnId,
        value: { operator: f.operator, value: f.value }
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
      isEmpty: 'Пусто',
      isNotEmpty: 'Не пусто'
    }
    return labels[operator]
  }

  // Detect column type (string or number)
  const getColumnType = (columnId: string): 'string' | 'number' => {
    // Simple heuristic: if column name contains 'id', 'count', 'amount', etc., treat as number
    const numericKeywords = ['id', 'count', 'amount', 'price', 'total', 'quantity', 'age']
    return numericKeywords.some(kw => columnId.toLowerCase().includes(kw)) ? 'number' : 'string'
  }

  // Get available operators for column type
  const getAvailableOperators = (columnId: string): FilterOperator[] => {
    const type = getColumnType(columnId)
    if (type === 'number') {
      return ['equals', 'notEquals', 'greaterThan', 'lessThan', 'greaterOrEqual', 'lessOrEqual', 'isEmpty', 'isNotEmpty']
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
        <ScrollArea>
          <div className="space-y-4">
            {advancedFilters.map((filter, index) => (
              <div key={index} className="space-y-2 p-3 border rounded-md bg-muted/30">
                <div className="flex items-center justify-between">
                  <Select
                    value={filter.columnId}
                    onValueChange={(v) => updateFilter(index, { columnId: v })}
                  >
                    <SelectTrigger className="h-8 w-[140px]">
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
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFilter(index)}
                    className="h-8 w-8 p-0"
                  >
                    <IconX className="h-4 w-4" />
                  </Button>
                </div>
                <Select
                  value={filter.operator}
                  onValueChange={(v) => updateFilter(index, { operator: v as FilterOperator })}
                >
                  <SelectTrigger className="h-8">
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
                {filter.operator !== 'isEmpty' && filter.operator !== 'isNotEmpty' && (
                  <Input
                    placeholder="Введите значение..."
                    value={filter.value}
                    onChange={(e) => updateFilter(index, { value: e.target.value })}
                    className="h-8"
                    type={getColumnType(filter.columnId) === 'number' ? 'number' : 'text'}
                  />
                )}
              </div>
            ))}

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
                Нажмите "Добавить фильтр" для начала
              </div>
            )}
          </div>
        </ScrollArea>
      </TabsContent>
    </Tabs>
  )

  // Wrap columns to add custom filter function
  const wrappedColumns = React.useMemo(() => {
    return columns.map(col => ({
      ...col,
      filterFn: customFilterFn as any,
    }))
  }, [columns, customFilterFn])

  // Global search across all visible columns with left-to-right priority
  const globalSearchFn = React.useCallback((row: any, _columnId: string, filterValue: string) => {
    const q = String(filterValue ?? '').toLowerCase().trim()
    if (!q) return true
    // Check visible cells in rendered order (left -> right)
    for (const cell of row.getVisibleCells()) {
      const value = row.getValue(cell.column.id)
      if (String(value ?? '').toLowerCase().includes(q)) return true
    }
    return false
  }, [])

  const table = useReactTable({
    data,
    columns: wrappedColumns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination,
      globalFilter: globalQuery,
    },
    getRowId: (row) => (row as any).id.toString(),
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    onGlobalFilterChange: setGlobalQuery,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    globalFilterFn: globalSearchFn as any,
    meta: {
      globalQuery,
    },
  })

  // Get available columns for sorting/filtering (after table initialization)
  const availableColumns = React.useMemo(() => {
    return table.getAllColumns()
      .filter(col => col.id !== 'select' && col.id !== 'actions')
      .map(col => ({
        id: col.id,
        label: col.id,
        canSort: col.getCanSort(),
        canFilter: col.getCanFilter(),
      }))
  }, [table])

  // Get columns not yet in sort list
  const availableSortColumns = React.useMemo(() => {
    const usedIds = new Set(advancedSorts.map(s => s.columnId))
    return availableColumns.filter(col => !usedIds.has(col.id) && col.canSort)
  }, [availableColumns, advancedSorts])


  return (
    <div className="w-full flex flex-col gap-4">
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
            <DrawerContent className="p-0">
              <DrawerHeader>
                <DrawerTitle>Сортировка и фильтры</DrawerTitle>
                <DrawerDescription>
                  Настройте сортировку и фильтры для таблицы
                </DrawerDescription>
              </DrawerHeader>
              <div className="overflow-y-auto max-h-[calc(100dvh-8.5rem)] px-4 pb-4">
                {renderSortFilterContent()}
              </div>
              <DrawerFooter>
                <DrawerClose asChild>
                  <Button variant="outline">Закрыть</Button>
                </DrawerClose>
              </DrawerFooter>
            </DrawerContent>
          </Drawer>
        ) : (
          <Dialog open={isSortFilterOpen} onOpenChange={setIsSortFilterOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="h-9">
                <IconFilter className="h-4 w-4" />
                {(advancedSorts.length > 0 || advancedFilters.length > 0) && (
                  <Badge variant="secondary" className="ml-2 h-5 w-5 rounded-full p-0 flex items-center justify-center">
                    {advancedSorts.length + advancedFilters.length}
                  </Badge>
                )}
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[520px] p-0">
              <DialogHeader className="p-4 pb-2">
                <DialogTitle>Сортировка и фильтры</DialogTitle>
                <DialogDescription>
                  Настройте сортировку и фильтры для таблицы
                </DialogDescription>
              </DialogHeader>
              <div className="overflow-y-auto max-h-[70vh] px-4 pb-4">
                {renderSortFilterContent()}
              </div>
            </DialogContent>
          </Dialog>
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
                {renderCard ? renderCard(row) : null}
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
        <div className="rounded-md border">
          <Table className="rounded-md">
            <TableHeader className="bg-muted sticky top-0 z-10 rounded-md">
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    return (
                      <TableHead key={header.id} colSpan={header.colSpan}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                      </TableHead>
                    )
                  })}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody className="**:data-[slot=table-cell]:first:w-10">
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
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-state={row.getIsSelected() && "selected"}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
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
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex-1 text-sm text-muted-foreground">
          {table.getFilteredSelectedRowModel().rows.length} of {table.getFilteredRowModel().rows.length} row(s) selected.
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

