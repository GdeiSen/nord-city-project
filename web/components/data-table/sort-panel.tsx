"use client"

import * as React from "react"
import {
  IconChevronDown,
  IconChevronUp,
  IconPlus,
  IconSortAscending,
  IconSortDescending,
  IconTrash,
} from "@tabler/icons-react"
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
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { ColumnSort } from "./types"

export interface DataTableSortPanelProps {
  advancedSorts: ColumnSort[]
  addSort: () => void
  removeSort: (index: number) => void
  updateSort: (index: number, updates: Partial<Pick<ColumnSort, "columnId" | "direction">>) => void
  moveSortUp: (index: number) => void
  moveSortDown: (index: number) => void
  getSortColumnOptions: (index: number) => { id: string; label: string }[]
  allSortColumnsUsed: boolean
  sortableColumns: { id: string; label: string }[]
  isMobile?: boolean
  className?: string
}

export function DataTableSortPanel({
  advancedSorts,
  addSort,
  removeSort,
  updateSort,
  moveSortUp,
  moveSortDown,
  getSortColumnOptions,
  allSortColumnsUsed,
  sortableColumns,
  isMobile = false,
  className,
}: DataTableSortPanelProps) {
  return (
    <ScrollArea>
      <div className={cn("space-y-3", isMobile && "pb-[50dvh]", className)}>
        {advancedSorts.map((sort, index) => {
          const columnOptions = getSortColumnOptions(index)
          return (
            <div
              key={sort.columnId ? `${sort.columnId}-${index}` : `empty-${index}`}
              className="overflow-hidden rounded-md border bg-muted/30 py-1.5"
            >
              <div className="flex items-center justify-between gap-2 border-b px-3 py-2.5 pb-3">
                <Select
                  value={sort.columnId || "__placeholder__"}
                  onValueChange={(v) =>
                    updateSort(index, {
                      columnId: v === "__placeholder__" ? "" : v,
                    })
                  }
                >
                  <SelectTrigger size="sm" className="h-8 min-w-[140px] flex-1">
                    <SelectValue
                      placeholder="Выберите столбец..."
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__placeholder__">
                      <span className="text-muted-foreground">
                        Выберите столбец...
                      </span>
                    </SelectItem>
                    {columnOptions.map((col) => (
                      <SelectItem key={col.id} value={col.id}>
                        {col.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeSort(index)}
                  className="h-8 w-8 shrink-0 p-0"
                  aria-label="Удалить сортировку"
                >
                  <IconTrash className="h-4 w-4" />
                </Button>
              </div>

              <div className="flex items-center gap-2 px-3 py-3">
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 shrink-0 p-0"
                    onClick={() => moveSortUp(index)}
                    disabled={index === 0}
                    aria-label="Переместить вверх"
                  >
                    <IconChevronUp className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 shrink-0 p-0"
                    onClick={() => moveSortDown(index)}
                    disabled={index === advancedSorts.length - 1}
                    aria-label="Переместить вниз"
                  >
                    <IconChevronDown className="h-4 w-4" />
                  </Button>
                </div>
                <Select
                  value={sort.direction}
                  onValueChange={(v) =>
                    updateSort(index, { direction: v as "asc" | "desc" })
                  }
                >
                  <SelectTrigger size="sm" className="h-8 min-w-[140px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="asc">
                      <div className="flex items-center gap-2">
                        <IconSortAscending className="h-4 w-4" />
                        По возрастанию
                      </div>
                    </SelectItem>
                    <SelectItem value="desc">
                      <div className="flex items-center gap-2">
                        <IconSortDescending className="h-4 w-4" />
                        По убыванию
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )
        })}

        {advancedSorts.length === 0 ? (
          sortableColumns.length === 0 ? (
            <Empty className="w-full py-6">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconSortAscending className="h-6 w-6" />
                </EmptyMedia>
                <EmptyTitle>Нет доступных столбцов</EmptyTitle>
                <EmptyDescription>
                  Нет столбцов, по которым можно настроить сортировку.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <Empty className="w-full py-6">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <IconSortAscending className="h-6 w-6" />
                </EmptyMedia>
                <EmptyTitle>Нет сортировок</EmptyTitle>
                <EmptyDescription>
                  Добавьте сортировку, чтобы упорядочить данные.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={addSort}
                  disabled={allSortColumnsUsed}
                >
                  <IconPlus className="h-4 w-4 mr-2" />
                  Добавить сортировку
                </Button>
              </EmptyContent>
            </Empty>
          )
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={addSort}
            className="w-full"
            disabled={allSortColumnsUsed || sortableColumns.length === 0}
          >
            <IconPlus className="h-4 w-4 mr-2" />
            Добавить сортировку
          </Button>
        )}
      </div>
    </ScrollArea>
  )
}
