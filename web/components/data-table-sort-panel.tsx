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
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { ColumnSort } from "@/lib/data-table/types"

export interface DataTableSortPanelProps {
  advancedSorts: ColumnSort[]
  addSort: (columnId: string) => void
  removeSort: (columnId: string) => void
  updateSortDirection: (columnId: string, direction: "asc" | "desc") => void
  moveSortUp: (index: number) => void
  moveSortDown: (index: number) => void
  availableSortColumns: { id: string; label: string }[]
  isMobile?: boolean
  className?: string
}

export function DataTableSortPanel({
  advancedSorts,
  addSort,
  removeSort,
  updateSortDirection,
  moveSortUp,
  moveSortDown,
  availableSortColumns,
  isMobile = false,
  className,
}: DataTableSortPanelProps) {
  return (
    <ScrollArea>
      <div className={cn("space-y-4", className)}>
        {advancedSorts.length > 0 && (
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">
              Активные сортировки
            </Label>
            {advancedSorts.map((sort, index) => (
              <div
                key={sort.columnId}
                className="flex items-center gap-2 rounded-md border bg-muted/30 p-2"
              >
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
                <span className="flex-1 text-sm font-medium capitalize">
                  {sort.columnId}
                </span>
                <Select
                  value={sort.direction}
                  onValueChange={(v) =>
                    updateSortDirection(sort.columnId, v as "asc" | "desc")
                  }
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

        {availableSortColumns.length > 0 && (
          <div className={cn("space-y-2", isMobile && "pb-[50dvh]")}>
            <Label className="text-xs text-muted-foreground">
              Доступные столбцы
            </Label>
            {availableSortColumns.map((col) => (
              <div
                key={col.id}
                className="flex items-center justify-between rounded-md border p-2 transition-colors hover:bg-muted/50"
              >
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
          <div className="py-8 text-center text-sm text-muted-foreground">
            Нет доступных столбцов для сортировки
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
