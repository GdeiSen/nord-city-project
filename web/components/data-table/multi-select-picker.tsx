"use client"

import * as React from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { ScrollArea } from "@/components/ui/scroll-area"
import { IconChevronDown } from "@tabler/icons-react"
import { cn } from "@/lib/utils"

export interface MultiSelectOption {
  value: string
  label: string
}

export interface MultiSelectPickerProps {
  options: MultiSelectOption[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  emptyMessage?: string
  getOptionLabel?: (opt: MultiSelectOption) => string
  className?: string
}

export function MultiSelectPicker({
  options,
  value,
  onChange,
  placeholder = "Выберите...",
  emptyMessage = "Нет вариантов",
  getOptionLabel = (o) => o.label,
  className,
}: MultiSelectPickerProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const selectedIds = new Set(
    value ? value.split(",").map((s) => s.trim()).filter(Boolean) : []
  )
  const filtered = React.useMemo(() => {
    if (!search.trim()) return options
    const q = search.toLowerCase()
    return options.filter(
      (o) =>
        getOptionLabel(o).toLowerCase().includes(q) ||
        o.value.toLowerCase().includes(q)
    )
  }, [options, search, getOptionLabel])

  const displayLabels = options
    .filter((o) => selectedIds.has(o.value))
    .map(getOptionLabel)

  const toggle = (optValue: string) => {
    const next = new Set(selectedIds)
    if (next.has(optValue)) {
      next.delete(optValue)
    } else {
      next.add(optValue)
    }
    onChange(Array.from(next).join(","))
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          className={cn(
            "h-8 w-full justify-between font-normal py-1.5 px-3",
            !displayLabels.length && "text-muted-foreground",
            className
          )}
        >
            <span className="flex flex-1 flex-wrap gap-1.5 items-center min-w-0">
            {displayLabels.length > 0 ? (
              displayLabels.map((label, i) => (
                <span
                  key={i}
                  className="bg-muted text-foreground inline-flex items-center rounded px-1.5 py-1 text-xs font-medium whitespace-nowrap"
                >
                  {label}
                </span>
              ))
            ) : (
              <span>{placeholder}</span>
            )}
          </span>
          <IconChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <div className="p-2 border-b">
          <Input
            placeholder="Поиск..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8"
            autoFocus
            onKeyDown={(e) => e.stopPropagation()}
          />
        </div>
        <ScrollArea className="max-h-[min(200px,var(--radix-popper-available-height))]">
          <div className="p-1">
            {filtered.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">
                {emptyMessage}
              </div>
            ) : (
              filtered.map((opt) => (
                <label
                  key={opt.value}
                  className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent"
                >
                  <Checkbox
                    checked={selectedIds.has(opt.value)}
                    onCheckedChange={() => toggle(opt.value)}
                  />
                  <span>{getOptionLabel(opt)}</span>
                </label>
              ))
            )}
          </div>
        </ScrollArea>
      </PopoverContent>
    </Popover>
  )
}
