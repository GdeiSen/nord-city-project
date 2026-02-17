/**
 * Column config for entity tables (users, tickets, feedbacks).
 * Maps to DataTableColumnMeta for filter/sort/search.
 */
import type { DataTableColumnMeta } from "@/components/data-table"

export type ColumnType = "string" | "number" | "date"

export interface TableColumnConfig {
  id: string
  label: string
  type?: ColumnType
  filterDbColumn?: string
  searchDbColumns?: string[]
  filterPicker?: "users" | "objects"
  filterSelect?: { value: string; label: string }[]
  filterable?: boolean
  sortable?: boolean
  nullable?: boolean
}

export function configToMeta(config: TableColumnConfig): DataTableColumnMeta {
  return {
    searchDbColumns: config.searchDbColumns ?? [config.filterDbColumn ?? config.id].filter(Boolean),
    filterDbColumn: config.filterDbColumn,
    filterPicker: config.filterPicker,
    filterSelect: config.filterSelect,
    type: config.type,
    nullable: config.nullable,
  }
}
