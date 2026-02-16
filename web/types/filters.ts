/**
 * Shared filter types for frontend and backend contract.
 * Single source of truth for filter structure used in DataTable and API.
 */

export type FilterOperator =
  | "contains"
  | "equals"
  | "notEquals"
  | "greaterThan"
  | "lessThan"
  | "greaterOrEqual"
  | "lessOrEqual"
  | "matchesRegex"
  | "dateRange"
  | "isEmpty"
  | "isNotEmpty"

export interface FilterItem {
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
  filters?: FilterItem[]
}
