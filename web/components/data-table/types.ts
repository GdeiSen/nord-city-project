import type { FilterOperator, FilterItem, ServerPaginationParams } from "@/types/filters"
import type { Row } from "@tanstack/react-table"

export type { FilterOperator, FilterItem as ServerFilterItem, ServerPaginationParams } from "@/types/filters"

export interface ColumnFilter {
  columnId: string
  operator: FilterOperator
  value: string
  dateFrom?: string
  dateTo?: string
}

export interface ColumnSort {
  columnId: string
  direction: "asc" | "desc"
}

export interface DataTableColumnMeta {
  searchDbColumns?: string[]
  filterDbColumn?: string
  filterPicker?: "users" | "objects"
  filterSelect?: { value: string; label: string }[]
  type?: "string" | "number" | "date"
  nullable?: boolean
}

export interface DataTableContextMenuActions<TData> {
  onEdit?: (row: Row<TData>) => void
  onDelete?: (row: Row<TData>) => void
  getCopyText?: (row: Row<TData>) => string
  deleteTitle?: string
  deleteDescription?: string
}
