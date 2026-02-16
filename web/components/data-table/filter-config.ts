/**
 * Filter column type system for DataTable.
 * Each column type defines its operators and drives the appropriate value editor UI.
 *
 * To add a new type:
 * 1. Add a new variant to FilterColumnConfig
 * 2. Add case in getOperators / getDefaultOperator
 * 3. Add value editor in FilterValueEditor component
 */

import type { FilterOperator } from "@/types/filters"

/** Operator labels in Russian */
export const FILTER_OPERATOR_LABELS: Record<FilterOperator, string> = {
  contains: "Содержит",
  equals: "Равно",
  notEquals: "Не равно",
  greaterThan: "Больше",
  lessThan: "Меньше",
  greaterOrEqual: "Больше или равно",
  lessOrEqual: "Меньше или равно",
  matchesRegex: "Regex",
  dateRange: "Период",
  isEmpty: "Пусто",
  isNotEmpty: "Не пусто",
}

export function getOperatorLabel(operator: FilterOperator): string {
  return FILTER_OPERATOR_LABELS[operator] ?? operator
}

// ---------------------------------------------------------------------------
// Filter column configs (discriminated union)
// ---------------------------------------------------------------------------

/** Numeric columns: id, count, priority, etc. */
export interface NumericFilterConfig {
  kind: "numeric"
  nullable?: boolean
  operators: FilterOperator[]
}

/** Date/time columns: created_at, updated_at, etc. */
export interface DatetimeFilterConfig {
  kind: "datetime"
  operators: FilterOperator[]
}

/** Text columns: username, description, etc. */
export interface TextFilterConfig {
  kind: "text"
  nullable?: boolean
  operators: FilterOperator[]
}

/** Relation columns: user, object - multi-select combobox */
export interface RelationFilterConfig {
  kind: "relation"
  relationType: "users" | "objects"
  operators: FilterOperator[]
}

/** Select columns: status, role - fixed options, multi-select combobox */
export interface SelectFilterConfig {
  kind: "select"
  options: { value: string; label: string }[]
  operators: FilterOperator[]
}

export type FilterColumnConfig =
  | NumericFilterConfig
  | DatetimeFilterConfig
  | TextFilterConfig
  | RelationFilterConfig
  | SelectFilterConfig

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NUMERIC_OPERATORS_ALL: FilterOperator[] = [
  "equals",
  "notEquals",
  "greaterThan",
  "lessThan",
  "greaterOrEqual",
  "lessOrEqual",
  "isEmpty",
  "isNotEmpty",
]
const NUMERIC_OPERATORS_REQUIRED: FilterOperator[] = [
  "equals",
  "notEquals",
  "greaterThan",
  "lessThan",
  "greaterOrEqual",
  "lessOrEqual",
]

const DATETIME_OPERATORS: FilterOperator[] = [
  "equals",
  "notEquals",
  "lessThan",
  "greaterThan",
]

const TEXT_OPERATORS_ALL: FilterOperator[] = [
  "contains",
  "equals",
  "notEquals",
  "matchesRegex",
  "isEmpty",
  "isNotEmpty",
]
const TEXT_OPERATORS_REQUIRED: FilterOperator[] = [
  "contains",
  "equals",
  "notEquals",
  "matchesRegex",
]

const RELATION_OPERATORS: FilterOperator[] = ["equals", "notEquals"]
const SELECT_OPERATORS: FilterOperator[] = ["equals", "notEquals"]

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

export function createNumericFilterConfig(
  nullable: boolean = true
): NumericFilterConfig {
  return {
    kind: "numeric",
    nullable,
    operators: nullable ? NUMERIC_OPERATORS_ALL : NUMERIC_OPERATORS_REQUIRED,
  }
}

export function createDatetimeFilterConfig(): DatetimeFilterConfig {
  return { kind: "datetime", operators: DATETIME_OPERATORS }
}

export function createTextFilterConfig(
  nullable: boolean = true
): TextFilterConfig {
  return {
    kind: "text",
    nullable,
    operators: nullable ? TEXT_OPERATORS_ALL : TEXT_OPERATORS_REQUIRED,
  }
}

export function createRelationFilterConfig(
  relationType: "users" | "objects"
): RelationFilterConfig {
  return { kind: "relation", relationType, operators: RELATION_OPERATORS }
}

export function createSelectFilterConfig(
  options: { value: string; label: string }[]
): SelectFilterConfig {
  return { kind: "select", options, operators: SELECT_OPERATORS }
}

// ---------------------------------------------------------------------------
// DataTableColumnMeta → FilterColumnConfig
// ---------------------------------------------------------------------------

export interface LegacyColumnMeta {
  type?: "string" | "number" | "date"
  filterPicker?: "users" | "objects"
  filterSelect?: { value: string; label: string }[]
  nullable?: boolean
}

export function getFilterConfigFromMeta(meta: LegacyColumnMeta & { id?: string } = {}): FilterColumnConfig {
  if (meta.filterPicker) {
    return createRelationFilterConfig(meta.filterPicker)
  }
  if (meta.filterSelect?.length) {
    return createSelectFilterConfig(meta.filterSelect)
  }
  const nullable = meta.nullable ?? (meta.id === "id" ? false : true)
  switch (meta.type) {
    case "number":
      return createNumericFilterConfig(nullable)
    case "date":
      return createDatetimeFilterConfig()
    case "string":
    default:
      return createTextFilterConfig(nullable)
  }
}

export function getOperators(config: FilterColumnConfig): FilterOperator[] {
  return config.operators
}

export function getDefaultOperator(config: FilterColumnConfig): FilterOperator {
  switch (config.kind) {
    case "datetime":
    case "relation":
    case "select":
      return "equals"
    case "numeric":
    case "text":
    default:
      return "equals"
  }
}

export function needsValue(operator: FilterOperator): boolean {
  return operator !== "isEmpty" && operator !== "isNotEmpty"
}

export function isDateRangeOperator(operator: FilterOperator): boolean {
  return operator === "dateRange"
}

export function isDatetimeValueOperator(operator: FilterOperator): boolean {
  return ["equals", "notEquals", "lessThan", "greaterThan"].includes(operator)
}

// ---------------------------------------------------------------------------
// Client-side filter function for TanStack Table
// ---------------------------------------------------------------------------

interface FilterValue {
  operator: FilterOperator
  value?: string
  dateFrom?: string
  dateTo?: string
}

/**
 * Creates a filter function for TanStack Table that handles advanced operators.
 */
export function createClientFilterFn(): (row: any, columnId: string, filterValue: any) => boolean {
  return (row: any, columnId: string, filterValue: any) => {
    if (!filterValue || typeof filterValue !== "object") return true

    const { operator, value, dateFrom, dateTo } = filterValue as FilterValue
    const cellValue = row.getValue(columnId)

    if (operator === "isEmpty") {
      return cellValue === null || cellValue === undefined || cellValue === ""
    }
    if (operator === "isNotEmpty") {
      return cellValue !== null && cellValue !== undefined && cellValue !== ""
    }

    if (operator === "dateRange") {
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

    if (!value) return true

    const cellStr = String(cellValue || "")
    const valueStr = String(value)
    const cellStrLower = cellStr.toLowerCase()
    const valueStrLower = valueStr.toLowerCase()

    if (operator === "contains") {
      return cellStrLower.includes(valueStrLower)
    }
    if (operator === "matchesRegex") {
      try {
        const re = new RegExp(valueStr, "i")
        return re.test(cellStr)
      } catch {
        return false
      }
    }
    if (operator === "equals") {
      const values = valueStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
      if (values.length > 1) {
        const cellId = String(cellValue ?? "")
        return values.includes(cellId)
      }
      if (/^\d{4}-\d{2}-\d{2}/.test(valueStr)) {
        const filterDate = new Date(valueStr)
        const cellDate = cellValue ? new Date(String(cellValue)) : null
        if (!isNaN(filterDate.getTime()) && cellDate && !isNaN(cellDate.getTime())) {
          return filterDate.toDateString() === cellDate.toDateString()
        }
      }
      return cellStrLower === valueStrLower
    }
    if (operator === "notEquals") {
      const values = valueStr
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
      if (values.length > 1) {
        const cellId = String(cellValue ?? "")
        return !values.includes(cellId)
      }
      if (/^\d{4}-\d{2}-\d{2}/.test(valueStr)) {
        const filterDate = new Date(valueStr)
        const cellDate = cellValue ? new Date(String(cellValue)) : null
        if (!isNaN(filterDate.getTime()) && cellDate && !isNaN(cellDate.getTime())) {
          return filterDate.toDateString() !== cellDate.toDateString()
        }
      }
      return cellStrLower !== valueStrLower
    }

    if (
      (operator === "lessThan" || operator === "greaterThan") &&
      /^\d{4}-\d{2}-\d{2}/.test(valueStr)
    ) {
      const filterDate = new Date(valueStr)
      const cellDate = cellValue ? new Date(String(cellValue)) : null
      if (cellDate && !isNaN(cellDate.getTime()) && !isNaN(filterDate.getTime())) {
        const filterTime = filterDate.getTime()
        const cellTime = cellDate.getTime()
        if (operator === "lessThan") return cellTime < filterTime
        return cellTime > filterTime
      }
    }

    const cellNum = parseFloat(String(cellValue))
    const valueNum = parseFloat(value)

    if (isNaN(cellNum) || isNaN(valueNum)) return true

    if (operator === "greaterThan") return cellNum > valueNum
    if (operator === "lessThan") return cellNum < valueNum
    if (operator === "greaterOrEqual") return cellNum >= valueNum
    if (operator === "lessOrEqual") return cellNum <= valueNum

    return true
  }
}
