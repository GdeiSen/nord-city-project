"use client"

import { IconFilter, IconPlus, IconTrash } from "@tabler/icons-react"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FilterValueEditor } from "./filter-value-editor"
import {
  getOperators,
  getOperatorLabel,
  createTextFilterConfig,
} from "./filter-config"
import type { FilterColumnConfig } from "./filter-config"
import type { ColumnFilter, FilterOperator } from "../types"
import type { FilterPickerData } from "@/hooks"

export interface AvailableFilterColumn {
  id: string
  label: string
  canFilter: boolean
  filterConfig: FilterColumnConfig
}

export interface DataTableFilterPanelProps {
  advancedFilters: ColumnFilter[]
  addFilter: () => void
  removeFilter: (index: number) => void
  updateFilter: (index: number, updates: Partial<ColumnFilter>) => void
  availableColumns: AvailableFilterColumn[]
  filterPickerData?: FilterPickerData
  openFilterPickerIndex: number | null
  onOpenFilterPickerIndexChange: (index: number | null) => void
}

export function DataTableFilterPanel({
  advancedFilters,
  addFilter,
  removeFilter,
  updateFilter,
  availableColumns,
  filterPickerData,
  openFilterPickerIndex,
  onOpenFilterPickerIndexChange,
}: DataTableFilterPanelProps) {
  const filterableColumns = availableColumns.filter((col) => col.canFilter)

  return (
    <div className="space-y-3">
      {advancedFilters.map((filter, index) => {
        const col = availableColumns.find((c) => c.id === filter.columnId)
        const config = col?.filterConfig ?? createTextFilterConfig()
        const operators = getOperators(config)
        const needsValue =
          filter.operator !== "isEmpty" && filter.operator !== "isNotEmpty"

        return (
          <div
            key={index}
            className="overflow-hidden rounded-md border bg-muted/30 py-1.5"
          >
            <div className="flex items-center justify-between gap-2 border-b px-3 py-2.5 pb-3">
              <Select
                value={filter.columnId}
                onValueChange={(v) => updateFilter(index, { columnId: v })}
              >
                <SelectTrigger size="sm" className="h-8 min-w-[140px] flex-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {filterableColumns.map((col) => (
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
                className="h-8 w-8 shrink-0 p-0"
                aria-label="Удалить фильтр"
              >
                <IconTrash className="h-4 w-4" />
              </Button>
            </div>

            <div className={`flex items-center gap-2 px-3 py-3 ${needsValue ? "border-b" : ""}`}>
              <Select
                value={filter.operator}
                onValueChange={(v) =>
                  updateFilter(index, { operator: v as FilterOperator })
                }
              >
                <SelectTrigger size="sm" className="h-8 min-w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {operators.map((op) => (
                    <SelectItem key={op} value={op}>
                      {getOperatorLabel(op)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {needsValue && (
              <div className="w-full px-3 py-2.5 pt-3">
                <FilterValueEditor
                  config={config}
                  operator={filter.operator}
                  value={filter.value}
                  dateFrom={filter.dateFrom}
                  dateTo={filter.dateTo}
                  onChange={(updates) => updateFilter(index, updates)}
                  filterPickerData={filterPickerData}
                  open={openFilterPickerIndex === index}
                  onOpenChange={(open) =>
                    onOpenFilterPickerIndexChange(open ? index : null)
                  }
                />
              </div>
            )}
          </div>
        )
      })}

      {advancedFilters.length === 0 ? (
        <Empty className="w-full py-6">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <IconFilter className="h-6 w-6" />
            </EmptyMedia>
            <EmptyTitle>Нет фильтров</EmptyTitle>
            <EmptyDescription>
              Добавьте фильтр, чтобы сузить результаты поиска.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button
              variant="outline"
              size="sm"
              onClick={addFilter}
              disabled={filterableColumns.length === 0}
            >
              <IconPlus className="h-4 w-4 mr-2" />
              Добавить фильтр
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <Button
          variant="outline"
          size="sm"
          onClick={addFilter}
          className="w-full"
          disabled={filterableColumns.length === 0}
        >
          <IconPlus className="h-4 w-4 mr-2" />
          Добавить фильтр
        </Button>
      )}
    </div>
  )
}
